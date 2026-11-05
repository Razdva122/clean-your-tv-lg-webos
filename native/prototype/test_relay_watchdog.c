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
static int released,ungrabbed,closed_input,closed_output,blocked_marker,watchdog_marker;
static int fake_open(const char*p,int flags,...){(void)flags;if(strstr(p,"relay.lock"))return 3;if(strstr(p,"/watchdog")){watchdog_marker++;return 4;}if(strstr(p,"/blocked")){blocked_marker++;return 4;}if(strstr(p,"event0"))return 10;if(strstr(p,"event1"))return 11;errno=ENOENT;return -1;}
static int fake_close(int fd){if(fd==10&&grabbed){closed_input++;if((fault==4||fault==7)){errno=EIO;return -1;}}if(fd==11&&(grabbed||cleanup_mode)){closed_output++;if(output_fault==6)break_output();if((fault==5||fault==7)){errno=EIO;return -1;}}return 0;}
static int fake_flock(int fd,int flags){(void)fd;(void)flags;return 0;}
static int fake_clock(clockid_t id,struct timespec*t){(void)id;t->tv_sec=now/1000;t->tv_nsec=(now%1000)*1000000;return 0;}
static int fake_ioctl(int fd,unsigned long request,...){
 va_list args;va_start(args,request);
 if(request==GRAB){int on=va_arg(args,int);if(on){grabbed=1;held=1;if(output_fault==1||output_fault==2)break_output();}else{assert(release_checks);ungrabbed++;if(fault==3||fault==7){va_end(args);errno=EIO;return -1;}}va_end(args);return 0;}
 void*b=va_arg(args,void*);va_end(args);
 if(request==NAME(256)){strcpy(b,fd==10?"LGE M-RCU - Builtin [0]":"LGE M-RCU - Builtin [1]");return 0;}
 if(request==KEYSTATE(256)){memset(b,0,256);if(fd==11&&(grabbed||cleanup_mode)){release_checks++;if(fault==1||fault==7){errno=EIO;return -1;}}if(held&&fd==11)((unsigned char*)b)[103/8]|=1<<(103%8);return 0;}
 if(request==_IOR('E',0x40,int[6])||request==_IOR('E',0x41,int[6])){memset(b,0,sizeof(int)*6);return 0;}
 memset(b,0,256);return 0;
}
static int fake_poll(struct pollfd*p,nfds_t n,int timeout){(void)n;(void)timeout;now+=scenario==2?100:2101;p[0].revents=0;p[1].revents=0;if(scenario==1)stop=1;if(scenario==2){p[0].revents=POLLIN;p[1].revents=POLLIN;}if(scenario==3)p[0].revents=POLLHUP;if(output_fault>=3&&output_fault<=5&&grabbed){break_output();if(output_fault>=4)p[1].revents=0;}return 1;}
static ssize_t fake_read(int fd,void*b,size_t size){(void)size;if(fd==0){*(char*)b='P';return 1;}if(fd==10&&scenario==2&&grabbed){struct ev e={0,0,1,output_fault==4?412:773,input_event++%2==0};memcpy(b,&e,sizeof e);return sizeof e;}errno=EAGAIN;return -1;}
static ssize_t fake_write(int fd,const void*b,size_t size){if(fd==1)return controller_write(b,size);if(fd==11){const struct ev*e=b;assert(e[0].type==1&&e[0].code==103&&e[0].value==0);assert(!ungrabbed);if(fault==2){errno=EIO;return -1;}if(fault==6)return (ssize_t)size-1;released++;held=0;}return (ssize_t)size;}
static void reset(void){now=0;stop=0;input_event=0;grabbed=held=released=ungrabbed=closed_input=closed_output=blocked_marker=watchdog_marker=cleanup_mode=release_checks=0;}
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
int main(void){
 closed_output_cleanup(0);closed_output_cleanup(2);closed_output_cleanup(5);
 for(int mode=0;mode<=6;mode++){output_backpressure(mode,0);}
 output_backpressure(1,7);
 for(scenario=0;scenario<4;scenario++){
  reset();fault=0;
  char*args[]={"relay",NULL};int reason=relay_main(1,args);
  assert(reason==(scenario==0?20:scenario==1?0:scenario==2?27:25));
  assert(watchdog_marker==(scenario==0));assert(blocked_marker==(scenario==1||scenario==2));
  assert(released==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
 }
 for(scenario=0;scenario<4;scenario++)for(fault=1;fault<=7;fault++){
  reset();char*args[]={"relay",NULL};int reason=relay_main(1,args);
  assert(reason==31);assert(release_checks==1&&ungrabbed==1&&closed_input==1&&closed_output==1);
  assert(watchdog_marker==(scenario==0));assert(blocked_marker==(scenario!=0));
 }
 for(fault=0;fault<=7;fault++){
  if(fault==3||fault==4)continue; /* Cleanup mode has no input grab/FD. */
  reset();cleanup_mode=held=1;char*args[]={"relay","cleanup",NULL};int reason=relay_main(2,args);
  assert(reason==(fault?11:0));assert(release_checks==1&&closed_output==1&&ungrabbed==0);
 }
 puts("PASS: watchdog/emergency cleanup attempts every release step and reports failures; cleanup command checks close");
}
