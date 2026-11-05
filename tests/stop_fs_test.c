#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "stop-fs.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#ifndef CYTV_STOP_TEST_PATH
#error "The test fixture requires a compile-time path"
#endif

#define CHECK(v) do { if (!(v)) { fprintf(stderr, "line %d: %s\n", __LINE__, #v); exit(1); } } while (0)
static struct cytv_stop_binding binding;
static char current_nonce[33];
static enum cytv_stop_test_point target;
static int action, ready_fd = -1, go_fd = -1;
static size_t entries, record_opens;
enum { NONE, FAIL_IO, CUT, CHANGE_RECORD, FIFO_RACE, REMOVE_RECORD,
       REPLACE_DIRECTORY, REPLACE_RECORD, CHANGE_MODE, BARRIER };

static void nonce(unsigned n, char out[33])
{
    CHECK(snprintf(out, 33, "%032x", n) == 32);
}

static void record_path(const char *id, char out[1024])
{
    CHECK(snprintf(out, 1024, "%s/Stop.%s", CYTV_STOP_TEST_PATH, id) < 1024);
}

static size_t canonical(const char *id, char out[128])
{
    int n = snprintf(out, 128, "{\"id\":\"%s\",\"op\":\"stop\",\"v\":1}\n", id);
    CHECK(n > 0 && n < 128);
    return (size_t)n;
}

static void fixture_record(unsigned n, mode_t mode)
{
    char id[33], path[1024], raw[128];
    nonce(n, id);
    record_path(id, path);
    size_t len = canonical(id, raw);
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
    CHECK(fd >= 0);
    CHECK(write(fd, raw, len) == (ssize_t)len);
    CHECK(fchmod(fd, mode) == 0);
    CHECK(close(fd) == 0);
}

static void initialize(void)
{
    struct stat s;
    CHECK(chmod(CYTV_STOP_TEST_PATH, 0770) == 0);
    CHECK(lstat(CYTV_STOP_TEST_PATH, &s) == 0);
    memset(&binding, 0, sizeof(binding));
    binding.version = CYTV_STOP_BINDING_VERSION;
    binding.directory_dev = s.st_dev;
    binding.directory_ino = s.st_ino;
    /* Expected credentials come from this fixture's creation authority. */
    binding.owner = getuid();
    binding.group = getgid();
    binding.producer_count = 1;
    binding.producers[0] = getuid();
    nonce(1, current_nonce);
}

static void unchanged_publication(const struct cytv_stop_publication *p)
{
    CHECK(!p->private_adopted && !p->physical_stop_verified);
    CHECK(p->channel_status == CYTV_STOP_UNKNOWN);
}

static void single_byte(int fd, int writing)
{
    char c = 'x';
    ssize_t n;
    do { n = writing ? write(fd, &c, 1) : read(fd, &c, 1); } while (n < 0 && errno == EINTR);
    CHECK(n == 1);
}

int cytv_stop_test_hook(enum cytv_stop_test_point point, int fd, int directory_fd)
{
    (void)directory_fd;
    if (point == CYTV_STOP_TEST_LIST_ENTRY) entries++;
    if (point == CYTV_STOP_TEST_RECORD_OPEN) record_opens++;
    if (!action || point != target) return 0;
    char path[1024], raw[128];
    record_path(current_nonce, path);
    switch (action) {
    case FAIL_IO: errno = EIO; return -1;
    case CUT: _exit(73);
    case BARRIER: single_byte(ready_fd, 1); single_byte(go_fd, 0); return 0;
    case CHANGE_RECORD: {
        int w = open(path, O_WRONLY | O_TRUNC);
        CHECK(w >= 0 && write(w, "{", 1) == 1 && close(w) == 0);
        break;
    }
    case FIFO_RACE:
        CHECK(unlink(path) == 0 && mkfifo(path, 0640) == 0);
        break;
    case REMOVE_RECORD: CHECK(unlink(path) == 0); break;
    case REPLACE_DIRECTORY:
        CHECK(rename(CYTV_STOP_TEST_PATH, CYTV_STOP_TEST_PATH ".old") == 0);
        CHECK(mkdir(CYTV_STOP_TEST_PATH, 0770) == 0);
        break;
    case REPLACE_RECORD: {
        CHECK(unlink(path) == 0);
        int w = open(path, O_WRONLY | O_CREAT | O_EXCL, 0600);
        size_t len = canonical(current_nonce, raw);
        CHECK(w >= 0 && write(w, raw, len) == (ssize_t)len);
        CHECK(fchmod(w, 0640) == 0 && close(w) == 0);
        break;
    }
    case CHANGE_MODE: CHECK(fd >= 0 && fchmod(fd, 0777) == 0); break;
    default: CHECK(0);
    }
    action = NONE;
    return 0;
}

