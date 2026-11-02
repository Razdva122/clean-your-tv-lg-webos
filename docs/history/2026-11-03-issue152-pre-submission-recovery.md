# No-root pre-submission removal recovery — 2026-11-03

Source correction for #152; no TV contacted or changed and no new owner
installation result is published. Source base:
`f75bdcfc247dd84200de83ea0989d5d225aca1d7` (`release/next`). No release/component
version, candidate selection, package signing or public delivery is selected.

## Cause and change

The recovery offer and the subsequent uninstall each required the global
`appInstallService/status` monitor for every pending journal. A fresh uninstall
reserves `uninstall / pending` before restoring LG Home; a restore failure can
leave that journal even though no package request has been submitted. Requiring
the monitor on a resumed pre-submission journal therefore added a permission
requirement that the same fresh uninstall never had.

The shared gate now treats exactly that original No-root journal like a fresh
uninstall. It requires `uninstall / pending`, empty/absent removal entries and
only known pre-submission fields, rejecting `previous` and unexpected fields.
Published v1.6.0 writes `removing` before any `dev/remove`, then persists each
`submitted` receipt before sending. This ordering is the proof boundary; neither
an inventory snapshot nor the filtered diagnostic projection is that proof.
The UI and backend recheck the journal independently. A separate default-No
confirmation still precedes restoration/removal, terminal replies and current
package/file absence are required, and setup starts only as a separate action.

Unknown/submitted operations, interrupted install and inherited previous
journals keep the existing monitor/refusal behavior. No automatic journal
clearing or inferred completion is added. #201's missing original transaction
proof remains unresolved. The retail firmware's exact reason for monitor denial
is not established by this source change; no ACL, privilege or endpoint is added.
Root behavior, native Helper/relay bytes and emergency/stop/watchdog state are
unchanged. The synthetic original-terminal fixture now models a submitted remove
at `removing`, rather than incorrectly treating a pre-submission reservation as
a submitted operation.

## Verification

- `npm ci` and repository-pinned Python build/runtime dependencies in a temporary
  environment; verified font cache reused without product changes.
- Baseline: 85 operation/recovery tests passed after installing the missing host
  fontTools requirement. Initial dependency setup used a nonexistent filename;
  corrected to `cytv/build-requirements.txt` before final validation.
- New regressions failed on original production code at both status gates;
  the GUI likewise failed to reach removal confirmation after the denied monitor.
- 104 operation/recovery/desktop tests passed after the correction. Cases cover
  explicit removal, default-No decline with byte-identical journal, a denied
  global monitor, LG Home before removal, write-ahead per-package submission,
  terminal wait, final absence, and a separate successful fresh install.
- Negative cases retain previous install (including null previous), unexpected
  fields, malformed removal entries, non-pending stages and submitted requests.
  Existing denied/busy/timeout/unknown monitor and uncertain-terminal tests remain.
- Complete affected checks and independent review are recorded in the PR.

The English recovery/CLI/developer references and twelve localized installer
user guides distinguish this unreleased correction from published 1.6.0. Czech
is outside the complete installer-guide set and has no changed recovery flow.
No strings, options, dependencies, persistent state or network endpoints added.

## Device limits and delivery

No physical EF950V recovery, installation, registration, Home/Back/emergency,
sound, standby, cold boot, OTA or rollback is claimed. The owner must use a
matching rebuilt installer and the same original saved connection; eligibility
is decided from the full local journal, never reconstructed from the export.
A successful removal would permit separately starting setup, not establish
complete model compatibility. Actual device failures must retain their receipt;
no repeated mutation or manual journal deletion is authorized by this record.
