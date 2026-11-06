# 中文 / Languages / Sprachen / Idiomas / Langues / Lingue / 언어 / भाषाएँ / Języki / Языки

Choose your language to download an installer and follow the setup steps.
Each guide also explains the remote controls, emergency exit and where to get help.
Detailed technical references remain in English.

[Documentation](README.md) · [Requirements and known limits](COMPATIBILITY.md)

Guides are available in the languages below. The installer and TV language
preferences are independent; choose a language in each app. Downloads in the
guides always point to the latest published release.

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
| Čeština | `cs` | [Čeština](i18n/cs.md) |
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

<a id="czech-tv-interface-unreleased-candidate"></a>

## Czech support and published downloads

The source now includes **Čeština** (`cs`) throughout the desktop/console,
Android and Homebrew installers, as well as the TV interface. Automatic language
selection recognizes `cs` and `cs-CZ`; an explicit choice is saved. The console
accepts `--language cs`.

This addition needs a new published build; it does not change previously published
installers. If your downloaded installer does not list Čeština, use English and
follow the [Czech installation guide](i18n/cs.md). Homebrew installer availability
is tracked separately in its [technical guide](../homebrew/README.md).
Browser/catalog checks are not physical TV or phone acceptance; native-speaker
review remains outstanding.