static void empty(void)
{
    struct cytv_stop_snapshot s;
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_OK);
    CHECK(s.count == 0 && s.observed_entries == 0);
}

static void publish(void)
{
    struct cytv_stop_publication p;
    struct cytv_stop_snapshot s;
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_OK);
    CHECK(p.durable_published && p.precheck_status == CYTV_STOP_OK);
    unchanged_publication(&p);
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_OK && s.count == 1);
    CHECK(strcmp(s.nonces[0], current_nonce) == 0);
    char path[1024]; struct stat st;
    record_path(current_nonce, path);
    CHECK(lstat(path, &st) == 0 && (st.st_mode & 07777) == 0640);
}

static void unbound(void)
{
    struct cytv_stop_snapshot s; struct cytv_stop_publication p;
    struct cytv_stop_binding zero = {0};
    CHECK(cytv_stop_scan(NULL, &s) == CYTV_STOP_UNKNOWN);
    CHECK(cytv_stop_scan(&zero, &s) == CYTV_STOP_UNKNOWN);
    CHECK(cytv_stop_publish(&zero, current_nonce, &p) == CYTV_STOP_UNKNOWN);
    CHECK(!p.durable_published); unchanged_publication(&p);
    struct cytv_stop_binding invalid = binding;
    invalid.producer_count = CYTV_STOP_MAX_PRODUCERS + 1;
    CHECK(cytv_stop_scan(&invalid, &s) == CYTV_STOP_UNKNOWN);
    CHECK(cytv_stop_publish(&invalid, current_nonce, &p) == CYTV_STOP_UNKNOWN);
    invalid = binding; invalid.producer_count = 2;
    invalid.producers[1] = invalid.producers[0];
    CHECK(cytv_stop_scan(&invalid, &s) == CYTV_STOP_UNKNOWN);
    CHECK(cytv_stop_publish(&binding, current_nonce, NULL) == CYTV_STOP_UNKNOWN);
    CHECK(cytv_stop_scan(&binding, NULL) == CYTV_STOP_UNKNOWN);
    empty();
}

static void mismatch(const char *kind)
{
    struct cytv_stop_snapshot s; struct cytv_stop_publication p; struct stat st;
    CHECK(chmod(CYTV_STOP_TEST_PATH, 0777) == 0);
    if (!strcmp(kind, "owner")) binding.owner++;
    else if (!strcmp(kind, "group")) binding.group++;
    else { binding.producers[0]++; CHECK(chmod(CYTV_STOP_TEST_PATH, 0770) == 0); fixture_record(1, 0640); }
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_UNKNOWN);
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_UNKNOWN);
    CHECK(!p.durable_published); unchanged_publication(&p);
    CHECK(lstat(CYTV_STOP_TEST_PATH, &st) == 0);
    if (strcmp(kind, "producer")) CHECK((st.st_mode & 07777) == 0777);
}

