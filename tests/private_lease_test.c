#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "private-io.h"
#include "stop-fs.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"line %d: %s (errno %d)\n",__LINE__,#x,errno); exit(1); } } while (0)
#define LOCK CYTV_PRIVATE_TEST_ROOT "/controller.lock"
#define JOURNAL CYTV_PRIVATE_TEST_ROOT "/journal"
static struct cytv_private_binding binding;
static struct cytv_lease *lease;
static struct cytv_private_tx *tx;
static int lifecycle_hook;
static int validate_hook, validate_hook_at;
static const char *executable;
static void byte(int fd, int sending) { char c='x'; ssize_t n; do { n=sending?write(fd,&c,1):read(fd,&c,1); } while(n<0&&errno==EINTR); CHECK(n==1); }
static struct cytv_private_identity identity(const char *path) { struct stat s; CHECK(lstat(path,&s)==0); struct cytv_private_identity id={s.st_dev,s.st_ino}; return id; }
static void init(int create) {
 if(create) { CHECK(chmod(CYTV_PRIVATE_TEST_ROOT,0700)==0); CHECK(mkdir(JOURNAL,0700)==0); int fd=open(LOCK,O_CREAT|O_EXCL|O_RDWR,0600); CHECK(fd>=0&&close(fd)==0); }
 memset(&binding,0,sizeof(binding)); binding.version=1; binding.owner=getuid(); binding.group=getgid(); binding.root=identity(CYTV_PRIVATE_TEST_ROOT); binding.journal=identity(JOURNAL); binding.lock=identity(LOCK);
}
static int probe(void) { int fd=open(LOCK,O_RDWR); CHECK(fd>=0); int ok=flock(fd,LOCK_EX|LOCK_NB)==0; if(!ok) CHECK(errno==EAGAIN||errno==EWOULDBLOCK); CHECK(close(fd)==0); return ok; }
int cytv_stop_test_hook(enum cytv_stop_test_point p,int fd,int dir) { (void)p;(void)fd;(void)dir;return 0; }
int cytv_private_test_hook(enum cytv_private_test_point p,int fd) {
 if(p==CYTV_PRIVATE_TEST_LEASE_CHECK) CHECK(fcntl(fd,F_GETFD)&FD_CLOEXEC);
 if(p==CYTV_PRIVATE_TEST_LEASE_CHECK&&validate_hook&&!--validate_hook_at) {
  int action=validate_hook;validate_hook=0;
  CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_UNKNOWN);
  CHECK(!probe());
  if(action==2)CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_BUSY&&tx);
  if(action==3)CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_BUSY&&lease);
 }
 if(p==CYTV_PRIVATE_TEST_TX_ACTIVE&&lifecycle_hook) {
  lifecycle_hook=0;
  CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_BUSY&&tx);
  CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_BUSY&&lease);
  CHECK(!probe());
  struct cytv_private_tx *other=NULL;
  CHECK(cytv_tx_begin(lease,&other)!=CYTV_PRIVATE_OK&&!other);
 }
 return 0;
}
static void acquire(void) { CHECK(cytv_lease_acquire(&binding,&lease)==CYTV_PRIVATE_OK&&lease); CHECK(!probe()); }
static void finish(void) { if(tx) CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_OK&&!tx); CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease); CHECK(probe()); }
static void failure(void) { CHECK(cytv_lease_acquire(&binding,&lease)!=CYTV_PRIVATE_OK&&!lease); }
static void waited(pid_t p) { int s; CHECK(waitpid(p,&s,0)==p&&WIFEXITED(s)&&WEXITSTATUS(s)==0); }
static void child_exec(int inherit) {
 acquire(); int ready[2],go[2]; CHECK(pipe(ready)==0&&pipe(go)==0);
 pid_t p=fork(); CHECK(p>=0);
 if(!p) {
  close(ready[0]);close(go[1]); int fd=-1;
  if(inherit) CHECK(cytv_lease_child_handoff(&lease,&fd)==CYTV_PRIVATE_OK&&!lease&&fd>=3);
  char a[24],b[24],c[24]; snprintf(a,sizeof(a),"%d",fd); snprintf(b,sizeof(b),"%d",ready[1]);snprintf(c,sizeof(c),"%d",go[0]);
  execl(executable,executable,inherit?"exec-adopt":"exec-idle",a,b,c,(char*)0);_exit(9);
 }
 close(ready[1]);close(go[0]);byte(ready[0],0);
 CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease);
 CHECK(probe()==!inherit);
 byte(go[1],1);waited(p);close(ready[0]);close(go[1]);CHECK(probe());
}
static void independent_stop(void) {
 acquire();
 CHECK(mkdir(CYTV_STOP_TEST_PATH,0770)==0&&chmod(CYTV_STOP_TEST_PATH,0770)==0);
 struct stat s; CHECK(lstat(CYTV_STOP_TEST_PATH,&s)==0);
 struct cytv_stop_binding b={0};b.version=1;b.directory_dev=s.st_dev;b.directory_ino=s.st_ino;b.owner=getuid();b.group=getgid();b.producer_count=1;b.producers[0]=getuid();
 pid_t p=fork();CHECK(p>=0);
 if(!p){CHECK(cytv_lease_child_discard(&lease)==CYTV_PRIVATE_OK&&!lease);struct cytv_stop_publication r;CHECK(cytv_stop_publish(&b,"00000000000000000000000000000001",&r)==CYTV_STOP_OK&&r.durable_published);_exit(0);}
 waited(p);CHECK(!probe());finish();
}
static void fork_discard(void) {
 acquire();int ready[2],go[2];CHECK(pipe(ready)==0&&pipe(go)==0);
 pid_t p=fork();CHECK(p>=0);
 if(!p){close(ready[0]);close(go[1]);CHECK(cytv_lease_child_discard(&lease)==CYTV_PRIVATE_OK&&!lease);byte(ready[1],1);byte(go[0],0);_exit(0);}
 close(ready[1]);close(go[0]);byte(ready[0],0);CHECK(!probe());
 CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease);CHECK(probe());
 byte(go[1],1);waited(p);close(ready[0]);close(go[1]);
}
static void shared_adopt(int additional_holder) {
 int fd=open(LOCK,O_RDWR);CHECK(fd>=0&&flock(fd,LOCK_SH|LOCK_NB)==0);
 int second=-1;
 if(additional_holder){second=open(LOCK,O_RDWR);CHECK(second>=0&&flock(second,LOCK_SH|LOCK_NB)==0);}
 CHECK(cytv_lease_adopt(&binding,fd,&lease)==CYTV_PRIVATE_UNKNOWN&&!lease);
 CHECK(fcntl(fd,F_GETFD)>=0);
 if(second>=0)CHECK(close(second)==0);
 CHECK(!probe()); /* The borrowed FD must still hold its shared lock. */
 int third=open(LOCK,O_RDWR);CHECK(third>=0&&flock(third,LOCK_SH|LOCK_NB)==0);
 CHECK(close(third)==0&&close(fd)==0);CHECK(probe());
}
static void validate_change(const char *target,const char *change) {
 const char *p=!strcmp(target,"lock")?LOCK:!strcmp(target,"journal")?JOURNAL:CYTV_PRIVATE_TEST_ROOT;
 int directory=strcmp(target,"lock")!=0;
 mode_t mode=directory?0700:0600;
 char saved[sizeof(CYTV_PRIVATE_TEST_ROOT)+64];CHECK(snprintf(saved,sizeof(saved),"%s.saved",p)>0);
 acquire();CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);
 CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_OK);
 if(!strcmp(change,"mode"))CHECK(chmod(p,directory?0755:0644)==0);
 else {
  CHECK(rename(p,saved)==0);
  if(!strcmp(change,"replace")) {
   if(directory)CHECK(mkdir(p,mode)==0);
   else {int fd=open(p,O_CREAT|O_EXCL|O_RDWR,mode);CHECK(fd>=0&&close(fd)==0);}
  }
 }
 CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_UNKNOWN);
 /* Unsafe/missing/replaced metadata cannot prevent actual cleanup. */
 CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_OK&&!tx);
 CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease);
 if(!strcmp(change,"mode"))CHECK(chmod(p,mode)==0);
 else {if(!strcmp(change,"replace"))CHECK((directory?rmdir(p):unlink(p))==0);CHECK(rename(saved,p)==0);}
 CHECK(probe());
}
int main(int argc,char **argv) {
 CHECK(argc>=2);alarm(10);executable=argv[0];const char *name=argv[1];
 if(!strcmp(name,"exec-adopt")||!strcmp(name,"exec-idle")) {
  CHECK(argc==5);init(0);int inherited=atoi(argv[2]),ready=atoi(argv[3]),go=atoi(argv[4]);
  if(!strcmp(name,"exec-adopt")){CHECK(!(fcntl(inherited,F_GETFD)&FD_CLOEXEC));CHECK(cytv_lease_adopt(&binding,inherited,&lease)==CYTV_PRIVATE_OK&&lease);CHECK(fcntl(inherited,F_GETFD)>=0&&close(inherited)==0);CHECK(!probe());}
  byte(ready,1);byte(go,0);if(lease) CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease);return 0;
 }
 init(1);
 if(!strcmp(name,"acquire")){acquire();CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK&&tx);finish();}
 else if(!strcmp(name,"contention")){acquire();pid_t p=fork();CHECK(p>=0);if(!p){CHECK(cytv_lease_child_discard(&lease)==CYTV_PRIVATE_OK);struct cytv_lease *other=NULL;CHECK(cytv_lease_acquire(&binding,&other)==CYTV_PRIVATE_BUSY&&!other);_exit(0);}waited(p);finish();}
 else if(!strcmp(name,"missing-lock")){CHECK(unlink(LOCK)==0);failure();CHECK(access(LOCK,F_OK)<0&&errno==ENOENT);}
 else if(!strcmp(name,"missing-journal")){CHECK(rmdir(JOURNAL)==0);failure();CHECK(access(JOURNAL,F_OK)<0&&errno==ENOENT);}
 else if(!strcmp(name,"root-mode")){CHECK(chmod(CYTV_PRIVATE_TEST_ROOT,0755)==0);failure();}
 else if(!strcmp(name,"journal-mode")){CHECK(chmod(JOURNAL,0770)==0);failure();}
 else if(!strcmp(name,"lock-mode")){CHECK(chmod(LOCK,0640)==0);failure();}
 else if(!strcmp(name,"lock-link")){CHECK(unlink(LOCK)==0&&symlink("journal",LOCK)==0);failure();}
 else if(!strcmp(name,"lock-fifo")){CHECK(unlink(LOCK)==0&&mkfifo(LOCK,0600)==0);failure();}
 else if(!strcmp(name,"lock-hardlink")){CHECK(link(LOCK,CYTV_PRIVATE_TEST_ROOT "/alias")==0);failure();}
 else if(!strcmp(name,"owner")){binding.owner++;failure();}
 else if(!strcmp(name,"group")){binding.group++;failure();}
 else if(!strcmp(name,"inode")){binding.lock.ino++;failure();}
 else if(!strcmp(name,"unbound")){struct cytv_private_binding zero={0};CHECK(cytv_lease_acquire(&zero,&lease)!=CYTV_PRIVATE_OK&&!lease);CHECK(cytv_lease_acquire(NULL,&lease)!=CYTV_PRIVATE_OK&&!lease);}
 else if(!strcmp(name,"adopt-unlocked")){int fd=open(LOCK,O_RDWR);CHECK(fd>=0);CHECK(cytv_lease_adopt(&binding,fd,&lease)!=CYTV_PRIVATE_OK&&!lease);CHECK(fcntl(fd,F_GETFD)>=0&&close(fd)==0);CHECK(probe());}
 else if(!strcmp(name,"adopt-other")){acquire();int fd=open(LOCK,O_RDWR);CHECK(fd>=0);struct cytv_lease *other=NULL;CHECK(cytv_lease_adopt(&binding,fd,&other)!=CYTV_PRIVATE_OK&&!other);CHECK(fcntl(fd,F_GETFD)>=0&&close(fd)==0);CHECK(!probe());finish();}
 else if(!strcmp(name,"adopt-readonly")){int fd=open(LOCK,O_RDONLY);CHECK(fd>=0&&flock(fd,LOCK_EX|LOCK_NB)==0);CHECK(cytv_lease_adopt(&binding,fd,&lease)!=CYTV_PRIVATE_OK&&!lease);CHECK(close(fd)==0);}
 else if(!strcmp(name,"adopt-shared"))shared_adopt(0);
 else if(!strcmp(name,"adopt-shared-other"))shared_adopt(1);
 else if(!strcmp(name,"adopt-cloexec")){int fd=open(LOCK,O_RDWR);CHECK(fd>=0&&flock(fd,LOCK_EX|LOCK_NB)==0);CHECK(cytv_lease_adopt(&binding,fd,&lease)==CYTV_PRIVATE_OK&&lease);CHECK(fcntl(fd,F_GETFD)>=0&&close(fd)==0);CHECK(!probe());finish();}
 else if(!strcmp(name,"wrong-fd")){CHECK(cytv_lease_adopt(&binding,-1,&lease)!=CYTV_PRIVATE_OK&&!lease);int fd=open(JOURNAL,O_RDONLY);CHECK(fd>=0);CHECK(cytv_lease_adopt(&binding,fd,&lease)!=CYTV_PRIVATE_OK&&!lease);CHECK(close(fd)==0);}
 else if(!strcmp(name,"lifecycle")){acquire();lifecycle_hook=1;CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK&&tx);CHECK(!probe());finish();CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_UNKNOWN);CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_UNKNOWN);}
 else if(!strcmp(name,"nested")){acquire();CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);struct cytv_private_tx *other=NULL;CHECK(cytv_tx_begin(lease,&other)==CYTV_PRIVATE_BUSY&&!other);finish();}
 else if(!strcmp(name,"wrong-pid")){acquire();pid_t p=fork();CHECK(p>=0);if(!p){struct cytv_private_tx *other=NULL;CHECK(cytv_tx_begin(lease,&other)!=CYTV_PRIVATE_OK&&!other);CHECK(cytv_lease_close(&lease)!=CYTV_PRIVATE_OK&&lease);CHECK(cytv_lease_child_discard(&lease)==CYTV_PRIVATE_OK&&!lease);_exit(0);}waited(p);CHECK(!probe());finish();}
 else if(!strcmp(name,"replacement")){acquire();CHECK(rename(LOCK,CYTV_PRIVATE_TEST_ROOT "/old")==0);int fd=open(LOCK,O_CREAT|O_EXCL|O_RDWR,0600);CHECK(fd>=0&&close(fd)==0);CHECK(cytv_tx_begin(lease,&tx)!=CYTV_PRIVATE_OK&&!tx);CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease);}
 else if(!strcmp(name,"exec-inherit"))child_exec(1);
 else if(!strcmp(name,"exec-unrelated"))child_exec(0);
 else if(!strcmp(name,"fork-discard"))fork_discard();
 else if(!strcmp(name,"root-replace")){acquire();CHECK(rename(CYTV_PRIVATE_TEST_ROOT,CYTV_PRIVATE_TEST_ROOT ".old")==0);CHECK(mkdir(CYTV_PRIVATE_TEST_ROOT,0700)==0);CHECK(cytv_tx_begin(lease,&tx)!=CYTV_PRIVATE_OK&&!tx);CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease);}
 else if(!strcmp(name,"journal-replace")){acquire();CHECK(rename(JOURNAL,JOURNAL ".old")==0);CHECK(mkdir(JOURNAL,0700)==0);CHECK(cytv_tx_begin(lease,&tx)!=CYTV_PRIVATE_OK&&!tx);finish();}
 else if(!strcmp(name,"stop-independent"))independent_stop();
 else if(!strcmp(name,"validate-live")){acquire();CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_OK);CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_OK);finish();CHECK(cytv_tx_validate(NULL)==CYTV_PRIVATE_UNKNOWN);}
 else if(!strcmp(name,"validate-wrong-pid")){acquire();CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);pid_t p=fork();CHECK(p>=0);if(!p){CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_UNKNOWN);CHECK(cytv_lease_child_discard(&lease)==CYTV_PRIVATE_OK);_exit(0);}waited(p);CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_OK);finish();}
 else if(!strcmp(name,"validate-busy")||!strcmp(name,"validate-ending")||!strcmp(name,"validate-closing")){acquire();CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);validate_hook=!strcmp(name,"validate-busy")?1:!strcmp(name,"validate-ending")?2:3;validate_hook_at=2;CHECK(cytv_tx_validate(tx)==(!strcmp(name,"validate-busy")?CYTV_PRIVATE_OK:CYTV_PRIVATE_UNKNOWN));CHECK(!validate_hook);if(strcmp(name,"validate-busy"))CHECK(cytv_tx_validate(tx)==CYTV_PRIVATE_UNKNOWN);finish();}
 else if(!strncmp(name,"validate-lock-",14))validate_change("lock",name+14);
 else if(!strncmp(name,"validate-journal-",17))validate_change("journal",name+17);
 else if(!strncmp(name,"validate-root-",14))validate_change("root",name+14);
 else CHECK(0);
 puts("PASS");return 0;
}
