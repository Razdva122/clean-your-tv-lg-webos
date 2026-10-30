# Theme selection, storage and transport (candidate)

Classic and Alpine are packaged in both editions. Classic is the unchanged default until an explicit choice; Alpine uses `builtin:alpine`. Channel remains an external, independently versioned showcase distribution. The historical external Alpine listing is archived; its published immutable bytes are retained.

## Trusted modules

- `theme-data.js`: public GitHub URL/collection resolution; commit pinning; bounded sequential XHR; SHA-256; typed manifest/rule validation; image signature/header/dimension checks and native image decode; Blob handle cleanup.
- `theme-store.js`: app-origin IndexedDB `ctv-themes-v1`, object store `packages`, keyed by descriptor digest. Writes are complete transactions. It bounds installed payload bytes at 24 MiB and eight cached versions, additionally subject to the device's own quota. Download failures do not commit partial packages.
- `theme-manager.js`: `tvhome.theme.choice.v1` accepted pointer plus `tvhome.theme.trial.v1` durable preview/startup marker. `selectInstalled(item)` verifies builtin/cache membership through `list()`, then applies and immediately persists without scheduling a timer. It keeps the durable marker before native preparation and CSS application, and restores the previous choice if preparation or persistence fails. Only showcase `begin(item)` schedules the 20-second trial: Keep commits the accepted pointer; Back/Revert/timeout restores the previously accepted appearance. LAN and URL installation choices use immediate installed selection. Incomplete trial/startup on relaunch falls back to Classic without erasing downloaded packages. Binary assets never enter localStorage.
- `theme-panel.js/css`: standard on-TV Themes settings, remote focus/navigation, URL input, explicit collection choice, installation progress/error, version selection/removal and clear-cache recovery. The trial confirmation stays outside the themed surface and leaves the app ribbon visible. Parent Settings are hidden only during the trial and restored afterwards.
- `theme-locales.js`: twelve-language settings labels. Validation/network diagnostics may use English technical messages.
- `builtin-theme-files.json`: explicit Alpine file inventory, mirrored by packaging/preview allowlists. `builtin-themes.json` pins the bundled descriptor digest. Alpine bytes and notices come from the immutable toolkit source/distribution recorded in the initial catalog review; the trusted built-in descriptor has a separate identity.

The core theme renderer adds no root commands, repository scripts or external CSS execution. The optional PC → TV receiver adds four owner-scoped Luna methods to the existing edition service; see its provisioning requirements below. Existing emergency Home release, key-up delivery and Home routing remain independent.

## Source behavior

Accept a public `https://github.com/OWNER/REPO` or an exact `https://raw.githubusercontent.com/OWNER/REPO/FULL_COMMIT/.../cytv-theme.json` (or `cytv-themes.json`). A repository URL resolves HEAD through the GitHub commits API, then probes the root collection; a genuine 404 falls back to a root single-theme descriptor. An invalid collection does not fall back. Collection selection is explicit and binds the entry ID/version/digest. Subsequent manifest-relative files stay under the same pinned distribution directory. Credentials, queries, arbitrary hosts, moving raw URLs and traversal are rejected. Redirects are rejected when the browser exposes the final response URL. GitHub rate limits and TLS/CORS failures surface as errors without changing the accepted theme.

Descriptors are at most 64 KiB; rules 128 KiB; image assets at most 2 MiB/1920×1080 each (the single `defaults.wallpaperAssetId` asset may be 3840×2160), previews 300 KiB/960×540, total assets 6 MiB. Every named rule/image/license/credits file must match size and SHA-256. Package transfer is sequential with 15-second per-request timeout and a 60-second package deadline. Native decode must complete within eight seconds/image, after bounded header inspection. Unreferenced cached files, unsupported APIs/layout scales, malformed images and incompatible minimum Home versions are rejected. Prepared handles are released on cancellation/rejection/replacement.