static void native_repair(void)
{
    struct cytv_stop_snapshot s; struct stat st;
    fixture_record(1, 0777);
    CHECK(chmod(CYTV_STOP_TEST_PATH, 0777) == 0);
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_OK && s.count == 1);
    CHECK(lstat(CYTV_STOP_TEST_PATH, &st) == 0 && (st.st_mode & 07777) == 0770);
    char path[1024]; record_path(current_nonce, path);
    CHECK(lstat(path, &st) == 0 && (st.st_mode & 07777) == 0777);
}

static void no_publisher_repair(void)
{
    struct cytv_stop_publication p; struct stat st;
    CHECK(chmod(CYTV_STOP_TEST_PATH, 0777) == 0);
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_UNKNOWN);
    CHECK(!p.durable_published);
    CHECK(lstat(CYTV_STOP_TEST_PATH, &st) == 0 && (st.st_mode & 07777) == 0777);
}

static void directory_change(int link)
{
    struct cytv_stop_snapshot s; struct cytv_stop_publication p;
    CHECK(rename(CYTV_STOP_TEST_PATH, CYTV_STOP_TEST_PATH ".old") == 0);
    if (link) CHECK(symlink(CYTV_STOP_TEST_PATH ".old", CYTV_STOP_TEST_PATH) == 0);
    else CHECK(mkdir(CYTV_STOP_TEST_PATH, 0770) == 0);
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_UNKNOWN);
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_UNKNOWN);
}

static void invalid_record(const char *kind)
{
    char path[1024]; record_path(current_nonce, path);
    if (!strcmp(kind, "symlink")) CHECK(symlink(CYTV_STOP_TEST_PATH ".outside", path) == 0);
    else if (!strcmp(kind, "fifo")) CHECK(mkfifo(path, 0640) == 0);
    else if (!strcmp(kind, "unknown")) {
        int fd = open(CYTV_STOP_TEST_PATH "/unknown", O_CREAT | O_EXCL | O_WRONLY, 0640);
        CHECK(fd >= 0 && close(fd) == 0);
    } else {
        fixture_record(1, 0640);
        if (!strcmp(kind, "hardlink")) CHECK(link(path, CYTV_STOP_TEST_PATH ".alias") == 0);
        else if (!strcmp(kind, "mode")) CHECK(chmod(path, 0660) == 0);
        else if (!strcmp(kind, "special")) {
            struct stat st; CHECK(chmod(path, 01777) == 0);
            CHECK(lstat(path, &st) == 0 && (st.st_mode & 01000));
        } else {
            int fd = open(path, O_WRONLY | O_TRUNC); CHECK(fd >= 0);
            if (!strcmp(kind, "oversize")) { char bytes[257]; memset(bytes, 'x', sizeof(bytes)); CHECK(write(fd, bytes, sizeof(bytes)) == (ssize_t)sizeof(bytes)); }
            else if (!strcmp(kind, "start")) {
                char raw[128]; int n = snprintf(raw, sizeof(raw), "{\"id\":\"%s\",\"op\":\"start\",\"v\":1}\n", current_nonce);
                CHECK(n > 0 && write(fd, raw, (size_t)n) == n);
            } else if (!strcmp(kind, "id")) {
                char raw[128], id[33]; nonce(2, id); size_t n = canonical(id, raw);
                CHECK(write(fd, raw, n) == (ssize_t)n);
            } else CHECK(write(fd, "{", 1) == 1);
            CHECK(close(fd) == 0);
        }
    }
    struct cytv_stop_snapshot s; struct cytv_stop_publication p;
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_UNKNOWN && s.count == 0);
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_UNKNOWN && !p.durable_published);
}

static void scan_race(int which, enum cytv_stop_test_point at)
{
    fixture_record(1, 0640); action = which; target = at;
    struct cytv_stop_snapshot s;
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_UNKNOWN && s.count == 0);
}

