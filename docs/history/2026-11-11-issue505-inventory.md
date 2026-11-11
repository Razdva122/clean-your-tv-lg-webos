# Issue 505: confirmed catalog reconciliation and live No-root icons

Related issue: [#505](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/505).
This is a focused implementation for a subsequent release, based on `60e6cac1`.
It does not change the frozen candidate inventory, versions, build pin or device
acceptance. No TV was contacted; no reporter diagnostics or installation result
is published here.

## Selected implementation and verification scope

1. Preserve the legacy merge behavior unless a bounded, validated full installed
   ID list confirms absence. No-root uses its existing paired SSAP `listApps`
   query even when launch points already include the tuner; Root derives IDs
   before the existing 200-app display limit. At most 300 unique nonempty bounded
   IDs are accepted. Every discovered app must be consistent with that list.
2. Remove confirmed absent catalog entries, ordered IDs and hidden IDs together;
   persist immediately without placing discoveries on Home. Roll back memory
   on storage failure. Rebuild Home when closing the picker.
3. Keep confirmed catalog state across ordinary restart, excluding immutable
   packaged stale entries. Preserve profile/rollback compatibility.
4. Resolve No-root image variants into local data URLs with exact TV host and
   fixed port confinement, no credentials or redirects, image signatures and
   bounded resources. Do not change pairing, permissions, Stop or Home routing.
5. Check model/transport/service boundaries, browser behavior, compiled legacy
   runtimes and shared UI source checks. Physical and final candidate acceptance
   are separate future release gates.

## Behavior and resource boundaries

The existing `tvhome.layout` version remains 1 with one optional local boolean,
`catalogConfirmed`. Legacy layouts keep the old merge until confirmed. The Root
validator accepts this boolean, but Root system capture strips it from exported
snapshots so published older validators accept the pruned layout. Confirmed
Root snapshots also replace the original packaged inventory with the pruned
catalog, preventing resurrection during offline restore. No-root's
existing opaque layout backup preserves it. A restored Root snapshot needs fresh
confirmation before excluding packaged seed data again. No new endpoint,
permission, pairing prompt, app launch or automatic placement is introduced.

No-root image fetching runs after discovery against the selected TV address,
using only HTTP(S) ports 80/443/3000/3001. Local TLS certificate verification is
relaxed only for this exact host, as for the existing paired TV transport.
There are at most four in-flight GETs, 128 KiB per image, 512 KiB embedded image
bytes and 2 MiB aggregate received bytes. Each GET has a one-second limit and
all work shares the original request deadline. Supplementary confirmation gets
at most one second or half of the remaining budget, preserving time for images
when firmware does not answer. Failed/unsupported images remain empty in the
fresh reply; the model retains existing usable icons. Raw inventories and URLs
are not added to diagnostics or public logs.

## Verification ledger

Existing baseline: the focused catalog, fallback and tuner command passed 11
host tests before edits. Existing release evidence cannot cover the new removal
authority, image fetching or persistent catalog flag; these are changed inputs.

- Regression-first: all seven initial focused tests failed before implementation
  for stale catalog retention, missing confirmation/persistence and absent live
  icon fetching. After implementation they passed; the final focused file has
  ten passing cases, including oversized/foreign/redirected images, aggregate
  cache limits, cancelled stalled requests, Root catalogs over 200 entries and
  silent optional confirmation with a successful image fetch.
- The combined model, service, Root budget/priority, tuner, layout/profile,
  controller, same-package bridge/jail and system profile command passed 119
  tests before the final review corrections. Affected corrections are checked
  separately below; unchanged device evidence is not rerun.
- Independent review found two issues: old Root validators reject the new layout
  field in transferred snapshots, and silent optional confirmation consumed all
  image time. Both were reproduced and corrected. The actual captured snapshot
  passes the original validator from `60e6cac1`, selected with
  `LEGACY_PROFILE_VALIDATOR`; the local flag remains unchanged. The end-to-end
  silent-query test confirms an image GET and embedded result with no deletion
  authority. Root capture/system restore, No-root bootstrap and catalog-string
  checks passed after these corrections.
- `tests/helper-compat.cjs` passed with current Node 23.11.0 and exact Node
  0.10.15, 0.10.25 and 0.12.2. The compiled runtime fixture now exercises real
  local HTTPS icon loading, the confirmed ID envelope, service response and
  existing watchdog/Stop regressions, not just parsing the added code.
- `PREVIEW_URL=<isolated local preview> node tests/apps/ui.cjs` passed. The real
  browser covers denied direct LS2 with same-package fallback, icon display,
  confirmed picker removal, Home rebuild, restart with stale packaged entries,
  explicit addition, existing partial/offline/Undo flows and Root icon refresh.
- The shared UI profile initially stopped at the new untranslated validation
  error string. Reusing the existing generic profile validation message fixed
  the affected catalog check without adding strings or weakening assertions.
  The final `bash scripts/test.sh ui` profile passed, including compiled web
  compatibility, theme/weather source checks and all Root UI checks. Subsequent
  Root snapshot-inventory correction reruns only affected profile and web
  compatibility checks; the prior unchanged UI groups remain reusable.
- `npm run format:check` and `git diff --check` passed. Independent review's
  offline-restore follow-up is covered by capture with a stale packaged app,
  original-validator validation and reconstruction from the portable snapshot.
  A further regression first failed on a legitimate iconless Root app; confirmed
  snapshots now embed the existing packaged Home icon as an inventory fallback
  while retaining the original empty icon in the saved layout. Capture, portable
  reconstruction and original-validator checks pass with that entry preserved.

## Documentation and delivery

`docs/APP-MANAGEMENT.md` describes the unpublished behavior and its limitations.
The practical localized guides in `docs/i18n/` retain their existing setup and
controls: this fix adds no installation step or control, and adds no translated
release banner. Existing user strings are reused. Release versions, inventory,
packaged artifacts and the current candidate ledger are unchanged.

Future release work must rebuild shared Home, its Helper app/service copies and
Root Home/service, plus embedded inventory copies in updater/coordinator and
installers. The coordinator must select new component versions as appropriate,
verify source/package correspondence and affected final artifact update/rollback
and catalog/icon cases. Do not reuse the currently published Helper pin for
changed source. Source/model/browser success does not establish a fix on the
reporter's TV. TV model, firmware/webOS, remote and physical package acceptance
for these bytes are untested. Home routing, sound, standby, cold boot, OTA,
rollback and the original reported resource URL remain untested on a device.
Keep #505 open through release and reporter confirmation.
