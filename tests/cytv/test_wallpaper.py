import errno
import base64
import importlib.util
import hashlib
import http.server
import sys
import time
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
HAS_BUILD_DEPS = importlib.util.find_spec('PySide6') is not None and importlib.util.find_spec('imageio_ffmpeg') is not None
if HAS_BUILD_DEPS:
    from PySide6.QtGui import QImage, QColor
    from cytv import wallpaper as w

@unittest.skipUnless(HAS_BUILD_DEPS, 'Optional desktop build dependencies are not installed')
class WallpaperTests(unittest.TestCase):
    def test_destination_and_pin_rejected_before_network(self):
        for host in ['localhost','127.0.0.1','169.254.1.2','100.64.0.1','8.8.8.8','192.168.1.1/path','::1',3232235778]:
            with self.subTest(host=host), self.assertRaises(ValueError): w.destination(host,'123456')
        for pin in ['12345','１２３４５６','1234567','12345a']:
            with self.assertRaises(ValueError): w.destination('192.168.1.2',pin)
        self.assertEqual(w.destination('192.168.1.2','123456'), '192.168.1.2')

    def test_real_preparation_source_quality_and_js_decoder(self):
        with tempfile.TemporaryDirectory() as tmp:
            for width,height,qualities in [(640,480,[]),(1920,1080,['1080p']),(3840,2160,['4k','1080p'])]:
                source=Path(tmp)/'source.png'; image=QImage(width,height,QImage.Format.Format_RGB32); image.fill(QColor('#426070')); image.save(str(source))
                result=w.prepare(source)
                self.assertEqual([v['quality'] for v in result['variants']],qualities)
                self.assertEqual(set(result), {'schemaVersion','kind','source','image','variants'})
                self.assertEqual((result['kind'],result['source']),('wallpaper','cytv'))
                for asset in [result['image']]+result['variants']:
                    data=base64.b64decode(asset['data'],validate=True)
                    self.assertEqual(len(data),asset['size']); self.assertEqual(hashlib.sha256(data).hexdigest(),asset['sha256'])
                    self.assertLessEqual(len(data),w.IMAGE_LIMIT if asset is result['image'] else (w.UHD_LIMIT if asset['quality']=='4k' else w.FHD_LIMIT))
                    if asset is not result['image']:
                        video=Path(tmp)/'video.mp4'; video.write_bytes(data)
                        info=json.loads(subprocess.check_output(['node','-e',"const d=require('./launcher/theme-data.js'); console.log(JSON.stringify(d.videoInfo(require('fs').readFileSync(process.argv[1]))))",str(video)],text=True))
                        self.assertEqual((info['width'],info['height']),(asset['width'],asset['height']))
            cropped=w.prepare(source,crop=(0,0,1920,1080))
            self.assertEqual([v['quality'] for v in cropped['variants']],['1080p'])

    def test_cancel_preparation(self):
        event=threading.Event(); event.set()
        with self.assertRaises(w.Cancelled): w.prepare('unused.png',cancel=event)

    def test_reject_bad_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'image.png'; file.write_bytes(b'not a PNG')
            with self.assertRaises(ValueError): w.load_image(file)

    def test_http_preflight_redirect_wrong_protocol_and_accepted_not_applied(self):
        class Reply:
            def __init__(self,status,body): self.status=status; self.body=body
            def read(self,n): return self.body[:n]
        class Connection:
            replies=[]; requests=[]
            def __init__(self,*a,**kw): self.sock=None
            def request(self,*a,**kw): self.requests.append((a,kw))
            def getresponse(self): return self.replies.pop(0)
            def close(self): pass
        envelope={'schemaVersion':1,'kind':'wallpaper','source':'cytv','image':{},'variants':[]}
        with patch.object(w.http.client,'HTTPConnection',Connection):
            for status,body in [(302,b'{}'),(200,b'{"wallpaperProtocol":2}'),(200,b'x'*65537)]:
                Connection.replies=[Reply(status,body)]; Connection.requests=[]
                with self.assertRaises(ValueError): w.upload('192.168.1.2','123456',envelope)
                self.assertEqual(len(Connection.requests),1)
            Connection.replies=[Reply(200,b'{"wallpaperProtocol":1}'),Reply(202,b'{}')]; Connection.requests=[]
            self.assertEqual(w.upload('192.168.1.2','123456',envelope),'received')
            self.assertEqual([r[0][:2] for r in Connection.requests],[('GET','/v1/wallpaper-capabilities'),('POST','/v1/wallpaper')])
            self.assertEqual(Connection.requests[0][1]['headers']['X-CYTV-PIN'],'123456')
            Connection.replies=[Reply(200,b'{"wallpaperProtocol":1}'),Reply(500,b'{}')]
            with self.assertRaises(ValueError): w.upload('192.168.1.2','123456',envelope)

    def test_real_http_preflight_and_post_no_redirect(self):
        requests=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                requests.append((self.command,self.path,self.headers.get('X-CYTV-PIN')))
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers(); self.wfile.write(b'{"wallpaperProtocol":1}')
            def do_POST(self):
                requests.append((self.command,self.path,self.headers.get('X-CYTV-PIN')))
                size=int(self.headers['Content-Length']); self.server.received=json.loads(self.rfile.read(size))
                self.send_response(202); self.end_headers(); self.wfile.write(b'{"received":true}')
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        original=w.http.client.HTTPConnection
        def connect(host,port,timeout):
            self.assertEqual((host,port),('192.168.1.2',8879))
            return original('127.0.0.1',server.server_port,timeout=timeout)
        envelope={'schemaVersion':1,'kind':'wallpaper','source':'cytv','image':{},'variants':[]}
        try:
            with patch.object(w.http.client,'HTTPConnection',side_effect=connect):
                self.assertEqual(w.upload('192.168.1.2','123456',envelope),'received')
            self.assertEqual(server.received,envelope)
            self.assertEqual(requests,[('GET','/v1/wallpaper-capabilities','123456'),('POST','/v1/wallpaper','123456')])
        finally: server.shutdown(); server.server_close(); thread.join()

    def test_cancel_terminates_running_preparation_process(self):
        cancel=threading.Event()
        with tempfile.TemporaryDirectory() as tmp:
            pidfile=Path(tmp)/'pid'
            command=[sys.executable,'-c',"import os,time,pathlib; pathlib.Path(__import__('sys').argv[1]).write_text(str(os.getpid())); time.sleep(60)",str(pidfile)]
            failures=[]
            def run():
                try: w.run_ffmpeg(command,cancel)
                except w.Cancelled: failures.append('cancelled')
            processes=[]
            original_popen=subprocess.Popen
            def spawn(*args,**kwargs):
                process=original_popen(*args,**kwargs); processes.append(process); return process
            process_patch=patch.object(w.subprocess,'Popen',side_effect=spawn); process_patch.start(); self.addCleanup(process_patch.stop)
            thread=threading.Thread(target=run); thread.start()
            deadline=time.monotonic()+3
            while not pidfile.exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(pidfile.exists())
            cancel.set(); thread.join(3)
            self.assertFalse(thread.is_alive()); self.assertEqual(failures,['cancelled'])
            self.assertEqual(len(processes),1); self.assertIsNotNone(processes[0].poll())

    def test_cancel_interrupts_real_waiting_http_response(self):
        arrived=threading.Event(); release=threading.Event(); cancel=threading.Event(); failures=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self): arrived.set(); release.wait(3)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server_thread=threading.Thread(target=server.serve_forever,daemon=True); server_thread.start()
        original=w.http.client.HTTPConnection
        def connect(host,port,timeout): return original('127.0.0.1',server.server_port,timeout=timeout)
        def transfer():
            try: w.upload('192.168.1.2','123456',{},cancel=cancel)
            except w.Cancelled: failures.append('cancelled')
        try:
            with patch.object(w.http.client,'HTTPConnection',side_effect=connect):
                thread=threading.Thread(target=transfer); thread.start(); self.assertTrue(arrived.wait(2)); cancel.set(); thread.join(2)
            self.assertFalse(thread.is_alive()); self.assertEqual(failures,['cancelled'])
        finally: release.set(); server.shutdown(); server.server_close(); server_thread.join()

    def test_cancel_interrupts_connection_close_response_body(self):
        self.check_partial_response_body(cancelled=True)

    def test_absolute_deadline_interrupts_connection_close_response_body(self):
        self.check_partial_response_body(cancelled=False)

    def check_partial_response_body(self,cancelled):
        arrived=threading.Event(); release=threading.Event(); cancel=threading.Event(); failures=[]; clock_offset=[0]
        real_monotonic=time.monotonic
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                self.send_response(200); self.send_header('Connection','close'); self.send_header('Content-Length','22'); self.end_headers()
                self.wfile.write(b'{'); self.wfile.flush(); arrived.set(); release.wait(3)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        server_thread=threading.Thread(target=server.serve_forever,daemon=True); server_thread.start()
        original=w.http.client.HTTPConnection
        def connect(host,port,timeout): return original('127.0.0.1',server.server_port,timeout=timeout)
        def transfer():
            try: w.upload('192.168.1.2','123456',{},cancel=cancel)
            except (w.Cancelled,ValueError) as error: failures.append(error)
        try:
            with patch.object(w.http.client,'HTTPConnection',side_effect=connect),patch.object(w.time,'monotonic',side_effect=lambda:real_monotonic()+clock_offset[0]):
                thread=threading.Thread(target=transfer); thread.start(); self.assertTrue(arrived.wait(2)); time.sleep(.05)
                if cancelled: cancel.set()
                else: clock_offset[0]=21
                thread.join(.8)
                self.assertFalse(thread.is_alive(),'Closing response detached its socket from HTTPConnection; cancellation must interrupt body reads')
            self.assertEqual(len(failures),1)
            self.assertIsInstance(failures[0],w.Cancelled if cancelled else ValueError)
        finally: release.set(); server.shutdown(); server.server_close(); server_thread.join(); thread.join(4)

    def test_cancel_during_nonblocking_connect_closes_owned_socket(self):
        started=threading.Event(); cancel=threading.Event(); failures=[]
        class ConnectingSocket:
            closed=False
            def setblocking(self,flag): pass
            def connect_ex(self,address): started.set(); return errno.EINPROGRESS
            def close(self): self.closed=True
        transport=ConnectingSocket()
        def pending(*args): time.sleep(.01); return [],[],[]
        def connect():
            try: w.connect_ipv4(('192.168.1.2',8879),time.monotonic()+20,cancel)
            except w.Cancelled: failures.append('cancelled')
        with patch.object(w.socket,'socket',return_value=transport),patch.object(w.select,'select',side_effect=pending):
            thread=threading.Thread(target=connect); thread.start(); self.assertTrue(started.wait(1)); cancel.set(); thread.join(.4)
        self.assertFalse(thread.is_alive()); self.assertEqual(failures,['cancelled']); self.assertTrue(transport.closed)

    def test_post_reconnect_uses_preflight_remaining_absolute_deadline(self):
        offset=[0]; real_monotonic=time.monotonic; transports=[]
        class ConnectingSocket:
            def __init__(self,immediate): self.immediate=immediate; self.closed=False
            def setblocking(self,flag): pass
            def connect_ex(self,address): return 0 if self.immediate else errno.EINPROGRESS
            def settimeout(self,timeout): self.timeout=timeout
            def close(self): self.closed=True
            def shutdown(self,*args): pass
        def create_socket(*args):
            transport=ConnectingSocket(not transports); transports.append(transport); return transport
        class Response:
            status=200
            def read(self,n): offset[0]=19.9; return b'{"wallpaperProtocol":1}'
        class Connection:
            def __init__(self,*args,**kwargs): self.sock=None
            def request(self,*args,**kwargs): self.sock=self._create_connection(('192.168.1.2',8879),20,None)
            def getresponse(self): self.sock=None; return Response()
            def close(self): pass
        def pending(*args): time.sleep(.01); return [],[],[]
        start=real_monotonic()
        with patch.object(w.http.client,'HTTPConnection',Connection),patch.object(w.socket,'socket',side_effect=create_socket),patch.object(w.select,'select',side_effect=pending),patch.object(w.time,'monotonic',side_effect=lambda:real_monotonic()+offset[0]):
            with self.assertRaisesRegex(ValueError,'Transfer timed out'):
                w.upload('192.168.1.2','123456',{})
        self.assertLess(real_monotonic()-start,.5); self.assertEqual(len(transports),2); self.assertTrue(transports[1].closed)
