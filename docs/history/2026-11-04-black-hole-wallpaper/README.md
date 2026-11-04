# Black Hole wallpaper integration — 2026-11-04

## Scope and artwork

PR #267 includes the video-layer dependency from #264, personal wallpaper transfer,
embedded UHD authoring, and reusable Black Hole wallpaper selection. The video author
is **Xecutioner**, [4K SCI-FI Black Hole](https://steamcommunity.com/sharedfiles/filedetails/?id=2981249186).
The maintainer confirmed author permission for non-commercial use and inclusion in
free CYTV distributions with explicit attribution. Artwork terms are separate from
MIT; see `themes/ribbon/LICENSE.txt`, `CREDITS.txt` and `THIRD_PARTY_NOTICES.md`.

Native capture and packaged video are 3840×2160 at 30 fps. No spatial upscaling is
used. The silent 12-second loop contains original scene motion and a one-second
end-to-start dissolve. A fragmented copy preserves the same encoded H.264 bytes.
Built-in wallpaper selection reuses the verified Ribbon media without applying its
layout. Accepting a different theme restores its own background; retained uploads
and Black Hole remain available for manual reselection.

## Focused private-device preview

This owner-authorized preview is preliminary UI evidence, not final release
acceptance. Device model and remote: unknown. OS release: webOS TV 11.2.0;
separate firmware identifier: unknown. Edition: isolated Root visual preview with
locked simulated native services, reference application fixtures and separate
storage. Main Home/service packages were not replaced. Installer platform: macOS,
existing verified Root SSH.

- Preview 0.0.2: original UHD Black Hole installed; owner liked artwork but observed
  approximately half-second pauses at file repeats. Frame analysis found no frozen
  frame run in the encoded loop.
- 0.0.3 added diagnostic wall/media clocks; owner identified the pause specifically
  at native MP4 restart.
- 0.0.4 used a continuous MSE sequence timeline. Owner confirmed smooth playback.
- 0.0.5 removed diagnostic overlays. 0.0.6 integrated the general wallpaper library.
  Cold application launch from its icon showed poster → black flash → video.
- 0.0.7 retained the poster until a presented-frame callback. Owner reported no black
  flash, but motion did not appear. This attempt was unsuccessful on the device.
- 0.0.8 added a decoded-progress alternative: validated dimensions, decoded-frame
  readiness and two advancing media samples, followed by two presentation frames.
  The unused callback is cancelled. Startup progress without decoded frames cannot
  indefinitely postpone the bounded fallback. After the app was confirmed absent
  from running apps, the owner opened its icon and confirmed video started, no
  black flash, and smooth playback.

The tested 0.0.8 IPK SHA256 was
`642a068d35a1b80374793b8f3ee7048a2c47cc9883545b0b7802b7b7a6413a64`.
Independent installer completion and deployed file hashes were checked. A UI-only
preview with simulated native services does not verify production media grants,
Home-button routing, application launch/control return, sound, TV power cold boot,
standby, OTA or rollback. These remain candidate gates. One device is not universal
compatibility evidence. Private addresses, keys, PINs, app inventories and raw logs
are not included here.

## Automated and browser evidence

- Full UI group and theme suite on the combined integration branch.
- Both-edition library selection, visible attribution, app reload, theme-owned
  background on a new choice, retained personal slot, and real UHD decode.
- Personal transfer/settings/restore regressions, packaged Ribbon offline/reload,
  callback cancellation and two asynchronous theme-confirmation race regressions.
- Real decoder across three continuous 12-second boundaries without seeking or
  waiting, bounded old-buffer removal, disposal, unsupported-MSE native fallback
  and tampered-fragment FHD fallback.
- Exact isolated preview startup/reload with all presented-frame callbacks
  suppressed; normal startup also checked. Browser timing is not a TV measurement.
- Independent code review approved confirmation serialization and the final
  decoded-progress handoff after regression fixes.

README and theme images are fresh shared-Home browser renders with reference icons;
they are not photographs of the TV. Browser demo pages use browser media URLs rather
than invoking simulated native-cache RPC. Their production-TV source/cache boundary
is unchanged. The public Pages deployment follows the later main release decision.
