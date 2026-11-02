# 中文 / Languages / Sprachen / Idiomas / Langues / Lingue / 언어 / भाषाएँ / Języki / Языки

Choose a complete user guide for installation, everyday controls, recovery,
updates and removal. Technical/developer references remain in English and are
linked at the end of each guide.

[Documentation](README.md) · [Requirements and known limits](COMPATIBILITY.md)

The published installer and TV interface offer these twelve languages. Technical
references remain in English. Localized guides describe the current user flow;
unpublished paths are identified separately.

| Language | Code | User guide |
| --- | --- | --- |
| English | `en` | [English](i18n/en.md) |
| Deutsch | `de` | [Deutsch](i18n/de.md) |
| Español | `es` | [Español](i18n/es.md) |
| Português (Brasil) | `pt-BR` | [Português (Brasil)](i18n/pt-BR.md) |
| Français | `fr` | [Français](i18n/fr.md) |
| Italiano | `it` | [Italiano](i18n/it.md) |
| 한국어 | `ko` | [한국어](i18n/ko.md) |
| हिन्दी | `hi` | [हिन्दी](i18n/hi.md) |
| Polski | `pl` | [Polski](i18n/pl.md) |
| Русский | `ru` | [Русский](i18n/ru.md) |
| 简体中文 | `zh-Hans` | [简体中文](i18n/zh-Hans.md) |
| 繁體中文 | `zh-Hant` | [繁體中文](i18n/zh-Hant.md) |

The installer starts with the computer's language; the TV interface starts with
the TV's language. Each offers a saved language choice and an automatic/system
option. These preferences are independent. CLI examples use `--language CODE`;
application identifiers, file names and command verbs are not translated.

[Project overview](../README.md) · [Desktop packages](DESKTOP_INSTALL.md) · [CLI reference](CLI.md)

For Chinese, an explicit Hans/Hant script takes precedence over the region.
Bare `zh`, CN and SG use Simplified; TW, HK and MO use Traditional. You can
override the automatic result in the existing language picker. Chinese TV
rendering remains subject to the recorded device-specific acceptance limits.

## Czech TV interface (unreleased candidate)

Issue [#211](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/211)
adds **Čeština** (`cs`) to Home and Root Home, their Settings, themes,
HDMI recovery and independent updater/recovery interfaces. On the TV choose
**Settings → Language → Čeština**; automatic mode recognizes `cs` and `cs-CZ`.
The preference is saved separately from the installer language and is preserved
by the candidate's profile/update validators. Application names and technical
identifiers stay unchanged.

[Český průvodce rozhraním TV](i18n/cs.md) covers the candidate interface.
Desktop, console, Android and Homebrew installers still offer the twelve
published languages above; `--language cs` is not an installer option.
Physical-TV and native-speaker review remain unverified; public delivery is
pending the normal candidate build, acceptance and release.
