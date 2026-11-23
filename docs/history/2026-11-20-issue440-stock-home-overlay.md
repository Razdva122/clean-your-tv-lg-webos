# Stock Home over content during Root removal

The public [#440 screen readings](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/440#issuecomment-7040820796)
show SAM retaining the content app while Surface Manager adds
`com.webos.app.home` with `_WEBOS_WINDOW_TYPE_HOME` above its CARD on display 0.
The owner [identified the content as YouTube](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/440#issuecomment-7041417886).
The probe hid its app ID, so test fixtures use a synthetic content ID.

The TV is LG 65NANO926PB, firmware 03.34.55, webOS 6.3.2, with a physical Home
button of unspecified remote model. The retained Root attempt used runtime
0.19.5. Explicit removal with the macOS ARM64 cytv 0.20.7 installer reached
`runtime-restore`, then `ui_release_failed / stock-foreground-unverified`.
The owner has preserved the pending removal. Successful cleanup and fresh Root
activation on this TV remain unverified.

## Offline investigation

The [LG support page](https://www.lg.com/fi/tuki/product/lg-65NANO926PB.AEU)
lists 03.34.55 in its history but currently links the newer 03.53.45 archive.
The exact 03.34.55 image was unavailable through that page. Earlier W21
03.53.45 investigations establish comparable factory components, but do not
establish this firmware's current foreground reply. No new firmware extraction
or execution is claimed. The owner's two bounded readings supply the live
response shapes replayed here.

## Correction and scope

Schema 3 webOS 6 removal after a failed UI-release acknowledgement can accept
exactly two surfaces: stock Home of type HOME and the CARD matching SAM's
content app. Home must be visible on the main display, with the existing
visibility defaults for omitted fields. CYTV apps, Helper, Live TV, screensaver,
additional surfaces and ambiguous display fields do not qualify for this path.
The existing webOS 5 Live TV path continues to use its factory-handler proof.

The new path requires a stock vendor filter chain, a second matching SAM reply,
fresh stopped native proof with the same token and an unchanged final chain.
The coordinator retains the original operation, ownership and package checks.
No additional TV file, endpoint, permission or setting is introduced.

Tests replay the reported surface shape through runtime restoration, including
the isolated child and compiled native guard. Negative cases cover hidden or
missing Home, wrong window type, extra surfaces, project apps, display ambiguity,
foreign filter chains, changed SAM/chain/native attempts and ordinary Restore.
The coordinator replay checks eventual verified cleanup after its modeled
restart and preserves the original failed request. TV bus replies and restart
are modeled, leaving original-device acceptance outstanding.

## Verification

- The new runtime replay failed at `stock-foreground-unverified` before the fix.
  All 64 compositor runtime tests pass with the correction.
- All 113 clean-removal tests pass, including the content/Home coordinator replay.
- All 52 native guardian tests pass. Their macOS fixture requires `ps` access;
  the sandboxed run failed because the sandbox denies that process read. The
  same suite passed when that host restriction was lifted.
- Independent review found no blocking findings. The late-chain-drift regression
  was corrected to mutate during the second SAM observation and passes.
- `git diff --check` passes. The exact firmware and owner TV were not executed.
