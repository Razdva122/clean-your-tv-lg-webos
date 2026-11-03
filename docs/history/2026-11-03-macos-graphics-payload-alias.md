# macOS graphics payload alias — 2026-11-03

Related issues: [#270](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/270),
[#271](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/271),
[#273](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/273).
This is host-only packaging evidence, not another user's installation report.

## Reproduction and cause

The published v1.6.0 `cytv-macos-arm64.zip` (cytv 0.7.0) has SHA-256
`b07f2cb8ed953eac69a70af9939fcb165e96a07851836d35de824d6bbb5b5934`,
matching the release's `SHA256SUMS`. The Intel archive `cytv-macos-x64.zip`
(SHA-256 `a5fa17fb28489ccda8cf77fa75e817a7f1969cd7aa70f50c0728f5ef1f576134`)
also matches the published checksum and has the same alias. Regular payload
files are under
`cytv.app/Contents/Resources/payload`; PyInstaller creates the directory alias
`Contents/Frameworks/payload -> ../Resources/payload`. The frozen interpreter's
`sys._MEIPASS` uses `Contents/Frameworks`.

Before the fix, `package.verify_payload` accepted the same published bytes through
both locations. `Installer.select_graphics` accepted the direct Resources path
but rejected the Frameworks alias with the reported embedded-graphics error.
`PurePosixPath(name).parents` includes `.`. Testing `payload / '.'` for symlinks
therefore rejected the packaging root itself, even for a valid, directly stored
`launcher.ipk`. This occurs before package upload or installation receipts.
The payload is complete; archive presence and correct SHA-256 do not avoid this
path-validation defect.

## Correction and boundaries

Exclude only `.` from the member-parent symlink check. The caller-supplied payload
root may be an alias, consistently with the existing payload verifier. Package
files and directories *inside* the root must still be direct; do not resolve all
paths first, which would hide unsafe member links. Manifest hashes, Root bundle
hashes, application ID, version, resolution and explicit UHD capability checks
remain enforced. All graphics variants and both editions use this shared check.

No version, release inventory, selected build, TV state, permission, endpoint or
recovery protocol is changed. New embedding installers must be rebuilt through
the release coordinator. Existing published archives are not modified.

## Verification

Host: macOS 15.6.1, arm64; isolated Python 3.11.12 environment with repository-pinned
build dependencies; PyInstaller 6.22.3. Baseline operation tests initially lacked
`fonttools` in the system Python; installing the declared build dependencies in
the isolated environment resolved that prerequisite without product changes.

- The new macOS-layout regression failed before the correction for both editions
  with the expected embedded-graphics error.
- All 78 operation tests passed after the correction. New negative cases use a
  payload alias and reject an individually linked IPK and a linked Root bundle
  directory before upload or a durable operation receipt.
- Published payload bytes passed selection for No-root/Root and UHD true/false
  through both Resources and Frameworks locations for both official macOS archives:
  sixteen combinations. The Intel payload also reproduced the old failure through
  the alias and passed through the direct path before the correction.
- An offline PyInstaller windowed `.app` probe imported the fixed implementation
  and embedded the unchanged published payload. It asserted that it was frozen
  and its payload root was a symlink; all four edition/capability combinations
  passed with the expected 1920x1080 or 1280x720 resolution. This is a packaging
  probe, not a rebuilt release installer or a physical installation.
- Independent read-only code review found no issues and independently passed all
  78 operation tests.

`PATH="$PWD/.venv/bin:$PATH" bash scripts/test.sh installer setup android`
passed: 222 setup, 670 cytv (two skips), 27 Android and 17 Homebrew Python tests,
plus the selected Homebrew JavaScript checks. The command exited 0.
Setup/control instructions and all twelve localized user guides were considered;
the correction restores existing validation behavior without changing their flow,
so no setup/control translation changes are needed.

No TV was contacted. TV model, firmware/webOS and remote are not applicable to
these host checks. Actual installation, Home routing, sound, emergency controls,
standby, cold boot, OTA and rollback on reporter devices remain untested. Final
rebuilt-installer checks, release acceptance, verified public delivery and reporter
confirmation remain separate; native Intel macOS, Windows, Linux and Android
installers were not executed in this task. Source tests do not establish device
compatibility.
