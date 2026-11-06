# Root AOD preservation: cross-project source review — 2026-11-05

Review of #323, source head `40bedf5b8819ac2a9d51c5ad0b73802ad6557f78`,
integrated in next-cycle staging. The maintainer reports that target B4/C4 devices
are unavailable. This is source research and host verification, not an owner
installation report, firmware reproduction or physical acceptance. No TV was
accessed, no peer code was executed, and no candidate/build selection was changed.

## Sources and applicability

| Project / pinned revision | Inspected material | Relevance |
| --- | --- | --- |
| Home Chooser `1123add757aafdf6922ce2b630e3bc192c408c38` | Firmware/VM study, Settings contract, override builder and watcher record writer | Closest match: complete profile categories and merged Settings writes |
| Simple LG Launcher `6ebf202e4c38062125e52bbd56ecf4a9a4d029e0` | `tools/defaulthome.sh`, Home hook | Uses SAM `setDefaultApp`; not an independent implementation of our changed transport |
| Glasshouse `d7f36056ad8daa52620edcd0b159413e70559dc6` | Home takeover, webOS 9/10 handling and firmware research | Primarily replaces the stock application's identity/files; useful lifecycle context, not proof of our profile fix |
| Homebar `168c190c3f4732ea26aec5c2442861bdd6927530` | webOS 10 override/takeover/native Home modules | Stock-identity/package takeover; B4 support reported by its author does not validate our different implementation |
| LG OSE Settings Service `d914394eeb8882a6a4c7a86872ecfa9b2af3be1b` | Access, write, notification and reply paths | Supports notification/storage semantics; OSE is not the target retail firmware |
| LG OSE SAM `96161d3e50670fb21daccfb12a75c35fe406ce0e` | Settings client and default-app symbol search | Inspected source lacks the retail default-app APIs; cannot prove target cache behavior |

Peer implementation and research are first-party publications by their authors.
Their firmware analysis/VM observations were read, not independently reproduced
here. They are not four independent reproductions of the same AOD failure.

## Findings

### Complete categories are the strongest supported part of the fix

Home Chooser's [firmware study](https://github.com/webosbrew/home-chooser/blob/1123add757aafdf6922ce2b630e3bc192c408c38/docs/research/home-key-and-home-app.md#L283-L334)
reports that webOS 10.3.1 replaces second-level profile values wholesale, whereas
11.2.0 deep-merges. A Home-only `categories` object can therefore remove AOD on
the studied 10.3.1 implementation. Device layers have different categories and
AOD targets; copying a fixed AOD application ID is not justified.

