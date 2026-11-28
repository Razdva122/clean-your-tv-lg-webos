# Issue 152: first cleanup pass after restart — 2026-11-28

Base: `1e7e7d1a0c2c58e9c09444af60822c13dee8d0ee` (`release/next`).
Report: [owner's two completed remove/reinstall cycles](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152#issuecomment-7237304724).
No TV connection or mutation, extra reporter probe or release selection.

## Cause and evidence

The cytv 0.25.0 reports on Windows AMD64 show the same result twice: after the
changed kernel was recognized, package removal and empty Helper/service directory
retention proceeded, but final readback failed with `allow_opaque=false` and
pre-package `terminal_cleanup/all_targets_terminal/project_catalog_absent=false`.
There were no observed project processes, process enumeration succeeded, and an
unrelated opaque interpreter kept `idle=false`. Retrying then completed with the
same changed-kernel proof and all four eligibility flags true. Pending was cleared.
The physical Home/relay and icon problems are separate, unverified by this fix.

The exception was computed only before the package loop. A resumed attempt that
obtained both Helper/Home terminals still used its original catalog and receipt
eligibility at final readback. Starting another attempt refreshed those inputs.
The local source fixture reproduced the same line-1663 refusal after its first
positively observed restart; the root-owned 0775 Linux fixture reproduced it too.
These were failures with the original host implementation, not fabricated cleanup
responses.

## Correction

Share the existing terminal eligibility predicate and evaluate submitted state
from the current mutable removal receipts. After all package requests finish,
read the catalog again and recompute terminal cleanup eligibility, its scoped
changed-kernel/opaque allowance and the diagnostic eligibility fields. Subsequent
inventory/SAM/controls/process verification still executes in the same attempt.

The rule still requires the observed kernel change and original process-idle
restart scope. Unsettled older work/configuration, failed/submitted package
requests, surviving catalog entries, visible project processes and missing process
observation remain blocking. The delegated-runtime-before-sweep guard is unchanged.
No new persistent field, endpoint, dependency, permission, UI control or TV JS.
The receipt already has the vendor terminals before the extra catalog read.

## Offline verification

- New regression failed against the original source after both fresh terminals,
  at final readback with cleanup-check-failed, then passed with this correction.
- The new exact ownership case performs two install/remove cycles. It creates
  resident installer history and unrelated opaque Node before package requests,
  verifies the first attempt requests a restart without package removals, then
  verifies the first postboot attempt obtains its own terminals and completes.
  No second cleanup invocation is used to make completion succeed.
- The existing network-disabled Linux fixture uses SDK UID5755/GID5000/groups
  44/505/509/777, root-owned 0775 containers, Helper state5999:5000/0775 and service
  slots0:0/0775 followed by5999:5000/0775 after fresh install. The new case was RED
  with original Python and GREEN with candidate Python. Production Node cleanup
  and boot-proof programs execute. Vendor mutation, intermediate install receipt,
  process entries and boot-ID transitions remain modeled; native Node22 is used.
- Negative source cases cover a surviving current catalog entry, a visible Home
  service process and cleared volatile marker with unchanged kernel; none becomes
  a verified removal. The unchanged boot proof later completes after an actual
  simulated kernel change. Independent read-only review found no actionable defect.

All six Linux ownership cases passed. `npm ci --offline` and diff checks passed.
`npm run format:check` reports pre-existing formatting failures in unchanged
`launcher/catalogs.js`, `launcher/update-panel.js` and
`root-edition/ui/root-updates.js`; their working bytes match the source base.
No unrelated JavaScript formatting was bundled into this Python-only correction.
The broader affected suite and final command totals are recorded in the PR. Prior
EF950V firmware investigation is reused; this is a host-only snapshot correction,
not a new stock ARM/QEMU firmware or physical TV acceptance run. Home-button,
postboot Home, icons, sound, standby, OTA and rollback are not established here.