Installed versions do not follow a branch or contact the author on startup. To update, install the newer descriptor and select its installed version (through Add by URL or Receive from computer), then remove the old inactive version. The settings confirmation restores Classic before deleting an active version; direct manager deletion of an active package remains forbidden. Clear downloaded themes restores Classic and empties only the theme cache.

## Profiles and updates

Theme state is separate from legacy `HomeData`/Root profile and updater contracts. Ordinary app-origin storage survives a normal relaunch; browser tests cover that path. Existing profile backup/export does not include the binary theme library. Legacy profile restore clears the accepted pointer/trial and starts Classic, while leaving downloaded versions available for reselection. System profile restore preserves existing app-origin choice, Columns and interruption markers because the snapshot does not encode them. The theme manager remains responsible for validating choice/cache and consuming interrupted markers safely; preserving a marker never resumes an unconfirmed trial. Explicit By theme and numeric Columns preferences retain their meaning. When the Columns key is absent, existing legacy config semantics remain unchanged: a theme pointer alone cannot prove that a nondefault count was accidental. Package/application removal may clear its app-origin data. No independent profile/OTA schema is silently extended.

## Verification and remaining hardware gate

`tests/themes/transport.cjs` checks SHA-256/UTF-8 vectors, URL boundaries and real Channel payload integrity. `tests/themes/selection-ui.cjs` runs both real renderer editions against app-owned IndexedDB and simulated pinned transport: built-ins, external installation, user columns, offline reload, cancellation, timeout, interrupted trial, bad hash rejection, storage ceiling and removal. Existing isolation/geometry/legacy-input suites remain required. Package and compatibility tests must include the new files in both editions.

Browser verification does not establish TV-origin IndexedDB availability/quota/persistence, platform TLS/CORS, actual remote/IME input, standby/cold boot, updater rollback or device compatibility. Before public release record device model, firmware/webOS, remote, edition, exact package versions, installation platform, actual expected/observed results and untested cases. No device was changed or verified by the browser tests. The maintainer authorized integrating the current implementation, including Themes, Columns and categorized settings, into the unfrozen `release/next` candidate on 2026-10-29. Further refinement and hardware acceptance remain separate follow-up work.

## Candidate browser acceptance record (2026-10-29)

Passed: `scripts/test.sh tv preview`, `npm run test:themes:browser`, geometry, legacy UI, Chromium 38/ES5 compatibility, twelve-language catalog checks and scoped lifecycle/transport tests. Subsequent review fixes were verified with focused unit/browser regressions.

An isolated desktop Chrome run also resolved, downloaded, hash-verified, decoded, previewed and accepted Channel 1.3.2 directly from its public GitHub raw commit URL without a transport mock. This verifies that desktop CORS/transport path, not TV TLS support. No credentials or device addresses were used.

Independent review reproduced and fixed stale asynchronous rollback overwriting a newer reset/preview, schema-valid collection paths being rejected and prerelease version comparison. Regressions also cover preparing cancellation, confirmation-save failure and blocked interaction behind the trial confirmation.

Browser captures: [standard Themes settings](theme-tv-review/settings.png) and [Alpine trial](theme-tv-review/alpine-trial.png); [snapshot provenance](theme-tv-review/provenance.json). Model, firmware/webOS, actual remote, installer platform and device tests remain unknown/not tested. Hardware installation, routing, sound, standby, cold boot, OTA and rollback have not been verified here. These historical browser artifacts do not establish physical acceptance or authorize public release. Integration into the unfrozen candidate follows the maintainer’s separate 2026-10-29 instruction; the release remains gated on exact-artifact validation and hardware acceptance.

The trusted toolkit preview wrapper sets `CYTV_THEME_AUTHOR_PREVIEW` before app boot so a persisted on-TV-style choice in that browser origin cannot race the author adapter and replace the source being edited. Normal TV packages and the main website preview do not set this flag and restore accepted themes normally.


## Development transfer and TV catalogue (next candidate)

