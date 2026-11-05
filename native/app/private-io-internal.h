#ifndef CYTV_PRIVATE_IO_INTERNAL_H
#define CYTV_PRIVATE_IO_INTERNAL_H
#include "private-io.h"
#include <sys/stat.h>

#if defined(CYTV_PRIVATE_TEST_ROOT) && !defined(CYTV_PRIVATE_TEST_BUILD)
#error "Private path overrides require an explicit test build"
#endif
#ifdef CYTV_PRIVATE_TEST_BUILD
#ifndef CYTV_PRIVATE_TEST_ROOT
#error "Private test builds require an isolated root"
#endif
#define CYTV_PRIVATE_ROOT CYTV_PRIVATE_TEST_ROOT
#define PRIVATE_HOOK(point, fd) cytv_private_test_hook(point, fd)
#else
#define CYTV_PRIVATE_ROOT "/cytv-helper-state"
#define PRIVATE_HOOK(point, fd) 0
#endif

struct cytv_lease {
    struct cytv_private_binding binding;
    int root_fd, journal_fd, lock_fd;
    pid_t pid;
    int closing;
    struct cytv_private_tx *active;
};
struct cytv_private_tx {
    struct cytv_lease *lease;
    pid_t pid;
    int busy, ending;
    int loaded;
    size_t count;
    unsigned char *arena;
    size_t lengths[CYTV_PRIVATE_MAX_EVENTS];
    struct stat stamps[CYTV_PRIVATE_MAX_EVENTS];
};
int cytv_private_check(struct cytv_lease *);
int cytv_private_enter(struct cytv_private_tx *);
void cytv_private_leave(struct cytv_private_tx *);
#endif
