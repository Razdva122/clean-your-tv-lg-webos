#ifndef CYTV_PRIVATE_IO_H
#define CYTV_PRIVATE_IO_H

#include <stddef.h>
#include <sys/types.h>

#define CYTV_PRIVATE_BINDING_VERSION 1u
#define CYTV_PRIVATE_MAX_EVENTS 64u
#define CYTV_PRIVATE_EVENT_BYTES 16384u

struct cytv_private_identity { dev_t dev; ino_t ino; };
/* Trusted provisioning configuration, never inferred from the objects admitted.
 * NoRoot only. No lease, inode, FD or raw event is Home authority. */
struct cytv_private_binding {
    unsigned version;
    uid_t owner;
    gid_t group;
    struct cytv_private_identity root, journal, lock;
};
enum cytv_private_status {
    CYTV_PRIVATE_OK = 0,
    CYTV_PRIVATE_UNKNOWN,
    CYTV_PRIVATE_BUSY,
    CYTV_PRIVATE_FULL,
    CYTV_PRIVATE_OVERFLOW
};
struct cytv_lease;
struct cytv_private_tx;

/* All APIs are synchronous, single serialized executor only; no concurrent
 * handle access, including close/end. Async bindings must reject new operations
 * on cancellation and drain all submitted IO before completion/end/close.
 * Handles are PID-bound. A lease lasts across transactions until explicit close.
 * No creation/repair, no arbitrary paths, no credential or authorization API. */
enum cytv_private_status cytv_lease_acquire(const struct cytv_private_binding *, struct cytv_lease **);
/* Trusted bootstrap only. Fresh LOCK_SH contention probe FIRST (rejects shared
 * locks without upgrading them), inherited LOCK_EX check SECOND.
 * Confirms current exclusion, not historical FD provenance. Borrows inherited
 * FD on both success and failure; stores a CLOEXEC duplicate on success. Caller
 * MUST close its original/extra duplicates after successful adopt. */
enum cytv_private_status cytv_lease_adopt(const struct cytv_private_binding *, int inherited_fd,
                                        struct cytv_lease **);
/* Close marks closing. BUSY retains handle and all FDs until tx ends; retry.
 * Never LOCK_UN: other intentional fork duplicates share the open description. */
enum cytv_private_status cytv_lease_close(struct cytv_lease **);
enum cytv_private_status cytv_tx_begin(struct cytv_lease *, struct cytv_private_tx **);
/* End marks ending. BUSY retains handle/lease while IO is active; retry after
 * the operation returns. Successful end consumes/nulls the tx, not the lease. */
enum cytv_private_status cytv_tx_end(struct cytv_private_tx **);
/* Only in a designated post-fork child, no outstanding tx: detach all library
 * FDs and return one non-CLOEXEC lease FD. Immediately exec the trusted receiver
 * or close it. Unrelated children MUST discard, not handoff. No extra duplicates
 * may survive; caller owns closing any FDs it duplicated outside this library. */
enum cytv_private_status cytv_lease_child_handoff(struct cytv_lease **, int *fd);
enum cytv_private_status cytv_lease_child_discard(struct cytv_lease **);

#ifdef CYTV_PRIVATE_TEST_BUILD
enum cytv_private_test_point {
    CYTV_PRIVATE_TEST_LEASE_CHECK,
    CYTV_PRIVATE_TEST_TX_ACTIVE
};
int cytv_private_test_hook(enum cytv_private_test_point, int file_fd);
#endif
#endif
