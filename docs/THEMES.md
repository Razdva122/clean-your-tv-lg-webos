# Choose and install themes

Theme support is included in Home 1.6.0 / release 1.5.0. The separate Themes category, ID-focused form and inline language selection ship in 1.5.3. Older packages do not gain the feature by copying a theme link. Fixed-layout Apply geometry has browser coverage; exact installed Appearance acceptance remains pending. Root Home can remain disabled after update/rollback, Settings can retain stale status after emergency/resume, and the earlier different-session standby failure remains unresolved. See [1.5.3 scope and limitations](RELEASE-1.5.3.md).

Authors: follow the [complete theme contribution walkthrough](development/CONTRIBUTING-THEMES.md) to create a theme, preview it on PC, test it on TV and submit it to Showcase.

## Included with Home

**Classic**, **Alpine** and **Ribbon** are built into both No-root and Root editions. They work without downloading a theme. Classic remains the initial default. Alpine has a mountain panorama, a large clock and one looping horizontal app ribbon. Its fixed eight-slot composition hides the Columns setting while active. Your saved column preference returns when you switch to an adjustable theme.

1.5.3: when a fixed-layout theme hides Columns, its empty row keeps the same space so applying the theme does not shorten Appearance’s scroll range. The hidden control is skipped by pointer, keyboard and accessibility navigation. This correction has browser regression coverage; physical-TV acceptance is pending.

**Channel** is an ordinary external theme in showcase. It is not part of the TV package. It uses a numbered list, selected-app artwork and pixel shortcut icons; its one-column default can be overridden by the user.

## Change to an included theme

1. Open Home, select **Settings → Themes**. The Themes pane itself contains preview cards for built-in and all downloaded themes, alongside the settings categories. Personal themes use their saved package preview, including offline and without a showcase listing. The separate Theme showcase button opens the published catalogue.
2. Choose **Classic**, **Alpine** or **Ribbon** in the installed list. The choice applies and saves immediately, without a confirmation timer. Downloaded themes in this list work the same way.
3. Return with **Back**, then **Back to Home**.

The accepted choice is restored on the next launch. Only **Try theme** inside **Theme showcase** starts a 20-second trial, after downloading a new theme. If Home closes during an unconfirmed showcase trial, the next launch starts Classic. Changing appearance does not replace your app order, hidden apps, inputs or Home-button routing. Settings, confirmations and recovery keep their standard appearance.

## Browse themes on TV

Open **Settings → Themes → Theme showcase**. Choose a miniature preview to see the theme's details. Only themes not installed on this TV appear here. Classic, Alpine and installed personal themes are hidden by identity, including when the catalogue has a newer version. Channel offers **Download theme**, then **Try theme**. After removal it returns to Showcase. Choose **Remove** on a downloaded theme and confirm. Removing the active theme restores Classic before deleting its files. Built-in themes cannot be removed. Use **Add by ID** or **Receive from computer** to update a hidden installed theme. Confirm **Keep theme** within 20 seconds. Downloading alone never changes Home.

Opening Theme showcase or choosing Refresh checks the main project repository for reviewed catalogue updates without updating Home or reloading the page. After a normal merge, new entries become available; an unmerged candidate may still show the bundled fallback. Offline or failed requests use bundled previews and entries. Online catalogue data and previews come from one exact project commit resolved through GitHub; downloading an external theme needs Internet access. A downloaded exact version is reused instead of fetched again. Theme files come from the recorded, commit-pinned source repository. Refreshing never installs a theme or changes the current selection. The scoped device check is recorded in [theme push acceptance](history/2026-10-29-theme-push-acceptance.md); complete release-package acceptance remains separate.

## Transfer a theme from your computer

Use matching Home and service packages from release 1.5.0. On an existing Root installation, updating the Home UI alone does not update its preserved private service; see the [provisioning requirements](development/TV-THEMES.md#pc--tv-push-primary-author-transfer). No Showcase submission, public repository or source commit is required for a local development test. The primary direction is **PC → TV**: the TV temporarily accepts the compiled theme; the computer makes an outgoing connection.

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

PC → TV is the only computer transfer direction. If the receiver is unavailable, update the matching Home and service set on TV and retry; the computer does not host a download server.

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

The cache is bounded at eight downloaded versions and 24 MiB of payload data, subject to a lower device quota. Remove inactive versions if saving fails. Downloaded themes are removed individually with confirmation; removing the active theme restores Classic first. Built-ins cannot be removed.

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

Open **http://127.0.0.1:8878/** to exercise Home/Settings and switch themes with the cards above the simulated TV. Browser storage is separate from your TV. Developer details: [TV theme lifecycle](development/TV-THEMES.md), [CSS API](development/THEME-CSS.md), [candidate status](development/THEMES.md).


## Parameterized ribbons (unreleased)

**Ribbon is bundled by this unreleased candidate** in both editions, alongside Classic and Alpine. Update Home, then select Ribbon in Settings → Appearance; no theme download or network connection is needed. Classic remains the default. Bundled Ribbon cannot be removed or replaced through downloaded-theme controls.

Themes can optionally configure the existing scenic ribbon's card sizes, spacing, skew, focused-card lift, captions and clock visibility. The theme chooses whether compact Inputs, Wi-Fi and Settings shortcuts appear at bottom left. With shortcut edge navigation, Left from the first visible application selects Settings, then Wi-Fi and Inputs; Right from Settings returns to that same visible edge. Themes without these options retain their previous appearance and controls.

These themes require the `ribbon-layout-v1` capability in Home. On a theme-enabled Home without this capability, both Add by ID and Receive from computer reject the new descriptor before saving/applying it: your current theme and saved selection stay unchanged. Exact error text depends on the installed version and may report an unsupported capability/API. Update Home and retry. A theme package does not upgrade Home. If you downgrade Home after already selecting an unsupported theme, startup recovery can restore Classic; that differs from a rejected new installation.

This support is under review. Browser checks do not establish physical-TV compatibility or public availability. See the [author contract](development/THEME-CSS.md#parameterized-scenic-ribbons-unreleased).