Computer transfer uses only the temporary TV receiver described below. The TV
never downloads a package from a computer-hosted HTTP endpoint. `ThemeData.unpackEnvelope`
decodes the bounded received envelope and applies the same descriptor, rules,
hash, image, API and minimum-version checks before the atomic cache write.
Ordinary repository installs remain HTTPS-only. The old address/PIN download
transport, computer-address preference and author-side sharing server are removed;
previously installed themes and repository source metadata are unaffected.

`node scripts/build-tv-theme-catalog.cjs` derives `launcher/theme-catalog.json` and local preview/notice files from the reviewed showcase registry. `--check` fails on drift, missing or orphaned assets; `npm run test:themes` includes that gate. Classic/Alpine are builtin cards; active Channel keeps its source URL, identity and digest. Removed/unavailable records are excluded. Packaging consumes the existing explicit inventory. Each explicit `ThemeManager.catalog(signal, onLocal)` call refreshes from `https://api.github.com/repos/Razdva122/clean-your-tv-lg-webos/git/ref/heads/main`, then requests `launcher/theme-catalog.json` at that exact commit on raw.githubusercontent.com. The optional callback receives validated bundled entries immediately before remote requests; callback failures reject. Only reviewed external entries are taken from that snapshot; running-version builtins remain local. Preview paths become pinned URLs within that project commit. Invalid, missing or unreachable remote data falls back to the bundled snapshot with an array `.notice`; cancellation rejects instead of falling back. Requests use existing status/redirect/size limits and nothing is persisted or installed by refresh. External IDs must match their commit-pinned source repository; installer verification still checks distribution hashes. New submissions require regenerating/reviewing catalogue assets and a normal merge into the main repository; an unmerged candidate may use fallback until those files are available there. Opening the separate showcase or Refresh invokes this without a Home update or page reload. Physical-TV network acceptance remains pending.

`tests/themes/envelope.cjs` covers byte integrity, envelope bounds and rejection
of retired computer-hosted download requests before network access.
`tests/themes/receiver-ui.cjs` covers the actual receiver UI contract, LS2 assembly,
cancellation, validation and immediate Apply in both editions. Appearance and
settings regressions verify that the removed form is absent and Retry/Back stay
accessible. Catalogue discovery retains external download/trial, received-package
installation and offline persistence coverage. Toolkit tests cover outgoing HTTP,
PIN/destination boundaries, and absence of the retired command and endpoints.
These browser tests use synthetic transport and do not establish new hardware
acceptance.

Historical evidence for the retired pull transport, 2026-10-29: `scripts/test.sh tv preview`, full both-edition theme browser suite, legacy UI and Chromium 38 compatibility passed. The toolkit suite passed 29 tests without skips against candidate export base `c2465f6329f535f075b0ab2ef6bc0d742a2588dd` (dirty snapshot). Real Chrome file-origin XHR accepted a compiled package through loopback with no mocked transport or disabled web security. Private-interface self-connections were unavailable in the development environment, so full LAN routing remains unverified. In-app browser catalogue download of the actual pinned Channel package also succeeded without changing the accepted theme. [Catalogue capture](theme-tv-review/catalog-lan.png) and [provenance](theme-tv-review/lan-catalog-provenance.json) record synthetic UI evidence, not physical-TV acceptance.


Installed-theme cards use `ThemeManager.preview(item)` to load the exact cached digest, verify its manifest/files and identity, and expose only its preview asset through a MIME-typed Blob URL. The UI owns an idempotent lease and revokes it on redraw, navigation, close, stale completion or image failure. These URLs are never persisted. Built-in previews use bundled files; the independent published showcase does not include personal installations. `installed-previews.cjs` verifies actual preview bytes and rejection of tampering; `installed-previews-ui.cjs` covers a custom theme absent from the catalogue offline in both editions and exercises lifecycle cleanup.


## Hidden Columns scroll geometry (next candidate)

