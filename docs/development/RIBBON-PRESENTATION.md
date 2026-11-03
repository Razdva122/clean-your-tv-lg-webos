# Root Ribbon presentation

This is an unreleased implementation, not a new compatibility or release claim.

The Root application keeps its existing identity and service. Its manifest uses
`defaultWindowType: overlay`, `transparent: true` and `handlesRelaunch: true`.
The application remains opaque by default. A theme can request overlay
presentation only through the paired `overlay-presentation-v1` contract on a
bounded scenic ribbon. No-root package metadata and Helper are unchanged.

`launcher/home-presentation.js` owns full/overlay/closed state and a generation
for async context/launch work. Only a fresh positive content observation enables
transparency. Power-on, unknown/empty context, suspended themes and actual visible
dialogs stay opaque. Theme apply/reset/suspend/resume invalidate old work.
Back is handled after dialog/input/reorder ownership. Reopening hidden Home
refreshes context; ordinary relaunch of a visible transparent bar dismisses it.
Visibility-first activation notifications are coalesced with their relaunch for
500 ms; the next Home closes immediately after that activation is consumed.
This event-timing assumption also needs device acceptance.
Successful content launches dismiss the Root host, including opaque themes,
without claiming successful playback. Failed or superseded launches do not.

The exact `status` payload `{"presentation":"context"}` uses the existing Root
service boundary and a separate UID-checked, two-second read-only compositor
request. It returns only `content: true|false|null`; app IDs, raw surfaces and
private inventories do not leave that operation. No recovery lock, route write,
persistent preference, ACG or network listener is added. The native startup
observer makes a fresh overlay check before remembered-input effects, retaining
its own ownership and explicit cleanup.

An opaque non-Ribbon theme/settings page still lives in the Root overlay host, so
underlying app/audio lifecycle may continue. Physical acceptance must cover that
behavior as well as Ribbon itself. The current task's browser captures are
synthetic, labeled and separate from any private device observations.

## Verification

Run the affected `scripts/test.sh ui tv preview` groups with installed build
requirements, plus `npm run test:themes:browser`. Focused state tests cover
context freshness, relaunch, modality and launch generations. The actual-renderer
demo test covers wallpaper/bright-content states, neutral cards/focus, Home/Back
and theme reset in both edition previews. Root tests cover normalized context,
recovery-busy isolation, startup/input suppression and race guards.

Before publication, the release coordinator still needs exact signed-candidate
acceptance for video/audio, app and HDMI switching, full fallback at power-on,
standby/wake, emergency gestures and updater/profile/rollback health. A prototype,
installation or successful browser check does not satisfy those gates.
