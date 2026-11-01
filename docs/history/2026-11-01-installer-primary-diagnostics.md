# Installer primary failures and diagnostic context — 2026-11-01

## Delivered source behavior

First stage of the maintainer-requested installer improvements: preserve the
initiating error and provide usable, filtered diagnostic context across desktop,
console and Android. This does not implement the later recovery wizard,
post-install acceptance flow, compatibility gate or connection-help stages.

New host receipts have a reserved private diagnostic correlation ID. Only their
creating invocation records the first failure; subsequent Status/Doctor reports
retain it separately from their own errors. Receipt snapshots are taken under
the existing TV lock. Legacy/unobserved causes remain explicitly not recorded;
new operations and TVs cannot inherit that association. Pre-receipt failures are
separate previous-attempt evidence, cleared after successful setup. Report/history
write failures do not alter device-work results or recovery journals.

Doctor now exports the filtered result of its existing status call and known
check outcomes. Setup/status/restore also offer successful-result reports. Reports
include fixed reason codes, safe known TV metadata and observed project versions.
A best-effort existing system-property read requests only model, firmware and SDK
after trusted SSH sign-in. Its five-second reply timeout retains the normal SSH
setup deadlines. No control pairing, mutation or log collection is added.

New Root coordinator code retains only the first fixed worker exception category
and bounded numeric subprocess status/errno. Those fields survive status and
continuation failures; raw command/output/message remains private. A private-log
write failure can no longer replace the original exception or prevent the existing
recovery-required record. The host revalidates returned failure categories without
repeating deployment or reading worker logs.

[Field, privacy and persistence contract](../development/INSTALLER-DIAGNOSTICS.md).
No diagnostic field grants recovery, activation or replay authority. Existing
request records gain filtered fields; no new TV state file, endpoint or permission
is introduced. Host diagnostic sidecars and the reserved correlation field are
new private persistent metadata. Existing operation receipts and handoff pins are
not rewritten to manufacture evidence. All twelve installer guides describe the
candidate-only report behavior; the Czech TV-only guide's installer scope is unchanged.

## Verification

- `npm ci` completed.
- Initiating-error retention/Doctor-result omission, address-shaped metadata,
  preserved safe TV/status evidence and Root worker-category regressions failed
  before their changes and passed afterward.
- 21 host context tests pass: cross-invocation primary/secondary errors, actual
  CLI install -> later status failure, new operation/TV isolation, legacy and
  corrupt/symlink evidence, reserved identity/checkpoints, disk failures,
  successful-export failure, metadata timeout and hostile nested data.
- 13 existing report tests and 5 receipt tests passed; Android exclusive-creation
  and byte-preservation assertions remain, with UUID-format validation added.
- `scripts/test.sh installer android setup` passed: 586 installer tests (2 platform
  skips), 23 Android, 220 setup cases and Homebrew payload/runtime/bridge/browser/
  continuation checks. Packaging includes the new shared Python module.
- `scripts/test.sh tv` passed: 968 Root and 132 System tests, UI/native input,
  watchdog/emergency, current-Node generated closure/HTTPS/Python binding and web
  compatibility checks. Exact legacy Node runtimes were not selected locally;
  no new legacy-runtime evidence is claimed.
- After that broad run, the reproduced private-log failure received its own
  guard and all 9 CoordinatorTests passed; final CI covers this final source.
- Independent focused reviews approved the final implementation. Two findings
  (IP-shaped model export and dropped primary TV/status evidence) were fixed with
  regressions. Final `git diff --check` passed.

Host/model tests only: no TV connection or new installation/recovery result.
Qt emitted platform/font capability warnings; neither those fixtures nor successful
packages establish physical rendering, Home, Back, emergency control, sound,
standby, cold boot, OTA or rollback acceptance.

## Packaging and release boundary

The candidate remains unfrozen, with no version/build/physical acceptance selected.
Rebuild desktop/console and Android installers with the shared module. The changed
Root coordinator bytes also require coherent Root/updater/infrastructure packaging
and component-version review at freeze; do not reuse equal-version published
packages or old candidate acceptance. Helper/native relay sources are unchanged.
No public release, signing, new hardware compatibility or recovery fix is claimed.
Original #229 and #230 remain open for their existing requested device evidence.
