#include <unistd.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/stat.h>
#include "lock.h"
#include <string.h>
static const char *controller_lock="/media/developer/apps/usr/palm/applications/com.local.nativehome/state/controller.lock";
static const char *stop_latch="/media/developer/apps/usr/palm/applications/com.local.nativehome/state/blocked";
static const char *watchdog_latch="/media/developer/apps/usr/palm/applications/com.local.nativehome/state/watchdog";
static const char *stop_generation="/media/developer/apps/usr/palm/applications/com.local.nativehome/state/stop-generation";
static int snapshot(const char *path, struct stat *stat) {
 if(lstat(path,stat)==0)return S_ISREG(stat->st_mode)?1:-1;
 return errno==ENOENT?0:-1;
}
static int unchanged(const char *path, int present, const struct stat *before) {
 struct stat after;
 return present>=0&&snapshot(path,&after)==present&&(!present||
  (before->st_dev==after.st_dev&&before->st_ino==after.st_ino&&
   before->st_mode==after.st_mode&&before->st_size==after.st_size&&
   before->st_uid==after.st_uid&&before->st_gid==after.st_gid&&
   before->st_nlink==1&&after.st_nlink==1&&
#ifdef __APPLE__
   before->st_mtimespec.tv_sec==after.st_mtimespec.tv_sec&&
   before->st_mtimespec.tv_nsec==after.st_mtimespec.tv_nsec&&
   before->st_ctimespec.tv_sec==after.st_ctimespec.tv_sec&&
   before->st_ctimespec.tv_nsec==after.st_ctimespec.tv_nsec));
#else
   before->st_mtim.tv_sec==after.st_mtim.tv_sec&&before->st_mtim.tv_nsec==after.st_mtim.tv_nsec&&
   before->st_ctim.tv_sec==after.st_ctim.tv_sec&&before->st_ctim.tv_nsec==after.st_ctim.tv_nsec));
#endif
}
static int lock_controller(int wait) {
 int lock=acquire_lock(controller_lock);
 if(lock>=0||!wait)return lock;
 struct stat stop, watchdog, generation, previous_lock;
 if(snapshot(controller_lock,&previous_lock)!=1)return -1;
 int blocked=snapshot(stop_latch,&stop), watched=snapshot(watchdog_latch,&watchdog),
     token=snapshot(stop_generation,&generation);
 if(blocked!=1||watched<0||token<0)return -1;
 for(int attempt=0;attempt<40;attempt++){
  usleep(100000);
  if(!unchanged(controller_lock,1,&previous_lock)||
     !unchanged(stop_latch,blocked,&stop)||!unchanged(watchdog_latch,watched,&watchdog)||
     !unchanged(stop_generation,token,&generation))return -1;
  lock=acquire_lock(controller_lock);
  if(lock>=0){
   struct stat opened;
   if(fstat(lock,&opened)==0&&opened.st_dev==previous_lock.st_dev&&
      opened.st_ino==previous_lock.st_ino&&unchanged(controller_lock,1,&previous_lock)&&
      unchanged(stop_latch,blocked,&stop)&&unchanged(watchdog_latch,watched,&watchdog)&&
      unchanged(stop_generation,token,&generation))return lock;
   close(lock);
   return -1;
  }
 }
 return -1;
}
int main(int argc,char**argv){
 if(argc<3||strcmp(argv[2],"--controller")!=0){
  pid_t entry=fork();if(entry<0)return 1;if(entry>0)return 0;
  setsid();setenv("NODE_PATH","/usr/lib/nodejs:/usr/lib/node_modules",1);
  execl("/usr/bin/node","node","/media/developer/apps/usr/palm/applications/com.local.nativehome/helper-entry.js",argc>1?argv[1]:"{}",(char*)0);_exit(2);
 }
int lock=lock_controller(argc==4&&!strcmp(argv[3],"--wait-for-stop"));if(lock<0)return 0;pid_t p=fork();if(p<0)return 1;if(p>0)return 0;setsid();setenv("NODE_PATH","/usr/lib/nodejs:/usr/lib/node_modules",1);int fd=open("/media/developer/apps/usr/palm/applications/com.local.nativehome/state/bootstrap.log",O_WRONLY|O_APPEND|O_CREAT,0660);if(fd>=0)dprintf(fd,"BOOTSTRAP uid=%d pid=%d\n",getuid(),getpid());if(fd>=0){dup2(fd,0);dup2(fd,1);dup2(fd,2);if(fd>2)close(fd);}execl("/usr/bin/node","node","/media/developer/apps/usr/palm/applications/com.local.nativehome/native.js",argc>1?argv[1]:"{}",(char*)0);_exit(2);}
