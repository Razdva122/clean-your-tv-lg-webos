/* Execute the actual relay against synthetic evdev, never a physical remote. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <sys/file.h>
#include <time.h>
#include <errno.h>
#include <string.h>
#include <stdarg.h>
#include <assert.h>
#include <sys/wait.h>
static char generation_directory[1024];
static int generation_entropy_failure;
static int generation_real_open(const char *name,int flags,...){if(generation_entropy_failure&&!strcmp(name,"/dev/urandom")){errno=EIO;return -1;}return open(name,flags);}
#define CYTV_GENERATION_DIRECTORY generation_directory
/* Keep generation storage real while substituting only TV evdev syscalls. */
#define open generation_real_open
#include "../app/stop-generation.h"
#undef open
static void new_generation(void){assert(cytv_generation_publish());}
static void prepare_generation(void){char tmp[]="/tmp/cytv-relay-generation-XXXXXX";assert(mkdtemp(tmp));assert(realpath(tmp,generation_directory));assert(chown(generation_directory,(uid_t)-1,getgid())==0);new_generation();}
static void remove_generation(void){char filename[1100];snprintf(filename,sizeof filename,"%s/stop-generation",generation_directory);assert(unlink(filename)==0);assert(rmdir(generation_directory)==0);}
/* These helpers use real pipe I/O, outside the evdev syscall doubles. */
static int controller_close(int fd){return close(fd);}
static ssize_t controller_write(const void*b,size_t size){return write(1,b,size);}
static int output_fault,pipe_reader;
static void break_output(void){
 if(output_fault==2){close(pipe_reader);return;}
 int flags=fcntl(1,F_GETFL);assert(flags>=0);assert(fcntl(1,F_SETFL,flags|O_NONBLOCK)==0);
 char b[512]={0};while(write(1,b,sizeof b)>0){}
 while(write(1,b,1)>0){}
 assert(errno==EAGAIN);assert(fcntl(1,F_SETFL,flags)==0);
}
#ifndef _IOC_READ
#define _IOC_READ IOC_OUT
#endif
static int fake_open(const char*,int,...),fake_close(int),fake_ioctl(int,unsigned long,...),fake_poll(struct pollfd*,nfds_t,int),fake_clock(clockid_t,struct timespec*),fake_flock(int,int);
static ssize_t fake_read(int,void*,size_t),fake_write(int,const void*,size_t);
#define open fake_open
#define close fake_close
#define ioctl fake_ioctl
#define poll fake_poll
#define clock_gettime fake_clock
#define flock fake_flock
#define read fake_read
#define write fake_write
#define main relay_main
#ifndef RELAY_SOURCE
#define RELAY_SOURCE "relay.c"
#endif
#include RELAY_SOURCE
#undef main
static uint64_t now;
static int scenario,grabbed,held,input_event,fault,cleanup_mode,release_checks;
static char recorded_stop_path[1100];
static int waiting;
static int suspend_hint,suspend_cancel,suspend_expired,power_polls,suspend_stop;
static int released,ungrabbed,closed_input,closed_output,blocked_marker,watchdog_marker;
/* A previously grabbed pair disappears. The replacement uses different event
 * numbers and appears in two stages, more than a minute later. */
