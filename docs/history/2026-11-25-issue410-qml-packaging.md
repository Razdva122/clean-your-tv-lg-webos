# Issue 410: QML asset incorrectly compiled for Node

The [public report after v1.28.0](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410#issuecomment-7143943729)
shows Root setup progressing beyond the previous ramfs gate and stopping before
package submission. This record contains technical facts from that report;
no TV was accessed during this investigation.

| Field | Observed result |
| --- | --- |
| TV | LG 60UJ6050-UA |
| Firmware / SDK / Node | 06.10.55 / 3.9.0 / 0.12.2 |
| Remote | Unknown; physical Home was not tested by this attempt |
| Edition / installer | Root Beta, cytv 0.24.2 console, Linux x86_64 / Python 3.12.16 |
| Existing No-root components | Home 1.20.5 / Helper 0.9.3; inventory observations |
| Operation | Install; host pending operation at `setup` |
| Expected | Pass runtime preparation, submit the Root package and verify installation |
| Actual | `TVCommandError`, driver exit 1, nested `ValueError` during embedded asset validation |
| Home, sound, standby, AC boot, OTA, rollback | Untested by the reported attempt |

## Reproduction and cause

The diagnostic points to released `deploy.py:303` calling
`c1_keyfilter.prepare()`, then `c1_keyfilter.py:670` calling the generic private
file reader and `c1_gate.py:50` rejecting the file. This occurs after private
runtime copying but before `home-backend.json`, the `c1-keyfilter` directory,
package submission or LS2 provisioning is created.

The shared legacy Node builder excluded `runtime/c1-home-filter.js` from its
Node transform, but did not exclude `runtime/embedded-home.js`. Consequently
it injected core-js, safe-buffer, Babel and a Node module/global wrapper into a
script loaded by the compositor's QML engine. The exact v1.28.0 source is
5,769 bytes; rebuilding it with the released compiler produces 285,303 bytes.
The existing private QML asset bound is 262,144 bytes. Replaying the released
secure reader against that output reproduces `Unsafe experimental backend file`.
Even lifting the size bound would leave Node-only code in the QML scope.

This failure depends on the selected script loader and build path, not a TV
model or firmware version. Ordinary Root already packages the raw asset; Beta
and the optional Node compatibility build share the faulty transform.

## Correction and verification scope

Both compositor scripts now retain their original bytes through the shared Node
builder. Actual Node service/boot scripts continue to receive their compatibility
runtime. Bundle inventories and hashes are regenerated normally; package paths,
backend formats, security bounds and Home/guardian behavior are unchanged.

The regression first failed for both shared compiler entry points. Another
regression built a real Beta bundle and reproduced failure through its actual
`prepare()` call, rather than validating only source text. With the correction,
the same bundle passes manifest verification and private file admission and
writes a schema4 descriptor. Factory compositor matching is modeled in this host
fixture; UID/mode/size checks execute through the real reader. Oversized and
writable QML files are still rejected. Both raw scripts are checked as ES5;
Node boot compatibility wrapping remains asserted.

The earlier [W17M firmware/QML findings](2026-11-20-embedded-home-adapter.md) and
[ramfs investigation](2026-11-23-issue410-root-ramfs-storage.md) retain their own
scope. This failure was reproduced entirely at the project build/admission
boundary using the exact published sources; another firmware download or TV
run is not needed to establish the packaging cause. No fresh QEMU or physical
Home result is claimed here.

## Retained setup recovery

The existing generic native restore correctly refuses a missing backend
selection when native runtime files are present. The reported failure leaves
exactly that incomplete state, so a fresh package alone cannot be installed
over it by clearing the host receipt.

The current verified removal coordinator now handles this one data-only case
before invoking native restore. It requires the original fenced deployment
record to be exactly `prepared` for the recorded package, a live cancellation
fence, no routing/inverse/descriptor/gate evidence, no Root package through both
API and fixed paths, no Root startup/LS2 registration and no original workers.
All retained support/runtime bytes must match the finite original manifest;
unknown, missing, linked or changed files remain a refusal. Manifest-only Beta
migration/recovery members are not mistaken for copied runtime files.

The old manifest bounds data removal; it is not executable authority. No old
Python, Node, QML or native file is run and no backend descriptor is invented.
Only the inapplicable runtime-restore child is skipped. Registration cleanup,
routes, package absence, private-tree retirement and final cleanup verification
continue through the existing gates. Ordinary profile Root, valid native
backends and unknown/submitted operations retain their previous recovery path.

The regression covers both actual Beta bundle contents with the old Node QML
transform and the exact direct native setup with no product request/submission.
The latter reaches verified cleanup without forcing a restart. A separate
failed coordinator fixture retains its restart requirement. Conflicting file,
routing, package, process and registration evidence preserves the payload and
prevents package removal. Late-phase cancellation remains unchanged.

Once a patched installer is available, the supported owner path is its existing
**Uninstall Clean Your TV** flow with the saved connection, following only the
recovery steps it requests. This removes project apps according to its existing
confirmation; it is not an in-place retry of the failed installation. Do not
recommend manual state deletion, removal of runtime guards or a fabricated
backend marker.

## Focused verification ledger

| Unit | Result |
| --- | --- |
| Original compiler regression | Failed for both Node compiler entry points before correction; passed after correction |
| Actual built Beta bundle admission | Failed at private QML admission before correction; passed with the original size/metadata guards afterward |
| C1/embedded bundle integration | 9 passed |
| Legacy Beta build suite | 7 cases, 3 optional exact-Node-runtime skips; the changed raw-asset/ES5 check passed separately after its final assertions |
| Pre-submission recovery | 6 passed, including real Beta inventory, direct no-request setup and conflicting-evidence subcases |
| Existing complete removal | 113 passed |
| Existing late-phase cancellation | 18 passed |
| Existing selected native restore/routing checks | 4 passed |
| Raw embedded adapter | 11 passed |
| Shared C1 filter | Passed |
| Independent packaging/recovery review | No remaining P1/P2 findings after the Beta manifest-only member correction |
| Whitespace | `git diff --check` passed |

Unchanged successful checks were reused. No candidate release build, package
signing, TV installation or Home/power acceptance is claimed by this ledger.

Complete installation, production LS2/guardian transport, visual Home,
physical remote input and device recovery remain target-TV acceptance gaps.
The implementation PR records focused test results and the recovery handling
for the already retained pre-submission state. The original issue remains open.
