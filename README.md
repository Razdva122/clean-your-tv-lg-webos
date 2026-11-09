![Clean Your TV — for LG webOS](assets/brand/readme-logo.png#gh-light-mode-only)
![Clean Your TV — for LG webOS](assets/brand/readme-logo-dark.png#gh-dark-mode-only)

<a id="clean-your-tv--lg-webos"></a>
<a id="what-it-does"></a>
<a id="how-it-works"></a>

# Clean Your TV

A personal home screen for LG webOS: your apps, your order, and a configurable
dock, without sponsored rows in this launcher. It runs on the TV; your computer
can be switched off after setup. It does not remove advertisements from other
LG screens or obtain root access.

## Installation guide in your language

[English](docs/i18n/en.md) · [Deutsch](docs/i18n/de.md) · [Español](docs/i18n/es.md) ·
[Português (Brasil)](docs/i18n/pt-BR.md) · [Français](docs/i18n/fr.md) · [Italiano](docs/i18n/it.md) ·
[한국어](docs/i18n/ko.md) · [हिन्दी](docs/i18n/hi.md) · [Polski](docs/i18n/pl.md) ·
[Čeština](docs/i18n/cs.md) · [Русский](docs/i18n/ru.md) · [简体中文](docs/i18n/zh-Hans.md) · [繁體中文](docs/i18n/zh-Hant.md).

<a id="browser-preview"></a>

[Project website](https://razdva122.github.io/clean-your-tv-lg-webos/) ·
[Try the browser demo](https://razdva122.github.io/clean-your-tv-lg-webos/demo/) ·
[Installation guide](docs/INSTALL.md) · [Help and recovery](docs/RECOVERY.md)

![Classic menu with reference app icons](docs/launcher-classic.jpg)

*Classic, the default built-in theme, shown in the browser preview. Reference apps are not bundled; TV functions are simulated.*

## Themes

Choose built-in **Classic**, **Liquid Glass** or **Ribbon**, or install community themes.
Manage them in **Settings → Themes** on your TV.

| Classic menu | Liquid Glass | Ribbon |
| --- | --- | --- |
| <img src="docs/launcher-classic.jpg" alt="Classic menu browser preview" width="280"> | <img src="docs/launcher-liquid-glass.jpg" alt="Liquid Glass browser preview" width="280"> | <img src="docs/launcher-ribbon.jpg" alt="Ribbon with Black Hole video by Xecutioner — browser preview" width="280"> |

Ribbon wallpaper video: **Xecutioner** · non-commercial use with attribution.

Ribbon stays inside the single full-screen Home app, with its own wallpaper in both editions. It does not show another app or HDMI behind the cards. See [compatibility](docs/COMPATIBILITY.md) for the tested scope.

**[Try the themes in the main browser preview →](https://razdva122.github.io/clean-your-tv-lg-webos/demo/)**

Use the theme cards above the simulated TV to switch themes and compare layouts,
then choose Root or No-root to preview either edition. No TV connection or
installation is needed. See the [theme guide](docs/THEMES.md) for installation
and creating your own theme.

<a id="install-with-cytv"></a>
<a id="get-started"></a>

## Download and install

<!-- release:downloads -->
Current stable release: **[v1.15.0](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.15.0)** — [release notes](docs/RELEASE-1.15.0.md).
<!-- /release:downloads -->

[![Download Windows x64 graphical installer — GUI ZIP](assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Download macOS Apple Silicon graphical installer — ZIP](assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Download macOS Intel graphical installer — ZIP](assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Download Linux x64 graphical installer — DEB](assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Download Android ARM64 installer — APK](assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

1. Download the installer for your computer or an ARM64 Android phone. The buttons follow the latest published release.
2. Prepare TV access and choose No-root or Root in the wizard.
3. Install, then check Home, Back, normal controls and emergency exit before daily use.

**[Follow the installation guide →](docs/INSTALL.md)**

Windows: extract the whole ZIP before opening the app. macOS: choose Apple Silicon
or Intel to match your Mac. See [desktop instructions](docs/DESKTOP_INSTALL.md)
or [Android requirements](android/README.md) for platform details.

<a id="what-you-need"></a>

## Choose your edition

| Your TV setup | Edition |
| --- | --- |
| LG Developer Mode, without root | **No-root** — Home and the on-TV Home Helper. Keep Developer Mode active. |
| Existing root access and trusted root SSH | **Root** — native Home routing and independent recovery. Do not enable Developer Mode over root. |

Both use the same launcher. Compatibility depends on the model, firmware and
remote: [check requirements and known limits](docs/COMPATIBILITY.md) first.

<a id="remote-control-guide"></a>
<a id="resume-after-an-emergency-exit"></a>

## Everyday use

- **Home** opens your launcher while Home control is enabled.
- **Hold OK** on a tile to move or hide it; **+ / Add app** adds an installed app to the grid.
- **Press Home three times within two seconds** to stop Home control and return to LG Home. This does not erase settings.
- After an emergency exit, resume explicitly through **Home Helper** (No-root) or the Root activation control. Opening Home alone does not clear the stop.

[Remote controls](docs/CONTROLS.md) · [Arrange apps](docs/APP-MANAGEMENT.md) ·
[Update or remove](docs/MAINTENANCE.md)

<a id="candidate-install-root-from-the-tv"></a>
<a id="developer-mode-auto-renewal--beta"></a>

## Before you rely on it

- Test results are specific to devices and versions. Read [compatibility](docs/COMPATIBILITY.md); a successful install alone does not prove daily reliability.
- The original **1.3.0 Root updater cannot install 1.4.0 through OTA**. Keep recovery records and read [the update limitations](docs/UPDATES.md) before attempting that transition.
- No-root needs an active Developer Mode session. Automatic renewal is optional Beta; continue monitoring LG's official timer.
- The on-TV **Homebrew Installer is unreleased**. Use the published computer/Android installer; [candidate details](homebrew/README.md) are for coordinated testing.

<a id="languages"></a>
<a id="software-updates"></a>

## Guides and help

[All documentation](docs/README.md) · [Guides in your language](docs/LANGUAGES.md) ·
[Report a problem or a successful installation](docs/FEEDBACK.md)

If an AI agent helps with installation, it should prepare a short, redacted result
and ask your permission before posting an issue. See [instructions for agents](AGENTS.md#installation-results-and-user-consent).

<a id="no-root-source-installation"></a>
<a id="run-locally"></a>
<a id="project-layout"></a>

For contributors: [build and technical references](docs/development/README.md),
[contributing](CONTRIBUTING.md), and [release history and test evidence](docs/history/README.md).

<a id="current-components-and-hardware-evidence"></a>

<details>
<summary>Versions in the stable download</summary>

<!-- release:components -->
| Component | Stable version |
| --- | --- |
| cytv installer | 0.16.0 |
| Home | 1.14.0 |
| Home Helper | 0.8.0 |
| Root edition | 0.15.0 |
| Both edition Updaters | 0.5.6 |
| Android installer / versionCode | 0.15.0 / 30 |
<!-- /release:components -->

Candidate v1.15.0 fresh System Updater: 1.2.8 / protocol 1. Published v1.14.0 uses 1.2.7. Existing supervisors stay pinned; installed 1.1.2 has no general replacement path. See the [delivery limits](docs/RELEASE-1.13.0.md).

Historical System Updater in 1.7.0: 1.2.0 / protocol 1.
See the [1.7.0 release notes](docs/RELEASE-1.7.0.md)
and historical [1.5.0 TV acceptance and limits](docs/RELEASE-1.5.0.md).

</details>

<a id="credits"></a>

## Credits and license

Built on [OmkarK97/webos-vibehack](https://github.com/OmkarK97/webos-vibehack)
and [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv).
Not affiliated with LG. [MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md).
