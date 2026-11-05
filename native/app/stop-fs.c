#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "stop-fs.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#if defined(CYTV_STOP_TEST_PATH) && !defined(CYTV_STOP_TEST_BUILD)
#error "Path overrides require an explicit test build"
#endif
#ifdef CYTV_STOP_TEST_BUILD
#ifndef CYTV_STOP_TEST_PATH
#error "Test builds require an isolated fixture path"
#endif
#define STOP_PATH CYTV_STOP_TEST_PATH
#define HOOK(point, fd, dir) cytv_stop_test_hook(point, fd, dir)
#else
#define STOP_PATH "/media/developer/apps/usr/palm/applications/com.local.nativehome/state/stop-inbox"
#define HOOK(point, fd, dir) 0
#endif

static int valid_nonce(const char *s)
{
    if (!s) return 0;
    for (size_t i = 0; i < CYTV_STOP_NONCE_LENGTH; i++)
        if (!((s[i] >= '0' && s[i] <= '9') || (s[i] >= 'a' && s[i] <= 'f'))) return 0;
    return s[CYTV_STOP_NONCE_LENGTH] == '\0';
}

static int producer(const struct cytv_stop_binding *b, uid_t uid)
{
    for (size_t i = 0; i < b->producer_count; i++) if (uid == b->producers[i]) return 1;
    return 0;
}

static int valid_binding(const struct cytv_stop_binding *b)
{
    if (!b || b->version != CYTV_STOP_BINDING_VERSION || !b->directory_ino ||
        b->owner == (uid_t)-1 || b->group == (gid_t)-1 ||
        !b->producer_count || b->producer_count > CYTV_STOP_MAX_PRODUCERS ||
        getuid() == 0 || geteuid() != getuid() || getegid() != getgid()) return 0;
    for (size_t i = 0; i < b->producer_count; i++) {
        if (b->producers[i] == (uid_t)-1) return 0;
        for (size_t j = 0; j < i; j++) if (b->producers[i] == b->producers[j]) return 0;
    }
    if (getgid() == b->group) return 1;
    gid_t groups[64];
    int n = getgroups(64, groups);
    if (n < 0) return 0;
    for (int i = 0; i < n; i++) if (groups[i] == b->group) return 1;
    return 0;
}

static int same_stat(const struct stat *a, const struct stat *b)
{
#ifdef __APPLE__
#define MTIME st_mtimespec
#define CTIME st_ctimespec
#else
#define MTIME st_mtim
#define CTIME st_ctim
#endif
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino &&
        a->st_mode == b->st_mode && a->st_uid == b->st_uid && a->st_gid == b->st_gid &&
        a->st_nlink == b->st_nlink && a->st_size == b->st_size &&
        a->MTIME.tv_sec == b->MTIME.tv_sec && a->MTIME.tv_nsec == b->MTIME.tv_nsec &&
        a->CTIME.tv_sec == b->CTIME.tv_sec && a->CTIME.tv_nsec == b->CTIME.tv_nsec;
#undef MTIME
#undef CTIME
}

static int pinned_directory(const struct cytv_stop_binding *b, const struct stat *s)
{
    return S_ISDIR(s->st_mode) && s->st_dev == b->directory_dev &&
        s->st_ino == b->directory_ino && s->st_uid == b->owner && s->st_gid == b->group;
}

static int check_directory(int fd, const struct cytv_stop_binding *b, struct stat *out)
{
    struct stat path;
    return fstat(fd, out) == 0 && lstat(STOP_PATH, &path) == 0 &&
        pinned_directory(b, out) && pinned_directory(b, &path) &&
        (out->st_mode & 07777) == 0770 && same_stat(out, &path);
}

