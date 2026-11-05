#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "private-io-internal.h"
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/file.h>
#include <unistd.h>

static int binding_valid(const struct cytv_private_binding *b)
{
    return b && b->version == CYTV_PRIVATE_BINDING_VERSION && getuid() != 0 &&
        getuid() == geteuid() && getgid() == getegid() && b->owner == getuid() &&
        b->group != (gid_t)-1 && b->root.ino && b->journal.ino && b->lock.ino;
}

static int pinned(const struct stat *s, const struct cytv_private_identity *id,
                  const struct cytv_private_binding *b, int directory)
{
    return s->st_dev == id->dev && s->st_ino == id->ino && s->st_uid == b->owner &&
        s->st_gid == b->group && (s->st_mode & 07777) == (directory ? 0700 : 0600) &&
        (directory ? S_ISDIR(s->st_mode) : (S_ISREG(s->st_mode) && s->st_nlink == 1 && s->st_size == 0));
}

static int directories_valid(struct cytv_lease *l)
{
    struct stat fd, path;
    const struct cytv_private_binding *b = &l->binding;
    return binding_valid(b) && fstat(l->root_fd, &fd) == 0 &&
        lstat(CYTV_PRIVATE_ROOT, &path) == 0 && pinned(&fd, &b->root, b, 1) &&
        pinned(&path, &b->root, b, 1) && fstat(l->journal_fd, &fd) == 0 &&
        fstatat(l->root_fd, "journal", &path, AT_SYMLINK_NOFOLLOW) == 0 &&
        pinned(&fd, &b->journal, b, 1) && pinned(&path, &b->journal, b, 1);
}

static int lock_valid(struct cytv_lease *l)
{
    struct stat fd, path;
    int flags = fcntl(l->lock_fd, F_GETFL);
    return flags >= 0 && (flags & O_ACCMODE) == O_RDWR && !(flags & O_APPEND) &&
        fstat(l->lock_fd, &fd) == 0 &&
        fstatat(l->root_fd, "controller.lock", &path, AT_SYMLINK_NOFOLLOW) == 0 &&
        pinned(&fd, &l->binding.lock, &l->binding, 0) &&
        pinned(&path, &l->binding.lock, &l->binding, 0);
}

/* A fresh open is a different open-file description. A SH probe must contend:
 * an EX probe would also contend against SH and could admit/upgrade a borrowed
 * shared lock. Closing the probe never unlocks the inherited/owned description.
 * Only EWOULDBLOCK/EAGAIN proves exclusive contention. */
