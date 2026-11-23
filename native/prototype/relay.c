#define _GNU_SOURCE
#include "filter.h"
#include "startup.h"
#include "../app/lock.h"
#include <stdio.h>
#include <stdarg.h>
#include <sys/stat.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <time.h>
#include <errno.h>
#include <string.h>
#include "../app/stop-generation.h"
#define GRAB _IOW('E',0x90,int)
#define BIT(ev,len) _IOC(_IOC_READ,'E',0x20+(ev),len)
#define KEYSTATE(len) _IOC(_IOC_READ,'E',0x18,len)
#define NAME(len) _IOC(_IOC_READ,'E',0x06,len)
/* Same long-press threshold as the webOS compositor: a held IR Home stays with webOS. */
#define IR_LONG_PRESS_MS 1000
static volatile sig_atomic_t stop;
static int output_failed;
static const char *setup_generation;
static int generation_cancelled;
static int generation_current(void){char current[34];return !setup_generation||(cytv_generation_read(current)&&!strcmp(current,setup_generation));}
/* A stalled controller must never hold the evdev grab by blocking stdout.
 * Only change pipe/socket flags, never an inherited terminal's flags. */
static int prepare_output(void){
 struct stat st;if(fstat(1,&st)<0)return -1;
 if(S_ISFIFO(st.st_mode)||S_ISSOCK(st.st_mode)){
  int flags=fcntl(1,F_GETFL);if(flags<0||fcntl(1,F_SETFL,flags|O_NONBLOCK)<0)return -1;
 }
 return 0;
}
static int report(const char *format,...){
 char line[512];va_list args;va_start(args,format);int n=vsnprintf(line,sizeof line,format,args);va_end(args);
 if(output_failed||n<0||n>=(int)sizeof line||write(1,line,n)!=n){output_failed=1;return -1;}
 return 0;
}
static void stopped(int n){(void)n;stop=1;}
static uint64_t ms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return(uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static int removed(int error) { return error == ENODEV || error == ENXIO; }
/* Read the kernel name when evdev permissions hide a node. An inaccessible
 * unrelated input need not prevent waiting for a known M-RCU endpoint. */
static int other_device(int index, const char *wanted) {
  char path[80], name[256];
  snprintf(path, sizeof path, "/sys/class/input/event%d/device/name", index);
  int fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
  if (fd < 0)
    return 0;
  ssize_t n = read(fd, name, sizeof name);
  close(fd);
  if (n <= 1 || n == (ssize_t)sizeof name || name[n - 1] != '\n')
    return 0;
  name[n - 1] = 0;
  return strcmp(name, wanted) != 0;
}
enum { DEVICE_ABSENT=-1, LOOKUP_FAILED=-2, DEVICE_AMBIGUOUS=-3 };
static int find_device(const char *wanted, int flags, int *index) {
  int missing = DEVICE_ABSENT, match = -1;
  for (int i = 0; i < 32; i++) {
    char path[64], name[256] = {0};
    snprintf(path, sizeof path, "/dev/input/event%d", i);
    int fd = open(path, flags | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) {
      if (errno != ENOENT && !removed(errno) && !other_device(i, wanted))
        missing = LOOKUP_FAILED;
      continue;
    }
    int named = ioctl(fd, NAME(sizeof name), name);
    if (named < 0 && !removed(errno) && !other_device(i, wanted))
      missing = LOOKUP_FAILED;
    if (named >= 0 && !strcmp(name, wanted)) {
      if (match >= 0) {
        close(match);
        close(fd);
        return DEVICE_AMBIGUOUS;
      }
      *index = i;
      match = fd;
      continue;
    }
    close(fd);
  }
  return match >= 0 ? match : missing;
}
static int release_keys(int out) {
  unsigned char bits[256] = {0};
  if (ioctl(out, KEYSTATE(sizeof bits), bits) < 0)
    return -1;
  for (int k = 1; k < 2048; k++)
    if (bits[k / 8] & (1 << (k % 8))) {
      struct ev events[2] = {{0, 0, 1, k, 0}, {0, 0, 0, 0, 0}};
      ssize_t n = write(out, events, sizeof events);
      if (n != (ssize_t)sizeof events) {
        if (n >= 0)
          errno = EIO;
        return -1;
      }
    }
  return 0;
}
static void latch_stop(int reason) {
  if (!generation_cancelled && reason != 20)
    (void)cytv_generation_publish();
  const char *latch =
      reason == 20
          ? "/media/developer/apps/usr/palm/applications/com.local.nativehome/state/watchdog"
          : "/media/developer/apps/usr/palm/applications/com.local.nativehome/state/blocked";
  int flag = open(latch, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (flag >= 0) {
    write(flag, "stopped", 7);
    close(flag);
  }
}
/* A raced unplug is distinct from a capability mismatch or a failed ioctl. */
static int compatible(int in, int out) {
  unsigned char a[256], b[256];
  for (int type = 0; type <= 3; type++) {
    memset(a, 0, sizeof a);
    memset(b, 0, sizeof b);
    if (ioctl(in, BIT(type, sizeof a), a) < 0 || ioctl(out, BIT(type, sizeof b), b) < 0)
      return removed(errno) ? -1 : 0;
    if (memcmp(a, b, sizeof a))
      return 0;
  }
  for (int axis = 0; axis < 2; axis++) {
    int left[6], right[6];
    if (ioctl(in, _IOR('E', 0x40 + axis, int[6]), left) < 0 ||
        ioctl(out, _IOR('E', 0x40 + axis, int[6]), right) < 0)
      return removed(errno) ? -1 : 0;
    if (memcmp(left + 1, right + 1, 5 * sizeof(int)))
      return 0;
  }
  return 1;
}
static int startup_in, startup_out, home_disabled, allow_absent;
static uint64_t startup_ack;
static struct filter pending_keys;
enum { INPUT_REMOVED=33 };
/* Inspect already-queued edges without forwarding them. Anchor kernel event
 * spacing to the monotonic clock used by the running filter. */
static int queued_emergency(struct filter *filter,const struct ev *events,int count,int grabbed){
 if(!count)return 0;
 uint64_t now=ms();
 const struct ev *last=&events[count-1];
 uint64_t end=(uint64_t)last->sec*1000+last->usec/1000;
 for(int i=0;i<count;i++){
  const struct ev *e=&events[i];
  uint64_t t=(uint64_t)e->sec*1000+e->usec/1000;
  uint64_t ago=t<=end?end-t:0;
  if(!grabbed&&e->type==0&&e->code==3){memset(filter,0,sizeof *filter);continue;}
  if(filter_event(filter,e,grabbed?(ago<now?now-ago:0):t)==RELEASE)return 1;
 }
 return 0;
}
/* After the destination disappears, drain the readable source solely for the
 * escape gesture. A malformed or unbounded queue is a terminal input fault. */
static int loss_reason(int in,struct filter *f,const struct ev *pending,int count){
 if(queued_emergency(f,pending,count,1))return 27;
 for(int i=0;i<64;i++){
  struct ev tail[64];
  ssize_t n=read(in,tail,sizeof tail);
  if(n==0||(n<0&&(errno==EAGAIN||removed(errno))))return 25;
  if(n<0||n%sizeof tail[0])return 26;
  if(queued_emergency(f,tail,n/sizeof tail[0],1))return 27;
 }
 return 26;
}
static int startup_keys(void){
 if(!generation_current())return 29;
 if(stop)return 29;
 /* Discard pre-grab input: webOS already received it. Never replay an old OK. */
 struct ev events[64];
 for(int i=0;i<64;i++){
  ssize_t n=read(startup_in,events,sizeof events);
  if(n<0&&errno==EAGAIN)break;
  if(n<=0||n%sizeof events[0])return allow_absent&&(n==0||(n<0&&removed(errno)))?INPUT_REMOVED:13;
  if(allow_absent&&!home_disabled){
   /* These keys already reached webOS. Observe complete emergency gestures
    * across batches while another key is held, without replaying any input. */
   if(queued_emergency(&pending_keys,events,n/sizeof events[0],0))return 27;
  }
  if(i==63)return 14;
 }
 unsigned char held[256]={0};
 if(ioctl(startup_in,KEYSTATE(sizeof held),held)<0)return allow_absent&&removed(errno)?INPUT_REMOVED:13;
 for(int i=0;i<256;i++)if(held[i])return 14;
 if(ioctl(startup_out,KEYSTATE(sizeof held),held)<0)return allow_absent&&removed(errno)?INPUT_REMOVED:15;
 for(int i=0;i<256;i++)if(held[i])return 16;
 return 0;
}
static int pump_controller(int timeout){
 if(!generation_current())return 29;
 if(stop)return 29;
 if(ms()-startup_ack>2000)return 20;
 struct pollfd p={0,POLLIN,0};int r=poll(&p,1,timeout);
 if(r<0)return errno==EINTR?(stop?29:0):23;
 if(p.revents&(POLLHUP|POLLERR|POLLNVAL))return 24;
 if(p.revents&POLLIN){
  char b[64];ssize_t n=read(0,b,sizeof b);if(n<=0)return 24;
  startup_ack=ms();
  for(int i=0;i<n;i++){if(b[i]=='D'||b[i]=='E'){
    home_disabled=b[i]=='D';memset(&pending_keys,0,sizeof pending_keys);
   }if(b[i]=='Q')return 29;if(b[i]=='S')raise(SIGSTOP);}
  if(report("P\n")<0)return 30;
 }
 return stop?29:0;
}
static int startup_pump(void){return pump_controller(50);}
/* The source is grabbed. Every exit goes through key-up, ungrab and close. */
static int forward_input(int in,int out,int ir){
 struct filter f={0},irf={0};uint64_t last=ms(),irDown=0,irRetry=ir<0?last+1000:0;int reason=0,device_removed=0,irSyncLost=0;struct pollfd p[4]={{in,POLLIN,0},{0,POLLIN,0},{ir,POLLIN,0},{out,0,0}};
 f.disabled=irf.disabled=home_disabled;
 if(!generation_current()){reason=29;generation_cancelled=1;}else report("READY\n");
 while(!generation_cancelled&&!stop&&!output_failed){if(!generation_current()){reason=29;generation_cancelled=1;break;}uint64_t now=ms();if(now-last>2000){reason=20;break;}if(filter_timeout(&f,now)==OPEN_LG&&report("LGHOME\n")<0)break;
 if(irRetry&&now>=irRetry){
  int index;
  p[2].fd=find_device("LGE RCU",O_RDONLY,&index);
  irRetry=p[2].fd<0?now+1000:0;
 }
 int r=poll(p,4,50);if(r<0){if(errno==EINTR)continue;reason=23;break;}
 if(!generation_current()){reason=29;generation_cancelled=1;break;}
 if(p[1].revents&(POLLHUP|POLLERR)){reason=24;break;}
 if(p[1].revents&POLLIN){char b[64];ssize_t n=read(0,b,sizeof b);if(n<=0){reason=24;break;}last=ms();for(int i=0;i<n;i++){if(b[i]=='D'){f.disabled=irf.disabled=1;f.home=irf.home=0;f.count=irf.count=0;irDown=0;}if(b[i]=='E'){f.disabled=irf.disabled=0;f.home=irf.home=0;f.count=irf.count=0;irDown=0;}home_disabled=f.disabled;if(b[i]=='Q')stop=1;if(b[i]=='S')raise(SIGSTOP);}if(report("P\n")<0)break;}
 /* Losing the IR source only disables IR Home; M-RCU keeps working. */
 int lost_ir=p[2].fd>=0&&(p[2].revents&(POLLHUP|POLLERR|POLLNVAL));
 if(!lost_ir&&p[2].fd>=0&&p[2].revents&POLLIN){struct ev e[64];ssize_t n=read(p[2].fd,e,sizeof e);
  lost_ir=n==0||(n<0&&removed(errno));
  if(n>0&&n%sizeof e[0]==0)for(int i=0;i<n/(int)sizeof e[0];i++){
   if(!generation_current()){reason=29;generation_cancelled=1;break;}
   /* Overflow invalidates this passive source, not the grabbed M-RCU path.
    * Discard events through SYN_REPORT and require a new complete press. */
   if(e[i].type==0&&e[i].code==3){irf.home=irf.short_press=irf.count=0;irDown=0;irSyncLost=1;continue;}
   if(irSyncLost){if(e[i].type==0&&e[i].code==0)irSyncLost=0;continue;}
   if(e[i].type!=1)continue;
   uint64_t t=ms();
   if(filter_event(&irf,e+i,t)==RELEASE){reason=27;stop=1;break;}
   if(e[i].code!=773)continue;
   if(e[i].value==1&&!irDown)irDown=t;
   else if(e[i].value==0&&irDown){int tap=t-irDown<IR_LONG_PRESS_MS;irDown=0;if(tap&&!irf.disabled&&report("IRHOME\n")<0)break;}
  }
  if(generation_cancelled||stop||output_failed)break;
 }
 if(lost_ir){
  close(p[2].fd);p[2].fd=-1;irRetry=ms()+1000;
  memset(&irf,0,sizeof irf);irf.disabled=home_disabled;irDown=0;irSyncLost=0;
  if(report("IR_LOST\n")<0)break;
 }
 /* Also watch the destination when no forwarded key is being written. */
 short endpoint_events=p[0].revents|p[3].revents;
 if(endpoint_events&(POLLHUP|POLLERR|POLLNVAL)){
  device_removed=!!(endpoint_events&POLLHUP);
  reason=endpoint_events&POLLNVAL?23:25;
  if(reason==25&&(p[0].revents&POLLIN))reason=loss_reason(in,&f,NULL,0);
  break;
 }
 if(p[0].revents&POLLIN){struct ev e[64];ssize_t n=read(in,e,sizeof e);if(n<0&&errno==EAGAIN)continue;if(n<=0||n%sizeof e[0]){device_removed=n==0||(n<0&&removed(errno));reason=device_removed?25:26;break;}for(int i=0;i<n/(int)sizeof e[0];i++){if(!generation_current()){reason=29;generation_cancelled=1;break;}/* Observe Back without consuming or changing its events. */
if(e[i].type==1&&e[i].code==412){if(e[i].value==1)report("BACK_DOWN\n");if(e[i].value==0)report("BACK_UP\n");if(output_failed)break;}
int a=filter_event(&f,e+i,ms());if(a==RELEASE){reason=27;stop=1;break;}if(!generation_current()){reason=29;generation_cancelled=1;break;}if(a==OPEN_HOME){if(report("HOME\n")<0)break;continue;}if(a==DROP)continue;ssize_t written=write(out,e+i,sizeof e[i]);if(written!=sizeof e[i]){device_removed=written<0&&removed(errno);reason=device_removed?25:28;
 if(device_removed)reason=loss_reason(in,&f,e+i+1,n/sizeof e[0]-i-1);
 break;}}}
 if(reason)break;
 }
 if(output_failed)reason=30;
 if(stop&&reason==25)reason=0;
 /* Stop emitting before ungrabbing the physical remote. */
 if(reason!=25)latch_stop(reason);
 /* Attempt every cleanup step even if an earlier one fails. A failed release
  * must not masquerade as a watchdog exit eligible for automatic recovery. */
 int cleanup=0,release_error=0,ungrab_error=0;
 if(release_keys(out)<0){cleanup|=1;release_error=errno;}
 if(ioctl(in,GRAB,0)<0){cleanup|=2;ungrab_error=errno;}
 if(close(in)<0)cleanup|=4;
 if(close(out)<0)cleanup|=8;
 if(p[2].fd>=0)close(p[2].fd);
 /* One missing endpoint is sufficient when every surviving endpoint was
  * released successfully. Short writes, other errors and failed closes remain fatal. */
 if(stop&&reason==25){latch_stop(0);reason=0;}
 if(!generation_current()&&reason==25){generation_cancelled=1;latch_stop(29);reason=29;}
 if(reason==25&&(device_removed||removed(release_error)||removed(ungrab_error))&&
    !(cleanup&12)&&(!release_error||removed(release_error))&&(!ungrab_error||removed(ungrab_error)))return INPUT_REMOVED;
 if(cleanup){if(reason==25)latch_stop(31);report("CLEANUP_FAILED %d CAUSE %d\n",cleanup,reason);reason=31;}
 return reason;
}

static int attach_inputs(int reconnecting, int *source, int *destination, int *infrared) {
  int in_index = -1, out_index = -1;
  int out = find_device("LGE M-RCU - Builtin [1]", O_RDWR, &out_index);
  if (out < 0)
    return reconnecting && out != LOOKUP_FAILED ? INPUT_REMOVED : 10;
  int in = find_device("LGE M-RCU - Builtin [0]", O_RDONLY, &in_index);
  int reason = 0;
  if (in < 0)
    reason = reconnecting && in != LOOKUP_FAILED ? INPUT_REMOVED : 12;
  else {
    int match = compatible(in, out);
    if (match != 1)
      reason = reconnecting && match < 0 ? INPUT_REMOVED : 12;
  }
  if (!reason && (report("DEVICE /dev/input/event%d LGE M-RCU - Builtin [1]\n", out_index) < 0 ||
                  report("DEVICE /dev/input/event%d LGE M-RCU - Builtin [0]\n", in_index) < 0))
    reason = 30;
  int ir = -1;
  if (!reason) {
    int index;
    ir = find_device("LGE RCU", O_RDONLY, &index);
    if (ir >= 0 && report("DEVICE /dev/input/event%d LGE RCU\n", index) < 0)
      reason = 30;
  }
  if (!reason) {
    startup_in = in;
    startup_out = out;
    allow_absent = reconnecting;
    memset(&pending_keys, 0, sizeof pending_keys);
    if (!reconnecting)
      reason = wait_for_release(ms, startup_keys, startup_pump);
    else
      for (;;) {
        reason = startup_keys();
        if (reason != 14 && reason != 16)
          break;
        reason = startup_pump();
        if (reason)
          break;
      }
  }
  if (!reason && !generation_current())
    reason = 29;
  if (!reason && stop)
    reason = 29;
  if (!reason && ioctl(in, GRAB, 1) < 0)
    reason = reconnecting && removed(errno) ? INPUT_REMOVED : 17;
  if (reason) {
    if (reason == 27)
      latch_stop(reason);
    if (reason == 12)
      report("FAIL incompatible\n");
    if (reason == 14)
      report("FAIL source-held\n");
    if (reason == 16)
      report("FAIL destination-busy\n");
    if (reason == 17)
      report("FAIL grab\n");
    if (ir >= 0)
      close(ir);
    int failed = in >= 0 && close(in) < 0;
    if (close(out) < 0 || failed)
      return 31;
    return reason;
  }
  *source = in;
  *destination = out;
  *infrared = ir;
  return 0;
}

int main(int argc, char **argv) {
  setup_generation = NULL;
  generation_cancelled = 0;
  home_disabled = argc > 1 && !strcmp(argv[argc - 1], "--home-off");
  if (home_disabled)
    argc--;
  int boot = argc > 1 && !strcmp(argv[1], "boot");
  if (boot && argc != 2 && argc != 3)
    return 29;
  if ((boot && argc == 3) || (argc > 1 && !strcmp(argv[1], "setup"))) {
    if (argc != 3 || !cytv_generation_token(argv[2]))
      return 29;
    setup_generation = argv[2];
    if (!generation_current()) {
      generation_cancelled = 1;
      latch_stop(29);
      return 29;
    }
  }
  output_failed = 0;
  signal(SIGPIPE, SIG_IGN);
  signal(SIGTERM, stopped);
  signal(SIGINT, stopped);
  int cleaning = argc > 1 && !strcmp(argv[1], "cleanup");
  if (prepare_output() < 0) {
    if (!cleaning)
      return 30;
    output_failed = 1;
  }
  int lock = acquire_lock(
      "/media/developer/apps/usr/palm/applications/com.local.nativehome/state/relay.lock");
  if (lock < 0)
    return 18;
  if (cleaning) {
    int index, out = find_device("LGE M-RCU - Builtin [1]", O_RDWR, &index);
    if (out < 0)
      return 10;
    int result = release_keys(out);
    if (close(out) < 0)
      result = -1;
    return result ? 11 : 0;
  }
  int waiting = 0, reason = 0, in, out, ir;
  startup_ack = ms();
  for (;;) {
    if (waiting) {
      /* Service Stop and the watchdog between scans, also without a wake event. */
      uint64_t next_scan = ms() + 1000;
      do {
        reason = pump_controller(250);
      } while (!reason && ms() < next_scan);
      if (reason)
        break;
    }
    reason = attach_inputs(boot || waiting, &in, &out, &ir);
    if (!reason) {
      waiting = 0;
      reason = forward_input(in, out, ir);
    }
    if (reason != INPUT_REMOVED)
      break;
    if (!waiting) {
      if (report("INPUT_WAIT\n") < 0) {
        latch_stop(30);
        reason = 30;
        break;
      }
      startup_ack = ms();
      waiting = 1;
    }
  }
  if (waiting && (reason == 20 || reason == 30))
    latch_stop(reason);
  if (reason == 29 && !generation_current() && !generation_cancelled) {
    generation_cancelled = 1;
    latch_stop(29);
  }
  if (report("EXIT %d\n", reason) < 0 && reason != 31 && reason != 30) {
    latch_stop(30);
    reason = 30;
  }
  return reason;
}
