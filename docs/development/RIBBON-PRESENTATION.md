# Root Ribbon presentation

This is an unreleased implementation, not a new compatibility or release claim.

The Root application keeps its existing identity and service. Its manifest uses
`defaultWindowType: overlay`, `transparent: true` and `handlesRelaunch: true`.
The application remains opaque by default. A theme can request overlay
presentation only through the paired `overlay-presentation-v1` contract on a
bounded scenic ribbon. No-root package metadata and Helper are unchanged.

`launcher/home-presentation.js` owns full/overlay/closed state, a context generation
and a separate launch generation. Only a fresh positive content observation enables
transparency. Power-on, unknown/empty context, suspended themes and actual visible
dialogs stay opaque. Tile editing and hide/undo own their controls while retaining
the active application background; they do not activate the Home wallpaper.
Entering/leaving control ownership invalidates stale successful launches without
invalidating a pending context query. Theme apply/reset/suspend/resume invalidate old work.
Back is handled after dialog/input/reorder ownership. Reopening hidden Home
refreshes context; ordinary relaunch of a visible transparent bar dismisses it.
Visibility-first activation notifications are coalesced with their relaunch for
500 ms; the next Home closes immediately after that activation is consumed.
This event-timing assumption also needs device acceptance.
Successful content launches dismiss the Root host, including opaque themes,
without claiming successful playback. Failed or superseded launches do not.

The exact `status` payload `{"presentation":"context"}` uses the existing Root
service boundary and a separate UID-checked read-only compositor request,
with a 1.5-second Root subprocess deadline and a two-second UI deadline. It returns only `content: true|false|null`; app IDs, raw surfaces and
private inventories do not leave that operation. No recovery lock, route write,
persistent preference, ACG or network listener is added. The native startup
observer makes a fresh overlay check before remembered-input effects, retaining
its own ownership and explicit cleanup.

Root also queries this context for opaque themes and power-on. Wallpaper video
and external-input previews require a current-generation literal `content:false`.
Unknown context holds the decoder before saved appearance restoration can attach
media. Refresh/hide revoke permission synchronously, and old asynchronous replies
cannot reacquire it. A decoder-only hold retains the static poster; transparent
presentation still hides it. Ordinary No-root CARD behavior is unchanged.

This is a bounded opening/refresh snapshot, not continuous decoder ownership.
There is no new polling, lease or background-change notification: content changes
without an existing UI refresh event still need physical/lifecycle acceptance.
This preventive fix does not establish the cause of the earlier C3 static-video
or unexpected-window-exit observations.

An opaque non-Ribbon theme/settings page still lives in the Root overlay host, so
underlying app/audio lifecycle may continue. Physical acceptance must cover that
behavior as well as Ribbon itself. The current task's browser captures are
synthetic, labeled and separate from any private device observations.

## Verification

Run the affected `scripts/test.sh ui tv preview` groups with installed build
requirements, plus `npm run test:themes:browser`. Focused state tests cover
context freshness, relaunch, modality and launch generations. The actual-renderer
demo test covers wallpaper/bright-content states, neutral cards/focus, Home/Back
and theme reset in both edition previews. `node tests/root-decoder-ui.cjs` compiles the actual Root renderer and exercises
cold restoration, denied/stale acquisition, real cache/HTTP MSE and native fallback,
and input preview release. Its LS2/activity transport and external-input media are
host simulations; Chrome decoding is not TV evidence. Root tests cover normalized context,
recovery-busy isolation, startup/input suppression and race guards.

Before publication, the release coordinator still needs exact signed-candidate
acceptance for video/audio, app and HDMI switching, full fallback at power-on,
standby/wake, emergency gestures and updater/profile/rollback health. A prototype,
installation or successful browser check does not satisfy those gates.