static void collision(void)
{
    fixture_record(1, 0640);
    char path[1024], expected[128], actual[128]; struct stat before, after;
    record_path(current_nonce, path); size_t len = canonical(current_nonce, expected);
    CHECK(lstat(path, &before) == 0);
    struct cytv_stop_publication p;
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_UNKNOWN && !p.durable_published);
    CHECK(lstat(path, &after) == 0 && before.st_ino == after.st_ino);
    int fd = open(path, O_RDONLY); CHECK(fd >= 0 && read(fd, actual, sizeof(actual)) == (ssize_t)len);
    CHECK(!memcmp(expected, actual, len) && close(fd) == 0);
}

static void capacity(int overflow)
{
    unsigned count = overflow ? 1000 : 16;
    for (unsigned i = 0; i < count; i++) fixture_record(i + 1, 0640);
    enum cytv_stop_status want = overflow ? CYTV_STOP_OVERFLOW : CYTV_STOP_FULL;
    struct cytv_stop_snapshot s; struct cytv_stop_publication p;
    CHECK(cytv_stop_scan(&binding, &s) == want);
    CHECK(s.observed_entries == (overflow ? 17u : 16u));
    CHECK(s.count == (overflow ? 0u : 16u));
    if (overflow) CHECK(record_opens == 0 && entries == 17);
    nonce(2000, current_nonce);
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == want && !p.durable_published);
    unchanged_publication(&p);
    char path[1024]; record_path(current_nonce, path); CHECK(access(path, F_OK) < 0 && errno == ENOENT);
}

static void concurrent(void)
{
    for (unsigned i = 1; i <= 15; i++) fixture_record(i, 0640);
    int ready[2], go[2]; CHECK(pipe(ready) == 0 && pipe(go) == 0);
    pid_t children[2];
    for (unsigned i = 0; i < 2; i++) {
        children[i] = fork(); CHECK(children[i] >= 0);
        if (children[i] == 0) {
            alarm(8); close(ready[0]); close(go[1]); ready_fd = ready[1]; go_fd = go[0];
            action = BARRIER; target = CYTV_STOP_TEST_PRECHECK; nonce(100 + i, current_nonce);
            struct cytv_stop_publication p;
            CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_OK && p.durable_published);
            unchanged_publication(&p); close(ready_fd); close(go_fd); _exit(0);
        }
    }
    close(ready[1]); close(go[0]);
    single_byte(ready[0], 0); single_byte(ready[0], 0);
    single_byte(go[1], 1); single_byte(go[1], 1); close(ready[0]); close(go[1]);
    for (unsigned i = 0; i < 2; i++) { int status; CHECK(waitpid(children[i], &status, 0) == children[i]); CHECK(WIFEXITED(status) && WEXITSTATUS(status) == 0); }
    struct cytv_stop_snapshot s;
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_OVERFLOW && s.observed_entries == 17);
}

static void retained_fd(void)
{
    fixture_record(1, 0777); char path[1024]; record_path(current_nonce, path);
    int fd = open(path, O_RDWR); CHECK(fd >= 0 && flock(fd, LOCK_EX | LOCK_NB) == 0);
    CHECK(chmod(CYTV_STOP_TEST_PATH, 0777) == 0);
    struct cytv_stop_snapshot s; struct cytv_stop_publication p;
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_OK);
    nonce(2, current_nonce);
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_OK && p.durable_published);
    CHECK(ftruncate(fd, 1) == 0);
    CHECK(cytv_stop_scan(&binding, &s) == CYTV_STOP_UNKNOWN);
    CHECK(close(fd) == 0);
}

static void publication_fault(int which, enum cytv_stop_test_point at)
{
    action = which; target = at; struct cytv_stop_publication p;
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_UNKNOWN);
    CHECK(!p.durable_published); unchanged_publication(&p);
}

static void cut(enum cytv_stop_test_point at)
{
    pid_t child = fork(); CHECK(child >= 0);
    if (child == 0) { action = CUT; target = at; struct cytv_stop_publication p; (void)cytv_stop_publish(&binding, current_nonce, &p); _exit(1); }
    int status; CHECK(waitpid(child, &status, 0) == child && WIFEXITED(status) && WEXITSTATUS(status) == 73);
    struct cytv_stop_snapshot s;
    CHECK(cytv_stop_scan(&binding, &s) == (at == CYTV_STOP_TEST_CREATED ? CYTV_STOP_UNKNOWN : CYTV_STOP_OK));
}