The shared layout panel marks the Columns wrapper with `home-columns-entry` and keeps the button’s `hidden` flag for existing remote navigation. Both settings styles retain the hidden row/button flex geometry using `visibility: hidden`; the wrapper also carries `aria-hidden`. This reserves the row and margin below the theme lane instead of shortening the scroll range and clamping the viewport during Apply. Genuine Columns focus still uses the #169 fallback; Apply and theme-card nodes are retained.

`columns-entry-geometry-ui.cjs` exercises both editions at 1080p/720p and narrow width, including Tab, direct focus and the accessibility tree. `selection-ui.cjs` visits the real By theme dialog and records Apply frames at the content’s lower scroll limit. These are browser regressions; new physical-TV acceptance is pending.

## Embedded Appearance controls (theme-followups)

The follow-up mounts HomeThemePanel inside the Appearance pane in both editions. Installed cards, catalogue/details and URL/LAN forms use the existing settings content surface; the category sidebar remains available. SettingsCategories activates/deactivates the embedded controller and yields keyboard handling only for its active subviews. Parent settings close and category changes cancel pending work and release preview leases. Ordinary installed selection keeps Settings styling suspended and saves immediately. Only an explicit showcase trial temporarily moves its trusted confirmation to the document body, reveals Home and then reattaches to Appearance on Keep/Revert/timeout. No new storage keys, network hosts or privileged services are introduced.

Navigation regressions cover native input defaults, two-step Back, async refresh focus ownership, successful immediate-apply focus, category changes and pending preview cleanup. Both editions and 48 locale/viewport combinations are covered. This follow-up is separate from the release-preparation branch; browser verification remains distinct from physical-TV acceptance.

Validation for the embedded follow-up: full theme unit/browser suites, both-edition settings navigation across 48 localized 720p/1080p layouts, category update badges, legacy settings unit checks and Chromium 38 compatibility passed. The author preview passed 31 tests against the initial embedded export and four focused preview tests against the final export; its guide now points directly to Appearance. A real parked-pointer focus regression was fixed by requiring coordinate-changing mouse movement before hover changes focus. Physical-TV acceptance was not performed.

The inline Showcase filters both bundled and refreshed entries against `ThemeManager.list()` by theme ID, including built-ins and personal installations. Removing the last installed version makes an entry visible again. Updates to hidden installed themes use URL/LAN installation. Catalogue revision discovery uses the small `refs/heads/main` Git ref response, validating the exact ref and commit object; full commit responses can exceed the 64 KiB transport limit. Size-limit errors are settled before aborting XHR so synchronous native abort events cannot replace them with cancellation errors.

## Scoped physical theme UI check — 2026-10-29

On LG OLED55C3RLA, firmware 43.21.71 / webOS SDK 11.2.0, an isolated Root UI fixture (`com.cleanyourtv.themeqa`, version 1.5.1) was installed from macOS over the saved SSH transport. UI controls were operated through the TV renderer debugger; a physical remote was not used and its model is unknown. The fixture contained the compiled theme/settings UI, an empty app inventory and a fixture-only direct UI bootstrap instead of production profile restoration. It installed no services or startup hooks and did not replace the existing Home 0.4.0. This is scoped UI evidence, not candidate-package or release acceptance.

Expected and observed: Settings → Appearance contained the installed cards; Showcase contained Channel only; Download fetched the actual pinned Channel package without changing Classic; Try displayed Channel and Keep saved it; reopening Showcase hid all installed IDs and showed the localized empty state; Back returned to installed cards; applying Classic allowed Channel removal; reopening Showcase showed Channel again. All these steps passed. Channel descriptor SHA-256 was `d94f984c28be6903401f8748626679644c82e6de21b79a47eccd2359859658b0`.

