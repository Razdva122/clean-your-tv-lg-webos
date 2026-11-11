#ifndef CYTV_STOP_GENERATION_H
#define CYTV_STOP_GENERATION_H
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#ifndef CYTV_GENERATION_DIRECTORY
#define CYTV_GENERATION_DIRECTORY "/media/developer/apps/usr/palm/applications/com.local.nativehome/state"
#endif
static int cytv_generation_token(const char *s) {
 if(!s||(s[0]!='I'&&s[0]!='S')||strlen(s)!=33)return 0;
 for(int i=1;i<33;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;
 return 1;
}
static int cytv_generation_group(gid_t group) {
 if(getuid()==0||getgid()==group)return 1;
 gid_t groups[64];int n=getgroups(64,groups);if(n<0)return 0;
 for(int i=0;i<n;i++)if(groups[i]==group)return 1;
 return 0;
}
static int cytv_generation_same(const struct stat *a,const struct stat *b) {
 return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&a->st_uid==b->st_uid&&a->st_gid==b->st_gid&&
 a->st_mode==b->st_mode&&a->st_nlink==b->st_nlink&&a->st_size==b->st_size&&
#ifdef __APPLE__
 a->st_mtimespec.tv_sec==b->st_mtimespec.tv_sec&&a->st_mtimespec.tv_nsec==b->st_mtimespec.tv_nsec&&
 a->st_ctimespec.tv_sec==b->st_ctimespec.tv_sec&&a->st_ctimespec.tv_nsec==b->st_ctimespec.tv_nsec;
#else
 a->st_mtim.tv_sec==b->st_mtim.tv_sec&&a->st_mtim.tv_nsec==b->st_mtim.tv_nsec&&
 a->st_ctim.tv_sec==b->st_ctim.tv_sec&&a->st_ctim.tv_nsec==b->st_ctim.tv_nsec;
#endif
}
static int cytv_generation_directory(void) {
 char parent[1024];struct stat s,b;
 if(strlen(CYTV_GENERATION_DIRECTORY)>=sizeof parent)return -1;
 strcpy(parent,CYTV_GENERATION_DIRECTORY);
 for(;;){if(lstat(parent,&s)<0||!S_ISDIR(s.st_mode))return -1;char *slash=strrchr(parent,'/');if(!slash||slash==parent)break;*slash=0;}
 if(lstat(CYTV_GENERATION_DIRECTORY,&s)<0||!S_ISDIR(s.st_mode)||(s.st_mode&07002)||
    (s.st_uid!=getuid()&&!(s.st_uid==5999&&s.st_gid==5000))||!cytv_generation_group(s.st_gid)||
    (getuid()!=0&&!(s.st_mode&(s.st_uid==getuid()?0200:0020))))return -1;
 int fd=open(CYTV_GENERATION_DIRECTORY,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
 if(fd<0)return -1;
 if(fstat(fd,&b)<0||s.st_dev!=b.st_dev||s.st_ino!=b.st_ino||s.st_mode!=b.st_mode||s.st_uid!=b.st_uid||s.st_gid!=b.st_gid){close(fd);return -1;}
 return fd;
}
static int cytv_generation_leaf(int dir,struct stat *s) {
 struct stat parent;if(fstat(dir,&parent)<0)return -1;
 if(fstatat(dir,"stop-generation",s,AT_SYMLINK_NOFOLLOW)<0)return errno==ENOENT?0:-1;
 return S_ISREG(s->st_mode)&&s->st_nlink==1&&s->st_size<=33&&(s->st_mode&07777)==0664&&s->st_gid==parent.st_gid?1:-1;
}
static int cytv_generation_same_directory(int dir) {
 struct stat a,b;
 return fstat(dir,&a)==0&&lstat(CYTV_GENERATION_DIRECTORY,&b)==0&&S_ISDIR(b.st_mode)&&
  a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_mode==b.st_mode&&a.st_uid==b.st_uid&&a.st_gid==b.st_gid;
}
static int cytv_generation_read(char token[34]) {
 int dir=cytv_generation_directory();if(dir<0)return 0;
 struct stat before,after;int fd=-1,ok=0;
 if(cytv_generation_leaf(dir,&before)!=1||before.st_size!=33)goto done;
 fd=openat(dir,"stop-generation",O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);if(fd<0)goto done;
 if(fstat(fd,&after)<0||!cytv_generation_same(&before,&after))goto done;
 size_t offset=0;while(offset<34){ssize_t n=pread(fd,token+offset,34-offset,(off_t)offset);if(n<0&&errno==EINTR)continue;if(n<0)goto done;if(!n)break;offset+=(size_t)n;}
 if(offset!=33)goto done;token[33]=0;
 if(fstat(fd,&after)<0||!cytv_generation_same(&before,&after)||cytv_generation_leaf(dir,&after)!=1||!cytv_generation_same(&before,&after))goto done;
 ok=cytv_generation_token(token)&&cytv_generation_same_directory(dir);
done:if(fd>=0)close(fd);close(dir);return ok;
}
static void cytv_generation_invalidate(int dir) {
 struct stat before,opened,path;int fd=-1,state=cytv_generation_leaf(dir,&before);
 if(state<0||!cytv_generation_same_directory(dir))return;
 if(!state){
  fd=openat(dir,"stop-generation",O_RDWR|O_CREAT|O_EXCL|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC,0600);
  if(fd>=0){
   if(fstat(fd,&opened)==0&&fstat(dir,&before)==0&&opened.st_uid==getuid()&&S_ISREG(opened.st_mode)&&opened.st_nlink==1&&
      fstatat(dir,"stop-generation",&path,AT_SYMLINK_NOFOLLOW)==0&&cytv_generation_same(&opened,&path)&&
      fchown(fd,(uid_t)-1,before.st_gid)==0&&fchmod(fd,0664)==0&&cytv_generation_same_directory(dir)){(void)fsync(fd);(void)fsync(dir);}
   close(fd);return;
  }
  if(errno!=EEXIST||cytv_generation_leaf(dir,&before)!=1)return;
 }
 fd=openat(dir,"stop-generation",O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);if(fd<0)return;
 if(fstat(fd,&opened)==0&&cytv_generation_same(&before,&opened)&&
    fstatat(dir,"stop-generation",&path,AT_SYMLINK_NOFOLLOW)==0&&cytv_generation_same(&before,&path)&&
    cytv_generation_same_directory(dir)&&ftruncate(fd,0)==0)(void)fsync(fd);
 close(fd);
}
static int cytv_generation_publish(void) {
 int dir=cytv_generation_directory();if(dir<0)return 0;
 int random=-1,fd=-1,ok=0,created=0;unsigned char bytes[16];char token[34],tmp[64];struct stat s,staged,current;
 if(cytv_generation_leaf(dir,&s)<0)goto done;
 random=open("/dev/urandom",O_RDONLY|O_CLOEXEC);if(random<0)goto done;
 size_t offset=0;while(offset<sizeof bytes){ssize_t n=read(random,bytes+offset,sizeof bytes-offset);if(n<0&&errno==EINTR)continue;if(n<=0)goto done;offset+=(size_t)n;}
 token[0]='S';for(int i=0;i<16;i++)snprintf(token+1+i*2,3,"%02x",bytes[i]);
 snprintf(tmp,sizeof tmp,".cytv-stop-%s",token+1);
 fd=openat(dir,tmp,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);if(fd<0)goto done;created=1;
 if(fstat(dir,&s)<0||fchown(fd,(uid_t)-1,s.st_gid)<0)goto done;
 offset=0;while(offset<33){ssize_t n=write(fd,token+offset,33-offset);if(n<0&&errno==EINTR)continue;if(n<=0)goto done;offset+=(size_t)n;}
 if(fchmod(fd,0664)<0||fsync(fd)<0||fstat(fd,&staged)<0||!S_ISREG(staged.st_mode)||staged.st_uid!=getuid()||staged.st_gid!=s.st_gid||
    (staged.st_mode&07777)!=0664||staged.st_nlink!=1||staged.st_size!=33||fstatat(dir,tmp,&current,AT_SYMLINK_NOFOLLOW)<0||!cytv_generation_same(&staged,&current)||
    cytv_generation_leaf(dir,&s)<0||!cytv_generation_same_directory(dir)||renameat(dir,tmp,dir,"stop-generation")<0)goto done;
 created=0;ok=fsync(dir)==0&&cytv_generation_same_directory(dir);
done:if(!ok)cytv_generation_invalidate(dir);if(fd>=0)close(fd);if(created)unlinkat(dir,tmp,0);if(random>=0)close(random);close(dir);return ok;
}
#endif