static int open_directory(const struct cytv_stop_binding *b, int repair)
{
    struct stat s, path;
    if (!valid_binding(b)) return -1;
    int fd = open(STOP_PATH, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return -1;
    if (fstat(fd, &s) < 0 || lstat(STOP_PATH, &path) < 0 ||
        !pinned_directory(b, &s) || !pinned_directory(b, &path) || !same_stat(&s, &path)) goto fail;
    if ((s.st_mode & 07777) != 0770) {
        if (!repair || getuid() != b->owner || fchmod(fd, 0770) < 0) goto fail;
    }
    if (HOOK(CYTV_STOP_TEST_DIR_OPEN, -1, fd) || !check_directory(fd, b, &s)) goto fail;
    return fd;
fail:
    (void)close(fd);
    return -1;
}

static size_t canonical(const char *nonce, char raw[CYTV_STOP_RECORD_CAP])
{
    int n = snprintf(raw, CYTV_STOP_RECORD_CAP, "{\"id\":\"%s\",\"op\":\"stop\",\"v\":1}\n", nonce);
    return n > 0 && (unsigned)n < CYTV_STOP_RECORD_CAP ? (size_t)n : 0;
}

static int record_metadata(const struct cytv_stop_binding *b, const struct stat *s)
{
    mode_t mode = s->st_mode & 07777;
    return S_ISREG(s->st_mode) && s->st_nlink == 1 && producer(b, s->st_uid) &&
        s->st_gid == b->group && (mode == 0640 || mode == 0777) &&
        s->st_size > 0 && s->st_size <= CYTV_STOP_RECORD_CAP;
}

/* Bounded pread, including an EOF witness. Never wait for a FIFO or socket. */
static int matching_content(int fd, const char *nonce)
{
    char raw[CYTV_STOP_RECORD_CAP + 1u], expected[CYTV_STOP_RECORD_CAP];
    size_t used = 0, len = canonical(nonce, expected);
    while (used < sizeof(raw)) {
        ssize_t n = pread(fd, raw + used, sizeof(raw) - used, (off_t)used);
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return 0;
        if (!n) return used == len && !memcmp(raw, expected, len);
        used += (size_t)n;
    }
    return 0;
}

static int stable_record(int dir, int fd, const char *name, const struct stat *before)
{
    struct stat after, path;
    return fstat(fd, &after) == 0 && fstatat(dir, name, &path, AT_SYMLINK_NOFOLLOW) == 0 &&
        same_stat(before, &after) && same_stat(&after, &path);
}

static int read_record(int dir, const struct cytv_stop_binding *b, const char *name)
{
    struct stat before, opened, directory;
    if (fstatat(dir, name, &before, AT_SYMLINK_NOFOLLOW) < 0 || !record_metadata(b, &before) ||
        HOOK(CYTV_STOP_TEST_BEFORE_RECORD_OPEN, -1, dir)) return 0;
    int fd = openat(dir, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return 0;
    int ok = fstat(fd, &opened) == 0 && same_stat(&before, &opened) &&
        !HOOK(CYTV_STOP_TEST_RECORD_OPEN, fd, dir) && matching_content(fd, name + 5) &&
        !HOOK(CYTV_STOP_TEST_RECORD_READ, fd, dir) && stable_record(dir, fd, name, &before) &&
        check_directory(dir, b, &directory);
    if (close(fd) < 0) ok = 0;
    return ok;
}

static int compare_nonce(const void *a, const void *b) { return strcmp(a, b); }

static enum cytv_stop_status scan_directory(int dir, const struct cytv_stop_binding *b,
                                          struct cytv_stop_snapshot *s)
{
    struct stat before, after;
    char names[CYTV_STOP_MAX_RECORDS][38];
    enum cytv_stop_status status = CYTV_STOP_UNKNOWN;
    if (!check_directory(dir, b, &before)) return status;
    int copy = dup(dir);
    if (copy < 0) return status;
    if (fcntl(copy, F_SETFD, FD_CLOEXEC) < 0) { (void)close(copy); return status; }
    DIR *stream = fdopendir(copy);
    if (!stream) { (void)close(copy); return status; }
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(stream);
        if (!entry) { if (errno) goto done; break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        s->observed_entries++;
        if (HOOK(CYTV_STOP_TEST_LIST_ENTRY, -1, dir)) goto done;
        if (s->observed_entries > CYTV_STOP_MAX_RECORDS) { status = CYTV_STOP_OVERFLOW; goto done; }
        if (strncmp(entry->d_name, "Stop.", 5) || !valid_nonce(entry->d_name + 5)) goto done;
        memcpy(names[s->observed_entries - 1], entry->d_name, sizeof(names[0]));
    }
    for (size_t i = 0; i < s->observed_entries; i++) {
        if (!read_record(dir, b, names[i])) goto done;
        memcpy(s->nonces[i], names[i] + 5, sizeof(s->nonces[i]));
    }
    if (!check_directory(dir, b, &after) || !same_stat(&before, &after)) goto done;
    s->count = s->observed_entries;
    qsort(s->nonces, s->count, sizeof(s->nonces[0]), compare_nonce);
    for (size_t i = 1; i < s->count; i++) if (!strcmp(s->nonces[i - 1], s->nonces[i])) goto done;
    status = s->count == CYTV_STOP_MAX_RECORDS ? CYTV_STOP_FULL : CYTV_STOP_OK;
done:
    if (closedir(stream) < 0) status = CYTV_STOP_UNKNOWN;
    if (status == CYTV_STOP_UNKNOWN || status == CYTV_STOP_OVERFLOW) {
        s->count = 0;
        memset(s->nonces, 0, sizeof(s->nonces));
    }
    s->status = status;
    return status;
}

enum cytv_stop_status cytv_stop_scan(const struct cytv_stop_binding *binding,
                                   struct cytv_stop_snapshot *snapshot)
{
    if (!snapshot) return CYTV_STOP_UNKNOWN;
    memset(snapshot, 0, sizeof(*snapshot));
    snapshot->status = CYTV_STOP_UNKNOWN;
    int dir = open_directory(binding, 1);
    if (dir < 0) return CYTV_STOP_UNKNOWN;
    enum cytv_stop_status status = scan_directory(dir, binding, snapshot);
    if (close(dir) < 0) {
        status = CYTV_STOP_UNKNOWN;
        snapshot->count = 0;
        memset(snapshot->nonces, 0, sizeof(snapshot->nonces));
    }
    snapshot->status = status;
    return status;
}

enum cytv_stop_status cytv_stop_publish(const struct cytv_stop_binding *binding,
                                      const char nonce[CYTV_STOP_NONCE_LENGTH + 1u],
                                      struct cytv_stop_publication *publication)
{
    if (!publication) return CYTV_STOP_UNKNOWN;
    memset(publication, 0, sizeof(*publication));
    publication->precheck_status = CYTV_STOP_UNKNOWN;
    publication->channel_status = CYTV_STOP_UNKNOWN;
    if (!valid_nonce(nonce) || !valid_binding(binding) || !producer(binding, getuid())) return CYTV_STOP_UNKNOWN;
    int dir = open_directory(binding, 0), fd = -1;
    if (dir < 0) return CYTV_STOP_UNKNOWN;
    struct cytv_stop_snapshot snapshot = {0};
    enum cytv_stop_status status = scan_directory(dir, binding, &snapshot);
    publication->precheck_status = status;
    if (status != CYTV_STOP_OK) goto done;
    status = CYTV_STOP_UNKNOWN;
    struct stat created, written, directory;
    char name[38], raw[CYTV_STOP_RECORD_CAP];
    if (HOOK(CYTV_STOP_TEST_PRECHECK, -1, dir) || !check_directory(dir, binding, &directory)) goto done;
    (void)snprintf(name, sizeof(name), "Stop.%s", nonce);
    fd = openat(dir, name, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, 0600);
    if (fd < 0) goto done;
    if (fstat(fd, &created) < 0 || !S_ISREG(created.st_mode) || created.st_nlink != 1 ||
        created.st_uid != getuid() || created.st_size != 0) goto done;
    if (created.st_gid != binding->group && fchown(fd, (uid_t)-1, binding->group) < 0) goto done;
    if (fchmod(fd, 0640) < 0 || HOOK(CYTV_STOP_TEST_CREATED, fd, dir)) goto done;
    size_t len = canonical(nonce, raw), used = 0;
    if (!len) goto done;
    while (used < len) {
        ssize_t n = write(fd, raw + used, len - used);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) goto done;
        used += (size_t)n;
    }
    if (fstat(fd, &written) < 0 || !record_metadata(binding, &written) ||
        written.st_dev != created.st_dev || written.st_ino != created.st_ino ||
        (written.st_mode & 07777) != 0640 || written.st_uid != getuid() ||
        HOOK(CYTV_STOP_TEST_WRITTEN, fd, dir) || HOOK(CYTV_STOP_TEST_BEFORE_FILE_SYNC, fd, dir) ||
        fsync(fd) < 0 || HOOK(CYTV_STOP_TEST_FILE_SYNCED, fd, dir) ||
        !check_directory(dir, binding, &directory) || HOOK(CYTV_STOP_TEST_BEFORE_DIR_SYNC, fd, dir) ||
        fsync(dir) < 0 || HOOK(CYTV_STOP_TEST_DIR_SYNCED, fd, dir) ||
        !stable_record(dir, fd, name, &written) || !matching_content(fd, nonce) ||
        !stable_record(dir, fd, name, &written) || !check_directory(dir, binding, &directory)) goto done;
    status = CYTV_STOP_OK;
done:
    /* Leave failed/partial records for fail-closed diagnosis; never delete by name. */
    if (fd >= 0 && close(fd) < 0) status = CYTV_STOP_UNKNOWN;
    if (close(dir) < 0) status = CYTV_STOP_UNKNOWN;
    publication->durable_published = status == CYTV_STOP_OK;
    return status;
}
