#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "private-io.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"line %d: %s (errno %d)\n",__LINE__,#x,errno);exit(1);} } while(0)
#define JOURNAL CYTV_PRIVATE_TEST_ROOT "/journal"
#define LOCK CYTV_PRIVATE_TEST_ROOT "/controller.lock"
static const unsigned char genesis[]="{ \"v\": 1, \"seq\": 0 }\n";
static const unsigned char next[]="{\"seq\":1,\"phase\":\"blocked\"}\n";
static struct cytv_private_binding binding;
static struct cytv_lease *lease;
static struct cytv_private_tx *tx;
static enum cytv_private_test_point target;
static int action;
static unsigned target_seq;
static size_t entries,opens;
enum {NONE,FAIL,CUT,CORRUPT,REPLACE,FIFO,DIR_REPLACE,LIFECYCLE};
static void path(unsigned seq,char out[1024]) { CHECK(snprintf(out,1024,JOURNAL "/entry.%04u.json",seq)<1024); }
static struct cytv_private_identity identity(const char *p) { struct stat s;CHECK(lstat(p,&s)==0);struct cytv_private_identity id={s.st_dev,s.st_ino};return id; }
static void record(unsigned seq,const unsigned char *raw,size_t n) { char p[1024];path(seq,p);int fd=open(p,O_CREAT|O_EXCL|O_WRONLY,0600);CHECK(fd>=0&&write(fd,raw,n)==(ssize_t)n&&fchmod(fd,0600)==0&&close(fd)==0); }
static int probe(void) { int fd=open(LOCK,O_RDWR);CHECK(fd>=0);int ok=flock(fd,LOCK_EX|LOCK_NB)==0;CHECK(close(fd)==0);return ok; }
static void setup(int with_genesis) {
 CHECK(chmod(CYTV_PRIVATE_TEST_ROOT,0700)==0&&mkdir(JOURNAL,0700)==0);
 int fd=open(LOCK,O_CREAT|O_EXCL|O_RDWR,0600);CHECK(fd>=0&&close(fd)==0);
 binding.version=1;binding.owner=getuid();binding.group=getgid();binding.root=identity(CYTV_PRIVATE_TEST_ROOT);binding.journal=identity(JOURNAL);binding.lock=identity(LOCK);
 if(with_genesis)record(0,genesis,sizeof(genesis)-1);
 CHECK(cytv_lease_acquire(&binding,&lease)==CYTV_PRIVATE_OK);
 CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);
}
static void finish(void) { CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_OK&&!tx);CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK&&!lease);CHECK(probe()); }
int cytv_private_test_hook(enum cytv_private_test_point p,int fd) {
 (void)fd;if(p==CYTV_PRIVATE_TEST_READ_ENTRY)entries++;if(p==CYTV_PRIVATE_TEST_READ_OPEN)opens++;
 if(!action||p!=target)return 0;
 int a=action;action=NONE;char name[1024];path(target_seq,name);
 if(a==FAIL){errno=EIO;return -1;}
 if(a==CUT)_exit(73);
 if(a==LIFECYCLE){CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_BUSY&&tx);CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_BUSY&&lease);CHECK(!probe());struct cytv_private_tx *other=NULL;CHECK(cytv_tx_begin(lease,&other)!=CYTV_PRIVATE_OK&&!other);return 0;}
 if(a==DIR_REPLACE){CHECK(rename(JOURNAL,JOURNAL ".old")==0&&mkdir(JOURNAL,0700)==0);return 0;}
 if(a==REPLACE||a==FIFO)CHECK(unlink(name)==0);
 if(a==FIFO){CHECK(mkfifo(name,0600)==0);return 0;}
 int w=open(name,O_WRONLY|O_TRUNC|(a==REPLACE?(O_CREAT|O_EXCL):0),0600);CHECK(w>=0);
 const unsigned char *raw=target_seq?next:genesis;size_t n=target_seq?sizeof(next)-1:sizeof(genesis)-1;
 if(a==CORRUPT){raw=(const unsigned char*)"x";n=1;}
 CHECK(write(w,raw,n)==(ssize_t)n&&close(w)==0);return 0;
}
static void loaded(size_t count) { struct cytv_journal_view v;CHECK(cytv_journal_read(tx,&v)==CYTV_PRIVATE_OK&&v.count==count);CHECK(v.records[0].seq==0&&v.records[0].len==sizeof(genesis)-1&&!memcmp(v.records[0].raw,genesis,sizeof(genesis)-1)); }
static void no_read(enum cytv_private_status status) { struct cytv_journal_view v;memset(&v,0x55,sizeof(v));CHECK(cytv_journal_read(tx,&v)==status&&v.count==0);for(size_t i=0;i<64;i++)CHECK(!v.records[i].raw&&!v.records[i].len); }
static void append_ok(void) { struct cytv_append_receipt r;CHECK(cytv_journal_append(tx,1,next,sizeof(next)-1,&r)==CYTV_PRIVATE_OK&&r.durable);CHECK(r.event.seq==1&&r.event.len==sizeof(next)-1&&!memcmp(r.event.raw,next,r.event.len)); }
static void append_bad(enum cytv_private_status status) { struct cytv_append_receipt r;memset(&r,0x55,sizeof(r));CHECK(cytv_journal_append(tx,1,next,sizeof(next)-1,&r)==status&&!r.durable&&!r.event.raw); }
static void invalid(const char *kind) {
 char p[1024];path(0,p);
 if(!strcmp(kind,"mode"))CHECK(chmod(p,0640)==0);
 else if(!strcmp(kind,"hardlink"))CHECK(link(p,CYTV_PRIVATE_TEST_ROOT "/alias")==0);
 else if(!strcmp(kind,"symlink")){CHECK(unlink(p)==0&&symlink("../controller.lock",p)==0);}
 else if(!strcmp(kind,"fifo")){CHECK(unlink(p)==0&&mkfifo(p,0600)==0);}
 else if(!strcmp(kind,"gap")){char q[1024];path(1,q);CHECK(rename(p,q)==0);}
 else if(!strcmp(kind,"unknown")){int fd=open(JOURNAL "/foreign",O_CREAT|O_EXCL|O_WRONLY,0600);CHECK(fd>=0&&close(fd)==0);}
 else {int fd=open(p,O_WRONLY|O_TRUNC);CHECK(fd>=0);if(!strcmp(kind,"oversize")){CHECK(ftruncate(fd,16385)==0);}else if(!strcmp(kind,"nul")){CHECK(write(fd,"a\0b",3)==3);}else if(!strcmp(kind,"utf8")){unsigned char bad[]={0xc0,0x80};CHECK(write(fd,bad,2)==2);}CHECK(close(fd)==0);}
 no_read(CYTV_PRIVATE_UNKNOWN);append_bad(CYTV_PRIVATE_UNKNOWN);
}
static void cut(enum cytv_private_test_point point) {
 loaded(1);CHECK(cytv_tx_end(&tx)==CYTV_PRIVATE_OK);CHECK(cytv_lease_close(&lease)==CYTV_PRIVATE_OK);
 pid_t p=fork();CHECK(p>=0);
 if(!p){CHECK(cytv_lease_acquire(&binding,&lease)==CYTV_PRIVATE_OK);CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);loaded(1);action=CUT;target=point;struct cytv_append_receipt r;(void)cytv_journal_append(tx,1,next,sizeof(next)-1,&r);_exit(1);}
 int s;CHECK(waitpid(p,&s,0)==p&&WIFEXITED(s)&&WEXITSTATUS(s)==73);
 CHECK(cytv_lease_acquire(&binding,&lease)==CYTV_PRIVATE_OK);CHECK(cytv_tx_begin(lease,&tx)==CYTV_PRIVATE_OK);
 if(point==CYTV_PRIVATE_TEST_APPEND_CREATED)no_read(CYTV_PRIVATE_UNKNOWN);else loaded(2);
}
static void utf8_boundaries(void) {
 static const struct {unsigned char raw[5];size_t len;int valid;} vectors[]={
  {{0x7f},1,1},{{0xc2,0x80},2,1},{{0xdf,0xbf},2,1},{{0xe0,0xa0,0x80},3,1},
  {{0xed,0x9f,0xbf},3,1},{{0xee,0x80,0x80},3,1},{{0xf0,0x90,0x80,0x80},4,1},
  {{0xf4,0x8f,0xbf,0xbf},4,1},{{0},1,0},{{0x80},1,0},{{0xc0,0x80},2,0},
  {{0xc1,0xbf},2,0},{{0xc2},1,0},{{0xc2,0x20},2,0},{{0xe0,0x9f,0xbf},3,0},
  {{0xed,0xa0,0x80},3,0},{{0xed,0xbf,0xbf},3,0},{{0xf0,0x8f,0xbf,0xbf},4,0},
  {{0xf4,0x90,0x80,0x80},4,0},{{0xf5,0x80,0x80,0x80},4,0},{{0xe2,0x82},2,0},
  {{0xf0,0x90,0x80},3,0},{{0xff},1,0},{{'a',0,'b'},3,0}
 };
 char name[1024];path(0,name);
 for(size_t i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){
  int fd=open(name,O_WRONLY|O_TRUNC);CHECK(fd>=0&&write(fd,vectors[i].raw,vectors[i].len)==(ssize_t)vectors[i].len&&close(fd)==0);
  struct cytv_journal_view v;enum cytv_private_status s=cytv_journal_read(tx,&v);
  if(vectors[i].valid){CHECK(s==CYTV_PRIVATE_OK&&v.count==1&&v.records[0].len==vectors[i].len&&!memcmp(v.records[0].raw,vectors[i].raw,vectors[i].len));}
  else CHECK(s==CYTV_PRIVATE_UNKNOWN&&v.count==0);
 }
}
int main(int argc,char **argv) {
 CHECK(argc==2);alarm(10);const char *name=argv[1];setup(strcmp(name,"missing")!=0);
 if(!strcmp(name,"read")){loaded(1);loaded(1);}
 else if(!strcmp(name,"append")){loaded(1);append_ok();loaded(2);}
 else if(!strcmp(name,"utf8-boundaries"))utf8_boundaries();
 else if(!strcmp(name,"append-invalid-utf8")){loaded(1);unsigned char bad[]={0xed,0xa0,0x80};struct cytv_append_receipt r;CHECK(cytv_journal_append(tx,1,bad,sizeof(bad),&r)==CYTV_PRIVATE_UNKNOWN&&!r.durable);append_bad(CYTV_PRIVATE_UNKNOWN);loaded(1);append_ok();}
 else if(!strcmp(name,"no-read"))append_bad(CYTV_PRIVATE_UNKNOWN);
 else if(!strcmp(name,"missing")){no_read(CYTV_PRIVATE_UNKNOWN);append_bad(CYTV_PRIVATE_UNKNOWN);}
 else if(!strncmp(name,"invalid-",8))invalid(name+8);
 else if(!strcmp(name,"full")){for(unsigned i=1;i<64;i++)record(i,next,sizeof(next)-1);loaded(64);struct cytv_append_receipt r;CHECK(cytv_journal_append(tx,64,next,sizeof(next)-1,&r)==CYTV_PRIVATE_FULL&&!r.durable);}
 else if(!strcmp(name,"full-bytes")){unsigned char *raw=malloc(16384);CHECK(raw);memset(raw,' ',16384);char p[1024];path(0,p);int fd=open(p,O_WRONLY|O_TRUNC);CHECK(fd>=0&&write(fd,raw,16384)==16384&&close(fd)==0);for(unsigned i=1;i<64;i++)record(i,raw,16384);struct cytv_journal_view v;CHECK(cytv_journal_read(tx,&v)==CYTV_PRIVATE_OK&&v.count==64);for(size_t i=0;i<64;i++)CHECK(v.records[i].seq==i&&v.records[i].len==16384&&!memcmp(v.records[i].raw,raw,16384));struct cytv_append_receipt r;CHECK(cytv_journal_append(tx,64,raw,16384,&r)==CYTV_PRIVATE_FULL&&!r.durable);free(raw);}
 else if(!strcmp(name,"overflow")){for(unsigned i=1;i<1000;i++)record(i,next,sizeof(next)-1);struct cytv_journal_view v;CHECK(cytv_journal_read(tx,&v)==CYTV_PRIVATE_OVERFLOW&&v.count==0&&v.observed_entries==65);CHECK(entries==65&&opens==0);}
 else if(!strcmp(name,"limit")){loaded(1);unsigned char *raw=malloc(16384);CHECK(raw);memset(raw,' ',16384);struct cytv_append_receipt r;CHECK(cytv_journal_append(tx,1,raw,16384,&r)==CYTV_PRIVATE_OK&&r.durable&&r.event.len==16384&&!memcmp(raw,r.event.raw,16384));free(raw);loaded(2);}
 else if(!strcmp(name,"append-oversize")){loaded(1);unsigned char raw[16385];memset(raw,'x',sizeof(raw));struct cytv_append_receipt r;CHECK(cytv_journal_append(tx,1,raw,sizeof(raw),&r)==CYTV_PRIVATE_UNKNOWN&&!r.durable);append_bad(CYTV_PRIVATE_UNKNOWN);loaded(1);append_ok();}
 else if(!strcmp(name,"wrong-seq")){loaded(1);struct cytv_append_receipt r;CHECK(cytv_journal_append(tx,2,next,sizeof(next)-1,&r)==CYTV_PRIVATE_UNKNOWN&&!r.durable);loaded(1);append_ok();}
 else if(!strcmp(name,"collision")){loaded(1);record(1,next,sizeof(next)-1);append_bad(CYTV_PRIVATE_UNKNOWN);loaded(2);}
 else if(!strcmp(name,"cache-mutation")){loaded(1);target_seq=0;action=CORRUPT;target=CYTV_PRIVATE_TEST_TX_ACTIVE;CHECK(cytv_private_test_hook(target,-1)==0);append_bad(CYTV_PRIVATE_UNKNOWN);}
 else if(!strcmp(name,"read-fifo-race")){action=FIFO;target=CYTV_PRIVATE_TEST_READ_BEFORE_OPEN;no_read(CYTV_PRIVATE_UNKNOWN);}
 else if(!strcmp(name,"read-replace")){action=REPLACE;target=CYTV_PRIVATE_TEST_READ_OPEN;no_read(CYTV_PRIVATE_UNKNOWN);}
 else if(!strcmp(name,"read-dir-replace")){action=DIR_REPLACE;target=CYTV_PRIVATE_TEST_READ_VERIFIED;no_read(CYTV_PRIVATE_UNKNOWN);}
 else if(!strcmp(name,"read-file-sync-fail")){action=FAIL;target=CYTV_PRIVATE_TEST_READ_FILE_SYNC;no_read(CYTV_PRIVATE_UNKNOWN);loaded(1);}
 else if(!strcmp(name,"read-dir-sync-fail")){action=FAIL;target=CYTV_PRIVATE_TEST_READ_DIR_SYNC;no_read(CYTV_PRIVATE_UNKNOWN);loaded(1);}
 else if(!strcmp(name,"append-file-sync-fail")||!strcmp(name,"append-dir-sync-fail")){loaded(1);action=FAIL;target=!strcmp(name,"append-file-sync-fail")?CYTV_PRIVATE_TEST_APPEND_FILE_SYNC:CYTV_PRIVATE_TEST_APPEND_DIR_SYNC;append_bad(CYTV_PRIVATE_UNKNOWN);append_bad(CYTV_PRIVATE_UNKNOWN);loaded(2);}
 else if(!strcmp(name,"append-corrupt")||!strcmp(name,"append-replace")){loaded(1);target_seq=1;action=!strcmp(name,"append-corrupt")?CORRUPT:REPLACE;target=CYTV_PRIVATE_TEST_APPEND_DIR_SYNCED;append_bad(CYTV_PRIVATE_UNKNOWN);}
 else if(!strcmp(name,"lifecycle-read")){action=LIFECYCLE;target=CYTV_PRIVATE_TEST_READ_VERIFIED;loaded(1);no_read(CYTV_PRIVATE_UNKNOWN);append_bad(CYTV_PRIVATE_UNKNOWN);CHECK(!probe());}
 else if(!strcmp(name,"lifecycle-append")){loaded(1);action=LIFECYCLE;target=CYTV_PRIVATE_TEST_APPEND_WRITTEN;append_ok();no_read(CYTV_PRIVATE_UNKNOWN);append_bad(CYTV_PRIVATE_UNKNOWN);CHECK(!probe());}
 else if(!strcmp(name,"cut-create"))cut(CYTV_PRIVATE_TEST_APPEND_CREATED);
 else if(!strcmp(name,"cut-write"))cut(CYTV_PRIVATE_TEST_APPEND_WRITTEN);
 else if(!strcmp(name,"cut-file-sync"))cut(CYTV_PRIVATE_TEST_APPEND_FILE_SYNCED);
 else if(!strcmp(name,"cut-dir-sync"))cut(CYTV_PRIVATE_TEST_APPEND_DIR_SYNCED);
 else CHECK(0);
 finish();puts("PASS");return 0;
}
