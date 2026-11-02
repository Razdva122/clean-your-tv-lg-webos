# Native startup sources implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Choose Clean natively as the first app for selected prior sources; remove all delayed boot/wake application launches.

**Architecture:** Existing guarded Home activation owns the native Root EIM entry. A guardian-owned, event-driven observer of foreground/native-input settings maintains or withdraws that remembered selection according to a private three-boolean policy; every mutation uses fresh checks and the existing operation lock. Source preferences remain separate from the legacy launcher/System profile schema, so the original installed supervisor contract remains compatible.

**Tech stack:** Existing Python runtime, bounded Luna subscriptions, Root JS service and existing TV settings controls; no dependencies.

**Spec:** User requirements in this plan, below.

## Global constraints / specification

- Defaults: `{tv:true,youtube:false,hdmi:false}`; `tv` groups LG Channels and Live TV. Root itself remains the selected Home.
- Home Off: source controls visible, muted, disabled, skipped by remote navigation, explanation that Change Home must be on; preferences retained.
- No automatic application `launch` in boot/wake paths. Preserve explicit Home, restore-before-rearm, key-up, independent watchdog/triple-Home, failsafe and explicit Off authority.
- Input/guardian health, current session/binding, package/owned EIM receipt, Home startup preference and operation serialization precede native mutations. Each optional RPC sequence fits 1.5 seconds.
- Preserve disallowed/protected foreground by withdrawing only our exact Root remembered selection to its recorded displaced pair. Never overwrite a different current native input. Unknown/missing/transient foreground cancels eligibility.
- Subscriptions provide triggers, not cached authority: re-read actual foreground/native pair and authority before the effect. On EOF/invalid subscription/session change cancel pending work; no reconnect/poll/retry loop.
- Save the actually displaced native pair before setLastInput; journal uncertain selection/withdrawal; reconcile by readback without blind replay. Existing Off/emergency cleanup handles owned pending native state.
- Private durable policy path `startup-policy.json`, schema1 + exact `sources` booleans. Do not extend legacy RootProfile/System schemas. Preserve policy across normal Root operations/updates; do not claim portable profile export.
- UI RPC through existing Root `status` payload `{startup:'status'}` and `enable` payload `{startup:'configure',sources:{tv:true,youtube:false,hdmi:false}}`. Same nested control response: `{returnValue:true,result:{returnValue:true,result:{sources,active}}}`. Actual Home Off rejects configuration; status still readable.
- User authorization covers implementation. No further native trial/package installation/publication without its applicable concrete permission. Manual experiments cannot establish acceptance of the permanent policy.

## Task 1 — Source controls (independent UI work)

Files: `root-edition/ui/root-settings.js`, `.css`, `root-locales.js`, settings tests; localized user guides where controls are described.

- [x] Add a failing real settings-module test for defaults/readback, exact payload, Home-Off disabled styling and blocked click/key activation, stale status and focus skipping.
- [x] Run the test and observe failure.
- [x] Add three switches in the existing Home settings section, root-authoritative reads and saved-value readback. Invalidate alongside existing Home status lifecycle; failed/unknown/busy status disables the group. Preserve existing Home controls behavior.
- [x] Translate visible strings, update twelve guides with candidate-only setup/control wording; no device success claims.
- [x] Run settings unit/browser, localization and compatibility checks.

Sample UI fixture:
```js
const startup = {sources:{tv:true,youtube:false,hdmi:false},active:false};
// Render actual module with fixture; assert three disabled controls and no RPC
// write when clicked, then deliver active status and assert saved checked values.
```

## Task 2 — Delete delayed launch paths (independent removal work)

Files: `runtime/intent_runtime.py`, `runtime/shutdown_state.py`, old presentation tests, `test_wake_lifecycle.py`, `test_intent_runtime.py`, `test_shutdown_state.py`.

- [x] Replace presentation assertions with a failing assertion that ordinary boot recovery and a complete power cycle issue zero application launches while retaining real health/binding/native cleanup tests.
- [x] Remove `_boot`'s optional presentation block and `present_boot`, `present_wake`, `_present_home`, `_native_channel`.
- [x] Remove `Monitor.presentation/request_wake`, `observe_power(...wake=...)` wiring. Keep power subscription/shutdown evidence, including proven ON baseline through preparation.
- [x] Delete obsolete presentation-only test file; rewrite lifecycle assertions retaining explicit Off/emergency/failsafe/package loss/new-session/cold-boot/duplicate callback coverage.
- [x] Run affected lifecycle/shutdown/native tests; do not modify startup observer files or add replacement native policy here.

## Task 3 — Durable policy, early native selection and service contract (coordinator)

Files: new `runtime/startup_policy.py`, `runtime/startup_observer.py`, `device_adapter.py` native receipt validation, `shutdown_state.py` one monitor integration after Task2, `cli.py`, service handlers/service, new policy/observer/service tests.

- [x] Write failing defaults/strict-policy, native select/withdraw, disallowed YouTube/HDMI, uncertainty/readback, Off/emergency/cancellation and stream loss tests. Use real private files and existing native fake bus; assert actual remembered pair and unchanged foreground, not mock-only calls.
- [x] Implement policy load/configure/status with mode0600 atomic writes and active-only configuration under the current operation lock.
- [x] Add bounded reconciliation to the existing owned EIM entry; record the current displaced pair and pending direction before mutation. No add/adopt/re-enable or application launch in the observer.
- [x] Add two bounded subscriptions with one coalescing worker, distinct-event cancellation and no reconnect/polling. Foreground source must be fresh and verified; EIM updates cannot reuse stale foreground to overrule a newer native selection.
- [x] Wire the above existing-method payloads and CLI startup operation; test exact booleans/field rejection, Home-Off and errors, preserve audio/recovery handlers.
- [x] Run affected Root/service/UI tests, full required scoped validation, source review and packaging.

Example independent assertions:
```python
self.assertEqual(load_sources(), {'tv': True, 'youtube': False, 'hdmi': False})
self.assertEqual(bus.last, displaced_channel_pair)  # after protected YouTube
self.assertEqual(bus.foreground, youtube_id)       # no launch at any stage
```

## Integration and acceptance

- [ ] Read every changed file and new review/comment before decisions; rewrite PR255 title/body to final scope. Preserve already approved historical report text and retain failed QA1.
- [x] Preliminary build metadata stays isolated from the implementation PR. The owner subsequently assigned this task candidate coordination and authorized overnight integration/freeze/build; final physical acceptance remains pending.
- [ ] Build/sign exact versioned QA source, verify hashes/signature/read-only preflight; obtain exact install consent, then ordinary original worker installation/health/profile/hashes.
- [ ] Owner-observed first screen on TV/Channels defaults, YouTube/HDMI opt-out and opt-in, Home-Off UI disable, emergency/Off persistence and affected cold/standby checks. Do not claim passes from package install or earlier manual trial.
- [ ] Prepare a consolidated redacted report/destination and obtain publication approval for new results. Reconcile issue171 labels with actual unresolved scope; no premature closure.
- [ ] Save commits/artifacts and archive both task-created managed worktrees after all necessary work is complete.
