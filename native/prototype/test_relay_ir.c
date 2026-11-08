/* Read-only IR path against synthetic evdev: a short IR Home is reported as IRHOME, a held one
 * stays with webOS, Home control Off suppresses it, IR is never grabbed or re-emitted, losing the
 * IR source keeps the relay running, and a triple IR Home releases (exit 27). */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <sys/ioctl.h>
#include <time.h>
#include <errno.h>
#include <string.h>
#include <stdarg.h>
#include <assert.h>
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
#include "relay.c"
#undef main
static uint64_t now;static int grabbed,ir_grabbed,step,irhome,lost,hangup,polls;static char pending;
/* One step per 100 ms poll. Code -1 = idle, 'D'/'E' = controller command on stdin.
 * Held Home (1.2 s, autorepeat): nothing. Short Home: IRHOME. Off: short Home ignored. On again.
 * 2.5 s idle so earlier taps do not count, then a quick triple Home: two IRHOME, then exit 27. */
static const int baseline[][2]={{773,1},{773,2},{773,2},{773,2},{773,2},{773,2},{773,2},{773,2},{773,2},{773,2},{773,2},{773,2},{773,0},
 {773,1},{773,0},
 {'D',0},{773,1},{773,0},{'E',0},
 {-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},{-1,0},
 {773,1},{773,0},{773,1},{773,0},{773,1},{773,0}};
#define LENGTH(a) ((int)(sizeof(a)/sizeof((a)[0])))
/* -2 = SYN_DROPPED, -3 = SYN_REPORT. No device interaction in these fixtures. */
static const int off_on[][2]={{773,1},{'D',0},{'E',0},{773,0}};
static const int overflow_taps[][2]={{773,1},{773,0},{773,1},{773,0},{-2,0},
 {773,1},{773,0},{-3,0},{773,1},{773,0}};
static const int overflow_press[][2]={{773,1},{-2,0},{773,0},{-3,0},{773,0},{773,1},{773,0}};
static const int overflow_emergency[][2]={{773,1},{773,0},{773,1},{773,0},{-2,0},{-3,0},
 {773,1},{773,0},{773,1},{773,0},{773,1},{773,0}};
static const int (*script)[2]=baseline;
static int steps=LENGTH(baseline);
/* event0 = M-RCU [0] (fd 10), event1 = M-RCU [1] (fd 11), event5 = LGE RCU (fd 12). */
static int fake_open(const char*p,int flags,...){(void)flags;if(strstr(p,"relay.lock"))return 3;if(strstr(p,"/blocked")||strstr(p,"/watchdog"))return 4;if(!strcmp(p,"/dev/input/event0"))return 10;if(!strcmp(p,"/dev/input/event1"))return 11;if(!strcmp(p,"/dev/input/event5"))return 12;errno=ENOENT;return -1;}
static int fake_close(int fd){(void)fd;return 0;}
static int fake_flock(int fd,int flags){(void)fd;(void)flags;return 0;}
static int fake_clock(clockid_t id,struct timespec*t){(void)id;t->tv_sec=now/1000;t->tv_nsec=(now%1000)*1000000;return 0;}
static int fake_ioctl(int fd,unsigned long request,...){
 va_list a;va_start(a,request);
 if(request==GRAB){int on=va_arg(a,int);va_end(a);if(fd==12)ir_grabbed=1;if(fd==10)grabbed=on;return 0;}
 void*b=va_arg(a,void*);va_end(a);
 if(request==NAME(256)){strcpy(b,fd==10?"LGE M-RCU - Builtin [0]":fd==11?"LGE M-RCU - Builtin [1]":"LGE RCU");return 0;}
 memset(b,0,request==_IOR('E',0x40,int[6])||request==_IOR('E',0x41,int[6])?sizeof(int)*6:256);return 0;
}
/* Each poll: heartbeat (or scripted command) on stdin plus the next scripted IR event. */
static int fake_poll(struct pollfd*p,nfds_t n,int timeout){(void)timeout;if(n==1){now+=50;p->revents=POLLIN;pending='P';return 1;}/* startup heartbeat */
 assert(n==3);now+=100;polls++;p[0].revents=0;p[1].revents=POLLIN;p[2].revents=0;pending='P';
 if(hangup){if(polls==1){assert(p[2].fd==12);p[2].revents=POLLHUP;}else{assert(p[2].fd==-1);stop=1;}return 1;}
 assert(p[2].fd==12);if(step>=steps){stop=1;return 1;}if(!grabbed)return 1;
 if(script[step][0]==-1){step++;return 1;}
 if(script[step][0]=='D'||script[step][0]=='E'){pending=(char)script[step][0];step++;return 1;}
 p[2].revents=POLLIN;return 1;}
static ssize_t fake_read(int fd,void*b,size_t size){(void)size;if(fd==0){*(char*)b=pending;return 1;}
 if(fd==12&&grabbed&&step<steps){struct ev e={0,0,script[step][0]<0?0:1,(uint16_t)(script[step][0]==-2?3:script[step][0]==-3?0:script[step][0]),script[step][1]};step++;memcpy(b,&e,sizeof e);return sizeof e;}errno=EAGAIN;return -1;}
static ssize_t fake_write(int fd,const void*b,size_t size){
 if(fd==1){if(size==7&&!memcmp(b,"IRHOME\n",7))irhome++;if(size==8&&!memcmp(b,"IR_LOST\n",8))lost++;}
 if(fd==11){const struct ev*e=b;for(size_t i=0;i<size/sizeof*e;i++)assert(e[i].code!=773);}/* only key releases at exit */
 return (ssize_t)size;}
int main(int argc,char**argv){
 char*args[]={"relay",NULL};
 if(argc==2){
  int expected=0,reason=0;
  if(!strcmp(argv[1],"off-on")){script=off_on;steps=LENGTH(off_on);}
  else if(!strcmp(argv[1],"overflow-taps")){script=overflow_taps;steps=LENGTH(overflow_taps);expected=3;}
  else if(!strcmp(argv[1],"overflow-press")){script=overflow_press;steps=LENGTH(overflow_press);expected=1;}
  else if(!strcmp(argv[1],"overflow-emergency")){script=overflow_emergency;steps=LENGTH(overflow_emergency);expected=4;reason=27;}
  else return 2;
  int actual=relay_main(1,args);
  printf("IR scenario %s: exit=%d IRHOME=%d\n",argv[1],actual,irhome);fflush(stdout);
  assert(actual==reason);assert(irhome==expected);assert(!ir_grabbed&&step==steps);
  return 0;
 }
 assert(relay_main(1,args)==27);
 assert(!ir_grabbed&&step==steps);
 assert(irhome==3);/* short Home once, then the first two taps of the triple; held and Off: none */
 stop=0;grabbed=0;polls=0;hangup=1;now=0;
 assert(relay_main(1,args)==0);
 assert(lost==1&&polls==2);
 printf("PASS: IR Home on short release only (held Home left to webOS, none while Off), never grabbed or re-emitted; lost IR keeps relay running; triple IR Home releases\n");
}
