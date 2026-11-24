# Root staging on ramfs TVs

Root installation chooses staging from observed filesystem capabilities, without
model, firmware or webOS version allowlists. A confirmed Linux ramfs `/tmp`
cannot provide a usable disk-space estimate. The installer keeps vendor package
scratch there, but moves its large Root product, full native bundle, System
Updater and Beta startup migration uploads to internal disk. A USB drive is not
required or used for executable staging.

## Admission and budgets

`cytv/storage.py` checks measured filesystems, groups requirements sharing a
filesystem and budgets staging, expanded packages, retained support and rollback
copies with a 16 MiB reserve per filesystem. For Root on confirmed ramfs, it also
charges the internal disk staging copy and checks vendor scratch against current
RAM: the scratch estimate plus a 16 MiB reserve must fit `MemAvailable` from
`/proc/meminfo`, or `MemFree` when `MemAvailable` is absent. Unknown capacity and measured shortfalls stop installation
before package submission; a ramfs zero-block report is never treated as free
disk capacity. These estimates do not guarantee vendor peak memory use.

`cytv/root_staging.py` verifies a measurable internal `/var/lib` filesystem and
root-owned ancestors without group or other write access. Its fixed staging root
is `/var/lib/clean-your-tv-root-staging`, owned by root with mode `0700` on the
same filesystem as `/var/lib`. It refuses foreign, linked or unsafe directories
instead of adopting or repairing them. Each operation creates a new exclusive
`cytv-<kind>-<random>` directory with mode `0700`, after checking the exact upload
byte requirement and disk reserve. Nested upload directories use `umask 077`;
files are private `0600`, or `0700` for an executable guard.

## Control code and recovery lifetime

Small coordinator code and native recovery support deliberately remain under
`/tmp`: their volatile lifetime bounds control and recovery admission across
restarts. Ordinary coordinator and native recovery staging omit package archives.
This differs from staging the full native installation bundle. Existing paths
remain under `/tmp` when that filesystem is not confirmed ramfs.

Full removal stages its verified support bundle in a private `/tmp` directory.
On ramfs it checks current RAM against the exact upload size and reserve before
staging. Removal can then start when internal storage falls below the
installation staging reserve. Insufficient RAM stops the upload and preserves
the removal receipt.

The installer does not set `TMPDIR`, remount vendor filesystems or modify vendor
package-manager temporary paths. It neither enlarges ramfs nor redirects all
system temporary files to disk.

## Receipts and retirement

Before the first uploaded byte, host receipts record `support_upload` for product
and System Updater support, or `native_payload` for a full native installation.
A support upload is not a package submission or a confirmed installed product.
Lost responses, interrupted uploads and unresolved operations retain their
staging and recovery evidence.

After known terminal success, host retirement checks the exact prepared file
inventory and SHA-256 hashes before deletion. It verifies root ownership, private
modes, ordinary single-link files, directory safety and expected subdirectories;
unknown or changed contents stop retirement. Product installation, full native
installation, System Updater setup and Beta startup migration retire their
persistent source copies only after their respective success proofs. Device
cleanup and its final tail also recognize the fixed internal root while preserving
legacy `/tmp` support paths and their ownership and identity checks. There is no
broad temporary-directory sweep or permission to execute retained foreign code.

## Verification and hardware acceptance gaps

Host and isolated runtime tests cover storage admission, private directory
creation, interruption receipts, exact retirement and both staging roots. Offline
firmware inspection and execution of a stock utility can establish its reported
filesystem behavior; neither is a complete TV installation or compatibility test.
Keep dated command results and firmware identities in [historical records](../history/README.md).

This change still requires acceptance on an authorized physical TV with confirmed
ramfs `/tmp`: ordinary installation and package readback, measured peak RAM and
disk behavior, interrupted upload and reconnect, successful source retirement,
full removal and rollback. Home routing, physical remote input, sound, standby,
cold boot and OTA remain separate device cases wherever affected; host or offline
success does not establish those outcomes. Do not infer support for every model
or firmware from a single device or from filesystem detection alone.

Exact inputs, reproduction and observed cases: [W17M offline evidence](../history/2026-11-23-issue410-root-ramfs-storage.md).
