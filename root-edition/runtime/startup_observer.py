"""Guardian-owned native preference events; no polling or launch fallback."""
import json
import os
import select
import subprocess
import threading
import time
import startup_policy as policy

SUBSCRIPTIONS={
    'foreground':('com.webos.applicationManager/getForegroundAppInfo',{'subscribe':True}),
    'input':('com.webos.settingsservice/getSystemSettings',{'category':'general',
        'keys':['lastInputApp','lastInputAppType','homeAutoLaunch'],'subscribe':True})}


class Observer:
    def __init__(self,transaction,boot,stop):
        self.transaction=transaction;self.boot=boot;self.stop=stop
        self.lock=threading.Lock();self.revision=0;self.pending=None;self.worker=None
        self.ready=set();self.closed=False;self.foreground=None;self.home_auto=None

    def cancel(self):
        with self.lock:self.revision+=1;self.pending=None

    def canceled(self,revision):
        with self.lock:return self.closed or self.stop.is_set() or revision!=self.revision

    def request(self,event):
        with self.lock:
            if self.closed or self.stop.is_set():return
            self.revision+=1;self.pending=(event,self.revision)
            if self.worker is None:
                self.worker=threading.Thread(target=self.work,daemon=True);self.worker.start()

    def work(self):
        while True:
            with self.lock:
                if self.closed or self.stop.is_set() or self.pending is None:
                    self.worker=None;return
                event,revision=self.pending;self.pending=None
            policy.reconcile(self.transaction,self.boot,
                lambda revision=revision:self.canceled(revision),event=event)

    def feed(self,name,value):
        initial=name not in self.ready
        if (name not in SUBSCRIPTIONS or not isinstance(value,dict)
                or value.get('returnValue') is not True
                or value.get('subscribed') is False
                or initial and value.get('subscribed') is not True):
            self.cancel();raise ValueError('Invalid native subscription')
        event='foreground';root_echo=False
        if name=='foreground':
            app=value.get('appId')
            if app is not None and (not isinstance(app,str) or len(app)>128):
                self.cancel();raise ValueError('Invalid foreground snapshot')
            self.foreground=app
        else:
            settings=value.get('settings')
            if not isinstance(settings,dict):
                self.cancel();raise ValueError('Invalid native settings snapshot')
            for key in ('lastInputApp','lastInputAppType','homeAutoLaunch'):
                if key in settings and (not isinstance(settings[key],str) or len(settings[key])>128):
                    self.cancel();raise ValueError('Invalid native setting')
            preference=settings.get('homeAutoLaunch',self.home_auto)
            event='policy' if (self.home_auto is not None and preference!=self.home_auto or initial and preference=='off') else 'input'
            self.home_auto=preference
            root_echo=settings.get('lastInputApp')==policy.d.CANDIDATE and event!='policy'
        self.ready.add(name)
        if len(self.ready)!=len(SUBSCRIPTIONS):return
        if self.home_auto=='off':
            # A routing hint only: reconcile rereads the real setting. Keep a
            # withdrawal wake-up across blank frames and delayed own echoes.
            event='policy'
        elif root_echo and not initial:
            return  # Do not discard a newer protected-app withdrawal.
        elif initial:
            event='foreground'
        if not self.foreground and event!='policy':
            self.cancel();return  # A blank frame cannot authorize a selection.
        self.request(event)

    def close(self,withdraw=True):
        with self.lock:
            self.closed=True;self.revision+=1;self.pending=None;worker=self.worker
        if worker is not None and worker is not threading.current_thread():worker.join(timeout=2)
        # Losing eligibility while otherwise healthy must not strand a proactive
        # preference over a later protected app. Ordinary Home recovery owns stop.
        if withdraw and not self.stop.is_set():
            policy.reconcile(self.transaction,self.boot,withdraw=True,event='disconnect')

    def run(self):
        children={};buffers={};opened=time.monotonic()
        try:
            for name,(uri,payload) in SUBSCRIPTIONS.items():
                children[name]=subprocess.Popen(['/usr/bin/luna-send','-i','luna://'+uri,json.dumps(payload)],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,close_fds=True)
                buffers[name]=''
            while not self.stop.is_set():
                from intent_runtime import boot_identity
                if boot_identity()!=self.boot:break
                if len(self.ready)!=len(SUBSCRIPTIONS) and time.monotonic()-opened>5:break
                ready=select.select([p.stdout for p in children.values()],[],[],.25)[0]
                if not ready:
                    if any(p.poll() is not None for p in children.values()):break
                    continue
                for name,child in children.items():
                    if child.stdout not in ready:continue
                    chunk=os.read(child.stdout.fileno(),4096)
                    if not chunk:raise ValueError('Native subscription ended')
                    buffers[name]+=chunk.decode('utf8')
                    if len(buffers[name])>8192:raise ValueError('Oversized native snapshot')
                    while buffers[name].strip():
                        buffers[name]=buffers[name].lstrip()
                        try:value,end=json.JSONDecoder().raw_decode(buffers[name])
                        except ValueError:
                            self.cancel();break
                        buffers[name]=buffers[name][end:];self.feed(name,value)
        except (OSError,ValueError,UnicodeError):pass
        finally:
            self.close()
            for child in children.values():
                if child.poll() is None:child.terminate()
                try:child.communicate(timeout=1)
                except subprocess.TimeoutExpired:child.kill();child.communicate(timeout=1)


def observe(transaction,boot,stop):
    Observer(transaction,boot,stop).run()
