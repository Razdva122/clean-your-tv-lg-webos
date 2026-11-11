#define _GNU_SOURCE
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <stdarg.h>
#include <errno.h>
static char generation_directory[256];
static int entropy_failure,temporary_failure,write_probe_failure;
static int generation_open(const char *name,int flags,...){
 if(entropy_failure&&!strcmp(name,"/dev/urandom")){errno=EIO;return -1;}
 return open(name,flags);
}
static int generation_openat(int dir,const char *name,int flags,...){
 if(write_probe_failure&&!strcmp(name,"stop-generation")&&(flags&O_ACCMODE)==O_RDWR){errno=EACCES;return -1;}
 if(temporary_failure&&!strncmp(name,".cytv-stop-",11)){errno=EIO;return -1;}
 mode_t mode=0;if(flags&O_CREAT){va_list args;va_start(args,flags);mode=(mode_t)va_arg(args,int);va_end(args);}
 return openat(dir,name,flags,mode);
}
#define CYTV_GENERATION_DIRECTORY generation_directory
#define open generation_open
#define openat generation_openat
#include "../app/stop-generation.h"
#undef open
#undef openat
int main(void) {
 strcpy(generation_directory,"/tmp/cytv-generation-XXXXXX");
 assert(mkdtemp(generation_directory));
 char resolved[1024];assert(realpath(generation_directory,resolved));assert(strlen(resolved)<sizeof generation_directory);strcpy(generation_directory,resolved);
 assert(chown(generation_directory,(uid_t)-1,getgid())==0);
 char a[34],b[34],file[300];
 assert(!cytv_generation_read(a));
 assert(cytv_generation_publish());assert(cytv_generation_read(a));
 assert(a[0]=='S'&&strlen(a)==33);
 write_probe_failure=1;assert(!cytv_generation_read(b));write_probe_failure=0;assert(cytv_generation_read(b)&&!strcmp(a,b));
 assert(cytv_generation_publish());assert(cytv_generation_read(b));
 assert(strcmp(a,b));
 snprintf(file,sizeof file,"%s/stop-generation",generation_directory);
 assert(chmod(file,0644)==0);assert(!cytv_generation_read(b));assert(!cytv_generation_publish());assert(chmod(file,0664)==0);
 for(int fault=0;fault<2;fault++){
  entropy_failure=fault==0;temporary_failure=fault==1;
  assert(!cytv_generation_publish());assert(!cytv_generation_read(b));
  struct stat invalid;assert(stat(file,&invalid)==0&&invalid.st_size==0);
  entropy_failure=temporary_failure=0;assert(cytv_generation_publish());
  assert(unlink(file)==0);entropy_failure=fault==0;temporary_failure=fault==1;
  assert(!cytv_generation_publish());assert(stat(file,&invalid)==0&&invalid.st_size==0);assert(!cytv_generation_read(b));
  entropy_failure=temporary_failure=0;assert(cytv_generation_publish());
 }
 int fd=open(file,O_WRONLY|O_TRUNC);assert(fd>=0);assert(write(fd,"bad",3)==3);close(fd);
 assert(!cytv_generation_read(b));
 assert(unlink(file)==0);assert(symlink("outside",file)==0);
 assert(!cytv_generation_publish());assert(!cytv_generation_read(b));
 assert(unlink(file)==0);assert(rmdir(generation_directory)==0);
 puts("PASS: real native Stop generation replacement and malformed/symlink refusal");
}
