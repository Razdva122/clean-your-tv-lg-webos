# Automatic Python runtime for Root Edition

[Documentation](README.md) · [Installation](INSTALL.md) · [Space and recovery](RECOVERY.md#private-python-and-low-var-space)

The published computer/Android installer can prepare the runtime when needed.

Root Edition needs Python 3.9 or newer on the TV, including the modules and
filesystem/process operations used by installation and recovery. The installer
keeps a suitable existing interpreter. A working system installation does not
download another Python, and ordinary desktop/Android installer packages do not
contain the ARM runtime archive.

If Root setup finds no suitable Python, it can download a separate, pinned ARMv7
runtime on the computer or Android device and transfer it through the existing
trusted SSH connection. The TV does not need Internet access for this step. The
download is about 26.3 MB. The normalized distribution materializes internal
archive links as independent regular files: about 119.3 MB installed and 51.5 MB
compressed for SSH transfer in the inspected artifact. Initial staging requires
**320 MiB free** on the TV; the installer checks this before provisioning.
Actual runtime compatibility is tested before
Root activation, not inferred from a TV model name.

**Setup diagnostics:** cytv distinguishes ABI, directory safety and space
failures and shows free/required MiB. Low-space diagnostics may identify large
WAM Session Storage without inspecting app contents. See [low /var space and
recovery](RECOVERY.md#private-python-and-low-var-space) before clearing state.

## Scope and compatibility

The first managed target is CPython 3.13.17, python-build-standalone 20261021,
`armv7-unknown-linux-gnueabi-install_only_stripped`. Its source artifact is pinned
by URL, byte size and SHA-256 in installer source. There is no remotely mutable
`latest` manifest or arbitrary download URL. The installer verifies the archive
before processing or executing it; a corrupt download/cache is never trusted.

The binary depends on a compatible ARM EABI Linux loader and system libraries.
`armv7l` alone does not prove compatibility. This does not replace system libc,
install Python 2 compatibility, or make every older webOS API compatible.
LG UK6540PTD / firmware 05.50.70 from issue #37 is the motivating case, not a
hardware-validated model for this feature. No boot, rollback or remote-input
acceptance is claimed for that model until the actual runtime has been tested on the TV.

## Installation and recovery

Managed Python lives in an immutable version slot under
`/var/lib/clean-your-tv-python/`, separate from system Python and TV application
packages. No `/usr/bin` symlink or global PATH change is made. Root and the
independent updaters persist private launchers and binding evidence so background
workers, boot recovery and subprocesses keep using their selected interpreter.
Installations without managed bindings retain their existing system-Python path.

Missing Python does not cause automatic downloads during status, doctor, restore
or removal. Only setup operations may provision a new runtime. Existing managed
bindings remain usable by maintenance commands without an Internet connection.
An incompatible target or failed smoke test stops setup with diagnostics before
Home is activated.

Runtime slots are retained when removing TV applications because recovery records
or another installed updater may still require them. Do not delete these files
while Root, an updater, rollback data or unfinished recovery references them.
An interrupted or foreign slot is not silently overwritten.

## Prepare the download for an offline setup

On a computer with Internet access, run:

```sh
cytv --prepare-python-runtime
```

This verifies and caches the optional archive without discovering or contacting a
TV. Use the same installer data directory for the subsequent setup. For a portable
cache, use `--data-dir /path/to/private-data` with both commands and transfer that
directory privately to the installation computer if necessary. Do not share a
data directory containing your normal SSH identities, pairing keys or profiles.
Prepare a fresh directory dedicated to the cache when moving it between devices.

<a id="unreleased-host-cache-failure-categories-200"></a>

### Host cache failure categories (#200)

In 1.6.0, diagnostic reports include `python_cache.reason` when private Python acquisition
fails: `network`, `tls`, `http`, `response-policy`, `size`, `sha256`, `deadline`,
`cache-access`, `cache-replace`, `cache-invalid` or `unknown`. These distinguish
connection/trust/HTTP failures, rejected response metadata, byte/hash/deadline
validation and local cache access or atomic publication. Reports include no URL,
private path, certificate contents or raw exception text. Existing translated
error messages and the offline preparation command remain unchanged.

CA verification, disabled proxies, redirect restrictions, size/deadline/SHA-256
checks and cache ownership rules remain enforced. An invalid existing archive is
not replaced automatically; failed downloads remove their temporary file when
possible. A failure category is diagnostic evidence, not permission to weaken TLS
or verification, reset a pending installation, or retry device recovery.

The old generic download error cannot identify the cause on a particular Mac;
success on a different host does not establish that cause either. The 1.6.0 change
adds host diagnostics only; Root recovery is outside that change.

**macOS trust context:** the download context additionally loads macOS's
system CA file. Published frozen Python builds can retain certificate paths from
their build machine that do not exist on another Mac, causing a `tls` failure
before archive validation. Certificate and hostname verification remain required;
no Python installation or global certificate/environment change is needed for the
corrected context. [Host reproduction and verification](history/2026-11-04-macos-python-download-trust.md)
cover the published CLI failure and a local corrected frozen probe. Final rebuilt
CLI/GUI acceptance and the reporter's original environment remain unverified;
the separate pending Root operation is unchanged.

## Development validation

Linux CI executes the pinned ARM32 interpreter under QEMU using
`python scripts/test-python-runtime.py`, in addition to offline unit tests. This
checks actual executable startup, native modules, locks, filesystem operations
and subprocess execution. It does not validate the TV's loader/libc, old kernel,
boot timing, webOS APIs or rollback; physical-TV feedback is still required.

## Provenance and licensing

Upstream: [python-build-standalone release 20261021](https://github.com/astral-sh/python-build-standalone/releases/tag/20261021).
Artifact SHA-256:
`4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea`.
The upstream license files accompany the optional runtime. Installing this
component adds a separately versioned dependency whose security updates require
a reviewed artifact-pin update and fresh validation.

## Candidate: offline runtime in CYTV Installer

**Unreleased on-TV Root path:** CYTV Installer embeds the authenticated normalized
runtime and its licenses, binding, inventory and provenance. The TV performs no
runtime download. Node.js 8+ verifies the fixed offline payload without needing
Python; only existing root with Homebrew exec can run it. The private ABI is
ARMv7 soft-float EABI5 Linux, including verified `armv8l` 32-bit userspace with a
compatible loader/libc. It does not support arbitrary ARM64 userspace.

Opening or checking status does not change the product, Home, runtime slots or
operation receipts. It may briefly stage verified code/data under a private
0700 execution directory, removed after the child exits. Missing Python requires an explicit
**Prepare runtime** action, followed by reinspection and final product review.
Suitable system Python 3.9+ or the verified private slot is reused. The free-space
threshold remains **335,544,320 bytes (320 MiB) after Installer installation**;
package-manager/TV staging capacity remains unmeasured. See the
[exact candidate artifact](development/HOMEBREW-INSTALL-ACCEPTANCE.md).

The slot, promotion lock, private staging and launch bindings remain independently
retained for recovery. Setup never changes global PATH or `/usr/bin`, activates
Home, or clears emergency off. Removing Installer or product apps does not grant
permission to delete referenced runtime slots. The host download/cache procedure
above continues to apply to ordinary cytv; it is distinct from the embedded
Homebrew payload.
