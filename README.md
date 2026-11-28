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

*Classic in the browser preview, featuring [PlxNative](https://github.com/GLinnik21/plx-native) in the first slot. TV functions are simulated.*

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
Current stable release: **[v1.30.0](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.30.0)** — [release notes](docs/RELEASE-1.30.0.md).
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

## Also for LG webOS

Watch movies and shows from your Plex library on your LG TV with
**PlxNative**, an unofficial Plex client with a responsive native
interface and 4K Dolby Vision playback on compatible TVs.

[Explore PlxNative →](https://github.com/GLinnik21/plx-native)

<a id="candidate-install-root-from-the-tv"></a>
<a id="developer-mode-auto-renewal--beta"></a>

## Before you rely on it

- Test results are specific to devices and versions. Read [compatibility](docs/COMPATIBILITY.md); a successful install alone does not prove daily reliability.
- The original **1.3.0 Root updater cannot install 1.4.0 through OTA**. Keep recovery records and read [the update limitations](docs/UPDATES.md) before attempting that transition.
- No-root needs an active Developer Mode session. Automatic renewal is optional; continue monitoring LG's official timer.
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
| cytv installer | 0.25.0 |
| Home | 1.23.0 |
| Home Helper | 0.11.1 |
| Root edition | 0.26.0 |
| Both edition Updaters | 0.6.9 |
| Android installer / versionCode | 0.23.4 / 57 |
<!-- /release:components -->

v1.15.0 fresh System Updater: 1.2.8 / protocol 1. v1.14.0 used 1.2.7. Existing supervisors stay pinned; installed 1.1.2 has no general replacement path. See the [delivery limits](docs/RELEASE-1.13.0.md).

Historical System Updater in 1.7.0: 1.2.0 / protocol 1.
See the [1.7.0 release notes](docs/RELEASE-1.7.0.md)
and historical [1.5.0 TV acceptance and limits](docs/RELEASE-1.5.0.md).

</details>

<!-- compatibility:readme -->
<details>
<summary>TV test results by webOS</summary>

✅ Home button verified · ❔ Partial or unconfirmed

<details>
<summary>❔ webOS 1</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ❔ | 32LB650V-ZN · No-root | 1.4.0 |
| ❔ | 55LB652V-ZA · No-root | 1.4.0-2536 |

</details>

<details>
<summary>❔ webOS 3</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ❔ | 49UJ651V-ZA · No-root | 3.5 |
| ❔ | 49UJ750V · No-root | 3.5 |
| ❔ | 60UJ6050-UA · No-root | SDK 3.9.0 |

</details>

<details>
<summary>✅ webOS 4</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ✅ | 55SK8100PLA · No-root | 4; SDK 4.4.0 |
| ✅ | 55UK7500PSA · No-root | SDK 4.4.0 |
| ✅ | UK6400PLF · No-root | 4.x |

</details>

<details>
<summary>✅ webOS 4.5–5</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ✅ | UM7450PLA · No-root | 4.5 |
| ❔ | 43UM7600PLB · No-root | 4.5 |
| ❔ | 49NANO80PNA · No-root | SDK 5.6.2 |
| ❔ | 55NANO81ANA · No-root | 5.6.2-21 |
| ❔ | 55UM7450PLA · No-root | SDK 4.10.0 |
| ❔ | 65UM7470PSA · No-root | 4.5 (build 4.10.2-29) |
| ❔ | LM6370PSB · No-root | 4.5 |
| ❔ | OLED55C9PLA · No-root | 4.5 / SDK 4.9.0 |

</details>

<details>
<summary>✅ webOS 6</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ✅ | 50NANO756PA · No-root | 6; SDK 6.5.3 |
| ✅ | OLED55B19LA · No-root | 6; SDK 6.5.3 |
| ✅ | OLED65C1PSA · Root | SDK 6.5.3 |
| ✅ | OLED65C11LB · Root | SDK 6.5.3 |
| ✅ | OLED65G19LA · No-root | SDK 6.5.3 |
| ✅ | OLED77C12LA · No-root | SDK 6.5.3 |
| ❔ | 43UP751C0ZF · No-root | SDK 6.5.3 |
| ❔ | 55UP7000PUA · No-root | 6.2.1 |
| ❔ | OLED55C11LB · No-root | 6.0 |
| ❔ | OLED55C14LB · No-root | 6 |

</details>

<details>
<summary>✅ webOS 22</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ✅ | OLED65C2AUA · Root | 22; SDK 7.4.0 |
| ❔ | 43NANO766QA · No-root | 22 |
| ❔ | 43UQ75003LF · No-root | 7.6.0 |
| ❔ | 55UQ7400PSF · No-root | 22 |

</details>

<details>
<summary>✅ webOS 24</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ✅ | OLED55G36LA · No-root | SDK 9.2.2 |
| ✅ | OLED65C27LA · Root | 9.2.1-2617 |
| ❔ | OLED55C37LA · Root | 24; SDK 9.2.1 |

</details>

<details>
<summary>✅ webOS 25</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ✅ | 50NANO80ASA · No-root | 25; SDK10.3.2 |
| ✅ | 55UR91006LA · No-root | SDK10.3.2 |
| ✅ | OLED42C24LA · No-root | 10.3.1 |
| ✅ | OLED55B36LA · No-root | SDK 10.3.2 |
| ✅ | OLED55C47LA · No-root | SDK 10.3.1 |
| ✅ | QNED75URA · No-root | 25 / SDK 10.3.2 |
| ❔ | 65QNED80SRA · No-root | 25; 10.3.2-33 reported |
| ❔ | 65QNED80TSA · No-root | SDK 10.3.2 |
| ❔ | 75NANO80TSA · No-root | 25; SDK 10.3.2 |
| ❔ | OLED42C2PSA · Root | 10.3.1-3006 (SDK 10.3.1) |
| ❔ | OLED48B46LA · Root | SDK 10.3.2 |
| ❔ | OLED55C2PUA · No-root | 10.3.1 / build 3006 |
| ❔ | OLED55C46LA · Root | 10.3.1 |

</details>

<details>
<summary>✅ webOS 26</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ✅ | OLED42C24LA · No-root | SDK 11.2.0 |
| ✅ | OLED55C3RLA · Root | SDK11.2.0 |
| ✅ | OLED77C34LA · No-root | SDK 11.2.0 |
| ✅ | OLED83G36LA · No-root | SDK 11.2.0 |
| ❔ | LG C3 · No-root | 26 |
| ❔ | OLED48C24LA · No-root | SDK 11.2.0 |
| ❔ | OLED55C5ELB · No-root | 26 |
| ❔ | OLED55C35LA · No-root | 26 (build 11.2.0-3711) |
| ❔ | OLED65C5PUA · No-root | 26; SDK 11.2.0-3706 |
| ❔ | OLED65C57LA · No-root | SDK 11.2.0 |
| ❔ | OLED65G39LA · Root | 26 / SDK 11.2.0 |
| ❔ | OLED77G5RLA · Root | SDK 11.2.0 |

</details>

<details>
<summary>❔ Version not reported</summary>

| Home | TV · Edition | Reported webOS |
| :---: | --- | --- |
| ❔ | LG C5 77″ · No-root | Not reported |
| ❔ | OLED48C55LA · No-root | Not reported |
| ❔ | OLED55C16LA · No-root | Not reported |
| ❔ | OLED55G59LS · No-root | Not reported |
| ❔ | OLED65C2PUA · No-root | Not reported |
| ❔ | OLED65C3LA · No-root | Not reported |
| ❔ | OLED65C3PUA · No-root | Not reported |
| ❔ | UN70006LA · No-root | Not reported |

</details>

[Test details and sources](docs/COMPATIBILITY.md#user-reported-working-tvs)

</details>
<!-- /compatibility:readme -->

<a id="credits"></a>

## Credits and license

Built on [OmkarK97/webos-vibehack](https://github.com/OmkarK97/webos-vibehack)
and [Gathin23/cleanyourtv](https://github.com/Gathin23/cleanyourtv).
Not affiliated with LG. [MIT license](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md).