static int contended(struct cytv_lease *l)
{
    int fd = openat(l->root_fd, "controller.lock", O_RDWR | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (fd < 0) return 0;
    struct stat s;
    int ok = fstat(fd, &s) == 0 && pinned(&s, &l->binding.lock, &l->binding, 0);
    if (ok) {
        int rc = flock(fd, LOCK_SH | LOCK_NB);
        ok = rc < 0 && (errno == EWOULDBLOCK || errno == EAGAIN);
    }
    if (close(fd) < 0) ok = 0;
    return ok;
}

int cytv_private_check(struct cytv_lease *l)
{
    return l && l->pid == getpid() && directories_valid(l) && lock_valid(l) &&
        contended(l) && flock(l->lock_fd, LOCK_EX | LOCK_NB) == 0 &&
        !PRIVATE_HOOK(CYTV_PRIVATE_TEST_LEASE_CHECK, l->lock_fd) &&
        directories_valid(l) && lock_valid(l);
}

static int dispose(struct cytv_lease *l)
{
    int ok = 1;
    if (l->lock_fd >= 0 && close(l->lock_fd) < 0) ok = 0;
    if (l->journal_fd >= 0 && close(l->journal_fd) < 0) ok = 0;
    if (l->root_fd >= 0 && close(l->root_fd) < 0) ok = 0;
    if (l->active) free(l->active->arena);
    free(l->active);
    free(l);
    return ok;
}

static struct cytv_lease *open_directories(const struct cytv_private_binding *b)
{
    if (!binding_valid(b)) return NULL;
    struct cytv_lease *l = calloc(1, sizeof(*l));
    if (!l) return NULL;
    l->binding = *b;
    l->root_fd = l->journal_fd = l->lock_fd = -1;
    l->pid = getpid();
    l->root_fd = open(CYTV_PRIVATE_ROOT, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (l->root_fd < 0) goto fail;
    struct stat s, path;
    if (fstat(l->root_fd, &s) < 0 || lstat(CYTV_PRIVATE_ROOT, &path) < 0 ||
        !pinned(&s, &b->root, b, 1) || !pinned(&path, &b->root, b, 1)) goto fail;
    l->journal_fd = openat(l->root_fd, "journal", O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (l->journal_fd < 0 || !directories_valid(l)) goto fail;
    return l;
fail:
    (void)dispose(l);
    return NULL;
}

enum cytv_private_status cytv_lease_acquire(const struct cytv_private_binding *b, struct cytv_lease **out)
{
    if (!out || *out) return CYTV_PRIVATE_UNKNOWN;
    struct cytv_lease *l = open_directories(b);
    if (!l) return CYTV_PRIVATE_UNKNOWN;
    enum cytv_private_status status = CYTV_PRIVATE_UNKNOWN;
    l->lock_fd = openat(l->root_fd, "controller.lock", O_RDWR | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC);
    if (l->lock_fd < 0 || !lock_valid(l)) goto fail;
    if (flock(l->lock_fd, LOCK_EX | LOCK_NB) < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) status = CYTV_PRIVATE_BUSY;
        goto fail;
    }
    if (!cytv_private_check(l)) goto fail;
    *out = l;
    return CYTV_PRIVATE_OK;
fail:
    (void)dispose(l);
    return status;
}

enum cytv_private_status cytv_lease_adopt(const struct cytv_private_binding *b, int inherited, struct cytv_lease **out)
{
    if (!out || *out || inherited < 3) return CYTV_PRIVATE_UNKNOWN;
    struct cytv_lease *l = open_directories(b);
    if (!l) return CYTV_PRIVATE_UNKNOWN;
    /* Borrow only for validation; failure never closes the caller's FD. */
    l->lock_fd = inherited;
    int ok = lock_valid(l) && directories_valid(l) && contended(l) &&
        flock(inherited, LOCK_EX | LOCK_NB) == 0;
    l->lock_fd = -1;
    if (!ok) goto fail;
    l->lock_fd = fcntl(inherited, F_DUPFD_CLOEXEC, 3);
    if (l->lock_fd < 0 || !cytv_private_check(l)) goto fail;
    /* Original stays caller-owned on every path; only the duplicate is ours. */
    *out = l;
    return CYTV_PRIVATE_OK;
fail:
    (void)dispose(l);
    return CYTV_PRIVATE_UNKNOWN;
}

enum cytv_private_status cytv_lease_close(struct cytv_lease **ptr)
{
    if (!ptr || !*ptr || (*ptr)->pid != getpid()) return CYTV_PRIVATE_UNKNOWN;
    struct cytv_lease *l = *ptr;
    l->closing = 1;
    if (l->active) return CYTV_PRIVATE_BUSY;
    *ptr = NULL;
    return dispose(l) ? CYTV_PRIVATE_OK : CYTV_PRIVATE_UNKNOWN;
}

enum cytv_private_status cytv_tx_begin(struct cytv_lease *l, struct cytv_private_tx **out)
{
    if (!out || *out || !l || l->pid != getpid() || l->closing) return CYTV_PRIVATE_UNKNOWN;
    if (l->active) return CYTV_PRIVATE_BUSY;
    if (!cytv_private_check(l)) return CYTV_PRIVATE_UNKNOWN;
    struct cytv_private_tx *t = calloc(1, sizeof(*t));
    if (!t) return CYTV_PRIVATE_UNKNOWN;
    t->lease = l;
    t->pid = getpid();
    t->busy = 1;
    l->active = t;
    *out = t;
    int failed = PRIVATE_HOOK(CYTV_PRIVATE_TEST_TX_ACTIVE, l->lock_fd);
    t->busy = 0;
    if (failed) { (void)cytv_tx_end(out); return CYTV_PRIVATE_UNKNOWN; }
    return CYTV_PRIVATE_OK;
}

int cytv_private_enter(struct cytv_private_tx *t)
{
    if (!t || t->pid != getpid() || t->busy || t->ending || t->lease->closing) return 0;
    t->busy = 1;
    if (!cytv_private_check(t->lease)) { t->busy = 0; return 0; }
    return 1;
}
void cytv_private_leave(struct cytv_private_tx *t) { t->busy = 0; }

enum cytv_private_status cytv_tx_validate(struct cytv_private_tx *t)
{
    if (!cytv_private_enter(t)) return CYTV_PRIVATE_UNKNOWN;
    int valid = cytv_private_check(t->lease) && !t->ending && !t->lease->closing;
    cytv_private_leave(t);
    return valid ? CYTV_PRIVATE_OK : CYTV_PRIVATE_UNKNOWN;
}

enum cytv_private_status cytv_tx_end(struct cytv_private_tx **ptr)
{
    if (!ptr || !*ptr || (*ptr)->pid != getpid()) return CYTV_PRIVATE_UNKNOWN;
    struct cytv_private_tx *t = *ptr;
    t->ending = 1;
    if (t->busy) return CYTV_PRIVATE_BUSY;
    t->lease->active = NULL;
    free(t->arena);
    free(t);
    *ptr = NULL;
    return CYTV_PRIVATE_OK;
}

enum cytv_private_status cytv_lease_child_discard(struct cytv_lease **ptr)
{
    if (!ptr || !*ptr || (*ptr)->pid == getpid()) return CYTV_PRIVATE_UNKNOWN;
    struct cytv_lease *l = *ptr;
    *ptr = NULL;
    return dispose(l) ? CYTV_PRIVATE_OK : CYTV_PRIVATE_UNKNOWN;
}

enum cytv_private_status cytv_lease_child_handoff(struct cytv_lease **ptr, int *out)
{
    if (!ptr || !*ptr || !out || (*ptr)->pid == getpid() || (*ptr)->active || (*ptr)->closing)
        return CYTV_PRIVATE_UNKNOWN;
    *out = -1;
    struct cytv_lease *l = *ptr;
    if (!directories_valid(l) || !lock_valid(l) || !contended(l) ||
        flock(l->lock_fd, LOCK_EX | LOCK_NB) < 0) return CYTV_PRIVATE_UNKNOWN;
    int fd = fcntl(l->lock_fd, F_DUPFD_CLOEXEC, 3);
    if (fd < 0) return CYTV_PRIVATE_UNKNOWN;
    *ptr = NULL;
    if (!dispose(l) || fcntl(fd, F_SETFD, 0) < 0) {
        (void)close(fd);
        return CYTV_PRIVATE_UNKNOWN;
    }
    *out = fd;
    return CYTV_PRIVATE_OK;
}
