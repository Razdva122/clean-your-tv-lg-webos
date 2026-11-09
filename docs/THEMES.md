# Choose and install themes

Theme support is included in Home 1.6.0 / release 1.5.0. The separate Themes category, ID-focused form and inline language selection ship in 1.5.4. Older packages do not gain the feature by copying a theme link. Fixed-layout Apply geometry has browser coverage; exact installed Appearance acceptance remains pending. Root Home can remain disabled after update/rollback, Settings can retain stale status after emergency/resume, and the earlier different-session standby failure remains unresolved. See [1.5.4 scope and limitations](RELEASE-1.5.4.md).

Authors: [suggest your theme](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new?template=theme-submission.yml) with a public link and license information. Maintainers handle catalogue integration and review. The [author walkthrough](development/CONTRIBUTING-THEMES.md) is optional for building and packaging it yourself.

<a id="included-with-the-unpublished-candidate"></a>

## Included with 1.7.0

Version 1.7.0 includes **Classic**, **Liquid Glass** and **Ribbon** in both editions, available offline. Classic remains the initial default and uses the header Inputs menu. Liquid Glass uses an input shelf; placement belongs to the selected theme, with no global placement switch. Live previews default on; an explicitly saved Off remains off. Disable **Settings → Appearance → Preview inputs on focus** to turn them off. They apply only to connected HDMI tiles in a shelf theme. HDMI previews may play sound or switch HDR on some TVs; silence is not guaranteed. Home does not automatically change global TV mute or HDR settings.

Version 1.6.0 instead includes Classic, Alpine and Ribbon. In 1.7.0, **Alpine 1.4.4** is available through Theme showcase. A saved `builtin:alpine` selection falls back to Classic with the visible recovery notice; it does not trigger a download or silently select Liquid Glass. Downloaded Alpine retains its mountain panorama, clock and fixed ribbon layout; its fixed layout hides Columns and preserves your adjustable-theme choice.

1.5.4: when a fixed-layout theme hides Columns, its empty row keeps the same space so applying the theme does not shorten Appearance’s scroll range. The hidden control is skipped by pointer, keyboard and accessibility navigation. This correction has browser regression coverage; physical-TV acceptance is pending.

Channel and Itachi are retired from the active candidate catalog. Existing installed copies and historical packages remain available; removing an installed retired theme does not make it reappear in the current showcase. Published stable catalog availability follows its own release.

## Change to an included theme

1. Open Home, select **Settings → Themes**. The Themes pane itself contains preview cards for built-in and all downloaded themes, alongside the settings categories. Personal themes use their saved package preview, including offline and without a showcase listing. The separate Theme showcase button opens the published catalogue.
2. In 1.7.0, choose **Classic**, **Liquid Glass** or **Ribbon** in the installed list. The choice applies and saves immediately, without a confirmation timer. Downloaded themes in this list work the same way.
3. Return with **Back**, then **Back to Home**.

The accepted choice is restored on the next launch. Only **Try theme** inside **Theme showcase** starts a 20-second trial, after downloading a new theme. If Home closes during an unconfirmed showcase trial, the next launch starts Classic. Changing appearance does not replace your app order, hidden apps, inputs or Home-button routing. Settings, confirmations and recovery keep their standard appearance.

## Browse themes on TV

Open **Settings → Themes → Theme showcase**. Choose a miniature preview to see the theme's details. Only themes not installed on this TV appear here. The 1.7.0 built-ins Classic, Liquid Glass and Ribbon, and installed personal themes are hidden by identity, including when the catalogue has a newer version. Available external themes offer **Download theme**, then **Try theme**. After removal, an active catalog entry returns to Showcase. Choose **Remove** on a downloaded theme and confirm. Removing the active theme restores Classic before deleting its files. Built-in themes cannot be removed. Use **Add by ID** or **Receive from computer** to update a hidden installed theme. Confirm **Keep theme** within 20 seconds. Downloading alone never changes Home.

Opening Theme showcase or choosing Refresh checks the main project repository for reviewed catalogue updates without updating Home or reloading the page. After a normal merge, new entries become available; an unmerged candidate may still show the bundled fallback. Offline or failed requests use bundled previews and entries. Online catalogue data and previews come from one exact project commit resolved through GitHub; downloading an external theme needs Internet access. A downloaded exact version is reused instead of fetched again. Theme files come from the recorded, commit-pinned source repository. Refreshing never installs a theme or changes the current selection. The scoped device check is recorded in [theme push acceptance](history/2026-10-29-theme-push-acceptance.md); complete release-package acceptance remains separate.

