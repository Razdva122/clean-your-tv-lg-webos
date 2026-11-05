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
/* Revalidate the live opaque tx and actual pinned lease/lock on its serialized
 * executor. OK is a current endpoint check, not future/atomic provenance or
 * Home authority. Does not consume the tx, alter journal views or end resources.
 * UNKNOWN includes invalid, busy, ending, closing or wrong-PID handles. */
enum cytv_private_status cytv_tx_validate(struct cytv_private_tx *);
/* End marks ending. BUSY retains handle/lease while IO is active; retry after
 * the operation returns. Successful end consumes/nulls the tx, not the lease.
 * Cleanup is independent of metadata validity; end is NOT a validation ACK. */
enum cytv_private_status cytv_tx_end(struct cytv_private_tx **);
/* Only in a designated post-fork child, no outstanding tx: detach all library
 * FDs and return one non-CLOEXEC lease FD. Immediately exec the trusted receiver
 * or close it. Unrelated children MUST discard, not handoff. No extra duplicates
 * may survive; caller owns closing any FDs it duplicated outside this library. */
enum cytv_private_status cytv_lease_child_handoff(struct cytv_lease **, int *fd);
enum cytv_private_status cytv_lease_child_discard(struct cytv_lease **);

struct cytv_private_event {
    unsigned seq;
    size_t len;
    const unsigned char *raw;
};
struct cytv_journal_view {
    size_t observed_entries; /* At most 65; no partial records on failure. */
    size_t count;
    struct cytv_private_event records[CYTV_PRIVATE_MAX_EVENTS];
};
struct cytv_append_receipt {
    int durable;
    struct cytv_private_event event;
};
/* Returned views expire at the next journal operation or tx_end. Bridge must
 * copy verified raw bytes before any later asynchronous operation. Read validates
 * UTF-8/no NUL, bounds, pinned metadata, exact FD/path bytes and fresh fsync, NOT
 * JSON/schema/hash chain/Home authority. JS must perform those semantic checks.
 * 64 valid events may be read; they never permit another append. No rotation.
 * Failure returns no partial snapshot; missing entry 0 never initializes state. */
enum cytv_private_status cytv_journal_read(struct cytv_private_tx *, struct cytv_journal_view *);
/* Requires prior successful read in this tx and exact next seq. No caller hash:
 * receipt contains actual readback bytes; JS hashes them and compares its intent.
 * Failure invalidates cached next-seq; no overwrite/delete/retry. A full recovery
 * read is allowed after IO returns only while tx/lease remain active. Ending or
 * closing forbids recovery. An in-flight append completes its checks and retains
 * its FDs; async cancellation must drain and fence the result before completion. */
enum cytv_private_status cytv_journal_append(struct cytv_private_tx *, unsigned seq,
                                          const unsigned char *raw, size_t len,
                                          struct cytv_append_receipt *);

#ifdef CYTV_PRIVATE_TEST_BUILD
enum cytv_private_test_point {
    CYTV_PRIVATE_TEST_LEASE_CHECK,
    CYTV_PRIVATE_TEST_TX_ACTIVE,
    CYTV_PRIVATE_TEST_READ_ENTRY,
    CYTV_PRIVATE_TEST_READ_BEFORE_OPEN,
    CYTV_PRIVATE_TEST_READ_OPEN,
    CYTV_PRIVATE_TEST_READ_FILE_SYNC,
    CYTV_PRIVATE_TEST_READ_DIR_SYNC,
    CYTV_PRIVATE_TEST_READ_VERIFIED,
    CYTV_PRIVATE_TEST_APPEND_CREATED,
    CYTV_PRIVATE_TEST_APPEND_WRITTEN,
    CYTV_PRIVATE_TEST_APPEND_FILE_SYNC,
    CYTV_PRIVATE_TEST_APPEND_FILE_SYNCED,
    CYTV_PRIVATE_TEST_APPEND_DIR_SYNC,
    CYTV_PRIVATE_TEST_APPEND_DIR_SYNCED,
    CYTV_PRIVATE_TEST_APPEND_VERIFIED
};
int cytv_private_test_hook(enum cytv_private_test_point, int file_fd);
#endif
#endif
