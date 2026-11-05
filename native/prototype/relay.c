#define _GNU_SOURCE
#include "filter.h"
#include "startup.h"
#include "../app/lock.h"
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
#define GRAB _IOW('E',0x90,int)
#define BIT(ev,len) _IOC(_IOC_READ,'E',0x20+(ev),len)
#define KEYSTATE(len) _IOC(_IOC_READ,'E',0x18,len)
#define NAME(len) _IOC(_IOC_READ,'E',0x06,len)
static volatile sig_atomic_t stop;
static void stopped(int n){(void)n;stop=1;}
static uint64_t ms(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return(uint64_t)t.tv_sec*1000+t.tv_nsec/1000000;}
static int find_device(const char *wanted,int flags){for(int i=0;i<32;i++){char p[64],name[256]={0};snprintf(p,sizeof p,"/dev/input/event%d",i);int fd=open(p,flags|O_NONBLOCK|O_CLOEXEC);if(fd<0)continue;if(ioctl(fd,NAME(sizeof name),name)>=0&&!strcmp(name,wanted)){printf("DEVICE %s %s\n",p,name);return fd;}close(fd);}return -1;}
static int release_keys(int out){unsigned char bits[256]={0};if(ioctl(out,KEYSTATE(sizeof bits),bits)<0)return -1;for(int k=1;k<2048;k++)if(bits[k/8]&(1<<(k%8))){struct ev e[2]={{0,0,1,k,0},{0,0,0,0,0}};if(write(out,e,sizeof e)!=sizeof e)return -1;}return 0;}
static void latch_stop(int reason){const char *latch=reason==20?"/media/developer/apps/usr/palm/applications/com.local.nativehome/state/watchdog":"/media/developer/apps/usr/palm/applications/com.local.nativehome/state/blocked";int flag=open(latch,O_WRONLY|O_CREAT|O_TRUNC,0644);if(flag>=0){write(flag,"stopped",7);close(flag);}}
static int compatible(int in,int out){unsigned char a[256],b[256];int types[]={0,1,2,3};for(int i=0;i<4;i++){memset(a,0,sizeof a);memset(b,0,sizeof b);if(ioctl(in,BIT(types[i],sizeof a),a)<0||ioctl(out,BIT(types[i],sizeof b),b)<0||memcmp(a,b,sizeof a))return 0;}for(int axis=0;axis<2;axis++){int a[6],b[6];if(ioctl(in,_IOR('E',0x40+axis,int[6]),a)<0||ioctl(out,_IOR('E',0x40+axis,int[6]),b)<0||memcmp(a+1,b+1,5*sizeof(int)))return 0;}return 1;}
static int startup_in,startup_out;
static uint64_t startup_ack;
static int startup_keys(void){
 if(stop)return 29;
 /* Discard pre-grab input: webOS already received it. Never replay an old OK. */
 struct ev events[64];
 for(int i=0;i<64;i++){
  ssize_t n=read(startup_in,events,sizeof events);
  if(n<0&&errno==EAGAIN)break;
  if(n<=0||n%sizeof events[0])return 13;
  if(i==63)return 14;
 }
 unsigned char held[256]={0};
 if(ioctl(startup_in,KEYSTATE(sizeof held),held)<0)return 13;
 for(int i=0;i<256;i++)if(held[i])return 14;
 if(ioctl(startup_out,KEYSTATE(sizeof held),held)<0)return 15;
 for(int i=0;i<256;i++)if(held[i])return 16;
 return 0;
}
static int startup_pump(void){
 if(stop)return 29;
 if(ms()-startup_ack>2000)return 20;
 struct pollfd p={0,POLLIN,0};int r=poll(&p,1,50);
 if(r<0)return errno==EINTR?(stop?29:0):23;
 if(p.revents&(POLLHUP|POLLERR|POLLNVAL))return 24;
 if(p.revents&POLLIN){
  char b[64];ssize_t n=read(0,b,sizeof b);if(n<=0)return 24;
  startup_ack=ms();
  for(int i=0;i<n;i++){if(b[i]=='Q')return 29;if(b[i]=='S')raise(SIGSTOP);}
  puts("P");
 }
 return stop?29:0;
}
int main(int argc,char**argv){
 setvbuf(stdout,NULL,_IOLBF,0);signal(SIGPIPE,SIG_IGN);signal(SIGTERM,stopped);signal(SIGINT,stopped);
 int lock=acquire_lock("/media/developer/apps/usr/palm/applications/com.local.nativehome/state/relay.lock");if(lock<0)return 18;
 int out=find_device("LGE M-RCU - Builtin [1]",O_RDWR);if(out<0)return 10;
 if(argc>1&&!strcmp(argv[1],"cleanup")){int r=release_keys(out);if(close(out)<0)r=-1;return r?11:0;}
 int in=find_device("LGE M-RCU - Builtin [0]",O_RDONLY);if(in<0||!compatible(in,out)){puts("FAIL incompatible");return 12;}
 startup_in=in;startup_out=out;startup_ack=ms();
 int startup_reason=wait_for_release(ms,startup_keys,startup_pump);
 if(startup_reason){if(startup_reason==14)puts("FAIL source-held");if(startup_reason==16)puts("FAIL destination-busy");return startup_reason;}
 if(ioctl(in,GRAB,1)<0){puts("FAIL grab");return 17;}
 puts("READY");struct filter f={0};uint64_t last=ms();int reason=0;struct pollfd p[2]={{in,POLLIN,0},{0,POLLIN,0}};
 while(!stop){uint64_t now=ms();if(now-last>2000){reason=20;break;}if(filter_timeout(&f,now)==OPEN_LG)puts("LGHOME");
 int r=poll(p,2,50);if(r<0){if(errno==EINTR)continue;reason=23;break;}
 if(p[1].revents&(POLLHUP|POLLERR)){reason=24;break;}
 if(p[1].revents&POLLIN){char b[64];ssize_t n=read(0,b,sizeof b);if(n<=0){reason=24;break;}last=ms();for(int i=0;i<n;i++){if(b[i]=='D'){f.disabled=1;f.home=0;f.count=0;}if(b[i]=='E'){f.disabled=0;f.home=0;f.count=0;}if(b[i]=='Q')stop=1;if(b[i]=='S')raise(SIGSTOP);}puts("P");}
 if(p[0].revents&(POLLHUP|POLLERR)){reason=25;break;}
 if(p[0].revents&POLLIN){struct ev e[64];ssize_t n=read(in,e,sizeof e);if(n<0&&errno==EAGAIN)continue;if(n<=0||n%sizeof e[0]){reason=26;break;}for(int i=0;i<n/(int)sizeof e[0];i++){/* Observe Back without consuming or changing its events. */
if(e[i].type==1&&e[i].code==412){if(e[i].value==1)puts("BACK_DOWN");if(e[i].value==0)puts("BACK_UP");}
int a=filter_event(&f,e+i,ms());if(a==RELEASE){reason=27;stop=1;break;}if(a==OPEN_HOME){puts("HOME");continue;}if(a==DROP)continue;if(write(out,e+i,sizeof e[i])!=sizeof e[i]){reason=28;stop=1;break;}}}
 }
 /* Stop emitting before ungrabbing the physical remote. */
 if(reason!=25)latch_stop(reason);
 /* Attempt every cleanup step even if an earlier one fails. A failed release
  * must not masquerade as a watchdog exit eligible for automatic recovery. */
 int cleanup=0;
 if(release_keys(out)<0)cleanup|=1;
 if(ioctl(in,GRAB,0)<0)cleanup|=2;
 if(close(in)<0)cleanup|=4;
 if(close(out)<0)cleanup|=8;
 if(cleanup){if(reason==25)latch_stop(31);printf("CLEANUP_FAILED %d CAUSE %d\n",cleanup,reason);reason=31;}
 printf("EXIT %d\n",reason);return reason;
}
