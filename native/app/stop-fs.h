#ifndef CYTV_STOP_FS_H
#define CYTV_STOP_FS_H

#include <stddef.h>
#include <sys/types.h>

#define CYTV_STOP_MAX_RECORDS 16u
#define CYTV_STOP_MAX_PRODUCERS 8u
#define CYTV_STOP_NONCE_LENGTH 32u
#define CYTV_STOP_RECORD_CAP 256u
#define CYTV_STOP_BINDING_VERSION 1u

/* Trusted caller configuration, never populated from the inode being admitted,
 * a shared record, SAM parameters or an untrusted runtime request. No discovery,
 * credential, private-journal or authorization operation is provided here.
 * UID 0 and set-ID callers are rejected; this adapter is for NoRoot actors. */
struct cytv_stop_binding {
    unsigned version;
    dev_t directory_dev;
    ino_t directory_ino;
    uid_t owner;
    gid_t group;
    size_t producer_count;
    uid_t producers[CYTV_STOP_MAX_PRODUCERS];
};

enum cytv_stop_status {
    CYTV_STOP_OK = 0,
    CYTV_STOP_FULL,
    CYTV_STOP_OVERFLOW,
    CYTV_STOP_UNKNOWN
};

struct cytv_stop_snapshot {
    enum cytv_stop_status status;
    size_t observed_entries; /* At most 17; overflow witness, not a full census. */
    size_t count;            /* Zero on UNKNOWN/OVERFLOW; no partial snapshot. */
    char nonces[CYTV_STOP_MAX_RECORDS][CYTV_STOP_NONCE_LENGTH + 1u];
};

struct cytv_stop_publication {
    enum cytv_stop_status precheck_status; /* Earlier observation only. */
    enum cytv_stop_status channel_status;  /* Always UNKNOWN after publication. */
    int durable_published;
    int private_adopted;       /* Always 0: private journal is not implemented. */
    int physical_stop_verified; /* Always 0: no input/relay operation. */
};

/* May repair ONLY the pinned directory owned by the actual unprivileged actor;
 * does not repair records. OK with records is not permission to start input. */
enum cytv_stop_status cytv_stop_scan(const struct cytv_stop_binding *binding,
                                   struct cytv_stop_snapshot *snapshot);

/* No mutex, directory repair, overwrite, deletion or post-publication census.
 * nonce is exactly 32 lowercase hexadecimal bytes followed by NUL. The caller
 * supplies a fresh random nonce; it is correlation, never authentication.
 * Successful return confirms only this record's verified publication with file
 * and directory fsync. Persistence depends on the actual backing filesystem.
 * Concurrent publishers may exceed 16; the next scan then returns OVERFLOW.
 * No guarantee covers deletion/corruption after the final observation, or an
 * unobserved record deleted before a scan. This is not an atomic snapshot or a
 * hard filesystem quota; the caller must block on UNKNOWN/FULL/OVERFLOW. */
enum cytv_stop_status cytv_stop_publish(const struct cytv_stop_binding *binding,
                                      const char nonce[CYTV_STOP_NONCE_LENGTH + 1u],
                                      struct cytv_stop_publication *publication);

#ifdef CYTV_STOP_TEST_BUILD
/* Fault injection exists only in an explicitly compiled HOST test binary. */
enum cytv_stop_test_point {
    CYTV_STOP_TEST_DIR_OPEN,
    CYTV_STOP_TEST_LIST_ENTRY,
    CYTV_STOP_TEST_BEFORE_RECORD_OPEN,
    CYTV_STOP_TEST_RECORD_OPEN,
    CYTV_STOP_TEST_RECORD_READ,
    CYTV_STOP_TEST_PRECHECK,
    CYTV_STOP_TEST_CREATED,
    CYTV_STOP_TEST_WRITTEN,
    CYTV_STOP_TEST_BEFORE_FILE_SYNC,
    CYTV_STOP_TEST_FILE_SYNCED,
    CYTV_STOP_TEST_BEFORE_DIR_SYNC,
    CYTV_STOP_TEST_DIR_SYNCED
};
int cytv_stop_test_hook(enum cytv_stop_test_point point, int file_fd, int directory_fd);
#endif
#endif