Its actual [override builder](https://github.com/webosbrew/home-chooser/blob/1123add757aafdf6922ce2b630e3bc192c408c38/app/src/homechooser/index.js#L88-L113)
copies existing categories before changing Home. The [watcher](https://github.com/webosbrew/home-chooser/blob/1123add757aafdf6922ce2b630e3bc192c408c38/service/src/watcher/record.c#L145-L172)
does the same. This directly supports #323's baseline-derived payload, rather
than relaxing equality or ignoring missing AOD. The peer filters underscore
metadata and has its own idle-app policy; that does not establish that its full
payload format or recovery policy should replace ours.

### Separate the Settings setter from profile replacement

The [default-app lookup study](https://github.com/webosbrew/home-chooser/blob/1123add757aafdf6922ce2b630e3bc192c408c38/docs/research/home-key-and-home-app.md#L257-L279)
reports SAM subscriptions to `general/defaultApps` and preservation of other
Settings entries by `setDefaultApp` on the sampled 9.2.1/10.3.1/11.2.0 firmware.
Its separate [boot-race analysis](https://github.com/webosbrew/home-chooser/blob/1123add757aafdf6922ce2b630e3bc192c408c38/docs/research/home-key-and-home-app.md#L509-L525)
reports a setter using SAM's cached map before the initial subscription arrives.
These findings do not identify the original owner's exact loss boundary.

Home Chooser's [merged writer](https://github.com/webosbrew/home-chooser/blob/1123add757aafdf6922ce2b630e3bc192c408c38/service/src/watcher/record.c#L27-L71)
also reads the Settings record, retains other entries and uses `setSystemSettings`.
However, it normally prefers `setDefaultApp` on newer firmware, with a fallback
only for an unknown method. This is supporting precedent, not identical B4/C4
acceptance of #323's unconditional direct writer. [Simple LG Launcher](https://github.com/fardroid/Simple-LG-launcher/blob/6ebf202e4c38062125e52bbd56ecf4a9a4d029e0/tools/defaulthome.sh#L56-L77)
likewise uses SAM's setter, not our exact transport.

### Notifications make the mechanism credible, not synchronously proven

LG OSE [defaults storage and notifications to enabled](https://github.com/webosose/settingsservice/blob/d914394eeb8882a6a4c7a86872ecfa9b2af3be1b/Src/SettingsServiceApi.cpp#L862-L877).
Its [write completion](https://github.com/webosose/settingsservice/blob/d914394eeb8882a6a4c7a86872ecfa9b2af3be1b/Src/PrefsDb8Set.cpp#L978-L1003)
posts notifications and replies without counting consumer application acknowledgements.
Together with Home Chooser's retail-firmware subscription research, this lowers
concern that direct writes inherently bypass SAM. It does not prove notification
ordering or actual Home routing on the target firmware.

Our `device_adapter.read()` obtains profiles and `transport.read()`; the latter
reads Settings despite the internal field name `sam_home`. Trial and recovery
can verify those stored values without independently observing SAM's live route.
Do not equate a `restored` host-policy record with a new physical Home test.
The [official OSE SAM Settings client](https://github.com/webosose/sam/blob/96161d3e50670fb21daccfb12a75c35fe406ce0e/src/bus/client/SettingService.cpp#L50-L67)
subscribes to locale data and cannot fill that retail evidence gap.

### Other projects and unresolved risks

[Glasshouse](https://github.com/rorygallagher2024/glasshouse/blob/d7f36056ad8daa52620edcd0b159413e70559dc6/server/lib/home-takeover.js#L1-L36)
and [Homebar](https://github.com/rawinek/webos-homebar/blob/168c190c3f4732ea26aec5c2442861bdd6927530/webos10/native-home.sh)
use stock-identity takeover mechanisms. Their different lifecycle behavior is
not a reason to add mounts, restart SAM, alter checkpoints or bypass our recovery.

Read/modify/write is not compare-and-swap. A concurrent foreign Settings write
can be overwritten before our final readback. Notifications do not establish
cross-service atomicity. New Settings writes may also be denied despite successful
reads. Existing failures remain failures; no blind fallback/retry is authorized.
Our journal binding/legacy terminal bridge has host checks but no independently
matching peer journal protocol or signed-device rollback result.

## Verdict and verification

No new demonstrated staging blocker was found. Full category preservation has
strong external support; the fresh merged Settings write has credible precedent
and notification mechanics. The existing AOD host regression models actual
published payloads with shallow category replacement and checks complete map
preservation, interrupted recovery, dynamic identity, legacy terminal compatibility,
invalid maps and non-replayed lost writes. Reusing that regression is more useful
than adding a second test with the same model.

The transport comment was clarified to describe a fresh Settings read instead of
asserting the unisolated setter-loss cause. This changes no runtime behavior.
The focused suites passed for this evidence update: 7 AOD regressions and 9
profile-plan tests (16 total, no skips). The previous 205-test staging result and
exact source-PR CI remain earlier evidence, not a fresh full-candidate pass.

**Unverified:** exact rebuilt B4/C4 packages, live Home and AOD behavior, SAM/cache
application and recovery, standby, true cold boot, controls/audio and signed
update/retained rollback. Lack of target hardware is explicit. Source review is
not substituted for those results or for mandatory candidate gates; the release
coordinator must keep the limitation visible and obtain any necessary release-risk
decision rather than mark the cases passed. #282 remains an unresolved report.