The first run exposed an oversized GitHub commit-metadata response (observed progress reached 128492 bytes against the 65536-byte limit). Synchronous XHR abort masked this as `Cancelled`, preventing catalogue fallback. The corrected fixture used the bounded Git-ref request and settled size-limit errors before abort; the complete scenario then passed. The unmerged catalogue was unavailable on main, so bundled catalogue fallback was observed; real remote Channel bytes downloaded successfully. Successful live catalogue refresh awaits publication of the catalogue on main and is not claimed here.

Test fixture IPK SHA-256: `c5bc0bd7f080d620f2b8934e1f3083890d5e02f390bb860361b18f2805bb524a`. Installed manager, panel, transport, locale and catalogue file hashes matched the assembled fixture. Russian UI was tested; later Chinese empty-state translation corrections were checked in the localization suite. The temporary application and uploaded IPK were removed, and existing Home 0.4.0 reopened successfully. Actual Home routing, physical-remote input, sound, standby, cold boot, OTA, package rollback, LAN transfer and production profile restoration were not tested in this run. No private diagnostics or personal screenshots are included.

Follow-up verification: `bash scripts/test.sh tv preview`, the complete `npm run test:themes:browser` suite in both editions, Chromium 38 compatibility and all 339 UI strings across twelve languages passed. The installation/filter/removal and synchronous-abort regressions were observed failing before their fixes and passing afterward.

## Historical computer-hosted pull attempt — 2026-10-29

The requested direct transfer was attempted from macOS (exact OS version unknown), Node 23.11.0 and toolkit candidate 0.1.0-candidate.1 to the same maintainer test LG OLED55C3RLA, firmware 43.21.71 / webOS SDK 11.2.0. Root UI fixture `com.cleanyourtv.themeqa` 1.5.1 used an empty inventory and fixture-only direct bootstrap, with no services/startup hooks. It did not replace ordinary Home 0.4.0. Fixture IPK SHA-256: `9fd3cf5e6f6eefac58f93756e623f945323653591f0afe5527db79863fe88c33`. Installed manager/panel/transport/locale/catalogue hashes matched the assembled fixture. UI actions were driven through browser controls and the TV debugger; physical remote model/input were not tested.

Expected: PC Send to TV creates a compiled Channel snapshot; the TV receives it by private address/PIN, applies without a timer, and restores the cached theme after sharing stops. Observed on PC: the real preview dialog created a PIN and listed private interfaces; the loopback endpoint served Channel with the valid PIN (200), rejected an invalid PIN (404) and an unrelated web origin (403). New PIN invalidated the previous PIN; Stop sharing closed TCP 8879. These PC checks passed without mock transport.

Observed on TV: Settings → Appearance → Receive from computer opened, but both wrong- and correct-PIN requests failed at the network boundary. Neither is a device-level PIN validation result. Bounded HTTP attempts from the TV to both advertised PC interfaces also failed. Native macOS firewall queries confirmed block-all mode (state 2) and a blocked Node.js rule; private-interface self-connections were reset while loopback remained usable.

The maintainer authorized a temporary exception with restoration. Noninteractive elevation was unavailable; an administrator-authorized attempt then encountered the managed-Mac command-line restriction and did not apply the change. The maintainer also could not change the setting manually. Original global/block-all/Node rule readings were verified unchanged. No tunnel, disabled browser security or substituted transport was used to describe a direct LAN success.

Result for the former computer-hosted pull transport: receive/apply/cache restoration was **blocked by the computer's enforced incoming-connection policy**. The primary TV-hosted push transport below supersedes that attempt. No LAN theme was installed. All direct receiving, persistence, fresh-PIN receiving, interrupted transfer, expiry and quota/device matrices remain unaccepted. The PC share was stopped, its browser closed, the temporary TV application/upload removed, and ordinary Home 0.4.0 reopened. A full retry requires a sender computer with permitted inbound TCP 8879. No addresses, PINs, SSIDs, credentials, inventories or private screenshots are retained in this public record. This is scoped evidence, not release-package, routing, sound, standby, cold-boot, OTA or rollback acceptance.

## PC → TV push: primary author transfer

