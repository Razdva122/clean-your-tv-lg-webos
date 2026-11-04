# Production No-root Ribbon integration

Requested by the maintainer on 2026-11-04; this extends the frozen candidate scope.
The selected build 41837911621:1 remains historical and cannot certify this change.

## Existing evidence

The standalone lab uses Developer Mode overlay metadata and the real shared Ribbon
renderer. The isolated prototype is not production Helper routing, startup, power, OTA
or emergency acceptance; final device evidence must use the product package. The
production Home currently remains a card and explicitly gates overlay on Root.

## Recommended architecture

Use the existing com.gathin.tvhome identity, profile, renewal service and package.
Give that Home the overlay/transparent/handlesRelaunch/no-splash metadata already
used by the lab. Reuse HomePresentation; remove no safety checks from Root.
Only Ribbon may request transparency. All other themes, manual launch without a
validated context, startup, wake, settings and unknown context draw an opaque
background. An opaque overlay can preserve underlying playback; it is not native
card lifecycle. This changed lifecycle must be documented and device-tested.

Helper supplies bounded launch facts on actual Home presses, not an unrestricted
compositor proxy or caller-supplied permission. Derive content eligibility from
the existing authenticated local SSAP observation, never from the panel itself.
Invalidate it on disconnect, power changes, unrelated launches and stale/out-of-
order observations. Read-only fresh-context request should reuse the existing
Home/Helper authenticated bridge after secure storage migration, rather than
adding a network listener or another shared writable file. Launch parameters
only identify the activation reason/generation; they cannot grant authority or
start Helper. If a trustworthy current observation cannot be established, render
opaque. Manual and startup launches default opaque even if cached content exists.

Physical Home opens Ribbon over eligible active content; the next ordinary Home
relaunch dismisses an unobstructed visible Ribbon. Back dismisses an unobstructed
Ribbon, but closes editing, menus and dialogs first. Input/app launch closes only
after success; failure retains UI. Dismissal must not trigger Helper return-after-
exit loops. Existing boot/wake return policy uses explicit opaque activation;
normal Home activation must not be confused with boot, settings or recovery.

Keep wallpaper decoding suspended before the context decision and throughout
overlay/settings transitions. Opaque fallback resumes only its intended wallpaper
policy after the mode is settled; unknown context initially uses a static image
to avoid stealing the underlying decoder. Preserve personal media and profile.
Emergency/off, stop, watchdog and explicit LG Home invalidate pending activation,
release interception and normally close the owned overlay before/with LG Home.
Never clear blocked/watchdog latches automatically or trust legacy 0777 keys.

## Alternatives

1. Separate production overlay companion: preserves the old card lifecycle for
   Home but adds identity, profile sharing, installation/update/rollback and
   focus ownership. Reserve for a measured platform incompatibility with the
   single-host design; it is more than a rename of the lab.
2. Convert Home to transparent CSS only: rejected because a native card still
   suspends the underlying app and cannot supply the requested behavior.

## Verification and integration

Focused tests first: full/overlay/unknown/startup/manual contexts; freshness and
reset; relaunch versus activation; callback generations; modal/edit/Undo Back
precedence; launch success/failure; normal dismissal versus return-after-exit;
stop/emergency races; legacy Helper/Home compatibility and no latch clearing.
Browser tests must load the actual compiled No-root renderer, not Root simulation.
Run legacy Node 0.10.15/0.10.25/0.12.2 and ES5 compatibility checks as applicable.
Inspect both 1080p/720p packages and all installer payload/manifests; keep app IDs,
service permissions, signed updater/rollback contracts coherent. Update all
12 localized guides and release documentation for actual behavior and limits.

Use a separate focused branch/PR to release/next, review before integration, then
select a new successful full candidate and matching signing output. Version
admission must use the normal supported transition, never equal-version force.
Coordinate the secure Helper fix, then test physical Home/Back/repeated Home,
Magic Remote focus, HDMI and video/audio, fullscreen fallback/settings/edit/Undo,
app launch/return, emergency/off/watchdog, standby, real AC boot, upgrade and
rollback. Test pristine No-root separately; rooted-C3 evidence cannot certify it.
Retain a draft RC with explicit failures/untested cases until gates pass. No
main merge or stable publication is authorized by this integration request.


## Approved choice and native seam

The maintainer approved the same-Home integration on 2026-11-04, including
underlying playback continuing beneath opaque themes. Production retains one
app identity and existing profile/update paths.

Frontend calls its own renewal service presentationContext; that service relays
only after measured Home caller authorization to
luna://com.local.nativehome/presentationContext. The normalized response is
{returnValue:true, eligible:boolean, content:true|false|null, generation:N,
observedAgeMs:number}. N is a safe nonnegative integer seeded independently per
native daemon lifetime; age including frontend transport must not exceed2000ms.
Eligible true requires content true; false eligibility never grants decoder
ownership. Content false requires separately established absence of underlying
content, not an inference from LG Home. Unknown keeps the static poster.
Physical activation carries only cytvHome:{reason:'home',generation:N}; the native
reply must independently match. Stop, power, off, dismissal and restart invalidate
generations. A separate authorized presentationDismissed request with N may
retire only that generation, never new activation or routing. Native inbound RPC
registration and complete measured caller binding remain implementation gates;
frontend tests simulate the seam and are not device acceptance.
