/* Independent compositor input/lifecycle health guardian. No mount operations. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/statvfs.h>
#ifdef __linux__
#include <sys/vfs.h>
#else
#include <sys/mount.h>
#endif
#include <time.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/prctl.h>
#endif
#ifdef CYTV_KEYFILTER_FIXTURE
#define STATE FIXTURE_ROOT "/state"
#define VOLATILE FIXTURE_ROOT "/volatile"
#define HOME FIXTURE_ROOT "/home"
#define LUNA FIXTURE_ROOT "/luna"
#define BOOT FIXTURE_ROOT "/boot"
#define TRUST_UID getuid()
#else
#define STATE "/var/lib/clean-your-tv-root/c1-keyfilter"
#define VOLATILE "/tmp/clean-your-tv-root-keyfilter"
#define HOME "/usr/bin/com.webos.app.home"
#define LUNA "/usr/bin/luna-send"
#define BOOT "/proc/sys/kernel/random/boot_id"
#define TRUST_UID 0
#endif
static volatile sig_atomic_t interrupted;
static void on_signal(int s) { interrupted = s; }
static long long now_ms(void) {
  struct timespec t;
  if (clock_gettime(CLOCK_MONOTONIC, &t))
    return -1;
  return (long long)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static unsigned long long mtime_ns(struct stat *s) {
#ifdef __APPLE__
  return (unsigned long long)s->st_mtimespec.tv_sec * 1000000000ULL +
         s->st_mtimespec.tv_nsec;
#else
  return (unsigned long long)s->st_mtim.tv_sec * 1000000000ULL +
         s->st_mtim.tv_nsec;
#endif
}
static int secure(const char *path, int directory) {
  struct stat s;
  return !lstat(path, &s) && s.st_uid == TRUST_UID && !(s.st_mode & 022) &&
         (directory ? S_ISDIR(s.st_mode) : S_ISREG(s.st_mode));
}
static int trusted_parents(const char *path) {
  char p[PATH_MAX];
  if (strlen(path) >= sizeof(p) || path[0] != '/')
    return 0;
  strcpy(p, path);
  for (char *q = p + 1; *q; q++)
    if (*q == '/') {
      *q = 0;
      struct stat s;
      if (lstat(p, &s) || !S_ISDIR(s.st_mode) ||
          (s.st_uid != TRUST_UID && s.st_uid != 0) ||
          ((s.st_mode & 022) && !(s.st_mode & S_ISVTX)))
        return 0;
      *q = '/';
    }
  return 1;
}
static int readfile(const char *path, char *buf, size_t size, int private) {
  int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
  if (fd < 0)
    return -1;
  struct stat s;
  if (fstat(fd, &s) ||
      (private &&
       (!S_ISREG(s.st_mode) || s.st_uid != TRUST_UID || (s.st_mode & 0777) != 0600))) {
    close(fd);
    return -1;
  }
  size_t n = 0;
  for (;;) {
    ssize_t z = read(fd, buf + n, size - 1 - n);
    if (z < 0 && errno == EINTR)
      continue;
    if (z < 0) {
      close(fd);
      return -1;
    }
    if (!z)
      break;
    n += (size_t)z;
    if (n == size - 1) {
      char c;
      if (read(fd, &c, 1) != 0) {
        close(fd);
        return -1;
      }
      break;
    }
  }
  close(fd);
  if (memchr(buf, 0, n))
    return -1;
  buf[n] = 0;
  return (int)n;
}
static int save(const char *name, const char *data) {
  char path[PATH_MAX], tmp[PATH_MAX];
  snprintf(path, sizeof(path), STATE "/%s", name);
  snprintf(tmp, sizeof(tmp), STATE "/.%s.%ld", name, (long)getpid());
  int f = open(tmp, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
  if (f < 0)
    return 0;
  size_t n = strlen(data), off = 0;
  while (off < n) {
    ssize_t z = write(f, data + off, n - off);
    if (z < 0 && errno == EINTR)
      continue;
    if (z <= 0) {
      close(f);
      unlink(tmp);
      return 0;
    }
    off += (size_t)z;
  }
  int ok = fsync(f) == 0;
  close(f);
  if (ok)
    ok = rename(tmp, path) == 0;
  if (!ok)
    unlink(tmp);
  int d = open(STATE, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
  if (d < 0)
    return 0;
  if (fsync(d))
    ok = 0;
  close(d);
  return ok;
}
static int erase(const char *name) {
  char path[PATH_MAX];
  snprintf(path, sizeof(path), STATE "/%s", name);
  if (unlink(path) && errno != ENOENT)
    return 0;
  int d = open(STATE, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
  if (d < 0)
    return 0;
  int ok = !fsync(d);
  close(d);
  return ok;
}
static int digits(const char *s, size_t n) {
  if (!n || n > 20 || (n > 1 && *s == '0'))
    return 0;
  for (size_t i = 0; i < n; i++)
    if (s[i] < '0' || s[i] > '9')
      return 0;
  return 1;
}
static int hex32(const char *s) {
  if (strlen(s) != 32)
    return 0;
  for (int i = 0; i < 32; i++)
    if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f')))
      return 0;
  return 1;
}
static int uuid(const char *s) {
  if (strlen(s) != 36)
    return 0;
  for (int i = 0; i < 36; i++)
    if (i == 8 || i == 13 || i == 18 || i == 23) {
      if (s[i] != '-')
        return 0;
    } else if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f')))
      return 0;
  return 1;
}
struct config {
  char token[33], boot[37];
  unsigned long long dev, ino, size, mtime;
};
static struct config cfg;
static int boot_matches;
static int uintline(char **p, const char *key, unsigned long long *v) {
  size_t n = strlen(key);
  if (strncmp(*p, key, n))
    return 0;
  char *start = *p + n, *end = strchr(start, '\n');
  if (!end || !digits(start, (size_t)(end - start)))
    return 0;
  errno = 0;
  char *tail;
  *v = strtoull(start, &tail, 10);
  if (errno || tail != end)
    return 0;
  *p = end + 1;
  return 1;
}
static int config_read(void) {
  char b[512], boot[64];
  int n = readfile(STATE "/config", b, sizeof(b), 1);
  if (n < 0)
    return 0;
  char *p = b;
  if (strncmp(p, "CYTV-C1-KEYFILTER-1\ntoken ", 26))
    return 0;
  p += 26;
  if (strlen(p) < 33 || p[32] != '\n')
    return 0;
  memcpy(cfg.token, p, 32);
  cfg.token[32] = 0;
  p += 33;
  if (!hex32(cfg.token) || strncmp(p, "boot ", 5) || strlen(p) < 42)
    return 0;
  p += 5;
  memcpy(cfg.boot, p, 36);
  cfg.boot[36] = 0;
  if (p[36] != '\n' || !uuid(cfg.boot))
    return 0;
  p += 37;
  if (!uintline(&p, "dev ", &cfg.dev) || !uintline(&p, "ino ", &cfg.ino) ||
      !uintline(&p, "size ", &cfg.size) ||
      !uintline(&p, "mtime_ns ", &cfg.mtime) || *p)
    return 0;
  if (readfile(BOOT, boot, sizeof(boot), 0) != 37 || boot[36] != '\n')
    return 0;
  boot[36] = 0;
  boot_matches = !strcmp(boot, cfg.boot);
  return 1;
}
/* Called while holding the operation lock. A delayed old process cannot mutate
 * a newer attempt after it dropped that lock for input, child work or
 * retirement. */