`theme-receiver/core.js` and `register.js` implement the same temporary receiver in both edition services. `scripts/theme_receiver.py` injects the canonical modules into each private package tree; source shims are never shipped with cross-package imports. No-root uses its existing `com.gathin.tvhome.renewal` service independently of renewal enablement; Root uses its own existing service. `themeReceiverStart/Status/Read/Stop` authenticate `ls2Message.applicationID()` against the owning Home app. No HTTP route exposes renewal, recovery or root runtime operations.

Root packaging embeds the canonical receiver closure into the existing `service.js` before private provisioning. No additional private recovery file or System Updater infrastructure path is required. Fresh receiver-enabled registrations store an explicit capability marker and grant only the four receiver methods to the owning Home app; legacy snapshots retain their original permission bytes. Pending repair, cancellation and both updater repair paths replay the recorded contract.

Updating the Home IPK alone does not add receiver support to an existing preserved private service or widen its LS2 permissions. Old registrations keep the receiver unavailable until supported explicit provisioning. This feature does not silently migrate a retained worker or registration. Validate the computer-assisted recovery/reinstallation and matching preparation on actual versioned artifacts before release; repeatedly replacing the UI package does not resolve a receiver-unavailable screen.

Opening Receive from computer creates one 10-minute session, a random service session ID and a six-digit PIN. Only private IPv4 addresses are advertised. HTTP POST `/v1/theme` on TV TCP 8879 requires `X-CYTV-PIN`, application/json, private/loopback local/peer addresses and exact local Host; browser Origin headers are rejected. Body cap is 10 MiB, request deadline 15 seconds, wrong-PIN cap 20; concurrent, malformed, oversized and expired uploads fail. Receipt returns 202 and closes the HTTP listener. That response confirms transport only, not validation/application.

The UI polls authenticated LS2 status and reads at most 48 KiB per base64 chunk, avoiding oversized bus replies. `ThemeManager.installEnvelope` uses the existing envelope, descriptor/rule/document/image hash and native decoding checks before writing IndexedDB. No author code executes. The optional store cancellation signal aborts an in-flight IndexedDB transaction; close, expiry, category change, app hiding and late start replies stop/invalidate sessions. The accepted active theme remains unchanged until explicit Apply, with no timer for this installed selection. Buffers/PINs are memory-only and bounded; stop or expiry releases them.

The computer's loopback preview endpoint `/theme-send` checks Host, Origin and a 4 KiB JSON request, compiles the selected snapshot and sends an outgoing Node HTTP POST. Destination validation allows only a literal RFC1918 IPv4 and fixed TV port, rejects URL/hostname/credentials and never follows redirects; deadline 20 seconds, response cap 64 KiB. The PC browser does not issue the network POST directly. Its primary dialog never starts a computer listener. CLI `send` follows the same path. No computer-hosted sharing server, `share` command or reverse-download form is provided.

[Scoped device acceptance](../history/2026-10-29-theme-push-acceptance.md) records successful direct PC → TV transport, actual receiver permissions/lifetime, validation, no-timer Apply, cache reload, cancellation/listener closure and removal on the maintainer C3 fixture. It does not establish a published package, unrooted-device compatibility, physical-remote input, OTA or rollback acceptance.

Root component and Home theme-engine versions are independent. Root packaging stamps `appinfo.themeEngineVersion` from the bundled Home renderer before replacing `appinfo.version` with the Root component number. ThemeManager validates this trusted local stamp when present and falls back to the normal Home version only when it is absent; malformed stamps fail closed. Thus Root 0.5.1 correctly accepts themes requiring Home engine 1.5.1 without bumping either component or accepting an author-supplied compatibility claim.

In the Appearance candidate, installed themes use preview cards with a separate selected badge and Apply/Remove controls. Showcase and Receive from computer are prominent entry actions; Add by URL, Restore Classic and Clear downloaded themes live under More options. Arrow navigation follows card/control geometry; Left at the edge returns to categories. Back to Home is the settings-wide exit. Hidden advanced controls are excluded from navigation.

