/* Private, inode-stable installer exclusion. A local lock is NOT a vendor
 * transaction barrier. Exec inherits fd 3; every effect child must retain it.
 * The lock and revocation tombstones are deliberately never removed. */
#define _GNU_SOURCE
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef CYTV_ROOT_LOCK_DIRECTORY
#define CYTV_ROOT_LOCK_DIRECTORY "/var/lib/clean-your-tv-installation"
#endif

static void refuse(void) { fputs("lifecycle-gate-unverified\n", stderr); exit(74); }
static int equal(struct stat a, struct stat b) { return a.st_dev == b.st_dev && a.st_ino == b.st_ino; }
static void directory(int fd, int mode) {
    struct stat s;
    if (fstat(fd, &s) || !S_ISDIR(s.st_mode) || (s.st_uid != 0 && s.st_uid != getuid())) refuse();
    if ((s.st_mode & 0022) && !(s.st_uid == 0 && (s.st_mode & S_ISVTX))) refuse();
    if (mode && (s.st_uid != getuid() || (mode==0750 && s.st_gid != getgid()) || (s.st_mode & 07777) != mode)) refuse();
}
static int open_root(const char *path,int mode) {
    char *copy, *part, *save = NULL;
    int fd, next;
    if (path[0] != '/' || strstr(path, "//") || path[strlen(path)-1] == '/') refuse();
    copy = strdup(path); if (!copy) refuse();
    fd = open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC); if (fd < 0) refuse();
    directory(fd, 0);
    for (part = strtok_r(copy, "/", &save); part; part = strtok_r(NULL, "/", &save)) {
        if (!strcmp(part,".") || !strcmp(part,"..")) refuse();
        next = openat(fd, part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
        if (next < 0) refuse();
        directory(next, (!save || *save == '\0')?mode:0); close(fd); fd = next;
    }
    free(copy); return fd;
}
static void regular(int fd) {
    struct stat s;
    if (fstat(fd, &s) || !S_ISREG(s.st_mode) || s.st_uid != getuid() || s.st_nlink != 1 ||
        s.st_gid != getgid() || (s.st_mode & 07777) != 0640) refuse();
}
static int marker(int root, const char *name, int create) {
    int fd = openat(root, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0 && errno == ENOENT && create) {
        fd = openat(root, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0640);
        if (fd < 0) refuse();
        if (write(fd, "revoked\n", 8) != 8 || fsync(fd) || fsync(root)) refuse();
    } else if (fd < 0 && errno == ENOENT) return 0;
    if (fd < 0) refuse();
    regular(fd); close(fd); return 1;
}
static int identifier(const char *value) {
    size_t i;if(strlen(value)!=32)return 0;
    for(i=0;i<32;i++)if(!strchr("0123456789abcdef",value[i]))return 0;
    return 1;
}
static int removal_owner(int root,const char *generation,int create) {
    int fd;char value[33];struct stat s;
    fd=openat(root,"removal-owner",O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0 && errno==ENOENT && create) {
        fd=openat(root,"removal-owner",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0640);
        if(fd<0 || write(fd,generation,32)!=32 || fsync(fd) || fsync(root))refuse();
        regular(fd);close(fd);return 1;
    }
    if(fd<0 && errno==ENOENT)return 0;
    if(fd<0)refuse();regular(fd);
    if(fstat(fd,&s) || s.st_size!=32 || read(fd,value,32)!=32)refuse();
    value[32]='\0';close(fd);if(!identifier(value))refuse();
    return !strcmp(value,generation)?1:-1;
}
static void execute(int root,int lock,char **command) {
    close(root);
    if(lock!=3){if(dup2(lock,3)<0)refuse();close(lock);}
    if(fcntl(3,F_SETFD,0)<0 || setenv("CYTV_LIFECYCLE_FD","3",1))refuse();
    execv(command[0],command);refuse();
}
static void root_lock(char **command) {
    int root=open_root(CYTV_ROOT_LOCK_DIRECTORY,0700),fd;
    struct stat s,named;
    fd=openat(root,"ownership.lock",O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);
    if(fd<0 || fstat(fd,&s) || !S_ISREG(s.st_mode) || s.st_uid!=getuid() ||
       s.st_nlink!=1 || (s.st_mode&07777)!=0600)refuse();
    if(flock(fd,LOCK_EX|LOCK_NB)){if(errno==EWOULDBLOCK || errno==EAGAIN)exit(75);refuse();}
    if(fstatat(root,"ownership.lock",&named,AT_SYMLINK_NOFOLLOW) || !equal(s,named))refuse();
    execute(root,fd,command);
}
int main(int argc, char **argv) {
    int root, lock, current, initialized, command=4,owner;
    struct stat opened, named, original, present;
    char revoked[48];
    if(argc>=3 && !strcmp(argv[1],"root-lock")){root_lock(argv+2);return 74;}
    if (argc < 4 || !identifier(argv[2]) || (strcmp(argv[3], "run") && strcmp(argv[3], "revoke") &&
        strcmp(argv[3],"remove") && strcmp(argv[3],"finish-removal"))) refuse();
    if ((!strcmp(argv[3],"run") && argc < 5) || (!strcmp(argv[3],"revoke") && argc != 4) ||
        (!strcmp(argv[3],"remove") && (argc<6 || !identifier(argv[4]))) ||
        (!strcmp(argv[3],"finish-removal") && argc!=4)) refuse();
    umask(0027); root = open_root(argv[1],0750); if (fstat(root, &original)) refuse();
    initialized = marker(root, "gate-established", 0);
    lock = openat(root, "lifecycle.lock", O_RDWR | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (lock < 0 && errno == ENOENT && !initialized)
        lock = openat(root, "lifecycle.lock", O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0640);
    if (lock < 0) refuse();
    regular(lock);
    while (flock(lock, LOCK_EX)) { if (errno != EINTR) refuse(); }
    regular(lock);
    if (fstat(lock, &opened) || fstatat(root, "lifecycle.lock", &named, AT_SYMLINK_NOFOLLOW) || !equal(opened,named)) refuse();
    if (fsync(lock) || fsync(root)) refuse();
    marker(root, "gate-established", 1);
    current = open_root(argv[1],0750);
    if (fstat(current, &present) || !equal(original,present)) refuse();
    close(current);
    owner=removal_owner(root,argv[2],0);if(owner<0)return 73;
    if(!strcmp(argv[3],"finish-removal")) {
        snprintf(revoked,sizeof(revoked),"completed-%s",argv[2]);
        if(owner!=1) {if(marker(root,revoked,0))return 0;refuse();}
        marker(root,revoked,1);
        if(unlinkat(root,"removal-owner",0) || fsync(root))refuse();return 0;
    }
    if(!strcmp(argv[3],"remove")) {
        if(!strcmp(argv[2],argv[4]))refuse();
        removal_owner(root,argv[2],1);
        snprintf(revoked,sizeof(revoked),"revoked-%s",argv[4]);marker(root,revoked,1);
        command=5;
    }
    snprintf(revoked, sizeof(revoked), "revoked-%s", argv[2]);
    if (!strcmp(argv[3], "revoke")) { marker(root, revoked, 1); close(root); close(lock); return 0; }
    if (marker(root, revoked, 0)) return 73;
    execute(root,lock,argv+command);return 74;
}
