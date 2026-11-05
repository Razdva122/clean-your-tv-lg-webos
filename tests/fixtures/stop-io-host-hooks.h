/* Explicit HOST build only: actual C operation/wire fault controls. */
#include <fcntl.h>
#include <stdio.h>
#include <time.h>
#include <sys/stat.h>
static int host_write(int fd,const unsigned char *p,size_t len){while(len){ssize_t n=write(fd,p,len);if(n<0&&errno==EINTR)continue;if(n<=0)return 0;p+=n;len-=(size_t)n;}return 1;}
static int host_fault(const char *want){char text[80]={0};int fd=open(CYTV_STOP_IO_HOOK_ROOT "/fault",O_RDONLY);if(fd<0)return 0;ssize_t n=read(fd,text,sizeof(text)-1);close(fd);return n>=0&&!strcmp(text,want);}
static void host_hold(void){int fd=open(CYTV_STOP_IO_HOOK_ROOT "/entered",O_WRONLY|O_CREAT|O_EXCL,0600);if(fd>=0)close(fd);alarm(20);while(access(CYTV_STOP_IO_HOOK_ROOT "/release",F_OK)<0){struct timespec delay={0,10000000};nanosleep(&delay,NULL);}alarm(0);}
int cytv_private_test_hook(enum cytv_private_test_point p,int fd){
 (void)fd;
 if(p==CYTV_PRIVATE_TEST_APPEND_WRITTEN&&access(CYTV_STOP_IO_HOOK_ROOT "/hold-append",F_OK)==0)host_hold();
 if(p==CYTV_PRIVATE_TEST_APPEND_FILE_SYNC&&host_fault("fail-append-sync")){errno=EIO;return -1;}
 if(p==CYTV_PRIVATE_TEST_APPEND_VERIFIED&&host_fault("crash-append"))_exit(73);
 return 0;
}
int cytv_stop_test_hook(enum cytv_stop_test_point p,int fd,int dir){
 (void)fd;(void)dir;
 if(p==CYTV_STOP_TEST_DIR_OPEN){
  if(host_fault("scan-lock-mode"))return chmod(CYTV_STOP_IO_HOOK_ROOT "/private/controller.lock",0644);
  if(host_fault("scan-journal-mode"))return chmod(CYTV_STOP_IO_HOOK_ROOT "/private/journal",0755);
  if(host_fault("scan-root-mode"))return chmod(CYTV_STOP_IO_HOOK_ROOT "/private",0755);
 }
 return 0;
}
/* Returns 0 for ordinary write, 1 if emitted, -1 if emission failed. */
int cytv_stop_io_test_reply(unsigned op,uint32_t id,unsigned char *header,const unsigned char *body,size_t len){
 (void)id;
 if(op!=2&&op!=4)return 0;
 if(host_fault("bad-magic")){header[0]|=0x80;return 0;}
 if(host_fault("old-id")){header[11]^=1;return 0;}
 if(host_fault("oversize")){header[12]=0x7f;header[13]=header[14]=header[15]=0xff;return host_write(1,header,16)?1:-1;}
 if(host_fault("partial"))return host_write(1,header,5)?1:-1;
 if(host_fault("stdout-eof")){close(1);return 1;}
 if(host_fault("stderr-eof")){close(2);return 1;}
 if(host_fault("stderr-overflow")){unsigned char noise[4097];memset(noise,'x',sizeof(noise));if(!host_write(2,noise,sizeof(noise)))return -1;}
 if(host_fault("bad-utf8")||host_fault("nul")||host_fault("wrong-receipt")){
  unsigned char *copy=malloc(len);if(!copy)return -1;memcpy(copy,body,len);
  size_t at=op==2?12:8;if(at>=len){free(copy);return -1;}
  copy[at]=host_fault("bad-utf8")?0xff:host_fault("nul")?0:'X';
  int ok=host_write(1,header,16)&&host_write(1,copy,len);free(copy);return ok?1:-1;
 }
 if(host_fault("split")){for(size_t i=0;i<16;i++){if(!host_write(1,header+i,1))return -1;struct timespec delay={0,1000000};nanosleep(&delay,NULL);}for(size_t i=0;i<len;){size_t n=len-i<13?len-i:13;if(!host_write(1,body+i,n))return -1;i+=n;}return 1;}
 if(host_fault("trailing")){unsigned char extra=0;return host_write(1,header,16)&&host_write(1,body,len)&&host_write(1,&extra,1)?1:-1;}
 if(host_fault("duplicate")){if(!host_write(1,header,16)||!host_write(1,body,len))return -1;struct timespec delay={0,20000000};nanosleep(&delay,NULL);unlink(CYTV_STOP_IO_HOOK_ROOT "/fault");return host_write(1,header,16)&&host_write(1,body,len)?1:-1;}
 return 0;
}
