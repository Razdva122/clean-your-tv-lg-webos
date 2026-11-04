#ifndef FIXTURE_ROOT
#error FIXTURE_ROOT must be a compile-time absolute directory
#endif
#define STATE FIXTURE_ROOT "/state"
#define COPY FIXTURE_ROOT "/volatile/gate"
#define HOME FIXTURE_ROOT "/home"
#define CHECK1 FIXTURE_ROOT "/checkpoint1"
#define CHECK2 FIXTURE_ROOT "/checkpoint2"
#define BOOT FIXTURE_ROOT "/boot"
#define MOUNTS FIXTURE_ROOT "/mountinfo"
#define LUNA FIXTURE_ROOT "/luna"
#define TRUST_UID getuid()
static int fixture_peers(void) {
  return access(FIXTURE_ROOT "/peer", F_OK) != 0;
}
static unsigned long long fixture_start(long pid) {
  char p[128];
  snprintf(p, sizeof(p), "/bin/ps -p %ld -o lstart=", pid);
  FILE *f = popen(p, "r");
  if (!f)
    return 0;
  char b[256];
  char *ok = fgets(b, sizeof(b), f);
  pclose(f);
  if (!ok)
    return 0;
  unsigned long long h = 1;
  for (char *q = b; *q; q++)
    h = h * 33 + (unsigned char)*q;
  return h;
}
static int fixture_stat(const char *path, struct stat *s) {
  FILE *f = fopen(MOUNTS, "r");
  if (!f)
    return -1;
  char line[16384], root[4096], target[4096];
  while (fgets(line, sizeof(line), f)) {
    if (sscanf(line, "%*d %*d %*s %4095s %4095s", root, target) == 2 &&
        !strcmp(target, path)) {
      const char *source = strstr(root, ".empty1")   ? COPY ".empty1"
                           : strstr(root, ".empty2") ? COPY ".empty2"
                                                     : NULL;
      if (source) {
        fclose(f);
        return lstat(source, s);
      }
    }
  }
  fclose(f);
  return lstat(path, s);
}
static int fixture_one_mount(const char *source, const char *target, int id) {
  char backup[PATH_MAX];
  snprintf(backup, sizeof(backup), "%s.original", target);
  if (rename(target, backup))
    return -1;
  struct stat s;
  if (stat(source, &s))
    return -1;
  if (S_ISDIR(s.st_mode)) {
    if (mkdir(target, 0700))
      return -1;
  } else if (link(source, target))
    return -1;
  FILE *f = fopen(MOUNTS, "a");
  if (!f)
    return -1;
  const char *root = access(FIXTURE_ROOT "/propagate", F_OK) == 0
                         ? source + strlen(FIXTURE_ROOT)
                         : source;
  fprintf(f, "%d 1 %u:%u %s %s rw%s - fixture fixture rw\n", id,
          (unsigned)major(s.st_dev), (unsigned)minor(s.st_dev), root, target,
          access(FIXTURE_ROOT "/propagate", F_OK) == 0 ? " shared:90" : "");
  fclose(f);
  return 0;
}
static int fixture_mount(const char *source, const char *target) {
  static int id = 100;
  if (fixture_one_mount(source, target, ++id))
    return -1;
  if (access(FIXTURE_ROOT "/propagate", F_OK) == 0) {
    char alias[PATH_MAX];
    snprintf(alias, sizeof(alias), FIXTURE_ROOT "/jail/%s",
             strrchr(target, '/') + 1);
    if (fixture_one_mount(source, alias, ++id))
      return -1;
  }
  return 0;
}
static int fixture_unmount(const char *target) {
  if (access(FIXTURE_ROOT "/fail-inverse", F_OK) == 0) {
    errno = EBUSY;
    return -1;
  }
  char backup[PATH_MAX];
  snprintf(backup, sizeof(backup), "%s.original", target);
  struct stat s;
  if (lstat(target, &s))
    return -1;
  if (S_ISDIR(s.st_mode))
    rmdir(target);
  else
    unlink(target);
  if (rename(backup, target))
    return -1;
  FILE *f = fopen(MOUNTS, "r");
  char b[65536] = {0}, line[16384], path[4096];
  while (fgets(line, sizeof(line), f))
    if (sscanf(line, "%*d %*d %*s %*s %4095s", path) != 1 ||
        strcmp(path, target))
      strncat(b, line, sizeof(b) - strlen(b) - 1);
  fclose(f);
  f = fopen(MOUNTS, "w");
  fputs(b, f);
  fclose(f);
  FILE *e = fopen(FIXTURE_ROOT "/inverse", "a");
  fprintf(e, "%s\n", target);
  fclose(e);
  /* Some kernels remove propagated peers with the primary; others leave
     aliases. Both models must be handled by inverse readback without guessed
     unmounts. */
  if (access(FIXTURE_ROOT "/auto-release", F_OK) == 0 &&
      !strstr(target, "/jail/")) {
    char alias[PATH_MAX];
    snprintf(alias, sizeof(alias), FIXTURE_ROOT "/jail/%s",
             strrchr(target, '/') + 1);
    if (fixture_unmount(alias))
      return -1;
  }
  return 0;
}
