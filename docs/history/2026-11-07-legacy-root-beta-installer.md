# Legacy Root Beta installer host verification, 2026-11-07

Scope: the maintainer-approved implementation for #383. This is source/build
validation on macOS ARM64 with Python 3.14.2 and Node 23.11.0, plus exact Node
0.12.2. No TV was accessed, installed, modified or tested. The model/firmware in
the issue is reporter evidence, not a device used for this run. Remote, native
ABI, actual Luna registration, Home controls, sound, standby, cold boot, OTA and
rollback on that TV remain untested. No public release or acceptance build is
selected by this record.

## Resulting behavior

- An identified older Node that fails ordinary Root admission offers No-root
  through existing root SSH. Exactly 0.12.2 also offers an explicitly confirmed
  Root Beta when its separate payload is embedded. Cancel is the default;
  `--yes` does not opt into Beta. Unknown Node output does not authorize a switch.
- Saved profiles retain product edition separately from root SSH and the Beta
  variant. Root/Beta share operation identity. Pending work in either edition
  or retained Root device state prevents switching. Root SSH keeps its pinned
  host identity and authentication; Developer Mode is not installed over root.
- Beta compiles the complete Root/recovery/coordinator/updater closure before
  hashing. Both graphics variants are embedded. The selected payload also
  supplies maintenance and cancellation support. Normal Root and the old host
  prototype retain Node 8+ admission; Beta device code admits only exact 0.12.2.
- Ordinary Beta OTA check/install is refused in both trusted Python handlers
  before offer or transaction work. Existing recovery workers, rollback,
  reconciliation, restoration and status are retained.
- Feedback remains a voluntary local report and manual issue-form submission.
  Diagnostics allowlist the variant, connection mode and measured Node version.
  No report, raw logs, credentials or device data were posted by this task.

## Failures found and corrected

1. Exact Node 0.12.2 rejects `--require` with exit 9. Beta retains the vendor
   bootstrap as its main script and loads diagnostics on entry into project
   service code. This loses coverage of failures before that entry; it does not
   replace or rewrite firmware modules.
2. Passive original-operation reads used `Buffer.alloc`, outside the compiled
   graph. A real exact-0.12 fixture returned `unsafe` before the correction and
   `read` afterward, while foreign ownership remains refused. Allocated bytes
   are fully filled before use.
3. Root-created No-root pairing configuration would otherwise retain root's
   group. Root-only observer uploads assign and verify the checked Helper state
   directory's UID/GID before publication. The process fixture checks both
   ownership assignments; it does not emulate actual TV sandbox acceptance.
4. Expected retained-state/module refusals initially exited the shell nonzero.
   Fixed markers now preserve their specific guidance separately from failed
   SSH transport. Direct No-root/root-SSH setup repeats the retained-state check.
5. Frontends now replace old prerequisite rows when edition changes, preserve
   the selected connection for maintenance and avoid Developer Mode guidance
   for the root SSH fallback. Android exposes the Beta identity in its target.

The original Developer Mode observer program was compared against the parent
revision and remains byte-identical, preserving its authenticated capsules.
Root SSH has a separate program, namespace, private sender and protected package
staging. A Root-owned state is not interpreted as consent to remove Root.

## Executed verification

- `npm ci --no-audit --no-fund` and `npm run prepare`; initial sandbox denial of
  hook configuration was resolved through the normal approved Git write.
- `.venv-cytv/bin/python scripts/build-cytv.py --payload-only`: complete normal
  and Beta payload built, with both graphics variants. Outer/inner payload
  hashes and selected maintenance payload verified.
- Exact `NODE012=... tests/root-node-compat.py --beta`: all 28 generated scripts,
  signatures, dispatch, receiver authorization, strict loopback TLS/hostname,
  redirects/bounds/failures and five Python bindings passed on Node 0.12.2 and
  current Node. Firmware services/native boundaries remain substituted. The
  sandbox initially refused loopback listening; the approved host run passed.
- Installer suite: **1050 tests passed, 2 skipped**; subsequent focused checks
  cover the final GUI row reset, direct root-SSH retained-state refusal and
  ordering of the selected-profile event.
- Root suite within `scripts/test.sh tv-runtime`: **1295 tests passed, 3 skipped**.
  System update tests: **132 passed**. The running shell later exited 127 at
  its final comparison because this task had inserted the Beta harness command
  into the script while it was executing. The script's syntax, remaining JS
  syntax checks and exact final file comparison were then run separately and
  passed; all preceding test-unit results above remain applicable. The newly
  inserted Beta harness also passed separately on exact Node 0.12.2.
- Android Python bridge/release checks: **44 tests passed**. Browser checks
  passed for default-cancel, retained No-root/root-SSH maintenance selection,
  Beta identity, existing progress/error rows and narrow-screen layout.
- No-root CLI fallback ran from ordinary Root refusal through Home/Helper
  package requests using one simulated SSH connection. A separate real detached
  Node/process/filesystem fixture completed root-SSH install and removal while
  retaining the original operation receipts.
- All 12 installer translations and 13 localized guides were checked. Formatting
  and `git diff --check` passed. Independent code review found no remaining
  P1/P2 issues after the corrections above.

An early installer run loaded the old translation catalog while translations
were being completed and failed only the new-message checks. The fresh complete
run above passed. Expected negative fixtures print vendor-busy tracebacks and
argument-parser errors; these do not represent failing tests.

## Installer choice clarity follow-up

The desktop alternative-edition prompt now uses visible cards with separate
Install No-root, Try Root Beta and Cancel actions. The headings immediately
identify No-root's reduced functionality and Root Beta's insufficient TV testing.
Descriptions explain the missing system Home routing/Root-only controls and
Beta's unavailable automatic updates. The second Beta confirmation also names
the action explicitly; cancellation remains the default. Shared copy and all
13 localized guides reflect these limitations.

Focused GUI, desktop bridge, CLI, runtime offer and translation checks passed
**113 tests**; Android checks passed **44 tests**. Layout checks cover all 13
languages at 900 by 680, including complete wrapped text, non-overlapping cards,
reachable actions and scrolling. Actual offscreen Qt screenshots were inspected;
no TV was contacted. Independent follow-up review found no remaining P1/P2 issues.

## Remaining release work

The implementation is not physical acceptance or a published compatibility fix.
Before publication, use an owner-authorized session with exact signed artifacts
to verify native bootstrap/registration, recovery before activation, actual
Home/emergency/input, sound, standby, cold boot and removal. Normal OTA stays
disabled for Beta. Keep #383 open; no result from another device or host fixture
can establish compatibility for its reporter.