enum recovery_case {
  BOTH_GONE,
  READ_GONE,
  WRITE_GONE,
  OUTPUT_HUP,
  HUP_TRIPLE,
  WRITE_TRIPLE,
  WRITE_QUEUED_TRIPLE,
  HUP_CLEAN,
  HOME_OFF,
  WAIT_STOP,
  WAIT_GENERATION,
  BAD_REPLACEMENT,
  DUPLICATE,
  BOOT_WAIT,
  BOOT_OFF,
  BOOT_HELD_TRIPLE,
  BOOT_DENIED,
  FIRST_ABSENT
};
static int reconnect_test, recovery_case, grabs, input_waits, ready_reports, home_reports;
static int destination_down, destination_up, forwarded_home, startup_event, wait_pings;
static int replacement_step, original_step, scans, pregrab_eof, reads_this_poll;
static int boot_case(void) { return recovery_case >= BOOT_WAIT && recovery_case <= BOOT_DENIED; }
static int is_reconnect_fd(int fd) { return fd >= 40 && fd <= 44; }
static int reopen_device(const char *name) {
  if (recovery_case == BOOT_DENIED && !strcmp(name, "/dev/input/event1")) {
    errno = EACCES;
    return -1;
  }
  if (!strcmp(name, "/dev/input/event0")) {
    scans++;
    if (!input_waits && recovery_case < BOOT_WAIT)
      return 40;
  }
  if (!strcmp(name, "/dev/input/event1") && !input_waits && recovery_case < BOOT_WAIT)
    return 41;
  if (recovery_case==DUPLICATE && !strcmp(name,"/dev/input/event10") && now>=65000 && now<69000)return 44;
  if (!strcmp(name, "/dev/input/event8") && now >= 60000)
    return 43;
  if (!strcmp(name, "/dev/input/event9") && now >= 65000)
    return 42;
  errno = ENOENT;
  return -1;
}
static int reconnect_ioctl(int fd, unsigned long request, va_list args) {
  if (request == GRAB) {
    int on = va_arg(args, int);
    assert(fd == 40 || fd == 42);
    if (on) {
      grabs++;
      if(fd==42&&recovery_case==DUPLICATE)assert(now>=69000);
      if (fd == 42)
        assert(now >= 65000 && !startup_event);
    } else if (fd == 40 && recovery_case != WRITE_GONE && recovery_case != OUTPUT_HUP &&
               recovery_case != HUP_CLEAN) {
      errno = ENODEV;
      return -1;
    }
    return 0;
  }
  void *buffer = va_arg(args, void *);
  if (request == NAME(256)) {
    strcpy(buffer, (fd == 40 || fd == 42 || fd == 44) ? "LGE M-RCU - Builtin [0]" : "LGE M-RCU - Builtin [1]");
    return 0;
  }
  if (request == KEYSTATE(256)) {
    memset(buffer, 0, 256);
    if (fd == 42 && (recovery_case == BOOT_WAIT || recovery_case == BOOT_HELD_TRIPLE) && !grabs &&
        now < 72500)
      ((unsigned char *)buffer)[1] = 1;
    if (fd == 41 && grabs && recovery_case != READ_GONE && recovery_case != HUP_CLEAN) {
      errno = ENODEV;
      return -1;
    }
    if (fd == 41 && destination_down > destination_up)
      ((unsigned char *)buffer)[103 / 8] |= 1 << (103 % 8);
    return 0;
  }
  size_t size = request == _IOR('E', 0x40, int[6]) || request == _IOR('E', 0x41, int[6])
                    ? sizeof(int) * 6
                    : 256;
  memset(buffer, 0, size);
  if (fd == 42 && recovery_case == BAD_REPLACEMENT)
    ((unsigned char *)buffer)[1] = 1;
  return 0;
}
static int reconnect_poll(struct pollfd *p, nfds_t n, int timeout) {
  assert(now < 79000);
  if (n == 1) {
    now += timeout;
    p[0].revents = POLLIN;
    if (input_waits && now >= 3000 && recovery_case == WAIT_GENERATION)
      new_generation();
    return 1;
  }
  assert(n == 4);
  now += (recovery_case==HUP_TRIPLE||recovery_case==WRITE_TRIPLE||recovery_case==WRITE_QUEUED_TRIPLE)?500:100;
  p[2].revents = 0;
  p[1].revents = POLLIN;
  p[3].revents = 0;
  if (p[0].fd == 40) {
    original_step++;reads_this_poll=0;
    if (original_step > 1 && (recovery_case == OUTPUT_HUP || recovery_case == HUP_TRIPLE)) {
      p[0].revents = recovery_case==HUP_TRIPLE?POLLIN:0;
      p[3].revents = POLLHUP;
      assert(original_step < 5);
    } else
      p[0].revents = original_step == 1 || recovery_case == READ_GONE || (recovery_case == WRITE_GONE || recovery_case==WRITE_TRIPLE||recovery_case==WRITE_QUEUED_TRIPLE)
                         ? POLLIN
                         : POLLHUP;
  } else {
    assert(p[0].fd == 42);
    p[0].revents = POLLIN;
    replacement_step++;
  }
  return 1;
}
static ssize_t reconnect_read(int fd, void *buffer) {
  if (fd == 0) {
    char command = 'P';
    if (input_waits) {
      wait_pings++;
      if (recovery_case == HOME_OFF && grabs == 1)
        command = 'D';
      if ((recovery_case == HOME_OFF || recovery_case == BOOT_OFF) && replacement_step == 4)
        command = 'Q';
      if (recovery_case == WAIT_STOP && now >= 3000)
        command = 'Q';
    }
    *(char *)buffer = command;
    return 1;
  }
  struct ev ev = {0, 0, 1, 103, 1};
  if (fd == 40 && grabs == 1) {
    reads_this_poll++;
    if(original_step>1&&recovery_case==WRITE_QUEUED_TRIPLE&&reads_this_poll==2){
      struct ev tap[6];
      for(int i=0;i<6;i++)tap[i]=(struct ev){0,(uint32_t)(i*55000),1,773,!(i%2)};
      memcpy(buffer,tap,sizeof tap);return sizeof tap;
    }
    if(reads_this_poll>1){errno=EAGAIN;return -1;}
    if(original_step>1&&(recovery_case==HUP_TRIPLE||recovery_case==WRITE_TRIPLE)&&startup_event){
      struct ev events[7];int first=recovery_case==WRITE_TRIPLE;
      events[0]=ev;
      for(int i=0;i<6;i++)events[first+i]=(struct ev){0,(uint32_t)(i*55000),1,773,!(i%2)};
      memcpy(buffer,events,(first+6)*sizeof ev);startup_event=0;return (first+6)*sizeof ev;
    }
    if(original_step>1&&(recovery_case==HUP_TRIPLE||recovery_case==WRITE_TRIPLE)){errno=EAGAIN;return -1;}
    if (original_step > 1 && recovery_case == READ_GONE) {
      errno = ENODEV;
      return -1;
    }
  } else if (fd == 42 && recovery_case == BOOT_HELD_TRIPLE && !grabs && now >= 71000 &&
             startup_event) {
    struct ev taps[6];
    for (int i = 0; i < 6; i++) {
      taps[i] = (struct ev){70, (uint32_t)(i * 100000), 1, 773, !(i % 2)};
    }
    memcpy(buffer, taps, sizeof taps);
    startup_event = 0;
    return sizeof taps;
  } else if (fd == 42 && recovery_case == BOOT_WAIT && !grabs && pregrab_eof) {
    pregrab_eof = 0;
    return 0;
  } else if (fd == 42 && recovery_case != BOOT_HELD_TRIPLE && grabs == (boot_case() ? 0 : 1) &&
             startup_event) {
    startup_event = 0;
  } else if (fd == 42 && grabs == (boot_case() ? 1 : 2)) {
    ev.code = 773;
    ev.value = !!(replacement_step % 2);
  } else {
    errno = EAGAIN;
    return -1;
  }
  memcpy(buffer, &ev, sizeof ev);
  return sizeof ev;
}
static ssize_t reconnect_write(int fd, const void *buffer, size_t size) {
  if (fd == 1) {
    if (size == 11 && !memcmp(buffer, "INPUT_WAIT\n", 11))
      input_waits++;
    if (size == 6 && !memcmp(buffer, "READY\n", 6))
      ready_reports++;
    if (size == 5 && !memcmp(buffer, "HOME\n", 5))
      home_reports++;
  } else if (fd == 41 || fd == 43) {
    const struct ev *ev = buffer;
    if (fd == 41 && original_step > 1 && (recovery_case == WRITE_GONE || recovery_case==WRITE_TRIPLE || recovery_case==WRITE_QUEUED_TRIPLE)) {
      errno = ENODEV;
      return -1;
    }
    if (ev->code == 103) {
      if (ev->value)
        destination_down++;
      else
        destination_up++;
    } else if (ev->code == 773)
      forwarded_home++;
    else
      assert(0);
  }
  return (ssize_t)size;
}
static int fake_open(const char *p, int flags, ...) {
  (void)flags;
  if (strstr(p, "relay.lock"))
    return 3;
  if (strstr(p, "/watchdog")) {
    watchdog_marker++;
    return 4;
  }
  if (strstr(p, "/blocked")) {
    blocked_marker++;
    return 4;
  }
  if (reconnect_test)
    return reopen_device(p);
  if (!strcmp(p, "/dev/input/event0"))
    return grabbed ? 20 : 10;
  if (!strcmp(p, "/dev/input/event1"))
    return grabbed ? 21 : 11;
  errno = ENOENT;
  return -1;
}
static int fake_close(int fd){if(fd==10&&grabbed){closed_input++;if((fault==4||fault==7)){errno=EIO;return -1;}}if(fd==11&&(grabbed||cleanup_mode)){closed_output++;if(output_fault==6)break_output();if((fault==5||fault==7||fault==10)){errno=EIO;return -1;}}return 0;}
static int fake_flock(int fd,int flags){(void)fd;(void)flags;return 0;}
static int fake_clock(clockid_t id,struct timespec*t){(void)id;t->tv_sec=now/1000;t->tv_nsec=(now%1000)*1000000;return 0;}
static int fake_ioctl(int fd,unsigned long request,...){
 va_list args;va_start(args,request);
 if(reconnect_test&&is_reconnect_fd(fd)){int result=reconnect_ioctl(fd,request,args);va_end(args);return result;}
 if(request==GRAB){int on=va_arg(args,int);if(on){grabbed=1;held=1;if(scenario==6)new_generation();if(output_fault==1||output_fault==2)break_output();}else{assert(release_checks);ungrabbed++;if(fault==3||fault==7||fault>=8){va_end(args);errno=(fault==8||fault==11)?ENODEV:EIO;return -1;}}va_end(args);return 0;}
 void*b=va_arg(args,void*);va_end(args);
 if(request==NAME(256)){strcpy(b,fd==10||fd==20?"LGE M-RCU - Builtin [0]":"LGE M-RCU - Builtin [1]");return 0;}
 if(request==KEYSTATE(256)){memset(b,0,256);if(scenario==5&&fd==10&&!now)((unsigned char*)b)[1]=1;if(fd==11&&(grabbed||cleanup_mode)){release_checks++;if(fault==11)raise(SIGTERM);if(fault==1||fault==7||fault>=8){errno=ENODEV;return -1;}}if(held&&fd==11)((unsigned char*)b)[103/8]|=1<<(103%8);return 0;}
 if(request==_IOR('E',0x40,int[6])||request==_IOR('E',0x41,int[6])){memset(b,0,sizeof(int)*6);return 0;}
 memset(b,0,256);return 0;
}
static int fake_poll(struct pollfd*p,nfds_t n,int timeout){if(reconnect_test)return reconnect_poll(p,n,timeout);if(n==1){now+=timeout;p[0].revents=POLLIN;power_polls++;return 1;}(void)timeout;now+=(scenario==2||scenario==4||scenario>=6)?100:2101;p[0].revents=0;p[1].revents=0;if(scenario==7)new_generation();if(scenario==8)p[0].revents=POLLIN;if(scenario==1)stop=1;if(scenario==2){p[0].revents=POLLIN;p[1].revents=POLLIN;}if(scenario==3||scenario==5)p[0].revents=POLLHUP;if(scenario==4){power_polls++;if(power_polls<=(suspend_expired?162:suspend_cancel?2:1))p[1].revents=POLLIN;else {p[0].revents=POLLHUP;if(suspend_stop)p[1].revents=POLLIN;}}if(output_fault>=3&&output_fault<=5&&grabbed){break_output();if(output_fault>=4)p[1].revents=0;}return 1;}
static ssize_t fake_read(int fd,void*b,size_t size){(void)size;if(reconnect_test)return reconnect_read(fd,b);if(fd==0){*(char*)b=waiting?'Q':scenario==5?'T':scenario==4&&power_polls>1&&suspend_stop?'Q':scenario==4&&power_polls==1&&suspend_hint?'T':scenario==4&&power_polls==2&&suspend_cancel?'R':'P';return 1;}if(fd==10&&scenario==8&&grabbed){new_generation();struct ev e={0,0,1,30,1};memcpy(b,&e,sizeof e);return sizeof e;}if(fd==10&&scenario==2&&grabbed){struct ev e={0,0,1,output_fault==4?412:773,input_event++%2==0};memcpy(b,&e,sizeof e);return sizeof e;}errno=EAGAIN;return -1;}
static ssize_t fake_write(int fd,const void*b,size_t size){
 if(reconnect_test)return reconnect_write(fd,b,size);
 if(fd==4&&recorded_stop_path[0]){
  FILE *file=fopen(recorded_stop_path,"wb");assert(file);
  assert(fwrite(b,1,size,file)==size&&fclose(file)==0);
 }
 if(fd==1){if(size==11&&!memcmp(b,"INPUT_WAIT\n",11))waiting=1;return controller_write(b,size);}
 if(fd==11){
  const struct ev*e=b;
  assert(e[0].type==1&&e[0].code==103&&e[0].value==0);
  assert(!ungrabbed);
  if(fault==2){errno=EIO;return -1;}
  if(fault==6)return (ssize_t)size-1;
  released++;
  held=0;
 }
 return (ssize_t)size;
}
static void reset(void){waiting=0;power_polls=0;now=0;stop=0;input_event=0;grabbed=held=released=ungrabbed=closed_input=closed_output=blocked_marker=watchdog_marker=cleanup_mode=release_checks=0;}
/* Modes: healthy pipe, full READY, EPIPE, full P, full Back, full Home, full EXIT. */
static void output_backpressure(int mode,int cleanup_fault){
 fflush(stdout);int channel[2];assert(pipe(channel)==0);pid_t child=fork();assert(child>=0);
 if(child==0){
  assert(dup2(channel[1],1)==1);controller_close(channel[1]);pipe_reader=channel[0];
  reset();scenario=mode>=3&&mode<=5?2:0;fault=cleanup_fault;output_fault=mode;
  char*args[]={"relay",NULL};int reason=relay_main(1,args);
  assert(reason==(cleanup_fault?31:mode?30:20));
  if(!cleanup_fault)assert(released==1&&held==0);
  assert(release_checks==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
  assert(blocked_marker==(mode!=0)&&watchdog_marker==(mode==0||mode==6));_exit(0);
 }
 controller_close(channel[1]);if(mode==2)controller_close(channel[0]);
 int status=0,done=0;for(int i=0;i<300;i++){if(waitpid(child,&status,WNOHANG)==child){done=1;break;}usleep(10000);}
 if(!done){kill(child,SIGKILL);waitpid(child,&status,0);fprintf(stderr,"FAIL: full controller stdout stranded relay beyond watchdog/cleanup bound\n");}
 if(mode!=2){controller_close(channel[0]);}
 assert(done&&WIFEXITED(status)&&WEXITSTATUS(status)==0);
}
static void closed_output_cleanup(int cleanup_fault){
 fflush(stdout);pid_t child=fork();assert(child>=0);
 if(child==0){
  reset();assert(controller_close(1)==0);
  char*args[]={"relay","cleanup",NULL};int reason=relay_main(1,args);
  assert(reason==30&&grabbed==0&&release_checks==0);
  reset();fault=cleanup_fault;cleanup_mode=held=1;reason=relay_main(2,args);
  assert(reason==(cleanup_fault?11:0));
  assert(release_checks==1&&closed_output==1&&ungrabbed==0);
  if(!cleanup_fault){assert(released==1&&held==0);}
  _exit(0);
 }
 int status;assert(waitpid(child,&status,0)==child);
 assert(WIFEXITED(status)&&WEXITSTATUS(status)==0);
}
static void simulate_triple_home_after_boot(int expanded){
 char generation[1100],before[34],after[34],marker[8]={0};
 assert(cytv_generation_read(before));
 snprintf(generation,sizeof generation,"%s/stop-generation",generation_directory);
 if(expanded){
  assert(chmod(generation_directory,0777)==0);
  assert(chmod(generation,0777)==0);
 }
 snprintf(recorded_stop_path,sizeof recorded_stop_path,"%s/blocked",generation_directory);
 reset();scenario=2;fault=output_fault=0;
 char *args[]={"relay",NULL};
 assert(relay_main(1,args)==27);
 assert(input_event==6&&blocked_marker==1&&watchdog_marker==0);
 assert(released==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
 FILE *file=fopen(recorded_stop_path,"rb");assert(file);
 assert(fread(marker,1,sizeof marker,file)==7&&fclose(file)==0);
 assert(strcmp(marker,"stopped")==0&&unlink(recorded_stop_path)==0);
 recorded_stop_path[0]=0;
 if(expanded){
  /* Native setup refuses the expanded token until the checked JS repair. */
  assert(!cytv_generation_read(after));
  assert(chmod(generation_directory,0700)==0);
  assert(chmod(generation,0664)==0);
 }else assert(cytv_generation_read(after)&&after[0]=='S'&&strcmp(before,after));
}
int main(void){
 prepare_generation();
 for (recovery_case = BOTH_GONE; recovery_case <= FIRST_ABSENT; recovery_case++) {
   reset();
   reconnect_test = 1;
   grabs = input_waits = ready_reports = home_reports = 0;
   destination_down = destination_up = forwarded_home = wait_pings = 0;
   pregrab_eof = startup_event = 1;
   replacement_step = original_step = scans = 0;
   char baseline[34], after[34];
   assert(cytv_generation_read(baseline));
   char *args[] = {"relay", boot_case() ? "boot" : "setup", baseline, "--home-off", NULL};
   int result = relay_main(recovery_case == BOOT_OFF ? 4 : 3, args);
   if(recovery_case==HUP_TRIPLE||recovery_case==WRITE_TRIPLE||recovery_case==WRITE_QUEUED_TRIPLE){
      assert(result==31&&blocked_marker==1&&grabs==1&&input_waits==0);
      reconnect_test=0;continue;
    }
    if (recovery_case == BOOT_DENIED || recovery_case == FIRST_ABSENT) {
     assert(result == 10 && grabs == 0 && ready_reports == 0 && input_waits == 0);
     reconnect_test = 0;
     continue;
   }
   assert(input_waits == 1 && wait_pings > 0);
   if (recovery_case == WAIT_STOP || recovery_case == WAIT_GENERATION) {
     assert(result == 29 && grabs == 1 && ready_reports == 1 && now < 65000);
   } else if (recovery_case == BOOT_HELD_TRIPLE) {
     assert(result == 27 && blocked_marker == 1 && grabs == 0 && home_reports == 0);
   } else if (recovery_case == HOME_OFF || recovery_case == BOOT_OFF) {
     assert(result == 0 && grabs == (boot_case() ? 1 : 2) && ready_reports == grabs &&
            home_reports == 0 && forwarded_home >= 3);
   } else if (recovery_case == BAD_REPLACEMENT) {
     assert(result == 12 && grabs == 1 && ready_reports == 1);
   } else {
     assert(result == 27 && grabs == (recovery_case == BOOT_WAIT ? 1 : 2) &&
            ready_reports == grabs && home_reports == 3);
     assert(scans < 1000 && now >= 65000 && forwarded_home == 0);
     assert(blocked_marker == 1 && watchdog_marker == 0);
     if (recovery_case == READ_GONE)
       assert(destination_down == 1 && destination_up == 1);
   }
   assert(cytv_generation_read(after));
   reconnect_test = 0;
 }
 simulate_triple_home_after_boot(0);
 simulate_triple_home_after_boot(1);
 for(scenario=1;scenario<=2;scenario++){
  reset();fault=output_fault=0;generation_entropy_failure=1;
  char*args[]={"relay",NULL};assert(relay_main(1,args)==(scenario==1?0:27));
  assert(released==1&&ungrabbed==1&&closed_input==1&&closed_output==1&&blocked_marker==1);
  char invalid[34];assert(!cytv_generation_read(invalid));
  generation_entropy_failure=0;new_generation();
 }
 for(scenario=6;scenario<=8;scenario++){
  reset();fault=output_fault=0;char baseline[34],latest[34];assert(cytv_generation_read(baseline));
  char*args[]={"relay","setup",baseline,NULL};assert(relay_main(3,args)==29);
  assert(grabbed&&released==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
  assert(blocked_marker==1&&watchdog_marker==0);assert(cytv_generation_read(latest)&&strcmp(baseline,latest));
 }
 closed_output_cleanup(0);closed_output_cleanup(2);closed_output_cleanup(5);
 for(int mode=0;mode<=6;mode++){output_backpressure(mode,0);}
 output_backpressure(1,7);
 for(scenario=0;scenario<4;scenario++){
  reset();fault=0;
  char baseline[34],latest[34];assert(cytv_generation_read(baseline));
  char*args[]={"relay",NULL};int reason=relay_main(1,args);
  assert(reason==(scenario==0?20:scenario==1?0:scenario==2?27:29));
  assert(watchdog_marker==(scenario==0));assert(blocked_marker==(scenario==1||scenario==2));
  assert(released==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
  assert(cytv_generation_read(latest));
  assert((strcmp(baseline,latest)==0)==(scenario==0||scenario==3));
 }
 for(scenario=0;scenario<4;scenario++)for(fault=1;fault<=7;fault++){
  reset();char*args[]={"relay",NULL};int reason=relay_main(1,args);
  assert(reason==(scenario==3&&fault==1?29:31));assert(release_checks==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
  assert(watchdog_marker==(scenario==0));assert(blocked_marker==(scenario!=0&&!(scenario==3&&fault==1)));
 }
 for(int hint=0;hint<5;hint++)for(int fail=8;fail<=11;fail++){
  reset();scenario=4;fault=fail;suspend_hint=hint!=0;suspend_cancel=hint==2;suspend_expired=hint==3;suspend_stop=hint==4;
  char*args[]={"relay",NULL};int reason=relay_main(1,args);
  int expected=fail==8&&hint!=4?29:31;
  assert(reason==expected);assert(blocked_marker==(expected==31)&&watchdog_marker==0);
  assert(release_checks==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
 }
 reset();scenario=5;fault=8;
 {char*args[]={"relay",NULL};assert(relay_main(1,args)==29);assert(blocked_marker==0&&closed_input==1&&closed_output==1);}
 for(fault=0;fault<=7;fault++){
  if(fault==3||fault==4)continue; /* Cleanup mode has no input grab/FD. */
  reset();cleanup_mode=held=1;char*args[]={"relay","cleanup",NULL};int reason=relay_main(2,args);
  assert(reason==(fault?11:0));assert(release_checks==1&&closed_output==1&&ungrabbed==0);
 }
 remove_generation();
 puts("PASS: boot and live evdev recovery, changed event numbers, Home Off, held keys, triple Home, Stop, watchdog and cleanup races");
}
