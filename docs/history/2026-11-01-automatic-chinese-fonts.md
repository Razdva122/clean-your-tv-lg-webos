# Automatic Chinese font preparation — 2026-11-01

Implementation PR #228; final reviewed source
`28d3654213e850955e53cf3857b333df5cf61fd6`. This is source/host verification,
not a TV installation report. No TV was connected or modified. Physical model,
firmware/webOS, remote, graphics, startup, power and OTA behavior remain untested
for these bytes. No private diagnostics or installation report are republished.

Merged into `release/next` as `a36d16ebbfae60833e4d8c6e738ef145c67ebf02`.
The merge tree exactly matches the reviewed and checked source tree.

## Result

Builders and live/static previews prepare compact static Chinese fonts from the
actual first-party runtime catalogs and compiler inputs. The collector parses
JavaScript/template literals, JSON, HTML and CSS as data, decodes escapes/entities,
preserves language scopes and includes calendar/autonym text. It does not execute
runtime or theme source. New translations no longer require manual TTF edits or
wording changes to fit a stale subset.

Simplified and Traditional Chinese retain their preferred face. Both faces serve
as fallbacks so shared names and legitimate mixed-script catalog text such as
`简约` and `简书` are covered. Unsupported CJK outside the pinned source union is
a clear build error. Non-CJK optional currency/formatting characters cannot create
false CJK requirements; supported punctuation, checkmarks and quotes are retained.
This prepares known static UI text, not every possible Unicode or user-provided
string.

Source inputs are Google Fonts commit
`e7db6ca603fd4862010383ff17ffd6cc4ffac1c0`, exact sizes/SHA-256, and build-only
fonttools 4.60.1. Cold builds fetch the verified originals; cached originals permit
offline generation. Atomic content/input-keyed caches reject corruption and
nonregular entries. Concurrent offline generation produced identical bytes.
Tracked source TTFs, runtime requirements, native Helper, signing keys and TV
permissions remain unchanged. No fonttools or preparation module ships inside TV
IPKs, and installed apps never fetch these source fonts.

## Review and regressions

Independent AI-assisted module/cache/collector and packaging/CI reviews approved.
Adversarial probes covered escaped generic strings, metadata keys, locale JSON,
HTML entities, inline scripts under default English documents, CSS escapes,
foreign regional language scopes, attribute spacing and conditional selectors.
Actual mixed-font generation and declared face priorities were checked.

Observed red/green cases include new `形`/`力` translations missing from retained
fonts, collector omissions, false currency requirements, malformed cache and FIFO
entries, real unsupported CJK, fixture dependencies and stale package assertions.

Initial CI failures were kept visible and corrected:

- The isolated recovery compiler fixture now copies its required font module,
  retaining stylesheet/polyfill/CA assertions.
- Browser validation waits for bounded HTTP readiness and checks process liveness;
  early failures/timeouts print diagnostics. All five original browser commands
  passed both warm-cache and empty-subset-cache runs using verified originals.
  Corrupted-source startup reported its error in 0.27 seconds.
- Root Updater's old byte comparison against retained source fonts now checks the
  prepared outputs, independently validates nonzero glyph IDs/static weight 400,
  and proves source immutability. Private/state exclusions, isolated runtime
  imports, CA/version/startup/rollback and tamper checks remain.

Final selected [CI run 41289788491](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41289788491) passed, including Linux/macOS runtime and browser checks. Integration policy, Windows and Intel macOS checks also passed. No required status was bypassed.

## Host and package evidence

- Primary focused final run: 18 Chinese preparation/package tests and 5 Root
  Updater setup tests passed.
- Primary affected run: UI/compatibility/theme checks, 218 setup, 563 installer
  (2 explicit platform skips), 23 Android and 5 preview tests passed. These
  preceded the last optional-symbol/Root-fixture correction; its focused final
  checks and final CI supply the delta evidence. Current production glyph sets
  and font bytes are unchanged by that correction.
- Chromium passed thirteen-language checks in both editions and inspected actual
  mixed glyph rendering: English uses packaged SC; Traditional uses preferred TC
  plus SC fallback. macOS Qt offscreen `QTextLayout` likewise resolved `简體` to
  the actual rebuilt TC and SC families. This is not native frozen-installer
  upgrade or physical-TV rendering evidence.
- Rebuilt local payload: 209 file hashes verified. All six font-bearing Home/Root
  HD/FHD and legacy updater IPKs plus standalone desktop fonts contain identical
  prepared faces and OFL files. Existing artifacts were revalidated against the
  final glyph inputs; CI-only and optional-symbol fixes do not change these bytes.
  These are developer artifacts, not a frozen full-candidate build or release pins.

| Face | Bytes | cmap entries | SHA-256 |
| --- | ---: | ---: | --- |
| SC | 213,636 | 734 | `379201e090df17770020d430bdee5e1cd728a23502a893fa08c8b43d5c3ae7d4` |
| TC | 178,288 | 607 | `7edbd255cfe6bbf4d562d313a8ce85c9e68858ee297332054c7a3f2b0e0185c5` |

Both are static weight 400, without variable axes, and smaller than retained
238,636/198,620-byte source faces. Local Home IPKs are about 5.53 MB; Root about
5.40 MB; Home/Root Updaters about 1.84/1.72 MB. Every package remains below 32 MiB,
each member below 16 MiB and unpacked payload below 64 MiB. Full static sources
were measured and rejected as the normal distribution choice: the user selected
automatic subsets, avoiding roughly 69 MiB of installer growth.

## Documentation and integration limits

Build/font provenance, developer/TV/Android entry points and dependency guidance
now describe automatic preparation, host-only source fetching, cache and offline
use. Normal builds leave the checkout's retained fonts unchanged. Public versions
and downloads remain the published baseline; no frozen build/acceptance was chosen.
Rebuild and bump every affected Home/Root/updater/installer artifact coherently at
freeze. Final signed artifact, platform upgrade, physical UI/control/startup and
update/rollback acceptance remain separate. Earlier #207 IR routing is unresolved.
