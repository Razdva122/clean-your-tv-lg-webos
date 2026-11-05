#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "private-io-internal.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

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
        a->st_uid == b->st_uid && a->st_gid == b->st_gid && a->st_mode == b->st_mode &&
        a->st_nlink == b->st_nlink && a->st_size == b->st_size &&
        a->MTIME.tv_sec == b->MTIME.tv_sec && a->MTIME.tv_nsec == b->MTIME.tv_nsec &&
        a->CTIME.tv_sec == b->CTIME.tv_sec && a->CTIME.tv_nsec == b->CTIME.tv_nsec;
#undef MTIME
#undef CTIME
}

static int utf8(const unsigned char *raw, size_t len)
{
    if (!raw || !len || len > CYTV_PRIVATE_EVENT_BYTES) return 0;
    for (size_t i = 0; i < len;) {
        unsigned value = raw[i++], count = 0, minimum = 0;
        if (!value) return 0;
        if (value < 0x80) continue;
        if (value >= 0xc2 && value <= 0xdf) { count = 1; minimum = 0x80; value &= 0x1f; }
        else if (value >= 0xe0 && value <= 0xef) { count = 2; minimum = 0x800; value &= 0x0f; }
        else if (value >= 0xf0 && value <= 0xf4) { count = 3; minimum = 0x10000; value &= 7; }
        else return 0;
        if (count > len - i) return 0;
        for (unsigned j = 0; j < count; j++) {
            unsigned c = raw[i++];
            if ((c & 0xc0) != 0x80) return 0;
            value = (value << 6) | (c & 0x3f);
        }
        if (value < minimum || value > 0x10ffff || (value >= 0xd800 && value <= 0xdfff)) return 0;
    }
    return 1;
}

static void event_name(unsigned seq, char name[16])
{
    (void)snprintf(name, 16, "entry.%04u.json", seq);
}

static int event_metadata(struct cytv_private_tx *t, const struct stat *s)
{
    const struct cytv_private_binding *b = &t->lease->binding;
    return S_ISREG(s->st_mode) && s->st_dev == b->journal.dev && s->st_nlink == 1 &&
        (s->st_mode & 07777) == 0600 && s->st_uid == b->owner && s->st_gid == b->group &&
        s->st_size > 0 && s->st_size <= CYTV_PRIVATE_EVENT_BYTES;
}

static int stable_event(struct cytv_private_tx *t, int fd, const char *name, const struct stat *before)
{
    struct stat after, path;
    return fstat(fd, &after) == 0 &&
        fstatat(t->lease->journal_fd, name, &path, AT_SYMLINK_NOFOLLOW) == 0 &&
        same_stat(before, &after) && same_stat(&after, &path);
}

/* Enumeration is independent of the retained directory's offset: dup would
 * share that offset and make a second read appear empty. No unbounded readdir. */
