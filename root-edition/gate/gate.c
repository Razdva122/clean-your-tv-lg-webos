#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/mount.h>
#include <sys/sysmacros.h>
#endif
#ifdef CYTV_GATE_FIXTURE
#include "native_gate_fixture.h"
#else
#define STATE "/var/lib/clean-your-tv-root/c1-gate"
#define COPY "/tmp/clean-your-tv-root-gate/gate"
#define HOME "/usr/bin/com.webos.app.home"
#define CHECK1 "/mnt/lg/cmn_data/checkpoint/com.webos.app.home"
#define CHECK2 "/tmp/checkpoint/com.webos.app.home"
#define BOOT "/proc/sys/kernel/random/boot_id"
#define MOUNTS "/proc/self/mountinfo"
#define LUNA "/usr/bin/luna-send"
#define TRUST_UID 0
#endif
#define LIMIT 16384
#define MTMAX 512
#define ARRAY(a) (sizeof(a) / sizeof((a)[0]))
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
       (!S_ISREG(s.st_mode) || s.st_uid != TRUST_UID || (s.st_mode & 077)))) {
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
  if (strncmp(p, "CYTV-C1-GATE-1\ntoken ", 21))
    return 0;
  p += 21;
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
static int stock_identity(void) {
  struct stat s;
  return secure(HOME, 0) && !stat(HOME, &s) &&
         (unsigned long long)s.st_dev == cfg.dev &&
         (unsigned long long)s.st_ino == cfg.ino &&
         (unsigned long long)s.st_size == cfg.size && mtime_ns(&s) == cfg.mtime;
}
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
static int preload(struct json *j) {
  int i = field(j, 0, "preload");
  if (i >= 0 && !literal(j, i, "true") && !literal(j, i, "false") &&
      !literal(j, i, "\"full\""))
    return -1;
  if (literal(j, i, "true") || literal(j, i, "\"full\""))
    return 1;
  i = field(j, 0, "params");
  if (i >= 0) {
    if (j->t[i].type != '{')
      return -1;
    int x = field(j, i, "preload");
    if (x >= 0 && !literal(j, x, "true") && !literal(j, x, "false") &&
        !literal(j, x, "\"full\""))
      return -1;
    if (literal(j, x, "true") || literal(j, x, "\"full\""))
      return 1;
  }
  return literal(j, field(j, 0, "launchMode"), "\"preload\"");
}
/* Mount authority is a bounded durable plan, including expected propagation
 * aliases. The private staged source inode/root and each original target inode
 * are captured before the bind. No setns, recursive/lazy unmount, or guessed
 * peer removal. */
#define OWNMAX 32
struct mountrec {
  int id, parent, group, unknown;
  unsigned maj, min;
  char root[4096], path[4096];
};
static struct mountrec mounts[MTMAX];
static int mountcount;
static const char *targets[] = {HOME, CHECK1, CHECK2};
static const char *sources[] = {COPY, COPY ".empty1", COPY ".empty2"};
struct entry {
  int id, kind, primary;
  unsigned long long dev, ino, olddev, oldino;
  char root[4096], path[4096];
};
struct active {
  char token[33];
  long pid;
  unsigned long long start;
  long long lease;
  int count;
  struct entry e[OWNMAX];
};
static struct active active;
static int topology_error;
static int related(const char *p, const char *t) {
  size_t n = strlen(t);
  return !strcmp(t, "/") || !strcmp(p, t) || (!strncmp(p, t, n) && p[n] == '/');
}
static int path_text(const char *p) {
  if (*p != '/' || strlen(p) >= PATH_MAX || strstr(p, "//") ||
      strstr(p, "/../") || strstr(p, "/./"))
    return 0;
  size_t length = strlen(p);
  if ((length >= 3 && !strcmp(p + length - 3, "/..")) ||
      (length >= 2 && !strcmp(p + length - 2, "/.")))
    return 0;
  for (; *p; p++)
    if (!strchr("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                "_./-",
                *p))
      return 0;
  return 1;
}
static int decode(char *s) {
  char *p = s, *q = s;
  while (*p) {
    if (*p == '\\') {
      if (strlen(p) < 4 || p[1] < '0' || p[1] > '7' || p[2] < '0' ||
          p[2] > '7' || p[3] < '0' || p[3] > '7')
        return 0;
      int v = (p[1] - '0') * 64 + (p[2] - '0') * 8 + p[3] - '0';
      if (!v)
        return 0;
      *q++ = (char)v;
      p += 4;
    } else
      *q++ = *p++;
  }
  *q = 0;
  return 1;
}
static int read_mount_table(const char *path, struct mountrec *out,
                            int *count) {
  FILE *f = fopen(path, "re");
  if (!f)
    return 0;
  char line[16384];
  int n = 0;
  size_t bytes = 0;
  while (fgets(line, sizeof(line), f)) {
    size_t len = strlen(line);
    bytes += len;
    if (!len || line[len - 1] != '\n' || bytes > 1024 * 1024 || n >= MTMAX) {
      fclose(f);
      return 0;
    }
    char *parts[64], *savep = NULL;
    int k = 0;
    for (char *p = strtok_r(line, " \n", &savep); p;
         p = strtok_r(NULL, " \n", &savep)) {
      if (k >= 64) {
        fclose(f);
        return 0;
      }
      parts[k++] = p;
    }
    int dash = 6;
    while (dash < k && strcmp(parts[dash], "-"))
      dash++;
    struct mountrec *m = &out[n];
    int pos = 0;
    if (k < 10 || dash + 3 != k - 1 || !digits(parts[0], strlen(parts[0])) ||
        !digits(parts[1], strlen(parts[1])) ||
        sscanf(parts[0], "%d%n", &m->id, &pos) != 1 || parts[0][pos] ||
        m->id <= 0 || sscanf(parts[1], "%d%n", &m->parent, &pos) != 1 ||
        parts[1][pos] ||
        sscanf(parts[2], "%u:%u%n", &m->maj, &m->min, &pos) != 2 ||
        parts[2][pos] || strlen(parts[3]) >= PATH_MAX ||
        strlen(parts[4]) >= PATH_MAX) {
      fclose(f);
      return 0;
    }
    strcpy(m->root, parts[3]);
    strcpy(m->path, parts[4]);
    if (!decode(m->root) || !decode(m->path) || m->path[0] != '/' ||
        m->root[0] != '/') {
      fclose(f);
      return 0;
    }
    m->group = 0;
    m->unknown = 0;
    for (int x = 6; x < dash; x++) {
      if (!strncmp(parts[x], "shared:", 7) &&
          digits(parts[x] + 7, strlen(parts[x] + 7))) {
        unsigned long g = strtoul(parts[x] + 7, NULL, 10);
        if (!g || g > INT_MAX || m->group) {
          fclose(f);
          return 0;
        }
        m->group = (int)g;
      } else
        m->unknown = 1;
    }
    for (int x = 0; x < n; x++)
      if (out[x].id == m->id) {
        fclose(f);
        return 0;
      }
    n++;
  }
  int ok = !ferror(f) && n > 0;
  fclose(f);
  *count = n;
  return ok;
}
static int mount_table(const char *path, struct mountrec *out, int *count) {
  errno = 0;
  int ok = read_mount_table(path, out, count);
  if (!ok && !errno)
    errno = EINVAL;
  return ok;
}
static int parent_mount(const char *path) {
  int best = -1;
  for (int x = 0; x < mountcount; x++)
    if (related(path, mounts[x].path) &&
        (best < 0 || strlen(mounts[x].path) > strlen(mounts[best].path)))
      best = x;
  return best;
}
static int affects(const struct mountrec *m) {
  for (int t = 0; t < 3; t++)
    if (related(targets[t], m->path) || related(sources[t], m->path))
      return 1;
  for (int x = 0; x < active.count; x++)
    if (related(active.e[x].path, m->path))
      return 1;
  return 0;
}
static int peer_check(void) {
#ifdef CYTV_GATE_FIXTURE
  for (int a = 0; a < mountcount; a++)
    (void)affects(&mounts[a]);
  if (!fixture_peers()) {
    topology_error = 1;
    return 0;
  }
  return 1;
#else
  struct stat own;
  if (stat("/proc/self/ns/mnt", &own))
    return 0;
  DIR *d = opendir("/proc");
  if (!d)
    return 0;
  struct dirent *e;
  int ok = 1;
  ino_t seen[1024];
  int sn = 0;
  for (;;) {
    errno = 0;
    e = readdir(d);
    if (!e) {
      if (errno)
        ok = 0;
      break;
    }
    if (!ok)
      break;
    if (!digits(e->d_name, strlen(e->d_name)))
      continue;
    char p[PATH_MAX];
    struct stat ns;
    snprintf(p, sizeof(p), "/proc/%s/ns/mnt", e->d_name);
    if (stat(p, &ns)) {
      if (errno == ENOENT || errno == ESRCH)
        continue;
      ok = 0;
      break;
    }
    if (ns.st_ino == own.st_ino)
      continue;
    int found = 0;
    for (int x = 0; x < sn; x++)
      if (seen[x] == ns.st_ino)
        found = 1;
    if (found)
      continue;
    if (sn >= 1024) {
      ok = 0;
      break;
    }
    seen[sn++] = ns.st_ino;
    snprintf(p, sizeof(p), "/proc/%s/mountinfo", e->d_name);
    struct mountrec *table = calloc(MTMAX, sizeof(*table));
    int n = 0;
    if (!table) {
      ok = 0;
      break;
    }
    if (!mount_table(p, table, &n)) {
      free(table);
      if (errno == ENOENT || errno == ESRCH)
        continue;
      ok = 0;
      break;
    }
    for (int x = 0; x < n; x++) {
      if (table[x].unknown)
        ok = 0;
      for (int t = 0; t < 3; t++)
        if (related(table[x].path, targets[t]))
          ok = 0;
      for (int a = 0; a < mountcount; a++)
        if (affects(&mounts[a]) && mounts[a].group &&
            table[x].group == mounts[a].group)
          ok = 0;
    }
    free(table);
  }
  closedir(d);
  if (!ok)
    topology_error = 1;
  return ok;
#endif
}
static int journal_write(void) {
  size_t cap = 1024 + (size_t)active.count * (2 * PATH_MAX + 256);
  char *b = calloc(1, cap);
  if (!b)
    return 0;
  int n =
      snprintf(b, cap, "CYTV-ACTIVE-2\n%s\n%ld %llu %lld\n%d\n", active.token,
               active.pid, active.start, active.lease, active.count);
  for (int x = 0; x < active.count; x++) {
    struct entry *e = &active.e[x];
    int z =
        snprintf(b + n, cap - (size_t)n, "%d %d %d %llu %llu %llu %llu %s %s\n",
                 e->id, e->kind, e->primary, e->dev, e->ino, e->olddev,
                 e->oldino, e->root, e->path);
    if (z < 0 || (size_t)z >= cap - (size_t)n) {
      free(b);
      return 0;
    }
    n += z;
  }
  int ok = save("active", b);
  free(b);
  return ok;
}
static int journal_read(void) {
  size_t cap = 1024 + OWNMAX * (2 * PATH_MAX + 256);
  char *b = malloc(cap);
  memset(&active, 0, sizeof(active));
  if (!b)
    return -1;
  int n = readfile(STATE "/active", b, cap, 1);
  if (n < 0) {
    free(b);
    struct stat suspect;
    return lstat(STATE "/active", &suspect) == 0 || errno != ENOENT ? -1 : 0;
  }
  int used = 0;
  if (sscanf(b, "CYTV-ACTIVE-2\n%32[a-f0-9]\n%ld %llu %lld\n%d\n%n",
             active.token, &active.pid, &active.start, &active.lease,
             &active.count, &used) != 5 ||
      !hex32(active.token) || active.pid <= 1 || active.lease < 0 ||
      active.count < 0 || active.count > OWNMAX) {
    free(b);
    return -1;
  }
  char *p = b + used;
  for (int x = 0; x < active.count; x++) {
    struct entry *e = &active.e[x];
    used = 0;
    if (sscanf(p, "%d %d %d %llu %llu %llu %llu %4095s %4095s\n%n", &e->id,
               &e->kind, &e->primary, &e->dev, &e->ino, &e->olddev, &e->oldino,
               e->root, e->path, &used) != 9 ||
        !used || e->id < -1 || e->kind < 0 || e->kind > 2 ||
        (e->primary != 0 && e->primary != 1) || !e->ino || !e->oldino ||
        !path_text(e->root) || !path_text(e->path)) {
      free(b);
      return -1;
    }
    for (int y = 0; y < x; y++)
      if (!strcmp(e->path, active.e[y].path)) {
        free(b);
        return -1;
      }
    p += used;
  }
  int ok = p == b + n;
  free(b);
  return ok ? 1 : -1;
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
#ifdef CYTV_GATE_FIXTURE
  return fixture_start(pid);
#else
  char path[64], b[4096];
  snprintf(path, sizeof(path), "/proc/%ld/stat", pid);
  return readfile(path, b, sizeof(b), 0) < 0 ? 0 : parse_proc_start(b);
#endif
}
static int lease_write(void) {
  char b[160], tmp[PATH_MAX];
  int n = snprintf(b, sizeof(b), "%s %ld %llu %lld\n", active.token, active.pid,
                   active.start, active.lease);
  snprintf(tmp, sizeof(tmp), COPY ".lease.%ld", (long)getpid());
  int f = open(tmp, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
  if (f < 0)
    return 0;
  int ok = write(f, b, (size_t)n) == n;
  close(f);
  if (ok)
    ok = rename(tmp, COPY ".lease") == 0;
  if (!ok)
    unlink(tmp);
  return ok;
}
static int healthy(void) {
  char b[160], token[33];
  long pid;
  unsigned long long start;
  long long lease;
  int used = 0;
  int n = readfile(COPY ".lease", b, sizeof(b), 1);
  if (n < 0 ||
      sscanf(b, "%32[a-f0-9] %ld %llu %lld\n%n", token, &pid, &start, &lease,
             &used) != 4 ||
      used != n || strcmp(token, active.token) || pid != active.pid ||
      start != active.start)
    return 0;
  long long now = now_ms();
  return boot_matches && active.pid > 1 && active.start &&
         process_start(active.pid) == active.start && now >= lease &&
         now - lease < 2000;
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
  char old[64], b[160];
  int latched = latch_read(old);
  if (latched < 0)
    return 0;
  if (latched > 0)
    reason = old;
  snprintf(b, sizeof(b), "%s %s\n", cfg.token, reason);
  return save("stopped", b) && save("outcome", b);
}
static int matching(const struct entry *e, int source) {
  struct stat s;
#ifdef CYTV_GATE_FIXTURE
  if (fixture_stat(e->path, &s))
    return 0;
#else
  if (lstat(e->path, &s))
    return 0;
#endif
  return (unsigned long long)s.st_dev == (source ? e->dev : e->olddev) &&
         (unsigned long long)s.st_ino == (source ? e->ino : e->oldino);
}
static int at_path(const char *path) {
  int found = -1;
  for (int x = 0; x < mountcount; x++)
    if (related(mounts[x].path, path)) {
      if (strcmp(mounts[x].path, path) || found >= 0)
        return -2;
      found = x;
    }
  return found;
}
static int mount_identity(const struct mountrec *m, const struct entry *e) {
  return m->maj == (unsigned)major((dev_t)e->dev) &&
         m->min == (unsigned)minor((dev_t)e->dev) && !strcmp(m->root, e->root);
}
static int inspect_mode(int *mounted, int recovery) {
  *mounted = 0;
  topology_error = 0;
  if (!mount_table(MOUNTS, mounts, &mountcount) || !peer_check())
    return 0;
  if (active.token[0] && strcmp(active.token, cfg.token))
    return 0;
  for (int t = 0; t < 3; t++) {
    int index = at_path(targets[t]);
    if (index == -2)
      return 0;
    if (index >= 0) {
      int found = 0;
      for (int a = 0; a < active.count; a++)
        if (!strcmp(active.e[a].path, targets[t]))
          found = 1;
      if (!found) {
        *mounted = 1;
        return 0;
      }
    }
  }
  for (int a = 0; a < active.count; a++) {
    struct entry *e = &active.e[a];
    int x = at_path(e->path);
    if (x == -2)
      return 0;
    if (x >= 0) {
      *mounted = 1;
      if (!e->id || (e->id > 0 && mounts[x].id != e->id) ||
          !mount_identity(&mounts[x], e) || mounts[x].unknown ||
          !matching(e, 1))
        return 0;
    } else if (!matching(e, 0) || (e->id > 0 && boot_matches && !recovery))
      return 0;
  }
  /* A new alias of a staged source not captured before the effect is ambiguous.
   */
  for (int x = 0; x < mountcount; x++)
    for (int a = 0; a < active.count; a++)
      if (mount_identity(&mounts[x], &active.e[a])) {
        int found = 0;
        for (int y = 0; y < active.count; y++)
          if (!strcmp(mounts[x].path, active.e[y].path))
            found = 1;
        if (!found)
          return 0;
      }
  return 1;
}
static int inspect(int *mounted) { return inspect_mode(mounted, 0); }
static int unbind(const char *path) {
#ifdef CYTV_GATE_FIXTURE
  return fixture_unmount(path);
#else
  return umount2(path, 0);
#endif
}
static int bind(const char *source, const char *target) {
#ifdef CYTV_GATE_FIXTURE
  return fixture_mount(source, target);
#else
  return mount(source, target, NULL, MS_BIND, NULL);
#endif
}
static int restore_owned(void) {
  int mounted;
  if (!boot_matches) {
    if (!inspect_mode(&mounted, 1) || mounted)
      return 0;
    for (int a = 0; a < active.count; a++)
      active.e[a].id = 0;
    return stock_identity();
  }
  if (!inspect_mode(&mounted, 1))
    return 0;
  for (int t = 2; t >= 0; t--)
    for (int primary = 1; primary >= 0; primary--)
      for (int a = 0; a < active.count; a++) {
        struct entry *e = &active.e[a];
        if (e->kind != t || e->primary != primary || !e->id)
          continue;
        if (!inspect_mode(&mounted, 1))
          return 0;
        int x = at_path(e->path);
        if (x >= 0) {
          if (!matching(e, 1) || !mount_identity(&mounts[x], e) ||
              (e->id > 0 && mounts[x].id != e->id))
            return 0;
          if (unbind(e->path))
            return 0;
        } else if (x != -1 || !matching(e, 0))
          return 0;
        e->id = 0;
        if (!journal_write() || !inspect_mode(&mounted, 1))
          return 0;
      }
  return inspect_mode(&mounted, 1) && !mounted && stock_identity();
}
static int root_for(const char *path, char *out, size_t cap) {
  int p = parent_mount(path);
  if (p < 0 || mounts[p].unknown) {
    topology_error = 1;
    return 0;
  }
  const char *relative = path + strlen(mounts[p].path);
  if (!strcmp(mounts[p].path, "/"))
    relative = path;
  int n =
      snprintf(out, cap, "%s%s",
               !strcmp(mounts[p].root, "/") ? "" : mounts[p].root, relative);
  return n > 0 && (size_t)n < cap && path_text(out);
}
static int add_plan(int kind, int primary, const char *path, const char *root,
                    struct stat *source) {
  if (active.count >= OWNMAX || !path_text(path) || !path_text(root) ||
      at_path(path) != -1 || !secure(path, kind > 0) || !trusted_parents(path))
    return 0;
  for (int x = 0; x < active.count; x++)
    if (related(path, active.e[x].path) || related(active.e[x].path, path))
      return 0;
  struct stat old;
  if (lstat(path, &old))
    return 0;
  struct entry *e = &active.e[active.count++];
  memset(e, 0, sizeof(*e));
  e->kind = kind;
  e->primary = primary;
  e->id = -1;
  e->dev = (unsigned long long)source->st_dev;
  e->ino = (unsigned long long)source->st_ino;
  e->olddev = (unsigned long long)old.st_dev;
  e->oldino = (unsigned long long)old.st_ino;
  strcpy(e->path, path);
  strcpy(e->root, root);
  return 1;
}
static int prepare_mounts(void) {
  int mounted;
  struct stat staging;
  char parent[PATH_MAX];
  strcpy(parent, COPY);
  char *slash = strrchr(parent, '/');
  if (!slash)
    return 0;
  *slash = 0;
  if (lstat(parent, &staging) || !secure(parent, 1) ||
      (staging.st_mode & 077) || access(COPY, X_OK))
    return 0;
  if (!inspect(&mounted) || mounted || !stock_identity() || !secure(COPY, 0) ||
      !trusted_parents(COPY))
    return 0;
  for (int t = 0; t < 3; t++) {
    struct stat src, old;
    if (lstat(targets[t], &old)) {
      if (t && errno == ENOENT)
        continue;
      return 0;
    }
    if (!secure(targets[t], t > 0) || !trusted_parents(targets[t]))
      return 0;
    if (t) {
      if (mkdir(sources[t], 0700) && errno != EEXIST)
        return 0;
      if (!secure(sources[t], 1))
        return 0;
      DIR *d = opendir(sources[t]);
      if (!d)
        return 0;
      struct dirent *e;
      int empty = 1;
      for (;;) {
        errno = 0;
        e = readdir(d);
        if (!e) {
          if (errno)
            empty = 0;
          break;
        }
        if (strcmp(e->d_name, ".") && strcmp(e->d_name, ".."))
          empty = 0;
      }
      closedir(d);
      if (!empty)
        return 0;
    }
    if (at_path(sources[t]) != -1 || stat(sources[t], &src))
      return 0;
    char root[PATH_MAX];
    if (!root_for(sources[t], root, sizeof(root)))
      return 0;
    int parent = parent_mount(targets[t]);
    if (parent < 0 || mounts[parent].unknown) {
      topology_error = 1;
      return 0;
    }
    if (!add_plan(t, 1, targets[t], root, &src))
      return 0;
    int group = mounts[parent].group;
    if (group)
      for (int p = 0; p < mountcount; p++)
        if (p != parent && mounts[p].group == group) {
          if (mounts[p].unknown ||
              strcmp(mounts[p].root, mounts[parent].root) ||
              mounts[p].maj != mounts[parent].maj ||
              mounts[p].min != mounts[parent].min) {
            topology_error = 1;
            return 0;
          }
          const char *relative = targets[t] + strlen(mounts[parent].path);
          if (!strcmp(mounts[parent].path, "/"))
            relative = targets[t];
          char alias[PATH_MAX];
          int n = snprintf(alias, sizeof(alias), "%s%s",
                           !strcmp(mounts[p].path, "/") ? "" : mounts[p].path,
                           relative);
          if (n <= 0 || (size_t)n >= sizeof(alias) ||
              !add_plan(t, 0, alias, root, &src)) {
            topology_error = 1;
            return 0;
          }
        }
  }
  if (!peer_check() || !journal_write())
    return 0;
  for (int t = 0; t < 3; t++) {
    int primary = -1;
    for (int a = 0; a < active.count; a++)
      if (active.e[a].kind == t && active.e[a].primary)
        primary = a;
    if (primary < 0)
      continue;
    if (interrupted || !inspect_mode(&mounted, 1) ||
        bind(sources[t], targets[t]))
      return 0;
    if (!inspect_mode(&mounted, 1))
      return 0;
    for (int a = 0; a < active.count; a++)
      if (active.e[a].kind == t) {
        int x = at_path(active.e[a].path);
        active.e[a].id = x >= 0 ? mounts[x].id : 0;
        if (active.e[a].primary && x < 0)
          return 0;
      }
    if (!journal_write())
      return 0;
  }
  return inspect(&mounted) && mounted;
}
static int lock_try(void) {
  struct stat state_info;
  if (!trusted_parents(STATE "/config") || !secure(STATE, 1) ||
      lstat(STATE, &state_info) || (state_info.st_mode & 077)) {
    errno = EPERM;
    return -1;
  }
  int f = open(STATE "/lock", O_RDWR | O_CREAT | O_CLOEXEC | O_NOFOLLOW, 0600);
  if (f < 0)
    return -1;
  struct stat s;
  if (fstat(f, &s) || s.st_uid != TRUST_UID || (s.st_mode & 077) ||
      !S_ISREG(s.st_mode) || flock(f, LOCK_EX | LOCK_NB)) {
    close(f);
    return -1;
  }
  return f;
}
static int lock_wait(int milliseconds) {
  long long deadline = now_ms() + milliseconds;
  for (;;) {
    int lock = lock_try();
    if (lock >= 0)
      return lock;
    if ((errno != EWOULDBLOCK && errno != EAGAIN && errno != EINTR) ||
        now_ms() >= deadline)
      return -1;
    poll(NULL, 0, 5);
  }
}
static int lock_state(void) { return lock_wait(1500); }
static int reply(int success, const char *reason) {
  int mounted = 0, jr = journal_read(), valid = inspect(&mounted);
  if (jr < 0)
    valid = 0;
  char why[64];
  int stopped = latch_read(why);
  if (stopped < 0)
    valid = 0;
  int health = valid && mounted && jr > 0 && healthy() && stopped == 0;
  int stock = valid && !mounted && stock_identity();
  const char *state = !valid || (mounted && (!health || stopped)) ? "blocked"
                      : health && mounted                         ? "armed"
                      : stopped > 0                               ? "stopped"
                      : stock                                     ? "stock"
                                                                  : "blocked";
  if (topology_error)
    reason = "unsupported_mount_topology";
  if (!strcmp(reason, "none") && stopped > 0)
    reason = why;
  printf("{\"returnValue\":%s,\"backend\":\"c1-native-gate\",\"state\":\"%s\","
         "\"mounted\":%s,\"healthy\":%s,\"token\":\"%s\",\"stock_verified\":%s,"
         "\"profiles\":null,\"stopped\":%s,\"reason\":\"%s\",\"guardian_pid\":%"
         "ld}\n",
         success && valid ? "true" : "false", state, mounted ? "true" : "false",
         health ? "true" : "false", cfg.token, stock ? "true" : "false",
         stopped > 0 ? "true" : "false", reason, jr > 0 ? active.pid : 0);
  return success && valid ? 0 : 1;
}
/* Child has a new process group, fixed argv/env, capped output and deadline. */
static int luna(const char *app) {
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
  pid_t pid = fork();
  if (pid < 0) {
    close(out[0]);
    close(out[1]);
    close(in[0]);
    close(in[1]);
    return 0;
  }
  if (!pid) {
    setpgid(0, 0);
    dup2(in[0], 0);
    dup2(out[1], 1);
    dup2(out[1], 2);
    struct rlimit r;
    unsigned long max = 65536;
    if (!getrlimit(RLIMIT_NOFILE, &r) && r.rlim_cur < max)
      max = (unsigned long)r.rlim_cur;
    for (unsigned long f = 3; f < max; f++)
      close((int)f);
    char payload[160];
    snprintf(payload, sizeof(payload), "{\"id\":\"%s\"}", app);
    char *args[] = {LUNA,    "-n",
                    "1",     "luna://com.webos.applicationManager/launch",
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
  return parse(&j, b) && literal(&j, field(&j, 0, "returnValue"), "true");
}
static void stock_launch(void) {
  pid_t p = fork();
  if (p == 0) {
    setsid();
    signal(SIGTERM, SIG_DFL);
    signal(SIGINT, SIG_DFL);
    interrupted = 0;
    int n = open("/dev/null", O_RDWR);
    if (n >= 0) {
      dup2(n, 0);
      dup2(n, 1);
      dup2(n, 2);
      if (n > 2)
        close(n);
    }
    for (int fd = 3; fd < 65536; fd++)
      close(fd);
    luna("com.webos.app.home");
    _exit(0);
  }
}
static int input_line(int fd, char *line, size_t *len, long long deadline) {
  for (;;) {
    if (interrupted)
      return -1;
    long long left = deadline - now_ms();
    if (left <= 0)
      return -2;
    struct pollfd p = {fd, POLLIN | POLLHUP, 0};
    int z = poll(&p, 1, left > 50 ? 50 : (int)left);
    if (z < 0) {
      if (errno == EINTR)
        continue;
      return -1;
    }
    if (!z)
      continue;
    char c;
    ssize_t n = read(fd, &c, 1);
    if (n < 0 && errno == EINTR)
      continue;
    if (n <= 0)
      return -1;
    if (c == '\n') {
      line[*len] = 0;
      *len = 0;
      return 1;
    }
    if (c < 'A' || c > 'Z' || *len >= 15)
      return -3;
    line[(*len)++] = c;
  }
}
static int guard(const char *token, int input, int ready, int seconds) {
  int op = lock_try();
  if (op < 0)
    return reply(0, "busy");
  struct stat i, r;
  char why[64];
  if (!boot_matches || !hex32(token) || strcmp(token, cfg.token) ||
      input <= 2 || ready <= 2 || input == ready || fstat(input, &i) ||
      fstat(ready, &r) || !S_ISFIFO(i.st_mode) || !S_ISFIFO(r.st_mode) ||
      (fcntl(input, F_GETFL) & O_ACCMODE) != O_RDONLY ||
      (fcntl(ready, F_GETFL) & O_ACCMODE) == O_RDONLY || latch_read(why) != 0) {
    close(op);
    return reply(0, "guard_refused");
  }
  int old = journal_read(), mounted;
  if (old < 0 || !inspect(&mounted) || mounted || old > 0) {
    stop(topology_error ? "unsupported_mount_topology" : "existing_attempt");
    close(op);
    return reply(0, "existing_attempt");
  }
  memset(&active, 0, sizeof(active));
  strcpy(active.token, token);
  active.pid = getpid();
  active.start = process_start(active.pid);
  active.lease = now_ms();
  if (!active.start || !journal_write() || !lease_write()) {
    stop("journal_failed");
    close(op);
    return reply(0, "journal_failed");
  }
  close(op);
  signal(SIGTERM, on_signal);
  signal(SIGINT, on_signal);
  signal(SIGHUP, on_signal);
  signal(SIGQUIT, on_signal);
  signal(SIGUSR1, on_signal);
  signal(SIGUSR2, on_signal);
  signal(SIGALRM, on_signal);
  signal(SIGPIPE, SIG_IGN);
  char line[17];
  size_t len = 0;
  long long start = now_ms();
  int result = input_line(input, line, &len, start + 2000);
  const char *reason = "input_not_ready";
  int armed = 0;
  if (result == 1 && !strcmp(line, "READY")) {
    active.lease = now_ms();
    op = lock_wait(500);
    if (op >= 0 && latch_read(why) == 0 && lease_write() && prepare_mounts() &&
        now_ms() - active.lease < 2000 && !interrupted) {
      char b[80];
      int n = snprintf(b, sizeof(b), "ARMED %s\n", token);
      int flags = fcntl(ready, F_GETFL);
      if (flags >= 0)
        fcntl(ready, F_SETFL, flags | O_NONBLOCK);
      if (write(ready, b, (size_t)n) == n) {
        close(ready);
        ready = -1;
        armed = 1;
        reason = "input_lost";
      } else
        reason = "ready_failed";
    } else
      reason = topology_error ? "unsupported_mount_topology" : "mount_refused";
    if (op >= 0)
      close(op);
  }
  if (ready >= 0)
    close(ready);
  long long trial = seconds ? start + seconds * 1000LL : LLONG_MAX;
  while (armed) {
    long long deadline = active.lease + 2000;
    if (trial < deadline)
      deadline = trial;
    result = input_line(input, line, &len, deadline);
    if (result < 0) {
      reason = interrupted         ? "signal"
               : now_ms() >= trial ? "trial_expired"
               : result == -2      ? "heartbeat_expired"
               : result == -3      ? "malformed_input"
                                   : "input_lost";
      break;
    }
    if (!strcmp(line, "PING")) {
      active.lease = now_ms();
      op = lock_wait(500);
      if (op < 0) {
        reason = "state_busy";
        break;
      }
      int latched = latch_read(why);
      int written = latched == 0 && lease_write();
      close(op);
      if (!written) {
        reason = latched > 0 ? "external_stop" : "journal_failed";
        break;
      }
    } else {
      reason = !strcmp(line, "ESCAPE")   ? "escape"
               : !strcmp(line, "LGHOME") ? "lg_home"
               : !strcmp(line, "LOST")   ? "input_lost"
                                         : "malformed_input";
      break;
    }
  }
  close(input);
  op = -1;
  long long until = now_ms() + 2000;
  while (op < 0 && now_ms() < until) {
    op = lock_wait(500);
    if (op < 0)
      poll(NULL, 0, 10);
  }
  if (op < 0)
    return reply(0, "recovery_busy");
  int latched = stop(reason);
  int restored = restore_owned();
  if (restored) {
    if (!erase("active"))
      restored = 0;
    else {
      memset(&active, 0, sizeof(active));
      stock_launch();
    }
  }
  int rc = reply(armed && latched && restored,
                 restored ? reason : "restore_blocked");
  close(op);
  return rc;
}
static int retire_guard(int lock) {
  if (boot_matches && active.pid > 1 && active.pid != (long)getpid() &&
      active.start && process_start(active.pid) == active.start) {
    pid_t pid = (pid_t)active.pid;
    unsigned long long start = active.start;
    kill(pid, SIGTERM);
    flock(lock, LOCK_UN);
    close(lock);
    long long until = now_ms() + 3000;
    while (now_ms() < until && process_start(pid) == start)
      poll(NULL, 0, 20);
    lock = lock_state();
    if (lock < 0)
      return -1;
    journal_read();
  }
  return lock;
}
int main(int argc, char **argv) {
  umask(077);
  if (argc == 2 && !strcmp(argv[1], "--selfcheck")) {
    struct json j;
    int ok = parse(&j, "{\"returnValue\":true}") &&
             !parse(&j, "{\"x\":1,\"x\":2}") &&
             hex32("0123456789abcdef0123456789abcdef") &&
             parse_proc_start("42 (native gate) S 1 2 3 4 5 6 7 8 9 10 11 12 "
                              "13 14 15 16 17 18 12345 0\n") == 12345 &&
             !parse_proc_start("42 (native gate) Z 1 2\n");
    printf("{\"returnValue\":%s,\"backend\":\"c1-native-gate\",\"selfcheck\":"
           "true}\n",
           ok ? "true" : "false");
    return !ok;
  }
  int lock =
      argc == 6 && !strcmp(argv[1], "--guard") ? lock_try() : lock_state();
  if (lock < 0) {
    puts("{\"returnValue\":false,\"backend\":\"c1-native-gate\",\"state\":"
         "\"blocked\",\"mounted\":false,\"healthy\":false,\"token\":\"\","
         "\"stock_verified\":false,\"profiles\":null,\"stopped\":true,"
         "\"reason\":\"state_untrusted\",\"guardian_pid\":0}");
    return 1;
  }
  if (!config_read()) {
    memset(&cfg, 0, sizeof(cfg));
    int rc = reply(0, "config_invalid");
    close(lock);
    return rc;
  }
  int jr = journal_read();
  if (argc == 2 && !strcmp(argv[1], "--status")) {
    int rc = reply(jr >= 0, "none");
    close(lock);
    return rc;
  }
  if (argc == 6 && !strcmp(argv[1], "--guard")) {
    unsigned long long fds[3];
    for (int x = 0; x < 3; x++) {
      char *p = argv[x + 3];
      if (!digits(p, strlen(p))) {
        close(lock);
        return reply(0, "arguments_invalid");
      }
      errno = 0;
      fds[x] = strtoull(p, NULL, 10);
      if (errno || fds[x] > INT_MAX) {
        close(lock);
        return reply(0, "arguments_invalid");
      }
    }
    if (fds[2] > 60) {
      close(lock);
      return reply(0, "arguments_invalid");
    }
    close(lock);
    return guard(argv[2], (int)fds[0], (int)fds[1], (int)fds[2]);
  }
  if (argc == 2 && !strcmp(argv[1], "--restore")) {
    int latch = stop("explicit_off");
    lock = retire_guard(lock);
    if (lock < 0)
      return reply(0, "recovery_busy");
    jr = journal_read();
    int ok = jr >= 0 && restore_owned();
    if (ok) {
      if (!erase("active"))
        ok = 0;
      else
        memset(&active, 0, sizeof(active));
    }
    int rc = reply(latch && ok, ok ? "explicit_off" : "restore_blocked");
    close(lock);
    return rc;
  }
  struct json j;
  int pre = argc == 2 && parse(&j, argv[1]) ? preload(&j) : -1;
  if (pre < 0) {
    int latched = stop("envelope_invalid");
    lock = retire_guard(lock);
    if (lock < 0)
      return reply(0, "recovery_busy");
    jr = journal_read();
    int restored = jr >= 0 && restore_owned();
    if (restored)
      erase("active");
    int rc =
        reply(0, latched && restored ? "envelope_invalid" : "restore_blocked");
    close(lock);
    return rc;
  }
  char why[64];
  int mounted = 0, valid = inspect(&mounted);
  if (boot_matches && jr > 0 && valid && mounted && healthy() &&
      latch_read(why) == 0) {
    close(lock);
    if (pre)
      return reply(1, "preload");
    if (luna("com.cleanyourtv.root.preview"))
      return reply(1, "redirected");
    lock = lock_state();
    if (lock < 0)
      return reply(0, "recovery_busy");
    journal_read();
    stop("launch_failed");
  } else
    stop("guardian_unhealthy");
  lock = retire_guard(lock);
  if (lock < 0)
    return reply(0, "recovery_busy");
  jr = journal_read();
  int ok = jr >= 0 && restore_owned();
  if (ok) {
    if (!erase("active"))
      ok = 0;
    else
      memset(&active, 0, sizeof(active));
    if (ok && !pre)
      stock_launch();
  }
  int rc = reply(ok, ok ? "stock_fallback" : "restore_blocked");
  if (lock >= 0)
    close(lock);
  return rc;
}