static void bad_nonce(void)
{
    struct cytv_stop_publication p;
    char short_nonce[CYTV_STOP_NONCE_LENGTH + 1u] = "abc";
    CHECK(cytv_stop_publish(&binding, short_nonce, &p) == CYTV_STOP_UNKNOWN && !p.durable_published);
    memset(current_nonce, 'A', 32); current_nonce[32] = 0;
    CHECK(cytv_stop_publish(&binding, current_nonce, &p) == CYTV_STOP_UNKNOWN && !p.durable_published);
    empty();
}

int main(int argc, char **argv)
{
    CHECK(argc == 2); alarm(10); initialize(); const char *name = argv[1];
    if (!strcmp(name, "empty")) empty();
    else if (!strcmp(name, "publish")) publish();
    else if (!strcmp(name, "unbound")) unbound();
    else if (!strncmp(name, "mismatch-", 9)) mismatch(name + 9);
    else if (!strcmp(name, "repair")) native_repair();
    else if (!strcmp(name, "publisher-no-repair")) no_publisher_repair();
    else if (!strcmp(name, "directory-replace")) directory_change(0);
    else if (!strcmp(name, "directory-symlink")) directory_change(1);
    else if (!strncmp(name, "invalid-", 8)) invalid_record(name + 8);
    else if (!strcmp(name, "fifo-race")) scan_race(FIFO_RACE, CYTV_STOP_TEST_BEFORE_RECORD_OPEN);
    else if (!strcmp(name, "remove-race")) scan_race(REMOVE_RECORD, CYTV_STOP_TEST_BEFORE_RECORD_OPEN);
    else if (!strcmp(name, "record-race")) scan_race(CHANGE_RECORD, CYTV_STOP_TEST_RECORD_OPEN);
    else if (!strcmp(name, "directory-race")) scan_race(REPLACE_DIRECTORY, CYTV_STOP_TEST_RECORD_READ);
    else if (!strcmp(name, "collision")) collision();
    else if (!strcmp(name, "full")) capacity(0);
    else if (!strcmp(name, "overflow")) capacity(1);
    else if (!strcmp(name, "concurrent")) concurrent();
    else if (!strcmp(name, "retained-fd")) retained_fd();
    else if (!strcmp(name, "file-sync-fail")) publication_fault(FAIL_IO, CYTV_STOP_TEST_BEFORE_FILE_SYNC);
    else if (!strcmp(name, "dir-sync-fail")) publication_fault(FAIL_IO, CYTV_STOP_TEST_BEFORE_DIR_SYNC);
    else if (!strcmp(name, "publish-replace")) publication_fault(REPLACE_RECORD, CYTV_STOP_TEST_DIR_SYNCED);
    else if (!strcmp(name, "publish-corrupt")) publication_fault(CHANGE_RECORD, CYTV_STOP_TEST_DIR_SYNCED);
    else if (!strcmp(name, "publish-mode")) publication_fault(CHANGE_MODE, CYTV_STOP_TEST_WRITTEN);
    else if (!strcmp(name, "cut-create")) cut(CYTV_STOP_TEST_CREATED);
    else if (!strcmp(name, "cut-write")) cut(CYTV_STOP_TEST_WRITTEN);
    else if (!strcmp(name, "cut-file-sync")) cut(CYTV_STOP_TEST_FILE_SYNCED);
    else if (!strcmp(name, "cut-dir-sync")) cut(CYTV_STOP_TEST_DIR_SYNCED);
    else if (!strcmp(name, "bad-nonce")) bad_nonce();
    else CHECK(0);
    puts("PASS"); return 0;
}