## Transfer a theme from your computer

Use matching Home and service packages from a complete supported release (1.8.2 or later for the current wallpaper flow). On an existing Root installation, updating the Home UI alone does not update its preserved private service; see the [provisioning requirements](development/TV-THEMES.md#pc--tv-push-primary-author-transfer). No Showcase submission, public repository or source commit is required for a local development test. The primary direction is **PC → TV**: the TV temporarily accepts the compiled theme; the computer makes an outgoing connection.

1. On TV open **Settings → Themes → Receive from computer**. Keep the pane open; it shows the **TV address**, six-digit PIN and expiry time.
2. On the computer run your theme in the author toolkit's **preview** or **showcase**, select it and press **Send to TV**.
3. Enter the address and PIN **from the TV** into the computer dialog, then choose **Send theme**. Enter just the private IPv4 address, without a URL or port.
4. After the TV verifies the received package, choose **Apply theme**. It saves immediately, without a 20-second timer. The computer's Sent status means transport completed; finish installation/application on TV.
5. Edit your theme on the computer as needed. For another snapshot, reopen Receive from computer on TV and send with its new PIN. Saving a file alone does not alter the TV copy.

Both devices must be on the same trusted home network. The receiver uses local HTTP and TCP **8879 on the TV**. No incoming computer port or Mac firewall exception is needed. Guest-network/client isolation can still prevent a connection. Only compiled theme data is accepted; the existing descriptor/hash/image/cache checks run before offering Apply. The PIN is not persisted. This is a temporary local transfer, not a cloud upload or automatic live editing.

The receiver closes after one upload, cancellation, leaving the pane, ten minutes, or too many invalid PIN attempts. Closing before a transfer completes cancels that session. Installed copies remain usable offline after the receiver closes or the computer turns off.

CLI alternative from the toolkit (use the values currently shown on TV):

```sh
npm run theme -- send ./my-theme --runtime .runtime/candidate --tv TV_PRIVATE_IPV4 --pin SIX_DIGIT_PIN
```

PC → TV is the only computer transfer direction; the computer does not host a download server. Published 1.8.2 has a known Root receiver LS2 refusal ([#337](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/337)), deferred from this candidate. If the receiver is refused, retain diagnostics; do not treat a matching UI update or repeated transfer as a fix. Other version mismatches require a supported complete Home/service update.

## Install a published theme by ID or link

In **Settings → Themes → Add by ID**, enter an ID such as `102300a209`,
`da.gd/102300a209`, `https://da.gd/102300a209`, or a supported full GitHub URL.
The field shows the expanded da.gd address before Load. Home uses the bounded
da.gd plain-text lookup API and then validates the returned GitHub destination; it does
not execute a shortener page or accept arbitrary hosts. Select the found theme
before downloading. Short links install published packages, not local PC files.

Authors can copy the ID from **TV link → Copy ID** in the toolkit preview or from
the theme's GitHub release notes. Creating links uses no da.gd account or API key.
If the service is unavailable, use the original full GitHub descriptor URL.

## Add another repository by URL

1. Browse themes in the [main browser preview](https://razdva122.github.io/clean-your-tv-lg-webos/) using the cards above Home. To install on the TV, use the on-TV Theme showcase, or copy the exact commit-pinned descriptor URL from the reviewed theme repository and enter it with the TV keyboard. Computer transfer above is the easier path for unpublished local work.
2. On TV, open **Settings → Themes → Add by ID**. Focus **Theme ID** and use OK/native keyboard to type or paste. Move to **Load** and select it.
3. Choose the returned theme. For a repository containing several themes, choose the specific entry; the installer does not select one silently. The download progress is shown. Cancel or Back stops the request.
4. After validation/saving, choose the new **Downloaded** version in Themes. Review its author/license and select it to apply and save immediately, without a timer.

Supported inputs are a public `https://github.com/OWNER/REPOSITORY` (collection index or single descriptor at its root) or an exact commit-pinned raw GitHub descriptor/collection URL. The showcase provides the second form. Private repositories, credentials, arbitrary hosts, moving raw URLs and install scripts are not accepted. Several themes may share one repository.

The installer verifies API/Home version, rule/asset limits, file sizes and SHA-256, image dimensions and actual decode. A failed download, incompatible theme or insufficient storage does not replace the current accepted theme. Source verification checks integrity, not author trust; prefer reviewed sources and inspect the supplied credits/license.

## Offline use, update and removal

After a successful install, files are stored in this Home application's IndexedDB cache. A normal restart does not contact the author. The TV still needs network access for apps and services that require it; the theme itself can be restored offline.

To update, install a new reviewed catalogue version, use a new version's link, or transfer a fresh development snapshot; select the installed version, or try and keep it through showcase. Updates are explicit: installed themes do not follow GitHub branches automatically. Several versions may be cached independently. Select **Remove** beside a downloaded version and confirm. Removing the active version restores Classic before its files are deleted; cancellation keeps the theme.

The published 1.8.2 cache is bounded at eight downloaded versions and 64 MiB of payload data, subject to a lower device quota. Remove inactive versions if saving fails. Downloaded themes are removed individually with confirmation; removing the active theme restores Classic first. Built-ins cannot be removed.

## Recovery

Open **Settings → Themes** and choose the **Classic** card to restore Classic immediately. An interrupted trial/startup or invalid accepted theme also returns to Classic on the next launch. The downloaded library is retained unless you clear it. Use the existing emergency Home exit/recovery instructions if Home itself cannot be opened; theme recovery does not change that emergency mechanism.

Theme images/choice are not included in legacy profile backup/export. A legacy profile restore resets the accepted theme to Classic; downloaded packages remain available for reselection if app storage is intact. A System update profile restore preserves the existing app-origin theme choice and Columns preference instead of treating their absence from the snapshot as a reset. Normal startup still validates that choice and its cached files; an interrupted trial, invalid choice or missing package falls back to Classic. Removing the application or resetting app data may erase its cache. Device storage behavior across updates, standby and cold boot still requires hardware acceptance.

## If something goes wrong

| Problem | Action |
| --- | --- |
| No Themes entry | This Home package predates the theme-enabled Home 1.6.0. |
| Link rejected | Copy the pinned raw descriptor from showcase, or use a public repository root with the documented index. |
| Download/network error | Check connectivity and source availability; GitHub API rate limits, CORS or old TV TLS can block access. Built-ins remain usable. |
| Hash/image/API error | Keep the accepted theme; ask the author for a new valid distribution. Do not disable verification. |
| Storage error | Remove inactive downloaded versions, or restore Classic and clear the theme cache. |
| New theme is unreadable | During a showcase trial, use Revert/Back or wait 20 seconds. For an installed choice, open Themes and select Classic or Restore Classic. An interrupted trial/startup recovers to Classic on relaunch. |

## Create a theme and preview on a computer

Start with the [tested toolkit candidate and bundled runtime](https://github.com/Razdva122/clean-your-tv-lg-theme/blob/48a7594c872794229801f0a6495952d3733a3f99/docs/CANDIDATE.md). Use [the author toolkit](https://github.com/Razdva122/clean-your-tv-lg-theme) and its [author walkthrough](https://github.com/Razdva122/clean-your-tv-lg-theme/blob/48a7594c872794229801f0a6495952d3733a3f99/docs/tutorial.md). The toolkit's local showcase is an author preview, separate from on-TV installed selection. Apps/services are simulated; it does not establish TV compatibility. See [submission rules](../showcase/README.md) to request a public listing. Personal installation does not require a showcase PR.

From the main checkout, build the primary preview website into a fresh directory:

```sh
python3 scripts/preview.py --build build/theme-site
python3 -m http.server 8878 --bind 127.0.0.1 --directory build/theme-site
```

Open **http://127.0.0.1:8878/** to exercise Home/Settings and switch themes with the cards above the simulated TV. Browser storage is separate from your TV. Developer details: [TV theme lifecycle](development/TV-THEMES.md), [CSS API](development/THEME-CSS.md), [development status](development/THEMES.md).


<a id="parameterized-ribbons-unreleased"></a>

## Parameterized ribbons

**Ribbon is bundled in 1.7.0** in both editions, alongside Classic and Liquid Glass. Update Home, then select Ribbon in **Settings → Themes**; no theme download or network connection is needed. Classic remains the default. Bundled Ribbon cannot be removed or replaced through downloaded-theme controls.

Themes can optionally configure the existing scenic ribbon's card sizes, spacing, skew, focused-card lift, captions and clock visibility. The theme chooses whether compact Inputs, Wi-Fi and Settings shortcuts appear at bottom left. With shortcut edge navigation, Left from the first visible application selects Settings, then Wi-Fi and Inputs; Right from Settings returns to that same visible edge. Themes without these options retain their previous appearance and controls.

These themes require the `ribbon-layout-v1` capability in Home. On a theme-enabled Home without this capability, both Add by ID and Receive from computer reject the new descriptor before saving/applying it: your current theme and saved selection stay unchanged. Exact error text depends on the installed version and may report an unsupported capability/API. Update Home and retry. A theme package does not upgrade Home. If you downgrade Home after already selecting an unsupported theme, startup recovery can restore Classic; that differs from a rejected new installation.

This support is included in 1.7.0. Browser checks do not establish physical-TV compatibility; see the [release acceptance and limits](RELEASE-1.7.0.md). See the [author contract](development/THEME-CSS.md#parameterized-scenic-ribbons-unreleased).

<a id="ribbon-over-applications-unreleased"></a>

## Ribbon in full-screen Home (1.8.2)

Ribbon is a theme of the existing Home application in both editions. Home uses
an ordinary full-screen card window, with its own wallpaper. There is no second
application and no video or HDMI displayed beneath the cards. Selecting Ribbon
does not change the native window type or Home routing.

A single black block groups the three shortcuts. Native solid app colors fill
the skewed cards, with a focused lift and bottom-local shade against the Home
wallpaper. Hold OK to edit one raised card; left/right moves it, Up selects its
cross, Down returns to the card, OK confirms and Back cancels. The cross hides
the app from Home and Undo restores it. Editing/hiding retains the selected
Home background and shows no explanatory footer.

Home opens or reactivates the ordinary Home window. Menus, settings, input-shelf
navigation and editors retain their normal Back handling; Home is not a
transient bar dismissed by another Home press. Selecting an application uses
normal TV app switching rather than forcing the Home window to close.

Wallpaper video and connected-input previews belong to Home. Hidden or unfocused
Home releases its media; unavailable playback retains the static poster. This
is not playback of a different app or HDMI underneath Ribbon. Existing Helper
emergency/watchdog, key-up handling, Root recovery and startup-source choices
remain separate from theme selection.

The previous overlay experiment is not the current Home contract. Published
1.8.2 has [limited exact-package observations](RELEASE-1.8.2.md); these do not accept
new candidate artifacts or other TVs. Verify the exact versioned packages
for launch latency, repeated Home, app switching, background playback, editing,
standby/wake and emergency/update/rollback behavior before release. See the
[presentation design](development/RIBBON-PRESENTATION.md).

## Storage estimates in candidate builds

Theme installation reports required, available and missing MiB for TV app
storage and its independent **64 MiB** theme-cache allowance. The separate
**8 themes** count limit asks you to remove a downloaded theme. Personal video
wallpapers also need computer temporary space and TV video-cache space.
See [storage estimates and recovery limits](DESKTOP_INSTALL.md#storage-estimates-in-candidate-builds)
for calculation reserves, unavailable quota readings and pending-install recovery.

## Weather integration

See the [shared weather contract](development/WEATHER.md) for supported formats, developer styling, preset reservations, compatibility and maintainer fork provenance. Home owns weather data and settings; themes contain no provider code.

## Weather

In the unpublished candidate, open **Settings → Weather** after Wallpapers.
Weather starts off. Turn it on, choose a city manually or explicitly request
approximate automatic location, then choose units and an available format.
Automatic lookup uses the network's approximate location; correct the city
manually if needed. Choose **Auto**, **MET Norway** or **Open-Meteo** as the
forecast provider. Auto starts with MET Norway, tries Open-Meteo once on failure,
then reuses the last successful source and its cache. A manually selected source
never switches providers automatically. New settings use Auto; saved settings
without a provider keep Open-Meteo. The actual source appears in settings. No
provider API key is required. Open **Data sources** in the Weather heading for
attribution. Weather and location preferences stay
local and are not included in legacy profile exports.

Classic and compatible downloaded themes support Compact, Now, In detail and
4 days. Liquid Glass supports Compact; Ribbon and Atmosphere hide weather; Ribbon sends no
weather requests. A theme can hide weather before the header when space is
limited. Offline data expires after six hours; unavailable weather does not
block Home. MET Norway refreshes no more often than every three hours. Missing
optional fields are hidden; MET does not supply feels-like temperature or
precipitation probability. Its daily ranges summarize forecast points, not
observed daily extremes. Provider availability depends on your network.

Forecast requests send the selected coordinates to `api.met.no` or
`api.open-meteo.com`. City search uses `geocoding-api.open-meteo.com`; optional
automatic location uses `get.geojs.io` and your public IP address. MET Norway
data is credited to the Norwegian Meteorological Institute (CC BY 4.0); provider
terms and other credits are available in Data sources. See
[weather implementation and limits](development/WEATHER.md)
and [candidate release notes](RELEASE-1.15.0.md).