Browser preview is identified by a marker injected exclusively by `preview/bridge.js`; packages do not inject this bridge. The receiver page explains TV-side setup without opening a listener. Physical TV startup failures offer Retry and Back; no other transfer direction is suggested. Subviews hide the unrelated Columns entry without changing its theme capability flag. Removal asks for confirmation; the UI resets Classic before deleting the active package, preserving the manager’s active-package deletion guard.

Catalogue refresh can render the bundled list before its network result. Each rebuild preserves the focused theme, Refresh or Back by stable identity and only restores focus if the theme pane owned it. A late result does not take focus from the settings footer. Deferred-response browser regressions cover both editions.


## Keyless short installation IDs (next candidate)

`ThemeData.shortLink` recognizes a bare 5–30 character da.gd ID or supported da.gd
URL. The field displays the normalized HTTPS URL before Load. `resolve` performs
one bounded 4 KiB plain-text request to the exact `da.gd/coshorten/ID` lookup endpoint;
exposed redirect destinations, nested shorteners and non-GitHub destinations are rejected. Normal
repository resolution and package integrity/version/image checks remain in place.
No JavaScript page/JSONP is loaded, and no Root LS2 permission changes are required.
The cached package retains its canonical GitHub source, so offline startup does
not depend on the shortener.

The author toolkit validates the public descriptor before creating a permanent
short URL, verifies the returned destination, and preserves the full URL on a
provider outage. Its pinned release workflow reads distributions as data and
updates only its owned note block using fresh release notes and the standard job
token. `tests/themes/short-links.cjs` covers target restrictions/cancellation and
`short-links-ui.cjs` covers ID hints and installation in both editions. A live
Chrome request resolved `102300a209`, fetched Channel 1.3.3 and verified all 12
files with descriptor digest `da7da0848ac0ecd60ebbcd964cb65a68fdf4fab54f30eebd56218c9d3141e17c`.
This is browser evidence, not physical-TV or published-app acceptance. The unpublished is.gd experiment is replaced rather than retained as a second ID namespace; full GitHub sources and PC-to-TV delivery are unchanged.


## Installed theme ribbon and Alpine inputs (next candidate)

Appearance keeps installed themes in one horizontal row, including on 720p screens.
The active identity **and digest** moves first; other installed versions keep their
relative order. Selection has its own tinted surface, border and filled badge;
keyboard focus remains a separate outline. Focus entering a card or one of its
actions scrolls the whole card into view without changing the active theme.
Showcase retains its separate catalog layout.

Alpine 1.4.4 uses a translucent scenic input sheet and a light-on-dark focus surface,
matching its shortcuts and library instead of the opaque Classic white selection.
The built-in descriptor and rules are regenerated from toolkit source
`95f812e505e81b1d4b706bd203f0e96306b1b18c`; hashed assets and license notices are unchanged.
The freshly exported candidate runtime requires Home/theme engine 1.6.0.

Earlier is.gd short-ID testing on the C3 candidate exposed a network/TLS
limitation: is.gd DNS agrees with the computer, IPv4 TCP connects but HTTPS does not
complete, and IPv6 is unavailable. Both is.gd and its www host were tested without
changing TV network settings or certificate validation. The same TV fetched the
pinned GitHub descriptor successfully; PC-to-TV delivery of Channel 1.3.3 passed.
This is a device/network observation, not proof of an is.gd service outage or of
a client-side fix. Use the full pinned GitHub URL or PC-to-TV transfer while this
path is unavailable. See the scoped [physical QA record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/141#issuecomment-6502701028).


The unpublished short-ID implementation now uses da.gd instead. On the same C3
and original network path, the new development data module resolved both
`102300a209` and `https://da.gd/102300a209`, loaded Channel 1.3.3 and verified all
12 files against the digest above. The installed application was not patched by
that module test. Signed-candidate UI acceptance remains separate.
