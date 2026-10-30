# LG webOS competitor features and user problem history

Snapshot: **25 October 2026**, approximately **18:49 UTC / 23:49 Asia/Yekaterinburg**.

Clean Your TV has a distinctive entry point: a shared installer and Home interface
for both Developer Mode and existing-root users. Luma concentrates on a native
launcher and its lifecycle. Lumen offers a richer ambient and personalisation
experience. Glasshouse extends into device administration, privacy, OLED care
and smart-home integration. CYTV's largest visible feature gaps are app
organisation/search, recent-app management, personalisation and quick controls;
the most consequential engineering lessons concern Home lifecycle, permissions,
startup sequencing and recovery.

## Products and publication baseline

The requested “glassnode” is interpreted as **Glasshouse**, the rooted webOS
dashboard. This identity fits the LG TV context; the original spelling alone
does not establish the user's intended project.

| Product | Exact baseline | Product emphasis | Important boundary |
| --- | --- | --- | --- |
| Our CYTV, [Razdva122/clean-your-tv-lg-webos](https://github.com/Razdva122/clean-your-tv-lg-webos) | [v1.2.0](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.2.0), `d5804f6` | Clean Home, No-root/Root setup, controlled recovery | Android and renewal retain preview/Beta status; device acceptance is limited |
| [Luma](https://github.com/ecklf/lg-luma) | [v2.8.5](https://github.com/ecklf/lg-luma/releases/tag/v2.8.5), `6271b13` | Native Rust/SDL/OpenGL launcher | Home takeover support differs from ordinary launcher operation |
| [Lumen upstream](https://github.com/ammar027/lumen-webos) | [v1.1.4](https://github.com/ammar027/lumen-webos/releases/tag/v1.1.4), `a85b99a` | tvOS-style launcher, ambient photos/video and controls | Root/HBC required; Chrome 79+ target does not imply every firmware works |
| [Sam's Lumen fork](https://github.com/samrenfrew/lumen-webos) | [v1.1.3](https://github.com/samrenfrew/lumen-webos/releases/tag/v1.1.3), `2216e6f` | Live TV guide, Immich, ambient presentation, performance experiments | Separate package/feed; some extra root configuration and device acceptance remain |
| [Glasshouse](https://github.com/rorygallagher2024/glasshouse) | [v0.118.0](https://github.com/rorygallagher2024/glasshouse/releases/tag/v0.118.0), `859f5e1` | Local dashboard, Home, privacy, apps, OLED and MQTT | Broad dashboard compatibility is wider than experimental Home replacement |

Luma's older web implementation is **v1.x in the same ecklf/lg-luma repository**;
v2.0.0 rewrote it as native and changed its app ID. `donnes/luma` is a fork;
`luma-home-tv/native-home` is a separate project. Lumen's ancestor
`partridgeworks/webos-launcher` has a No-root claim that cannot be inherited by
current Lumen. References to `lasharor/cleanyourtv-WebOS` in Lumen research concern
another project, whose features must not be credited to our CYTV.

Evidence and lineage: [Luma](LUMA.md#identity-and-historical-browser-predecessor),
[Lumen](LUMEN.md#snapshot-and-ownership), [Glasshouse](GLASSHOUSE.md),
[our published baseline](CYTV.md).

## How to read the feature matrix

**✓** = documented in the selected published version; **R** = CYTV Root only;
**NR** = CYTV No-root only; **β** = Beta/preview; **△** = partial, optional separate
setup, or important acceptance restriction explained in the cell/appendix;
**—** = no released capability established in the reviewed sources. A dash is
not proof that no implementation exists anywhere in the repository or fork
network. “Native” and “web” describe architecture, not measured comparative speed.

Each numbered row is a distinct user capability or operational property. The
linked evidence appendices supply direct release, code, issue and PR sources
for the cells. Features inherited by Lumen upstream from Sam are credited to
both when the upstream release actually contains the port.

### Installation and Home lifecycle

| # | Capability | CYTV | Luma | Lumen | Sam fork | Glasshouse |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Install and use through Developer Mode without root | NR | — | — | — | — |
| 2 | Everyday use without an external computer watcher | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3 | One installer choosing No-root or Root | ✓ | — | — | — | — |
| 4 | Own graphical Windows/macOS/Linux installer | ✓ | — | — | — | △ deployment script |
| 5 | Android TV installation workflow | β | — | — | — | — management app is different |
| 6 | Homebrew Channel feed/IPK distribution | △ custom signed update feeds | ✓ | ✓ | ✓ separate feed | △ IPK; catalog approval pending at tag |
| 7 | Automatic desktop/CLI TV discovery | ✓ | — | — | — | — |
| 8 | Saved connection profiles and SSH trust review | ✓ | external tooling | external tooling | external tooling | external tooling |
| 9 | Root setup can supply a verified private TV Python | R | — | — | — | — |
| 10 | Home key opens the alternative launcher | ✓ edition-specific | △ version-specific takeover/Input Hook | △ default-app/hook/watcher | △ hook/default route | △ experimental Home |
| 11 | Back out of the last app returns to alternative Home | △ NR flash; R scoped evidence | △ supported takeover | △ chosen routing method | △ chosen routing method | △ supported Home |
| 12 | Avoid destroying Home on every Home press | △ edition-specific | ✓ lifecycle registration | △ separate keepalive config | △ separate tuning | △ Home lifecycle |
| 13 | Automatic return after standby/wake | △ model/build-specific | △ supported takeover | △ optional wake tool | △ optional root watcher | △ supported Home |
| 14 | Cold-start route and early-start handling | △ black interval remains | △ boot hook; early-start PR pending | △ startup gate | △ boot cache/watcher | △ bounded Home-start gate |
| 15 | On-remote emergency/temporary LG Home escape | ✓ triple Home | — shell restore documented | △ CC/restore route | △ CC/hook restore | ✓ hold Home/heartbeat fallback |

Sources: [CYTV setup/lifecycle](CYTV.md#features-and-evidence),
[Luma facts 35–40](LUMA.md#forty-comparison-facts),
[Lumen facts 32–39](LUMEN.md#stable-feature-facts-40-rows), [Glasshouse evidence](GLASSHOUSE.md).

### Apps and navigation

| # | Capability | CYTV | Luma | Lumen | Sam fork | Glasshouse |
| --- | --- | --- | --- | --- | --- | --- |
| 16 | Personal favourites/dock or selected Home apps | ✓ | ✓ | ✓ | ✓ | ✓ Home rows |
| 17 | Reorder tiles with remote hold-OK | ✓ | ✓ | ✓ | ✓ | ✓ |
| 18 | Multirow application presentation | ✓ | ✓ Apps | ✓ | ✓ | ✓ separate rows |
| 19 | Add installed apps from a fresh inventory | ✓ | ✓ | ✓ | ✓ | ✓ |
| 20 | Hide/restore an app without uninstalling | ✓ | ✓ | ✓ home selection | ✓ home selection | ✓ |
| 21 | Immediate Undo after hiding a tile | ✓ | — | — | — | — |
| 22 | Group apps into folders | — | — | ✓ | ✓ | — |
| 23 | Search apps in launcher | — | ✓ | — | — | △ management/catalog search |
| 24 | App category filters | — | ✓ | — | — | △ homebrew catalog |
| 25 | Recent-app row/history | — | ✓ | ✓ | ✓ Recent row | ✓ |
| 26 | Separate recent-app card switcher | — | ✓ | ✓ | — | ✓ |
| 27 | Close one app from recent-app UI | — | ✓ | ✓ | — | ✓ |
| 28 | Close all recent apps | — | — latest code | ✓ protects Lumen | — | ✓ |
| 29 | Indicator for currently running apps | — | — | ✓ | ✓ | △ recent-app information |
| 30 | Uninstall downloaded apps from TV interface | — | — | ✓ confirmed action | ✓ confirmed action | ✓ |
| 31 | Install/update third-party homebrew apps | — | — | — Store shortcut only | — Store shortcut only | ✓ catalogs |
| 32 | Read installed app icons with fallback | ✓ | ✓ async bounded cache | ✓ | ✓ | ✓ |
| 33 | Persistent local layout across restart | ✓ | ✓ | ✓ | ✓ plus root backup | ✓ |
| 34 | Configure app-name visibility | — | ✓ Home/Apps separately | ✓ | ✓ | — |
| 35 | Reduced-motion option | — | ✓ | ✓ | ✓ | — |
| 36 | Wheel navigation in launcher | — pass-through only | ✓ | — | — | — |
| 37 | Number-key launch shortcuts | △ LG Quick Access setup | — | ✓ first six dock apps | △ implemented; TV key check | ✓ remote keys/Quick Access |

Sources: [CYTV apps](CYTV.md#features-and-evidence),
[Luma state/recents](LUMA.md#forty-comparison-facts),
[Lumen apps/accessibility](LUMEN.md#stable-feature-facts-40-rows), [Glasshouse apps/Home](GLASSHOUSE.md).

### Appearance and ambient media

| # | Capability | CYTV | Luma | Lumen | Sam fork | Glasshouse |
| --- | --- | --- | --- | --- | --- | --- |
| 38 | Clock and date on Home | ✓ | ✓ | ✓ | ✓ | ✓ |
| 39 | Time-based greeting | ✓ | ✓ optional name | — | — | — |
| 40 | UI localisation | ✓ 10 languages | ✓ 8 released | ✓ 9 listed | ✓ inherited 9 | ✓ English/Spanish |
| 41 | Explicit 12/24-hour clock setting | — locale format | ✓ | ✓ | ✓ | — |
| 42 | Clock seconds/custom clock presentation | — | ✓ seconds | ✓ detailed controls | △ inherited clock | ✓ clock screensaver |
| 43 | Bundled selectable wallpaper gallery | — | ✓ 9 backgrounds | ✓ | ✓ | — personal uploads |
| 44 | Personal photos as wallpaper | — | — open PR | ✓ Immich | ✓ Immich | ✓ upload |
| 45 | Automatic wallpaper selection/rotation | — | — request pending | ✓ | ✓ | ✓ time-of-day slots |
| 46 | Video/aerial wallpapers | — | — | ✓ streaming | ✓ streaming | — |
| 47 | Hide dock to enjoy wallpaper | — | — request pending | ✓ | ✓ | — |
| 48 | Dark/light/automatic theme | — | — | ✓ | ✓ | ✓ dashboard light/dark |
| 49 | Wallpaper dimming and readability controls | — | — | ✓ night/always/hidden dock | ✓ | △ text/accent colours |
| 50 | Live/dock glass blur choices | — | — native visual treatment | ✓ optional; GPU tradeoff | ✓ optional | — |
| 51 | Custom photo screensaver | — | — uses LG policy | ✓ | ✓ | — other custom savers |
| 52 | Immich albums/favourites/on-this-day | — | — | ✓ SSH configuration | ✓ SSH configuration | — |
| 53 | Portrait pairing/face-aware photo crop | — | — | ✓ | ✓ | — |
| 54 | Print/art presentation with credits | — | — | △ art collection | ✓ print look/library | — |
| 55 | Dedicated StandBy clock faces | — | — | ✓ | — | △ own clock saver |
| 56 | Custom clock/starfield/fireworks saver | — | — | △ clock/aerial alternatives | △ photo ambience | ✓ |
| 57 | Replace screensaver over other foreground apps | — | — | △ optional watcher | △ separate root watcher | △ supported-version hooks |
| 58 | Current-weather widget | — | ✓ | ✓ | ✓ | — |
| 59 | Detailed hourly rain/forecast widget | — | — current weather only | — | △ next 7h; TV acceptance pending | — |
| 60 | User chooses weather location without mandatory IP lookup | — | ✓ explicit city search | ✓ city selection | ✓ opt-in city/IP Auto | — |

Sources: [CYTV limits](CYTV.md#product-gaps-in-the-published-baseline),
[Luma weather/backgrounds](LUMA.md#forty-comparison-facts),
[Lumen and fork media](LUMEN.md#stable-feature-facts-40-rows), [Glasshouse screensavers/Home](GLASSHOUSE.md).

### Inputs and TV controls

| # | Capability | CYTV | Luma | Lumen | Sam fork | Glasshouse |
| --- | --- | --- | --- | --- | --- | --- |
| 61 | HDMI/input launch shortcuts | ✓ | ✓ | ✓ | ✓ | ✓ |
| 62 | Per-input show/hide/connected-only policy | △ setup inventory | ✓ On/Off/Auto | — | — | ✓ visibility/connection state |
| 63 | Edit custom input names from launcher | — setup labels | ✓ | — normalised HDMI names | — | — |
| 64 | Connected HDMI-CEC device details | — | △ connection state | — | — | ✓ |
| 65 | Live tuner channel row with current programme | — | — | — | ✓ | ✓ Home channels |
| 66 | Full grid programme guide | — | — | — | ✓ actual 8h horizon | — |
| 67 | Quick Control Center | — LG settings shortcut | — | ✓ | ✓ | ✓ dashboard controls |
| 68 | Screen off while TV remains active | — shortcut not established | — | ✓ | ✓ | ✓ |
| 69 | Brightness/backlight control in own UI | — | — | ✓ | ✓ | ✓ |
| 70 | Picture-mode selection in own UI | — | — | ✓ | ✓ | ✓ |
| 71 | Sound-mode/output controls in own UI | — | — | △ sound controls | △ sound controls | ✓ output routing |
| 72 | HDMI/video signal details including HDR/VRR | — | — | — | — | ✓ supported signals |
| 73 | Wi-Fi/LG network-settings shortcut | ✓ | — | △ LG Settings | △ LG Settings | △ network dashboard |
| 74 | Remap branded/colour/Guide remote keys system-wide | — | △ external Input Hook | △ external Input Hook | △ external Input Hook | △ version/key limits |
| 75 | Sleep, power and genuine restart controls | — normal remote | — | △ Control Center | ✓ restart correction | ✓ |

Sources: [CYTV UI](CYTV.md#features-and-evidence), [Luma inputs](LUMA.md#forty-comparison-facts),
[Lumen controls and guide](LUMEN.md#stable-feature-facts-40-rows), [Glasshouse controls](GLASSHOUSE.md).

### Privacy and device administration

| # | Capability | CYTV | Luma | Lumen | Sam fork | Glasshouse |
| --- | --- | --- | --- | --- | --- | --- |
| 76 | Alternative Home without sponsored rows | ✓ | ✓ | ✓ | ✓ | ✓ |
| 77 | Device-wide ad/telemetry endpoint blocker | — | — | △ two extra hosts in optional tool | — empty hosts-extra | ✓ |
| 78 | ACR/tracking/agreement visibility and controls | — | — | — | — | ✓ |
| 79 | Disable selected background telemetry services | — | — | — | — future idea | ✓ |
| 80 | Hide non-removable LG apps from stock Home | — hides own tiles | — hides own tiles | — | — | ✓ |
| 81 | Remove stock Home recommendation/card sections | — | — | — | — | △ webOS-specific |
| 82 | LG firmware-update blocking control | R Homebrew preference | — | △ notifications only | — | ✓ own policy controls |
| 83 | CPU/temperature/RAM/network telemetry | — installation diagnostics only | — | — | △ developer measurements | ✓ live metrics |
| 84 | OLED panel hours/compensation counters | — | — | — | — | ✓ supported OLED |
| 85 | Pixel Refresher status/scheduling | — | — | — | — | ✓ supported OLED |
| 86 | OLED protection switches | — | — | — | — | ✓ firmware/panel-dependent |
| 87 | Service-menu access/unlock controls | — | — | — | — | ✓ supported firmware |
| 88 | Browser D-pad/media/volume remote | — | — | — | — | ✓ |
| 89 | MQTT/Home Assistant device and remote events | — | — | — | — future idea | ✓ |
| 90 | Prometheus metric export | — | — | — | — | ✓ |

Sources: [CYTV firmware policy](CYTV.md#features-and-evidence),
[Lumen limits and project-name distinction](LUMEN.md#do-not-overstate--useful-comparison-interpretation),
[Glasshouse privacy, OLED and integrations](GLASSHOUSE.md).

### Updates and support

| # | Capability | CYTV | Luma | Lumen | Sam fork | Glasshouse |
| --- | --- | --- | --- | --- | --- | --- |
| 91 | Update own software from TV UI | △ rooted TV plus separate bootstrap | — pending PR | △ HBC distribution | △ HBC distribution | ✓ |
| 92 | Signed release policy plus package verification | ✓ signed manifests | △ checksum feed | △ checksum feed | △ checksum feed | △ HTTPS/version; catalog hashes |
| 93 | Independent whole-edition rollback with profile | △ implemented; full TV acceptance pending | — | — | △ settings backup only | △ own update/backup workflow |
| 94 | Refuse blind replay after ambiguous installer outcome | ✓ durable receipts | — | — | — | — equivalent ledger not established |
| 95 | Dedicated Helper Home-press diagnosis | NR | — | — | — | — |
| 96 | User-facing diagnostics/status/export workflow | ✓ desktop/CLI; Android scoped | △ startup stderr | △ root tools | △ bounded log/tools | ✓ dashboard/logs |
| 97 | Explicit return-to-LG-Home and removal path | ✓ | ✓ | ✓ manual method | ✓ manual method | ✓ |
| 98 | Preserve emergency/off intent across update/recovery | ✓ | — | — | — | △ Home restore state |
| 99 | Optional Developer Mode auto-renewal on TV | NR β | — | — | — | — |
| 100 | Compatibility evidence separated by feature/model | ✓ documented limits | ✓ issue/device evidence | △ small device set | △ single main target | ✓ tested-TV table; Home narrower |

Sources: [CYTV updates/recovery](CYTV.md), [Luma delivery limits](LUMA.md),
[Lumen publication/config boundaries](LUMEN.md), [Glasshouse maintenance](GLASSHOUSE.md).

## Important problems in competitor updates and issues

The detailed appendices distinguish release-note claims, code present at a
published tag, contributor/maintainer device checks and explicit reporter
acceptance. An issue can remain open after one symptom is fixed, or close with
an unsupported device, a partial improvement or outstanding hardware testing.

### Luma

| User problem | Delivered change or remaining work | Implication for CYTV |
| --- | --- | --- |
| Home presses restart the launcher, lose state and show black intervals | v2.7.0/v2.8.0 add version-specific lifecycle registration; scoped webOS 5/6 and C3/webOS 26 evidence | Treat Home identity, lifecycle and foreground registration as separate compatibility cases |
| OLED screensaver stops starting after lifecycle changes | [#87](https://github.com/ecklf/lg-luma/issues/87), [#91](https://github.com/ecklf/lg-luma/pull/91), v2.8.5 allow SDL screensaver requests; original OLED acceptance pending | Every Home/keepalive change needs an idle OLED case alongside responsiveness tests |
| Text sharpness improvement regresses C2 | [#25](https://github.com/ecklf/lg-luma/issues/25), [#97](https://github.com/ecklf/lg-luma/pull/97); proposed MSAA restoration is unreleased | Keep rendering modes and model-specific comparisons reproducible |
| Request for true 4K UI | #25 remains open; drawable size and panel/compositor output differ | Verify the displayed path before advertising 4K |
| Missing Hangul and false ARD logo on “dashboard” | [#19](https://github.com/ecklf/lg-luma/issues/19)/[#22](https://github.com/ecklf/lg-luma/pull/22) and [#20](https://github.com/ecklf/lg-luma/issues/20)/[#21](https://github.com/ecklf/lg-luma/pull/21), v2.1.0 | Test real app titles and use exact app IDs for curated branding |
| Early-boot empty inventory and no-op arrow black damage | v2.8.5 inventory retry/root read; v2.8.2 damage fix | Separate initial readiness, cached fallback and renderer correctness |
| Inputs clutter Home | [#2](https://github.com/ecklf/lg-luma/issues/2), v1.1.0 hiding; reordering deferred | Track partial requests separately |
| Personal photos, wallpaper rotation, earlier cold start and self-update | Open issues/PRs at snapshot | These remain opportunities; they are not released Luma capabilities |

Full evidence: [17 issue outcome cases covering all 14 Luma issues](LUMA.md#user-problems-and-actual-outcomes--all-fourteen-issues-covered),
plus additional release-only improvements.

### Lumen and Sam fork

| User problem | Delivered change or remaining work | Implication for CYTV |
| --- | --- | --- |
| Initial built-in catalogue misses installed apps | Upstream v1.0.1 reads all apps and improves icon sizing | Fresh inventory and a usable fallback matter immediately after setup |
| Empty navigation/add-app prompt flashes during startup | [#2](https://github.com/ammar027/lumen-webos/issues/2), bounded readiness gate in v1.1.x; no explicit released-version reporter retest | Gate incomplete UI without waiting forever |
| Pointer movement jumps to first row; second-row lag | [#4](https://github.com/ammar027/lumen-webos/issues/4), pointer/backdrop fixes; original hardware acceptance limited | Check pointer plus scrolling with real multirow data |
| webOS 4.4/Chromium 53 shows a blank screen | [#5](https://github.com/ammar027/lumen-webos/issues/5), explanatory message; device remains unsupported | Explain runtime requirements before installation or at first failure |
| Root shell works but app's HBC exec is denied | [#9](https://github.com/ammar027/lumen-webos/issues/9), unresolved on reported webOS 11.2.0 | Test the jailed app's actual caller, beyond SSH root |
| Checksums point to an older filename | [PR #7](https://github.com/ammar027/lumen-webos/pull/7), alternate fix and corrected assets; proposal itself unmerged | Validate release version, filename, size and digest together |
| Wrong wallpaper selected; dock blur tied to unrelated toggle | v1.1.1 corrects selection and blur independence | Exercise combined settings and direct selection semantics |
| Close all closes Lumen itself | Upstream v1.1.4 excludes launcher | Protect Home/recovery processes in any future app-closing UI |
| Restart enters standby instead of restarting | Sam v1.1.1 changes reboot method; maintainer target check, reporter acceptance pending | Distinguish standby, software restart and cold power loss |
| Last-row labels clipped; widgets reveal icons before text | Sam layout change and v1.1.3 widget sequencing; acceptance limits remain | Test end-of-grid and async-content layout |
| Programme guide empty after startup | Sam stable cache/fallback mitigates missing tuner data; pre-tune acceptance remains | Keep cached content and current data visibly distinct |

Full evidence: [20 problem/fix cases](LUMEN.md#user-problem-and-fix-cases-20).

### Glasshouse

| User problem | Delivered change or remaining work | Implication for CYTV |
| --- | --- | --- |
| Server appears alive but event loop is wedged | v0.6.0 heartbeat watchdog; v0.6.1 stops misdiagnosing suspended standby as a hang | Watchdog time must account for suspend/wake |
| Privacy consent changes revert after reboot | [#61](https://github.com/rorygallagher2024/glasshouse/issues/61), v0.26.0 updates the accepted-agreement source; reporter confirms persistence | Verify the authoritative state and reboot persistence |
| Blocker reports active although another tool owns the hosts mount | v0.27.0 adds ownership marker and mount handling | Read effective state and coexistence, beyond a saved preference |
| Dashboard blank when token enabled | [#152](https://github.com/rorygallagher2024/glasshouse/issues/152), v0.39.1 local-request auth correction; reporter confirms | Check both local TV UI and authenticated remote access |
| Disabling alwaysready distorts Plex video | [#374](https://github.com/rorygallagher2024/glasshouse/issues/374), v0.74.0 removes it from debloat and restores it | Service names do not establish safe removability |
| eARC reports zero volume or ignores slider | [#406](https://github.com/rorygallagher2024/glasshouse/issues/406)/[#437](https://github.com/rorygallagher2024/glasshouse/issues/437), v0.75.5 and v0.80.2–3 use correct service/relative keys | Separate receiver state, relative keys and absolute-volume capability |
| Older TV app stays blank without fetch/Promise | [#379](https://github.com/rorygallagher2024/glasshouse/issues/379), v0.76.0; v0.117.1 adds older-engine support | Test the complete built package on the claimed old runtime |
| Watchdog restart loses its deleted working directory | [#506](https://github.com/rorygallagher2024/glasshouse/issues/506), v0.80.4 chooses a persistent working directory | Update/recovery workers must survive package replacement |
| Existing updater rejects newer package as vnull | [#586](https://github.com/rorygallagher2024/glasshouse/issues/586), v0.82.2 restores metadata placement within old reader's limit | Test the already-installed updater against future package layout |
| Privacy inspection starts the services it is inspecting | v0.106.0 avoids waking stopped recognition/ad daemons | Read-only status checks must also be checked for side effects |
| Missing optional Home module stops dashboard and MQTT | [#865](https://github.com/rorygallagher2024/glasshouse/issues/865), v0.117.0 fail-soft startup; reporter confirms v0.118.0 recovery although issue stays open | Keep recovery/control available when an optional module fails |
| Home/standby preferences, dropped early Home and SAM-related black screens | [#895](https://github.com/rorygallagher2024/glasshouse/issues/895), [#927](https://github.com/rorygallagher2024/glasshouse/issues/927), [#366](https://github.com/rorygallagher2024/glasshouse/issues/366) retain unresolved/partial scope | Keep these as acceptance cases rather than copying risky timing assumptions |

Full evidence: [30 historical fix cases](GLASSHOUSE.md#historical-delivered-fixes-and-what-they-actually-establish),
[eight unresolved or limited cases](GLASSHOUSE.md#eight-unresolvedlimited-cases-to-keep-beside-the-positive-matrix),
and closed-report interpretation guards. Glasshouse Home supports webOS 9,
treats webOS 10 as experimental and gates webOS 11 behind an experimental
flag. These remain separate from dashboard compatibility.

## What the history suggests for CYTV

These are opportunities and acceptance cases, not scheduled commitments or
claims that competitor bugs reproduce in CYTV.

| Area | Why it matters | Concrete candidate or acceptance result |
| --- | --- | --- |
| Home reliability | All three product families encounter startup/lifecycle/firmware boundaries | Record Home/Back, rapid standby, real restart, cold start, late network, idle OLED and other Home modifications separately |
| Installation diagnosis | Root access and successful IPK installation do not prove app permissions or input support | Check actual app/service caller and retain a concise failure report tied to the attempt |
| Recovery | Interruption can leave routing and installer state disagreeing | Finish original-device acceptance for existing durable recovery and complete edition rollback before broadening claims |
| App search | Luma already offers case-insensitive search; CYTV's larger inventories require scrolling | Search the local catalogue with remote-friendly input and retain focus when closing search |
| Folders | Lumen offers meaningful organisation beyond hide/reorder | Add folders only if they remain easy to navigate, edit and recover |
| Recents | Luma/Lumen/Glasshouse expose recent activity and app closing | A focused recent-app view, with verified close results and protected Home/recovery identities |
| Personalisation | Lumen is substantially ahead in wallpaper/photos/ambient features | Start with a small offline wallpaper choice and optional weather; evaluate richer media separately |
| Quick controls | Lumen and Glasshouse reduce trips through LG Settings | A small firmware-aware panel for the most useful controls; disable unsupported operations clearly |
| Input quality | Luma catches false connected-state data; Glasshouse surfaces CEC details | Clear per-input visibility/name choices and real connection-state checks |
| Accessibility | Luma/Lumen offer reduced motion and label choices | Reduced motion, readable text and consistently visible remote focus |
| Feature boundaries | Glasshouse separates own Home, stock Home cleanup and device-wide privacy controls | Keep each operation and its effect clear if privacy/admin features are added |
| Integration scope | Glasshouse's MQTT/OLED features expand the product considerably | Treat smart-home/OLED administration as optional product extensions with their own acceptance scope |

CYTV's existing No-root path, guided multi-platform setup, ten languages,
emergency escape, diagnostics and update/recovery design deserve clear
presentation. Their value depends on preserving the documented limitations:
renewal Beta, Android preview, model-specific Helper behaviour and unfinished
full-system TV update/rollback acceptance.

## Evidence corrections that materially change the comparison

1. Luma v2.8.5 has **eight** shipped languages; French is later main-branch work.
2. Luma's current Recents code closes **one** app; historical “Close all” text is stale.
3. Luma's closed screensaver issue still requires OLED/webOS 25–26 confirmation.
4. Luma v1.x web and v2.x native have different app IDs and compatibility paths.
5. Sam's “full week” programme-guide claim conflicts with the released code's
   **eight-hour** schedule horizon and four-hour cold-start cache.
6. Several Sam photo/settings features have already been ported into upstream
   Lumen; they cannot all be described as fork exclusives.
7. Lumen's closed old-webOS issue delivers an explanation, not support for that device.
8. Lumen's service-debloat references name a different CleanYourTV repository.
9. Glasshouse issue state and its latest reporter outcome must be read separately.
10. Our own v1.2.0 diagnostics/partial recovery improvements do not resolve the
    original installation/device failures that the release explicitly preserves.

## Coverage and reproducibility

| Scope | Release inventory | Issues examined | Deeper linked evidence |
| --- | --- | --- | --- |
| Luma | All 23 published records | All 14 actual issues; 28 comments, 75 timeline entries | 19 relevant upstream PR conversations/reviews |
| Lumen upstream | All 11 records | All 4 actual issues, plus all 5 PRs | Comments, timelines and linked fork PR |
| Sam fork | All 4 records | Its one aggregate issue | Published code, dated measurements, root configuration and feeds |
| Glasshouse | All 205 release records inventoried | 39 selected complete issue discussions/timelines | 58 directly linked PR descriptions/comments/reviews |
| CYTV | Public v1.2.0 metadata and pinned source/docs | Published compatibility/acceptance record | Current unpublished desktop/Android work excluded |

The research uses official repository code/docs, releases and complete included
issue discussions. It does not install competitors on a TV or produce a shared
hardware performance benchmark. Feature presence, a published implementation,
one-device acceptance and broad compatibility remain distinct conclusions.

Verification: the matrix has exactly 100 unique numbered rows. All 105 distinct
pinned source paths were checked against their GitHub trees; local links,
section anchors and table column counts were checked. The repository's
`npm ci` and `scripts/test.sh` completed during research; these are software
checks of the shared local checkout, not competitor hardware qualification.
