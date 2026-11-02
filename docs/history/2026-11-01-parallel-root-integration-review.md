# Parallel Root fixes — integration review, 2026-11-01

PR #221 (`059183338b06e3e225b3504c7a82c445a0713b0f`) and PR #222
(`66cfe2ddaf4f35514ab2f9a65981f83b8cb652d9`) were independently reviewed before
integration into unfrozen candidate #210. Both have successful final selected
CI. #222 merged as `d33dba7e81ff040a57562b55a41f97095393e29f`; #221 merged as
`5114236679603cdac83f811ac086ab14adb09708`.

## Review decisions

No blocking correctness, privacy or admission finding remains. The #221 refresh
resolved history-index and diagnostics-test conflicts while retaining every
existing cache privacy regression and the new Root-boundary allowlist regression.
Both sides were independently compared after resolution.

#221 exports only fixed action/boundary categories, adds no command or retry,
and preserves original pending/trust bytes. The passive reader does not execute
log text or establish recovery-record binding. Existing auth, third-party Home
and owner-consent refusals stay explicit. Exact-source handoffs retain their
original code/source pins; later Root source changes do not replace them.

#222 rejects stale Settings responses and requires an explicit later Enable.
Read-only Check status uses existing strings in all twelve locales. Retained
rollback health is admitted only for the original fully committed untouched
candidate, exact writer/cache and full installed payload; routing is restored
before the rollback anchor changes authority. Off/emergency cancellation stays
authoritative. The legacy selector fixture is hash-verified and isolated.

## Combined verification

The combined tree `64a1fe85` included current candidate `c54dbd7d`, refreshed
#221 and final #222. Actual merged product/test inputs match that tree exactly;
only later documentation and release inventory differed at reconciliation.

Local checks passed with installed npm and installer/Qt dependencies:

- Diagnostics 12, Root inspection/recovery 12, shared/cross-client Root 11,
  passive reader 5, actual Qt desktop recovery 12, historical System rollback
  recovery 39, package identity 16 and update Home resume 33: **140 Python tests**.
- Root Settings module harness and actual launcher/Settings/exit Chrome harness:
  emergency resume, relaunch, delayed status, explicit Enable and Off passed.
  The browser harness used its required temporary local HTTP preview server.
- Independent review additionally passed seven immutable-supervisor rollback
  anchor cases and confirmed the identity/intent guards. Reviewer environments
  without Qt or sandbox loopback do not supply extra GUI/browser acceptance;
  the coordinator's installed-Qt/browser checks above do.
- #221 final CI: [41274819958](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41274819958).
- #222 final CI: [41274697228](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41274697228).

The earlier GUI expectation depended on clearing unfinished removal journals.
#218 deliberately preserves them; the corrected test now requires an explicit
recovery offer, identical retained receipt and no upload/install/remove calls.
The final combined GUI run passed; this is no longer an outstanding test failure.

## Remaining scope and release gates

No TV was contacted or modified. These are source/host/browser checks, not
signed-package acceptance. Forward #202 cancellation and standby #171 remain
unresolved; #206 source fix awaits normal verified publication and exact-package
acceptance. Original #101/#133/#161/#216/#200 recovery remains unresolved and open.
No completed recovery or firmware compatibility is inferred from diagnostics.

Rebuild affected Root app/support, Root Updater, System supervisor/infrastructure
and embedding desktop/Android installers at freeze. Shared `package_identity.py`
and `runtime/update_guard.py` change private copied bytes; review Root,
infrastructure, updater and System versions/pins together. Existing System source
baseline is 1.1.2. Do not reuse old artifact hashes, receipts or acceptance for
new bytes. Helper source is unchanged. No version, candidate build or acceptance
pin was selected by this integration.

#221 maintainer documentation does not change ordinary setup/controls or any of
the twelve localized guide boundaries. #222's candidate control guidance still
has the final documentation reconciliation recorded in candidate #210. Preserve
published workaround/history evidence until normal release reconciliation.

Exact finalized packages still need affected controls/emergency, sound,
standby/cold boot, update and retained rollback observations in an agreed owner
session. Publication and issue shipping notices remain the normal release task.
