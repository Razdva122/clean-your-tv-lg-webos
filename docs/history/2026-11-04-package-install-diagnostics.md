# Package installation diagnostics and LG CLI comparison — 2026-11-04

## Scope

Maintainer-side offline investigation for [#307](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/307).
No TV contacted or changed. These are package/source observations, not an owner's
installation report, compatibility acceptance or recovery procedure. The original
installation failure remains unresolved.

## Published package and controlled comparison

Downloaded `com.local.nativehome_0.6.22_arm.ipk` from
[v1.7.1](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.7.1).
SHA-256 matches published `SHA256SUMS`:
`0e8477113fd8afc57b5f3bfc7271a3b7de99dcce2fb2516d7e386eff06ec00cf`.
The archive has 82 entries: 72 regular files and ten directories. Its service
subtree contains eleven regular files, including `package.json`, `services.json`
and `service.js`; package metadata declares that service.

Installed official npm `@webos-tools/cli@3.2.5` into an external temporary directory
with lifecycle scripts disabled. npm integrity:
`sha512-cKmIJ5WpmQjiwiv1CKcsvRyfT3FhxDt1eb/f5h+Yo1mHWx+qbS9+R4ikY6cF+Yp/ZNELbUD0SZiQCEx6VHQe+g==`.
After extracting the published package into an empty temporary directory,
repacked its application and service locally:

```sh
ares-package --no-minify "$EXTRACTED/usr/palm/applications/com.local.nativehome" \
  "$EXTRACTED/usr/palm/services/com.local.nativehome.service" --outdir "$OUTPUT"
```

`--no-minify` matters: the CLI's default run also minifies JavaScript. The
no-minify output has the same 72 file paths and identical application/service
file bytes. Only `packageinfo.json` serialization differs; parsed metadata is
identical. CLI output has 87 entries, adding five shared ancestors: `usr`,
`usr/palm`, `usr/palm/applications`, `usr/palm/packages`, `usr/palm/services`.

| Property | Published CYTV package | Local LG CLI output |
| --- | --- | --- |
| Shared ancestor entries | Omitted | Present |
| Service root mode | `0755` | `0777` |
| Application/service state modes | `0770`, explicit prisoner/jailer ownership | `0777`, host ownership |
| Control metadata | Package/version/architecture/maintainer/description | Also section/priority/installed size/package format/packager fields |

CLI output incorporates host ownership and is a comparison artifact only; it was
not installed, uploaded or selected for distribution. Do not copy its ownership
or broaden CYTV permissions as a speculative fix. The official
[packager reference](https://github.com/webos-tools/cli/blob/6d866e0fe06c1842e783ad10d551dbba8d39561e/lib/package.js#L1561-L1610)
shows recursive tar creation and directory mode adjustment;
[service staging](https://github.com/webos-tools/cli/blob/6d866e0fe06c1842e783ad10d551dbba8d39561e/lib/package.js#L1898-L1918)
creates service directories recursively. This v3.2.5 tag's `lib/package.js` was
verified byte-identical to the installed npm package's source.

macOS BSD tar extracted the original archive into an empty destination, creating
the missing parents and all eleven service files. This does not exercise the
retail webOS 3.9 installer. These differences remain candidates for device/vendor
investigation; none is an established cause. No packaging change or additional
owner installation is requested.

## Diagnostic loss and correction

LG OSE `appinstalld2` at
[`938ffd716c0c250bdb860100e9a41d3bd5b0b452`](https://github.com/webosose/appinstalld2/tree/938ffd716c0c250bdb860100e9a41d3bd5b0b452)
emits `install failed` / `remove failed` and `details.reason` in
[`Task.cpp`](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/installer/Task.cpp#L364-L401).
CYTV already rejects those failure replies, but its diagnostic allowlists
discarded the states. No assertion is made that a particular discarded state
or reason was present in #307's original reply.

The change retains those two states using existing lowercase state normalization
and optionally preserves only these exact strings from
[`IpkInstallStep.cpp`](https://github.com/webosose/appinstalld2/blob/938ffd716c0c250bdb860100e9a41d3bd5b0b452/src/step/IpkInstallStep.cpp#L122-L149):

`FAILED_INTERNAL_ERROR`, `FAILED_CREATE_TMP`, `FAILED_NOT_ENOUGH_TEMP_SPACE`,
`FAILED_NOT_ENOUGH_INSTALL_SPACE`, `FAILED_PACKAGEFILE_NOT_FOUND`,
`FAILED_PACKAGEFILE_CORRUPT`, `FAILED_VERIFY`, `FAILED_IPKG_INSTALL`, `FAILED_INSTALL`.

Unknown text is not exported; categories are not inferred from numeric codes.
OSE is not a retail firmware contract. Existing error decisions, status calls,
recovery guards, journal retention, package permissions and payload bytes remain
unchanged. The [#201 terminal-readback limitation](../development/NO-ROOT-TERMINAL-HANDOFF.md)
remains unresolved. An improved report cannot authorize clearing pending.

## Verification and limits

Source-shaped regression tests failed before implementation because states
became `unknown` and reasons were absent. They cover current report export, fixed
reason categories, hostile/structured values, a later recovery failure, history
retention and byte-identical pending journals. No physical installation, service
registration, Home routing, sound, standby, cold boot, OTA or rollback acceptance
is claimed. No versions, selected candidate build or release scope were changed.

Verified locally on macOS after `npm ci` and installing the declared Python
requirements into an isolated temporary environment:

- Focused diagnostic/history suite: 38 tests passed.
- `scripts/test.sh installer`: Homebrew/runtime/UI checks and 754 cytv tests
  passed (72 optional checks skipped).
- Setup suite: 234 tests passed. Android suite: 35 tests passed.
- Local Markdown targets and `git diff --check` passed.
- Independent code review found no actionable defects.

Initial broad runs could not launch Chrome in the sandbox and lacked Python
runtime dependencies; these environment issues were resolved before the verified
runs above. Full frozen-candidate and physical-TV checks were not performed.
This PR is queued after frozen candidate #281, not added to its scope.