static enum cytv_private_status enumerate(struct cytv_private_tx *t, size_t *observed,
                                         size_t *count, struct stat *before)
{
    *observed = *count = 0;
    int fd = openat(t->lease->root_fd, "journal", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return CYTV_PRIVATE_UNKNOWN;
    struct stat retained;
    if (fstat(fd, before) < 0 || fstat(t->lease->journal_fd, &retained) < 0 ||
        !same_stat(before, &retained) || !cytv_private_check(t->lease)) {
        (void)close(fd);
        return CYTV_PRIVATE_UNKNOWN;
    }
    DIR *stream = fdopendir(fd);
    if (!stream) { (void)close(fd); return CYTV_PRIVATE_UNKNOWN; }
    char names[CYTV_PRIVATE_MAX_EVENTS][16];
    int bad_name = 0;
    enum cytv_private_status status = CYTV_PRIVATE_UNKNOWN;
    for (;;) {
        errno = 0;
        struct dirent *entry = readdir(stream);
        if (!entry) { if (errno) goto done; break; }
        if (!strcmp(entry->d_name, ".") || !strcmp(entry->d_name, "..")) continue;
        ++*observed;
        if (PRIVATE_HOOK(CYTV_PRIVATE_TEST_READ_ENTRY, -1)) goto done;
        if (*observed > CYTV_PRIVATE_MAX_EVENTS) { status = CYTV_PRIVATE_OVERFLOW; goto done; }
        if (strnlen(entry->d_name, 16) != 15) bad_name = 1;
        else memcpy(names[*observed - 1], entry->d_name, 16);
    }
    if (bad_name || !*observed) goto done;
    unsigned char seen[CYTV_PRIVATE_MAX_EVENTS] = {0};
    for (size_t i = 0; i < *observed; i++) {
        if (strncmp(names[i], "entry.", 6) || strcmp(names[i] + 10, ".json")) goto done;
        unsigned seq = 0;
        for (size_t j = 6; j < 10; j++) {
            if (names[i][j] < '0' || names[i][j] > '9') goto done;
            seq = seq * 10 + (unsigned)(names[i][j] - '0');
        }
        if (seq >= *observed || seen[seq]) goto done;
        seen[seq] = 1;
    }
    *count = *observed;
    status = CYTV_PRIVATE_OK;
done:
    if (closedir(stream) < 0) status = CYTV_PRIVATE_UNKNOWN;
    if (status != CYTV_PRIVATE_OK) *count = 0;
    return status;
}

static int read_event(struct cytv_private_tx *t, unsigned seq, unsigned char *raw,
                      size_t *len, struct stat *stamp, int sync)
{
    char name[16]; event_name(seq, name);
    struct stat before, opened;
    int dir = t->lease->journal_fd;
    if (fstatat(dir, name, &before, AT_SYMLINK_NOFOLLOW) < 0 || !event_metadata(t, &before) ||
        PRIVATE_HOOK(CYTV_PRIVATE_TEST_READ_BEFORE_OPEN, -1)) return 0;
    int fd = openat(dir, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return 0;
    int ok = 0;
    if (fstat(fd, &opened) < 0 || !same_stat(&before, &opened) ||
        PRIVATE_HOOK(CYTV_PRIVATE_TEST_READ_OPEN, fd)) goto done;
    size_t size = (size_t)before.st_size, used = 0;
    while (used < size) {
        ssize_t n = pread(fd, raw + used, size - used, (off_t)used);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) goto done;
        used += (size_t)n;
    }
    unsigned char extra;
    ssize_t n;
    do { n = pread(fd, &extra, 1, (off_t)size); } while (n < 0 && errno == EINTR);
    if (n != 0 || !utf8(raw, size)) goto done;
    if (sync && (PRIVATE_HOOK(CYTV_PRIVATE_TEST_READ_FILE_SYNC, fd) || fsync(fd) < 0)) goto done;
    if (!stable_event(t, fd, name, &before)) goto done;
    *len = size;
    *stamp = before;
    ok = 1;
done:
    if (close(fd) < 0) ok = 0;
    return ok;
}

static int stable_snapshot(struct cytv_private_tx *t, const struct stat *directory)
{
    struct stat after;
    if (!cytv_private_check(t->lease) || fstat(t->lease->journal_fd, &after) < 0 ||
        !same_stat(directory, &after)) return 0;
    for (size_t i = 0; i < t->count; i++) {
        char name[16]; event_name((unsigned)i, name);
        if (fstatat(t->lease->journal_fd, name, &after, AT_SYMLINK_NOFOLLOW) < 0 ||
            !same_stat(&t->stamps[i], &after)) return 0;
    }
    return cytv_private_check(t->lease);
}

static unsigned char *slot(struct cytv_private_tx *t, size_t index)
{
    return t->arena + index * CYTV_PRIVATE_EVENT_BYTES;
}

/* Revalidate the exact cached history, never silently adopt changed bytes as
 * the basis for a caller's already-computed append/hash-chain decision. */
static int verify_cache(struct cytv_private_tx *t)
{
    size_t observed, count;
    struct stat directory;
    if (enumerate(t, &observed, &count, &directory) != CYTV_PRIVATE_OK || count != t->count) return 0;
    unsigned char *scratch = malloc(CYTV_PRIVATE_EVENT_BYTES);
    if (!scratch) return 0;
    int ok = 1;
    for (size_t i = 0; i < count; i++) {
        size_t len;
        struct stat stamp;
        if (!read_event(t, (unsigned)i, scratch, &len, &stamp, 0) || len != t->lengths[i] ||
            !same_stat(&stamp, &t->stamps[i]) || memcmp(scratch, slot(t, i), len)) { ok = 0; break; }
    }
    free(scratch);
    return ok && stable_snapshot(t, &directory);
}

enum cytv_private_status cytv_journal_read(struct cytv_private_tx *t, struct cytv_journal_view *out)
{
    if (!out) return CYTV_PRIVATE_UNKNOWN;
    memset(out, 0, sizeof(*out));
    if (!cytv_private_enter(t)) return CYTV_PRIVATE_UNKNOWN;
    t->loaded = 0;
    t->count = 0;
    size_t count;
    struct stat directory;
    enum cytv_private_status status = enumerate(t, &out->observed_entries, &count, &directory);
    if (status != CYTV_PRIVATE_OK) goto done;
    status = CYTV_PRIVATE_UNKNOWN;
    if (!t->arena) t->arena = malloc(CYTV_PRIVATE_MAX_EVENTS * CYTV_PRIVATE_EVENT_BYTES);
    if (!t->arena) goto done;
    for (size_t i = 0; i < count; i++) {
        if (!read_event(t, (unsigned)i, slot(t, i), &t->lengths[i], &t->stamps[i], 1)) goto done;
    }
    t->count = count;
    if (PRIVATE_HOOK(CYTV_PRIVATE_TEST_READ_DIR_SYNC, t->lease->journal_fd) ||
        fsync(t->lease->journal_fd) < 0 || PRIVATE_HOOK(CYTV_PRIVATE_TEST_READ_VERIFIED, -1) ||
        !stable_snapshot(t, &directory)) goto done;
    t->loaded = 1;
    out->count = count;
    for (size_t i = 0; i < count; i++) {
        out->records[i].seq = (unsigned)i;
        out->records[i].len = t->lengths[i];
        out->records[i].raw = slot(t, i);
    }
    status = CYTV_PRIVATE_OK;
done:
    if (status != CYTV_PRIVATE_OK) t->count = 0;
    cytv_private_leave(t);
    return status;
}

enum cytv_private_status cytv_journal_append(struct cytv_private_tx *t, unsigned seq,
                                          const unsigned char *raw, size_t len,
                                          struct cytv_append_receipt *out)
{
    if (!out) return CYTV_PRIVATE_UNKNOWN;
    memset(out, 0, sizeof(*out));
    if (!cytv_private_enter(t)) return CYTV_PRIVATE_UNKNOWN;
    int loaded = t->loaded;
    t->loaded = 0;
    enum cytv_private_status status = CYTV_PRIVATE_UNKNOWN;
    int fd = -1;
    if (!loaded || !t->count) goto done;
    if (t->count == CYTV_PRIVATE_MAX_EVENTS) { status = CYTV_PRIVATE_FULL; goto done; }
    if (seq != t->count || !utf8(raw, len)) goto done;
    memmove(slot(t, seq), raw, len);
    if (!verify_cache(t) || !cytv_private_check(t->lease)) goto done;
    char name[16]; event_name(seq, name);
    int dir = t->lease->journal_fd;
    fd = openat(dir, name, O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, 0600);
    if (fd < 0) goto done;
    struct stat created, written;
    if (fstat(fd, &created) < 0 || !S_ISREG(created.st_mode) || created.st_nlink != 1 ||
        created.st_uid != t->lease->binding.owner || created.st_size != 0) goto done;
    if (created.st_gid != t->lease->binding.group &&
        fchown(fd, (uid_t)-1, t->lease->binding.group) < 0) goto done;
    if (fchmod(fd, 0600) < 0 || PRIVATE_HOOK(CYTV_PRIVATE_TEST_APPEND_CREATED, fd)) goto done;
    size_t used = 0;
    while (used < len) {
        ssize_t n = write(fd, slot(t, seq) + used, len - used);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) goto done;
        used += (size_t)n;
    }
    if (fstat(fd, &written) < 0 || !event_metadata(t, &written) ||
        written.st_dev != created.st_dev || written.st_ino != created.st_ino ||
        (size_t)written.st_size != len || PRIVATE_HOOK(CYTV_PRIVATE_TEST_APPEND_WRITTEN, fd) ||
        PRIVATE_HOOK(CYTV_PRIVATE_TEST_APPEND_FILE_SYNC, fd) || fsync(fd) < 0 ||
        PRIVATE_HOOK(CYTV_PRIVATE_TEST_APPEND_FILE_SYNCED, fd) || !cytv_private_check(t->lease) ||
        PRIVATE_HOOK(CYTV_PRIVATE_TEST_APPEND_DIR_SYNC, dir) || fsync(dir) < 0 ||
        PRIVATE_HOOK(CYTV_PRIVATE_TEST_APPEND_DIR_SYNCED, fd) ||
        !stable_event(t, fd, name, &written)) goto done;
    t->lengths[seq] = len;
    t->stamps[seq] = written;
    t->count = (size_t)seq + 1;
    if (!verify_cache(t) || PRIVATE_HOOK(CYTV_PRIVATE_TEST_APPEND_VERIFIED, fd) ||
        !stable_event(t, fd, name, &written) || !cytv_private_check(t->lease)) goto done;
    status = CYTV_PRIVATE_OK;
done:
    if (fd >= 0 && close(fd) < 0) status = CYTV_PRIVATE_UNKNOWN;
    if (status == CYTV_PRIVATE_OK) {
        t->loaded = 1;
        out->durable = 1;
        out->event.seq = seq;
        out->event.len = len;
        out->event.raw = slot(t, seq);
    }
    /* Keep any partial/unacknowledged record; recovery is a full explicit read. */
    cytv_private_leave(t);
    return status;
}