static int same_config(void) {
  struct config expected = cfg;
  int previous_boot = boot_matches;
  int valid = config_read();
  int same = valid && !strcmp(expected.token, cfg.token) &&
             !strcmp(expected.boot, cfg.boot) && expected.dev == cfg.dev &&
             expected.ino == cfg.ino && expected.size == cfg.size &&
             expected.mtime == cfg.mtime;
  cfg = expected;
  boot_matches = previous_boot;
  return same;
}
static int stock_identity(void) {
  if (!trusted_parents(HOME)) return 0;
  int fd = open(HOME, O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
  if (fd < 0) return 0;
  struct stat s;
  int ok = !fstat(fd, &s) && S_ISREG(s.st_mode) && s.st_nlink == 1 &&
           !(s.st_mode & 07022) && (s.st_mode & 0111) &&
           s.st_size >= 52 && s.st_size <= 16 * 1024 * 1024;
  if (ok && s.st_uid != TRUST_UID) {
    struct statfs fs;
    struct statvfs vfs;
    ok = s.st_uid == 1001 && !fstatfs(fd, &fs) && !fstatvfs(fd, &vfs) &&
         (vfs.f_flag & ST_RDONLY);
#ifdef __linux__
    ok = ok && fs.f_type == 0x73717368;
#else
    ok = ok && !strcmp(fs.f_fstypename, "squashfs");
#endif
  }
  ok = ok && (unsigned long long)s.st_dev == cfg.dev &&
       (unsigned long long)s.st_ino == cfg.ino &&
       (unsigned long long)s.st_size == cfg.size && mtime_ns(&s) == cfg.mtime;
  close(fd);
  return ok;
}
static unsigned long long parse_proc_start(const char *b) {
  const char *p = strrchr(b, ')');
  if (!p || p[1] != ' ' || !p[2] || p[3] != ' ' || p[2] == 'Z' || p[2] == 'X' ||
      p[2] == 'x')
    return 0;
  p += 2;
  for (int f = 3; f < 22; f++) {
    p = strchr(p, ' ');
    if (!p)
      return 0;
    p++;
  }
  const char *end = p;
  while (*end >= '0' && *end <= '9')
    end++;
  if (!digits(p, (size_t)(end - p)) || (*end && *end != ' ' && *end != '\n'))
    return 0;
  errno = 0;
  unsigned long long start = strtoull(p, NULL, 10);
  return errno ? 0 : start;
}
static unsigned long long process_start(long pid) {
#if defined(CYTV_KEYFILTER_FIXTURE) && defined(__APPLE__)
  char cmd[128], b[256];
  snprintf(cmd, sizeof(cmd), "/bin/ps -p %ld -o stat= -o lstart=", pid);
  FILE *f = popen(cmd, "r");
  if (!f) return 0;
  char *ok = fgets(b, sizeof(b), f);
  pclose(f);
  if (!ok) return 0;
  char *p = b;
  while (*p == ' ' || *p == '\t') p++;
  if (*p == 'Z' || *p == 'X') return 0;
  while (*p && *p != ' ' && *p != '\t') p++;
  unsigned long long hash = 1;
  for (; *p; p++) hash = hash * 33 + (unsigned char)*p;
  return hash;
#else
  char path[64], b[4096];
  snprintf(path, sizeof(path), "/proc/%ld/stat", pid);
  return readfile(path, b, sizeof(b), 0) < 0 ? 0 : parse_proc_start(b);
#endif
}
static int latch_read(char *reason) {
  char b[160], token[33], why[64];
  int used = 0, n = readfile(STATE "/stopped", b, sizeof(b), 1);
  if (n < 0) {
    struct stat suspect;
    return lstat(STATE "/stopped", &suspect) == 0 || errno != ENOENT ? -1 : 0;
  }
  if (sscanf(b, "%32[a-f0-9] %63[a-z_]\n%n", token, why, &used) != 2 ||
      used != n || !hex32(token))
    return -1;
  if (strcmp(token, cfg.token))
    return 0;
  strcpy(reason, why);
  return 1;
}
static int stop(const char *reason) {
  if (!same_config())
    return 0;
  char old[64], b[160];
  int latched = latch_read(old);
  if (latched < 0)
    return 0;
  if (latched > 0)
    reason = old;
  snprintf(b, sizeof(b), "%s %s\n", cfg.token, reason);
  return save("stopped", b) && save("outcome", b);
}
/* Persistent identity is written once. Heartbeats stay in private volatile files. */
static struct {
  char token[33], boot[37];
  long pid;
  unsigned long long start;
  long long born;
} active;
static int private_dir(const char *path) {
  struct stat s;
  return trusted_parents(path) && !lstat(path, &s) &&
         S_ISDIR(s.st_mode) && s.st_uid == TRUST_UID && !(s.st_mode & 077);
}
static int private_lock(const char *name,int milliseconds) {
  if (!private_dir(STATE) || !trusted_parents(STATE "/config")) return -1;
  char path[PATH_MAX];
  snprintf(path,sizeof(path),STATE "/%s",name);
  int fd = open(path, O_RDWR|O_CREAT|O_NOFOLLOW|O_CLOEXEC, 0600);
  struct stat s;
  if (fd < 0) return -1;
  if (fstat(fd,&s) || !S_ISREG(s.st_mode) || s.st_uid != TRUST_UID ||
      (s.st_mode & 077)) { close(fd); return -1; }
  long long until = now_ms()+milliseconds;
  while (flock(fd,LOCK_EX|LOCK_NB)) {
    if ((errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) || now_ms()>=until) {
      close(fd); return -1;
    }
    poll(NULL,0,5);
  }
  return fd;
}
static int lock_wait(int milliseconds) { return private_lock("lock",milliseconds); }
static int lock_state(void) { return lock_wait(1000); }
static int effect_fd=-1;
static int absent(const char *path) {
  struct stat s;
  return lstat(path,&s) && errno == ENOENT;
}
static int active_read(void) {
  char b[256], expected[256];
  memset(&active,0,sizeof(active));
  int n = readfile(STATE "/active",b,sizeof(b),1);
  if (n < 0) return absent(STATE "/active") ? 0 : -1;
  if (sscanf(b,"CYTV-KEYFILTER-ACTIVE-1\n%32[a-f0-9]\n%36[a-f0-9-]\n%ld %llu %lld",
             active.token,active.boot,&active.pid,&active.start,&active.born) != 5 ||
      !hex32(active.token) || !uuid(active.boot) || active.pid <= 1 ||
      active.pid > INT_MAX || !active.start || active.born < 0) return -1;
  snprintf(expected,sizeof(expected),"CYTV-KEYFILTER-ACTIVE-1\n%s\n%s\n%ld %llu %lld\n",
           active.token,active.boot,active.pid,active.start,active.born);
  return !strcmp(b,expected) && !strcmp(active.token,cfg.token) &&
         !strcmp(active.boot,cfg.boot) ? 1 : -1;
}
static int active_live(void) {
  return boot_matches && active.pid > 1 && active.start &&
         process_start(active.pid) == active.start;
}
static int active_write(void) {
  char b[256];
  snprintf(b,sizeof(b),"CYTV-KEYFILTER-ACTIVE-1\n%s\n%s\n%ld %llu %lld\n",
           active.token,active.boot,active.pid,active.start,active.born);
  return save("active",b);
}
static int volatile_ready(void) {
  if (mkdir(VOLATILE,0700) && errno != EEXIST) return 0;
  return private_dir(VOLATILE);
}
static int pulse_write(const char *name, long long input, long long control, int armed) {
  if (!private_dir(VOLATILE)) return 0;
  char p[PATH_MAX], tmp[PATH_MAX], b[256];
  snprintf(p,sizeof(p),VOLATILE "/%s",name);
  snprintf(tmp,sizeof(tmp),VOLATILE "/.%s.%ld",name,(long)getpid());
  int n=snprintf(b,sizeof(b),"%s %ld %llu %lld %lld %d\n",active.token,active.pid,
                 active.start,input,control,armed);
  int fd=open(tmp,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
  if (fd<0) return 0;
  int ok=write(fd,b,(size_t)n)==n;
  close(fd);
  if (ok) ok=!rename(tmp,p);
  if (!ok) unlink(tmp);
  return ok;
}
static int pulse_read(const char *name, long long *input, long long *control, int *armed) {
  char p[PATH_MAX], b[256], expected[256], token[33];
  long pid; unsigned long long start;
  if (!private_dir(VOLATILE)) return 0;
  snprintf(p,sizeof(p),VOLATILE "/%s",name);
  if (readfile(p,b,sizeof(b),1)<0 ||
      sscanf(b,"%32[a-f0-9] %ld %llu %lld %lld %d",token,&pid,&start,input,control,armed)!=6 ||
      *input<0 || *control<0 || (*armed!=0 && *armed!=1)) return 0;
  snprintf(expected,sizeof(expected),"%s %ld %llu %lld %lld %d\n",token,pid,start,*input,*control,*armed);
  return !strcmp(expected,b) && !strcmp(token,active.token) &&
         ((pid==active.pid && start==active.start) ||
          (!strcmp(name,"broker") && pid==0 && start==0));
}
static int fresh(long long stamp) {
  long long now=now_ms();
  return stamp>0 && now>=stamp && now-stamp<2000;
}
static int health(void) {
  long long i,c,b,u; int armed,unused;
  return active_live() && stock_identity() &&
         pulse_read("health",&i,&c,&armed) && armed && fresh(i) && fresh(c) &&
         pulse_read("broker",&b,&u,&unused) && fresh(b);
}
/* A bounded valid startup is stock routing, but not retired-stock proof. */
static int pending(void) {
  long long i,c,b,u; int armed,unused;
  return active_live() && stock_identity() && now_ms()>=active.born &&
         now_ms()-active.born<2000 &&
         pulse_read("health",&i,&c,&armed) && !armed &&
         (!i || fresh(i)) && (!c || fresh(c)) &&
         ((pulse_read("broker",&b,&u,&unused) && fresh(b)) || absent(VOLATILE "/broker"));
}
static int reply(int success, int valid, const char *reason) {
  char why[64];
  int jr=valid ? active_read() : -1;
  int stopped=valid ? latch_read(why) : -1;
  valid=valid && jr>=0 && stopped>=0;
  int healthy=valid && jr>0 && !stopped && health();
  int stock=valid && stock_identity() && (jr==0 || !active_live());
  const char *state=!valid ? "blocked" : healthy ? "armed" : stopped ? "stopped" : (stock || (jr>0 && pending())) ? "stock" : "blocked";
  if (stopped>0 && !strcmp(reason,"none")) reason=why;
  printf("{\"returnValue\":%s,\"backend\":\"c1-native-gate\",\"routing\":\"compositor-keyfilter-v1\","
         "\"state\":\"%s\",\"mounted\":false,\"healthy\":%s,\"stock_verified\":%s,"
         "\"stopped\":%s,\"token\":\"%s\",\"guardian_pid\":%ld,\"reason\":\"%s\",\"profiles\":null}\n",
         success&&valid ? "true":"false",state,healthy ? "true":"false",stock ? "true":"false",
         stopped!=0 ? "true":"false",cfg.token,jr>0 ? active.pid:0,reason);
  return success&&valid ? 0:1;
}
static int channel_fd(int fd, int output) {
  struct stat s; int flags=fcntl(fd,F_GETFL);
  return fd>2 && flags>=0 && !fstat(fd,&s) && S_ISFIFO(s.st_mode) &&
         (output ? (flags&O_ACCMODE)!=O_RDONLY : (flags&O_ACCMODE)==O_RDONLY);
}
static int separate_pipes(int a,int b) {
  struct stat x,y;
  return !fstat(a,&x) && !fstat(b,&y) && (x.st_dev!=y.st_dev || x.st_ino!=y.st_ino);
}
struct channel { char line[17]; size_t len; long long last; int ready; };
static const char *consume(int fd,struct channel *c,int controller) {
  char ch;
  ssize_t n=read(fd,&ch,1);
  if (n<0 && (errno==EINTR || errno==EAGAIN)) return NULL;
  if (n<=0) return controller ? "controller_lost":"input_lost";
  if (ch=='\n') {
    c->line[c->len]=0; c->len=0;
    if ((!c->ready && !strcmp(c->line,"READY")) || (c->ready && !strcmp(c->line,"PING"))) {
      c->ready=1; c->last=now_ms(); return NULL;
    }
    if (!strcmp(c->line,"ESCAPE")) return "escape";
    if (!strcmp(c->line,"LGHOME")) return "lg_home";
    if (!strcmp(c->line,"LOST")) return controller ? "controller_lost":"input_lost";
    return "malformed_input";
  }
  if (ch<'A' || ch>'Z' || c->len>=16) return "malformed_input";
  c->line[c->len++]=ch;
  return NULL;
}
#define LIMIT 16384
/* Bounded JSON parser. Keys are unescaped ASCII; duplicate keys are rejected.
 */
struct jt {
  int start, end, next, children;
  char type;
};
struct json {
  const char *s;
  int p, n, count;
  struct jt t[512];
};
static void ws(struct json *j) {
  while (j->p < j->n && strchr(" \t\r\n", j->s[j->p]))
    j->p++;
}
static int value(struct json *j, int depth);
static int string(struct json *j, int key) {
  int start = j->p++;
  while (j->p < j->n) {
    unsigned char c = (unsigned char)j->s[j->p++];
    if (c == '"')
      return start;
    if (c < 32 || c >= 128)
      return -1;
    if (c == '\\') {
      if (key || j->p >= j->n)
        return -1;
      char e = j->s[j->p++];
      if (strchr("\"\\/bfnrt", e))
        continue;
      if (e != 'u' || j->p + 4 > j->n)
        return -1;
      for (int x = 0; x < 4; x++)
        if (!strchr("0123456789abcdefABCDEF", j->s[j->p++]))
          return -1;
    }
  }
  return -1;
}
static int value(struct json *j, int depth) {
  ws(j);
  if (depth > 16 || j->count >= 512 || j->p >= j->n)
    return -1;
  int id = j->count++;
  struct jt *t = &j->t[id];
  t->start = j->p;
  t->children = 0;
  char c = j->s[j->p];
  t->type = c;
  if (c == '{' || c == '[') {
    j->p++;
    ws(j);
    char end = c == '{' ? '}' : ']';
    if (j->p < j->n && j->s[j->p] == end)
      j->p++;
    else
      for (;;) {
        if (c == '{') {
          ws(j);
          if (j->p >= j->n || j->s[j->p] != '"' || j->count >= 512)
            return -1;
          int k = j->count++;
          j->t[k].start = j->p;
          if (string(j, 1) < 0)
            return -1;
          j->t[k].end = j->p;
          j->t[k].next = k + 1;
          j->t[k].type = '"';
          for (int old = id + 1; old < k; old = j->t[old + 1].next) {
            int a = j->t[old].start, b = j->t[old].end;
            if (b - a == j->p - j->t[k].start &&
                !memcmp(j->s + a, j->s + j->t[k].start, (size_t)(b - a)))
              return -1;
          }
          ws(j);
          if (j->p >= j->n || j->s[j->p++] != ':')
            return -1;
        }
        if (value(j, depth + 1) < 0)
          return -1;
        t->children++;
        ws(j);
        if (j->p >= j->n)
          return -1;
        if (j->s[j->p] == end) {
          j->p++;
          break;
        }
        if (j->s[j->p++] != ',')
          return -1;
      }
  } else if (c == '"') {
    if (string(j, 0) < 0)
      return -1;
  } else if (c == 't' || c == 'f' || c == 'n') {
    const char *s = c == 't' ? "true" : c == 'f' ? "false" : "null";
    int n = (int)strlen(s);
    if (j->n - j->p < n || memcmp(j->s + j->p, s, (size_t)n))
      return -1;
    j->p += n;
  } else {
    int p = j->p;
    if (j->s[j->p] == '-')
      j->p++;
    if (j->p >= j->n)
      return -1;
    if (j->s[j->p] == '0')
      j->p++;
    else {
      if (j->s[j->p] < '1' || j->s[j->p] > '9')
        return -1;
      while (j->p < j->n && j->s[j->p] >= '0' && j->s[j->p] <= '9')
        j->p++;
    }
    if (j->p < j->n && j->s[j->p] == '.') {
      j->p++;
      int b = j->p;
      while (j->p < j->n && j->s[j->p] >= '0' && j->s[j->p] <= '9')
        j->p++;
      if (b == j->p)
        return -1;
    }
    if (j->p < j->n && (j->s[j->p] == 'e' || j->s[j->p] == 'E')) {
      j->p++;
      if (j->p < j->n && (j->s[j->p] == '+' || j->s[j->p] == '-'))
        j->p++;
      int b = j->p;
      while (j->p < j->n && j->s[j->p] >= '0' && j->s[j->p] <= '9')
        j->p++;
      if (b == j->p)
        return -1;
    }
    if (j->p == p)
      return -1;
    t->type = '0';
  }
  t->end = j->p;
  t->next = j->count;
  return id;
}
static int parse(struct json *j, const char *s) {
  memset(j, 0, sizeof(*j));
  size_t n = strnlen(s, LIMIT + 1);
  if (n > LIMIT)
    return 0;
  j->s = s;
  j->n = (int)n;
  if (value(j, 0) != 0 || j->t[0].type != '{')
    return 0;
  ws(j);
  return j->p == j->n;
}
static int field(struct json *j, int obj, const char *name) {
  if (j->t[obj].type != '{')
    return -1;
  for (int i = obj + 1; i < j->t[obj].next; i = j->t[i + 1].next) {
    struct jt *t = &j->t[i];
    if (t->end - t->start == (int)strlen(name) + 2 &&
        !memcmp(j->s + t->start + 1, name, strlen(name)))
      return i + 1;
  }
  return -1;
}
static int literal(struct json *j, int id, const char *s) {
  return id >= 0 && j->t[id].end - j->t[id].start == (int)strlen(s) &&
         !memcmp(j->s + j->t[id].start, s, strlen(s));
}
/* Child has a new process group, fixed argv/env, capped output and deadline. */
static int luna(const char *method, const char *app) {
  int out[2], in[2];
  if (!secure(LUNA, 0) || !trusted_parents(LUNA) || access(LUNA, X_OK))
    return 0;
  if (pipe(out))
    return 0;
  if (pipe(in)) {
    close(out[0]);
    close(out[1]);
    return 0;
  }
  pid_t owner=getpid();
  pid_t pid = fork();
  if (pid < 0) {
    close(out[0]);
    close(out[1]);
    close(in[0]);
    close(in[1]);
    return 0;
  }
  if (!pid) {
#ifdef __linux__
    if (prctl(PR_SET_PDEATHSIG,SIGKILL) || getppid()!=owner) _exit(127);
#else
    (void)owner;
#endif
    setpgid(0, 0);
    dup2(in[0], 0);
    dup2(out[1], 1);
    dup2(out[1], 2);
    struct rlimit r;
    unsigned long max = 65536;
    if (!getrlimit(RLIMIT_NOFILE, &r) && r.rlim_cur < max)
      max = (unsigned long)r.rlim_cur;
    /* Retain the effect lock through exec: even abrupt parent death cannot
     * let a successful restore overtake this still-running fixed LS2 child. */
    if (effect_fd>=0) fcntl(effect_fd,F_SETFD,0);
    for (unsigned long f = 3; f < max; f++)
      if ((int)f!=effect_fd) close((int)f);
    char payload[160];
    snprintf(payload, sizeof(payload), "{\"id\":\"%s\"}", app);
    char *args[] = {LUNA,    "-n",
                    "1",     (char *)method,
                    payload, NULL};
    char *env[] = {"PATH=/usr/bin:/bin", "LANG=C", NULL};
    execve(LUNA, args, env);
    _exit(127);
  }
  setpgid(pid, pid);
  close(out[1]);
  close(in[0]);
  fcntl(out[0], F_SETFL, O_NONBLOCK);
  char b[LIMIT + 1];
  size_t n = 0;
  long long deadline = now_ms() + 2000;
  int status = 0, done = 0, ok = 1;
  while (!done) {
    if (now_ms() >= deadline || interrupted) {
      ok = 0;
      break;
    }
    struct pollfd p = {out[0], POLLIN | POLLHUP, 0};
    int z = poll(&p, 1, 25);
    if (z < 0 && errno != EINTR) {
      ok = 0;
      break;
    }
    for (;;) {
      ssize_t r = read(out[0], b + n, LIMIT - n);
      if (r > 0) {
        n += (size_t)r;
        if (n >= LIMIT) {
          ok = 0;
          break;
        }
      } else if (r < 0 && errno == EINTR)
        continue;
      else
        break;
    }
    if (!ok)
      break;
    pid_t w = waitpid(pid, &status, WNOHANG);
    if (w == pid)
      done = 1;
    else if (w < 0 && errno != EINTR) {
      ok = 0;
      break;
    }
  }
  kill(-pid, SIGKILL);
  if (!done) {
    long long reap_deadline = now_ms() + 250;
    while (now_ms() < reap_deadline) {
      pid_t reaped = waitpid(pid, &status, WNOHANG);
      if (reaped == pid) {
        done = 1;
        break;
      }
      if (reaped < 0 && errno != EINTR)
        break;
      poll(NULL, 0, 5);
    }
    if (!done)
      ok = 0;
  }
  close(in[1]);
  close(out[0]);
  if (!ok || memchr(b, 0, n) || !WIFEXITED(status) || WEXITSTATUS(status))
    return 0;
  b[n] = 0;
  struct json j;
  if (!parse(&j,b)) return 0;
  if (literal(&j,field(&j,0,"returnValue"),"true")) return 1;
  /* SAM PolicyManager::close uses ErrCode_CLOSE (40) when this exact app
   * already has no running instance. Only that owned close is idempotent. */
  return !strcmp(method,"luna://com.webos.applicationManager/closeByAppId") &&
         !strcmp(app,"com.cleanyourtv.root.preview") &&
         literal(&j,field(&j,0,"returnValue"),"false") &&
         literal(&j,field(&j,0,"errorCode"),"40") &&
         literal(&j,field(&j,0,"errorText"),
                 "\"com.cleanyourtv.root.preview is not running\"");
}
/* Routing is already durably stopped before these bounded best-effort UI calls.
 * Replies establish LS2 acknowledgement only, never physical visibility. */
static int release_ui(void) {
  interrupted=0;
  int closed=luna("luna://com.webos.applicationManager/closeByAppId",
                  "com.cleanyourtv.root.preview");
  int launched=luna("luna://com.webos.applicationManager/launch",
                    "com.webos.app.home");
  return closed && launched;
}
static int guard(const char *token,int input,int control,int ready,int seconds,int lock) {
  char why[64];
  if (!boot_matches || !hex32(token) || strcmp(token,cfg.token) ||
      !channel_fd(input,0) || !channel_fd(control,0) || !channel_fd(ready,1) ||
      input==control || input==ready || control==ready ||
      !separate_pipes(input,control) || !separate_pipes(input,ready) || !separate_pipes(control,ready) ||
      !stock_identity() ||
      latch_read(why)!=0 || active_read()!=0 || !volatile_ready()) {
    close(lock); return reply(0,1,"guard_refused");
  }
  strcpy(active.token,token); strcpy(active.boot,cfg.boot);
  active.pid=getpid(); active.start=process_start(active.pid); active.born=now_ms();
  /* A new explicit attempt owns fresh volatile evidence. Retire the prior
   * broker pulse under the state lock; even a same-token pre-guard pulse must
   * be renewed by an actual subscriber after this guardian starts. */
  int broker_retired=unlink(VOLATILE "/broker")==0 || errno==ENOENT;
  if (!broker_retired || !active.start || !active_write() || !pulse_write("health",0,0,0)) {
    stop("journal_failed"); close(lock); return reply(0,1,"journal_failed");
  }
  close(lock);
  signal(SIGTERM,on_signal); signal(SIGINT,on_signal); signal(SIGHUP,on_signal);
  signal(SIGQUIT,on_signal); signal(SIGUSR1,on_signal); signal(SIGUSR2,on_signal);
  signal(SIGALRM,on_signal); signal(SIGPIPE,SIG_IGN);
  fcntl(ready,F_SETFL,fcntl(ready,F_GETFL)|O_NONBLOCK);
  struct channel channels[2]; memset(channels,0,sizeof(channels));
  long long born=active.born;
  int armed=0;
  const char *reason=NULL;
  while (!reason) {
    struct pollfd fds[2]={{input,POLLIN|POLLHUP,0},{control,POLLIN|POLLHUP,0}};
    int z=poll(fds,2,20);
    if (z<0 && errno!=EINTR) { reason="input_lost"; break; }
    for (int x=0;x<2 && !reason;x++)
      if (fds[x].revents) reason=consume(fds[x].fd,&channels[x],x);
    if (reason) break;
    lock=lock_wait(3000);
    if (lock<0) { reason="state_busy"; break; }
    if (!same_config() || active_read()!=1 || active.pid!=(long)getpid() ||
        active.start!=process_start(getpid())) { close(lock); return reply(0,1,"stale_attempt"); }
    long long now=now_ms(), b=0,u=0; int unused=0;
    int broker=pulse_read("broker",&b,&u,&unused);
    if (interrupted) reason="signal";
    else if (latch_read(why)!=0) reason="external_stop";
    else if (!stock_identity()) reason="home_changed";
    else if (seconds && now-born>=seconds*1000LL) reason="trial_expired";
    else if (now-(channels[0].ready ? channels[0].last:born)>=2000) reason="input_expired";
    else if (now-(channels[1].ready ? channels[1].last:born)>=2000) reason="controller_expired";
    else if ((broker && !fresh(b)) ||
             (!broker && (armed || !absent(VOLATILE "/broker") || now-born>=2000))) reason="broker_expired";
    if (!reason && !armed && channels[0].ready && channels[1].ready && broker && fresh(b)) {
      char ack[80]; int n=snprintf(ack,sizeof(ack),"ARMED %s\n",token);
      /* Publish health only together with the readiness acknowledgement. */
      if (!pulse_write("health",channels[0].last,channels[1].last,1) || write(ready,ack,(size_t)n)!=n)
        reason="ready_failed";
      else { armed=1; close(ready); ready=-1; }
    } else if (!reason && !pulse_write("health",channels[0].last,channels[1].last,armed)) reason="journal_failed";
    close(lock);
  }
  if (ready>=0) close(ready);
  close(input); close(control);
  lock=lock_wait(3000);
  if (lock<0) return reply(0,1,"recovery_busy");
  if (!same_config() || active_read()!=1 || active.pid!=(long)getpid() ||
      active.start!=process_start(getpid())) { close(lock); return reply(0,1,"stale_attempt"); }
  /* Explicit restore owns UI release after this process has retired. */
  int delegated=latch_read(why)>0 && !strcmp(why,"explicit_off");
  int ok=stop(reason);
  /* Identity is unchanged and this guardian is retiring. Keep records on error. */
  if (ok) ok=erase("active");
  if (ok && !delegated) {
    close(lock);
    effect_fd=private_lock("effect.lock",3000);
    if (effect_fd<0 || !release_ui()) { ok=0; reason="ui_release_failed"; }
    if (effect_fd>=0) { close(effect_fd); effect_fd=-1; }
    lock=lock_state();
    if (lock<0) return reply(0,0,"recovery_busy");
  }
  int rc=reply(ok,1,reason); close(lock); return rc;
}
static int restore(int lock) {
  int latched=stop("explicit_off"); /* Guardian observes this under its state lock. */
  int jr=active_read();
  if (!latched || jr<0) { int rc=reply(0,1,"restore_blocked"); close(lock); return rc; }
  if (jr>0 && active_live()) {
    long pid=active.pid; unsigned long long start=active.start;
    /* Never signal a stored PID: /proc start checks cannot make kill atomic
     * with PID reuse on Linux 4.4. Durable stop is the retirement request. */
    close(lock);
    long long until=now_ms()+3000;
    while (now_ms()<until && process_start(pid)==start) poll(NULL,0,20);
    lock=lock_state();
    if (lock<0) return reply(0,1,"recovery_busy");
    if (!same_config() || process_start(pid)==start || active_read()<0) {
      int rc=reply(0,1,"retirement_failed"); close(lock); return rc;
    }
  }
  int ok=same_config() && active_read()>=0 && !active_live() && erase("active");
  const char *reason=ok ? "explicit_off":"restore_blocked";
  if (ok) {
    close(lock);
    effect_fd=private_lock("effect.lock",3000);
    if (effect_fd<0 || !release_ui()) { ok=0; reason="ui_release_failed"; }
    if (effect_fd>=0) { close(effect_fd); effect_fd=-1; }
    lock=lock_state();
    if (lock<0) return reply(0,0,"recovery_busy");
  }
  int rc=reply(ok,1,reason); close(lock); return rc;
}
int main(int argc,char **argv) {
  umask(077);
  if (argc==2 && !strcmp(argv[1],"--selfcheck")) {
    int ok=hex32("0123456789abcdef0123456789abcdef") &&
           parse_proc_start("42 (guardian) S 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 12345 0\n")==12345;
    printf("{\"returnValue\":%s,\"backend\":\"c1-native-gate\",\"routing\":\"compositor-keyfilter-v1\",\"selfcheck\":true}\n",ok ? "true":"false");
    return !ok;
  }
  if (argc==3 && !strcmp(argv[1],"--home")) {
    signal(SIGTERM,on_signal); signal(SIGINT,on_signal); signal(SIGHUP,on_signal);
    signal(SIGQUIT,on_signal); signal(SIGPIPE,SIG_IGN);
    effect_fd=private_lock("effect.lock",3000);
    if (effect_fd<0) return reply(0,0,"effect_busy");
  }
  int lock=argc==2 && !strcmp(argv[1],"--restore") ? lock_wait(4000):lock_state();
  if (lock<0) return reply(0,0,"state_untrusted");
  if (!config_read()) { memset(&cfg,0,sizeof(cfg)); close(lock); return reply(0,0,"config_invalid"); }
  if (argc==2 && !strcmp(argv[1],"--status")) {
    int rc=reply(1,1,"none"); close(lock); return rc;
  }
  if (argc==3 && !strcmp(argv[1],"--home")) {
    char why[64];
    if (!hex32(argv[2]) || strcmp(argv[2],cfg.token) || !boot_matches ||
        active_read()!=1 || latch_read(why)!=0 || !stock_identity() || !health()) {
      int rc=reply(0,1,"home_refused"); close(lock); return rc;
    }
    /* effect.lock serializes UI effects; state stays available to leases and
     * status while this bounded launch runs. Stops latch before waiting here. */
    close(lock);
    int launched=!interrupted && luna("luna://com.webos.applicationManager/launch",
                                     "com.cleanyourtv.root.preview");
    lock=lock_state();
    if (lock<0) { close(effect_fd); effect_fd=-1; return reply(0,0,"recovery_busy"); }
    int stopped=latch_read(why);
    int ok=launched && !interrupted && same_config() && stopped==0 && health();
    int release=!ok && stopped==0 && same_config() && stop("home_failed");
    if (release) {
      close(lock); release_ui(); lock=lock_state();
      if (lock<0) { close(effect_fd); effect_fd=-1; return reply(0,0,"recovery_busy"); }
    }
    int rc=reply(ok,1,ok ? "home_launched":"home_failed");
    close(lock); close(effect_fd); effect_fd=-1; return rc;
  }
  if (argc==2 && !strcmp(argv[1],"--restore")) return restore(lock);
  if (argc==2 && !strcmp(argv[1],"--lease")) {
    char why[64]; int jr=active_read(), stopped=latch_read(why);
    int ok=jr>=0 && stopped>=0;
    if (ok && !stopped && boot_matches && stock_identity() && volatile_ready()) {
      if (jr==0) {
        /* Compositor subscribes before guard creation; no invented guardian. */
        strcpy(active.token,cfg.token);
        ok=pulse_write("broker",now_ms(),0,0);
      } else if (active_live()) {
        long long i,c,b,u; int armed,unused;
        int h=pulse_read("health",&i,&c,&armed);
        int prior=pulse_read("broker",&b,&u,&unused);
        if (!h || (armed && (!fresh(i)||!fresh(c))) ||
            (prior && !fresh(b)) ||
            (!prior && (armed || !absent(VOLATILE "/broker") || now_ms()-active.born>=2000))) {
          ok=stop("lease_expired");
        } else ok=pulse_write("broker",now_ms(),0,0);
      }
    }
    int rc=reply(ok,1,"none"); close(lock); return rc;
  }
  if (argc==7 && !strcmp(argv[1],"--guard")) {
    unsigned long long values[4];
    for (int x=0;x<4;x++) {
      char *s=argv[x+3]; errno=0;
      if (!digits(s,strlen(s))) { close(lock); return reply(0,1,"arguments_invalid"); }
      values[x]=strtoull(s,NULL,10);
      if (errno || values[x]>INT_MAX) { close(lock); return reply(0,1,"arguments_invalid"); }
    }
    if (values[3]>60) { close(lock); return reply(0,1,"arguments_invalid"); }
    return guard(argv[2],(int)values[0],(int)values[1],(int)values[2],(int)values[3],lock);
  }
  int rc=reply(0,1,"arguments_invalid"); close(lock); return rc;
}
