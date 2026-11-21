# Engineering debt and repair plan

**20 November 2026.** Start with the Android installer. A clean selection of the Python modules intended for the APK fails to import the bridge that both connection inspection and installation use. Fixing that boundary gives the next Android change a meaningful smoke test.

**Scope.** This review follows selected paths through the installers, Home, the update services, packaging, CI and the website. The working checkout was `codex/doctor-setup-continuation` at `6cb6c4fd` with local edits. The locally available `origin/release/next` at `6b796df0` was 608 commits ahead. Each item below applies to that integration snapshot. Links to newer implementation details use the integration commit. Relative links open the corresponding files in this checkout. The earlier maintainability batch is already integrated at `ca0561df`. The existing installer outcomes plan covers support journeys and HDMI discovery. [Earlier installer plan](2026-11-18-installer-user-outcomes.md)

**Initial audit evidence.** Items 1–4, 6, 7 and 10 include offline observations. Items 5 and 8 follow the file-selection and lifetime rules in source. Item 9 includes a ZIP timestamp experiment and inspection of the TAR writer. At the time of the audit there was no matching Android APK for runtime verification. Device failure rates, live site state and published artifact contents were outside the audit.

## Implementation and verification

All ten repairs are on the local branch `codex/engineering-debt-20261120`, based on `6b796df0`. The numbered sections preserve the original implementation plan. The table records which paths were exercised.

| Area | Observed result |
| --- | --- |
| Android bridge and payload retention (1, 8) | An API 35 ARM64 emulator loaded the packaged Python bridge, dispatched the CLI, distinguished a local inspection error from closed SSH ports, and cancelled an installation before transport through the service callbacks. A failed B extraction kept A usable. A successful B and then C retired older copies, a repeated C reused its extraction, and a failed deletion was retried. Profiles, identity and pending recovery files stayed byte-identical. |
| App inventory (2) | An interrupted icon fetch used an alternate or the bundled fallback and finished the inventory with the expected counters. The source installer retained an ordinary app and the tuner without artwork, and kept its empty-inventory check. |
| Updates (3, 4) | Controlled overlapping calls in the legacy updater restored renewal once. Root update and rollback fixtures removed an orphan package while preserving peer-store references. Unknown, malformed and pending records retained the cache. Seven System rollback compatibility scenarios passed against the retained supervisor. |
| Helper and release packaging (5, 9) | The shell staging set and Python-generated IPK contained the expected Helper resources and excluded untracked fixture files. Both pinned Helper versions retained their checksums. Both outer archives repeated byte-for-byte across fixture timestamps and umasks, preserved the executable bit, and changed hash for changed content. |
| CI and compatibility catalog (6, 10) | The 15 scope tests passed, including delivery of preview notices and packaged docs to their consuming checks. A synthetic `25; SDK 11.2.0` entry appeared under webOS 26 in both the generated README and built website, with its reported text preserved. The website built 145 pages with the combined changes and passed its link and localization checks. |
| Downloaded themes (7) | Browser checks covered both Home editions at 1280 and 1920 pixels. After rollback, cancellation preserved eight incompatible downloads, removing one allowed a compatible replacement, and removing an incomplete active record restored Classic. The row and confirmation identify the same download. All 13 user guides include the recovery step. |

The Android test used a fresh debug APK with one synthetic TV payload file, SHA-256 `b21bf871ff046a54e78c9274974a0cfc9f54d9a2b5aff31550c73cae31727d52` for the APK. The native runner passed with the corrected instrumentation APK, SHA-256 `1eba65a7b91f71667c242a84b15abcabd71821e225bedfee50e9cad5b427915c`. Production Android code for this check was built at `74764e52`. The later WebView change `bdfdd4b5` was tested in Chromium. In that case a delayed result for TV A arrived after the address had changed to TV B. Both the success and failure cases now leave B available for inspection. Physical TV and signed-release acceptance remain part of release QA.

## Order of work

| Order | Change | Reason for its place |
| --- | --- | --- |
| 1 | Restore the packaged Android entry point | Affects both discovery and starting an operation |
| 2 | Keep apps when optional artwork fails | A single image can stop setup or remove a usable tile |
| 3 | Serialize renewal restoration in the legacy Home Updater | Concurrent callers can overwrite a successful result |
| 4 | Align Root update receipts with cache cleanup | A completed transaction can prevent space recovery |
| 5 | Use explicit inputs for both Helper build paths | Local files can enter a freshly built package |
| 6 | Route catalog and embedded document changes to their consumers | Real catalog changes select zero checks |
| 7 | Allow removal of incompatible downloaded themes | An owner can exhaust all eight slots after a Home rollback |
| 8 | Bound Android payload retention across upgrades | Each changed manifest can leave another full copy on the phone |
| 9 | Make outer release archives reproducible | Reassembly can change download hashes for identical inputs |
| 10 | Group conflicting webOS versions by their stated SDK | The website and README share a parser that contradicts the catalog rule |

Each numbered item can ship as a focused change into `release/next`. Item 8 can reuse the Android package test from item 1. Item 10 benefits from the CI coverage in item 6. Use the repository virtual environment for the Python commands below. For JavaScript checks, use the locked dependencies installed with `npm ci`. Preserve Chromium 38 and the Helper's Node 0.10.15 floor, existing emergency controls, recovery receipts, and the normal release acceptance process. [Contribution rules](../../../CONTRIBUTING.md)

### 1. Restore the packaged Android entry point

The staging script excludes `cytv.desktop`. The bridge imports retry labels from it, and the shared CLI imports it at module load and again during dispatch. An isolated import using the staging selection raised `ModuleNotFoundError: No module named 'cytv.desktop'`. The same conflict appears in the cached `origin/main` at `fddc12d5`. The Activity maps an inspection exception to two unavailable SSH transports. The service uses the same bridge to start operations. The host bridge tests load from the checkout, where the missing module is present. [Staging selection](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/android/stage.py#L30) · [Bridge import](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/android/app/src/main/python/android_bridge.py#L6) · [CLI import](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/cytv/cli.py#L17) · [Activity error handling](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/android/app/src/main/java/com/cleanyourtv/android/MainActivity.kt#L99)

- Add a case to `android/tests/test_bridge.py` that stages the production Python selection into a temporary directory. In a fresh isolated interpreter, load the bridge with only those project sources on its import path and call the shared CLI with `--version`. A source-tree fallback would hide both the initial and the dispatch-time imports.
- Move shared prompt constants into the existing `cytv/prompts.py`. In `cytv/cli.py`, use the existing console frontend identity for desktop-only paths. Preserve the frozen desktop payload preflight and desktop-only CLI options. Run the existing Android retry-prompt and desktop parser cases to check behavior. Give local bridge initialization errors a distinct inspection result so they cannot look like a TV with both ports closed.
- Extend the native `OperationChecks.kt` fixture to load `android_bridge` through Chaquopy and exercise a synthetic local operation. Acceptance requires successful import and dispatch on a newly staged build, a distinct local-error result, and correct behavior for a genuine negative SSH inspection. Run the bridge suite and the native fixture on that build.

### 2. Keep app inventory independent of artwork

In the packaged installer, an interrupted chunked icon response can raise `http.client.IncompleteRead` outside the existing fallback handler. Injecting it into `Inventory.build` aborted the inventory and left diagnostics at `reading`. The documented source installer has a second policy. On download failure it skips ordinary apps and reserves the fallback for the tuner. A run of the real sync function with one synthetic ordinary app and an unavailable icon wrote an empty app list. The shell installer rejects that list. [Packaged inventory](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/cytv/tv.py#L156) · [Source sync](../../../sync-apps.py#L50) · [Installer check](../../../install.sh#L94)

- Extend `tests/cytv/test_tv.py` with an ordinary app whose first download raises `IncompleteRead`. Test a valid alternate icon and exhaustion of all alternatives. Run the source sync on an ordinary app without artwork as well as the existing tuner case.
- Handle the interrupted response at the optional fetch boundary. Reuse the shared icon selection and fallback behavior where feasible. Preserve the source installer's on-disk icon paths and `--list` output, and the packaged installer's size budgets and embedded format.
- Run `.venv-cytv/bin/python -m unittest discover -s tests/cytv -p test_tv.py`. Both installers must retain the app ID and title. The packaged result must finish with `status=complete` and the correct failure and fallback counts. A genuinely empty app inventory must still stop setup.

### 3. Keep the legacy updater busy until renewal restoration settles

The Home-only updater returns the promise from `restore` inside a `try` and clears `busy` in `finally`. The UI polls `reconcile` while Home independently submits `healthy`. With a deferred renewal response, the actual manager called `resumeRenewal` twice. The poll saved `complete`, then the earlier call failed and saved `renewal-recovery` over it. This is the retained Home-only path for older installations. [Manager](../../../updater-service/manager.js#L139) · [UI poll](../../../updater-app/app.js#L146) · [Home callback](../../../launcher/profile-bootstrap.js#L119)

- Extend `tests/updates/transaction-pause.cjs` with a deferred `resumeRenewal`. Start `healthy`, wait for the first restore call, then issue `reconcile`. Repeat for rollback and for restoration after a failed install. Use controlled promises so the ordering is deterministic.
- Await the restoration inside each guarded branch in `updater-service/manager.js`, including reconciliation and rollback. A second caller must observe the existing busy behavior for the whole operation.
- Run `node tests/updates/transaction-pause.cjs` and `node tests/updates/manager.cjs`. Require one resume, one final result, and zero package replays on recovery. A genuine renewal failure must remain retryable after the first call settles.

### 4. Make Root update writers and cache cleanup agree on receipts

Root Home writes transaction-scoped `ready`, `confirm` and rollback readiness records. The shared Root/System cache scanner rejects each of the three filenames with `unknown retention record`. Finalization calls the scanner across both stores. Its refusal retains obsolete packages even when the update itself completes. The existing storage fixture constructs a terminal journal directly and can omit the records a real transaction leaves. [Health writer](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/root-edition/updater/core.py#L319) · [Scanner](../../../root-edition/updater/store.py#L192) · [Terminal fixture](../../../root-edition/tests/test_update_storage.py#L31)

- Exercise forward completion and successful rollback using the health writer in `root-edition/tests/test_update_storage.py` and the existing manager fixture in `test_update_core.py`. Seed one unreferenced package and one reference owned by the peer store.
- Share the recognized receipt names with the writer and validate each supported record shape. Include the integration branch's companion update and rollback journals in the writer inventory. Keep unknown, unfinished, changed or malformed evidence grounds for retaining every package. Retain old valid receipts across upgrades.
- Run the two named test modules through unittest discovery in `root-edition/tests`. Only the orphan should disappear in the completed cases. Check that a pending companion operation or an unknown record still removes zero packages, and that the update outcome survives a cleanup error.

### 5. Use the same explicit Helper inputs in both builds

The Python builder starts with Git's file list, then adds every local file under `native/app/vendor/ws-legacy`. The package filter accepts every `vendor/` entry. All 18 intended files at the audited revision are already tracked. The shell builder also recursively copies the vendor directory and uses globs for top-level Helper sources. A stray local file can therefore change a newly compiled Helper. Pinned prebuilt Helpers take a separate branch. [Python selection](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/scripts/build-cytv.py#L43) · [Package filter](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/scripts/build-cytv.py#L253) · [Shell staging](../../../scripts/build.sh#L28)

- In `tests/cytv/test_build_assets.py`, put a tracked vendor resource, an untracked notes file and an unrelated top-level JS file in a disposable checkout. Assert the exact staged member set in both build paths.
- Have both builders consume the same tracked Helper inputs and the explicitly named development dependencies. Preserve generated screensaver resources, service modules, vendor licenses and private-state exclusions.
- Inspect fresh fixture IPK members and run the existing Helper compatibility checks. The extra files must be absent, the required vendor files present, and selection of a pinned Helper must yield its original checksum.

### 6. Route changes by what consumes the file

The site reads `docs/compatibility-reports.json`, and its verifier also reads the README and compatibility guide. The CI selector skips most of `docs/` and sends the README only to setup. The actual path sets from commits `9185293c` and `074109f2` selected zero groups. A corresponding main push can skip the Pages build. The same early exit skips `LICENSE`, `THIRD_PARTY_NOTICES.md` and the Android setup guide README even though the payload builder reads them. [CI selection](../../../scripts/ci-scope.py#L18) · [Site verifier](../../../website/scripts/verify.mjs#L54) · [Pages build condition](../../../.github/workflows/preview-pages.yml#L36) · [Packaged guide](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/6b796df09264ee2efbebf871375ddf827d32d11f/scripts/build-cytv.py#L184)

- Extend the path table in `tests/setup/test_ci_scope.py` with the two historical file sets, a README-only change, each embedded document, and an unrelated developer note. Exercise both a focused PR and a main push.
- Route the known data and document inputs to their consuming checks before the generic documentation exclusion. Preserve setup coverage for the README, site preview for the catalog, and existing full-candidate selection.
- Run `.venv-cytv/bin/python -m unittest discover -s tests/setup -p test_ci_scope.py`. The historical changes must select `preview`, embedded files must select a check that actually stages or reads them, and the unrelated note must retain its narrow scope.

### 7. Give the owner a way to remove an incompatible theme

The theme picker hides packages that fail validation against the current Home version. IndexedDB still counts them toward eight packages and 64 MiB. Eight in-memory revisions of a real theme verified on a matching Home version. With the older Home version the picker exposed only Classic in the fixture. The owner's Remove action lives on individual visible rows. [Compatibility check](../../../launcher/theme-data.js#L865) · [Picker](../../../launcher/theme-manager.js#L276) · [Cache limit](../../../launcher/theme-store.js#L277)

- Extend `tests/themes/video-cache.cjs` and `tests/themes/installed-previews-ui.cjs` with eight downloaded themes requiring a newer Home, followed by rollback and an attempt to add a compatible ninth package.
- In `theme-store.js`, `theme-manager.js` and `theme-panel.js` under `launcher/`, expose a removable entry for each unavailable record, identified by its storage key. Use a safe localized label and give it only the removal action. Continue validating all theme data before preview or application, and preserve existing active/trial protections.
- Exercise the picker in both editions. Cancel must retain all eight entries. After explicit removal of one, the compatible package must install and the other seven must remain. Include a record with incomplete file data so one bad entry can also be removed.

### 8. Retire superseded Android payload extractions

The Android service names its extraction directory after the manifest hash. It rebuilds an incomplete copy at the current hash and leaves directories for earlier hashes in private storage. Each APK upgrade with a changed manifest can add a full payload. One available local payload was about 304 MiB. This measures the example payload only. [Extraction and lifetime](../../../android/app/src/main/java/com/cleanyourtv/android/InstallerService.kt#L123)

- Extend `android/app/src/androidTest/java/com/cleanyourtv/android/OperationChecks.kt` with three synthetic manifests A, B and C, an interrupted B extraction, and populated profile and recovery fixtures.
- Under the existing single-operation ownership in `InstallerService.kt`, retire only identified, superseded payload directories after the replacement is ready and references have been accounted for. Preserve all data needed to resume an interrupted operation. Ensure cleanup is retryable and keeps the working payload when replacement fails.
- After A → B → C, retained copies must have a documented bound, with an explicit reason for any copy pinned by recovery. Repeating C must reuse it. Compare profiles, identity fixtures and pending receipts before and after the upgrade byte-for-byte.

### 9. Make the downloadable ZIP and TAR.GZ stable across assembly retries

The release assembler writes verified payloads into a fresh temporary tree. ZIP members inherit mtimes or the current ZIP creation time, and the TAR.GZ writer records filesystem and gzip metadata. A fixed-content ZIP entry created under two clocks produced two SHA-256 values. Retrying assembly can therefore change a draft download's digest. This observation concerns the two outer bundles. [Archive writers](../../../scripts/assemble-release.py#L274) · [Draft upload](../../../.github/workflows/release.yml#L125)

- In `tests/setup/test_automatic_release.py`, assemble both outer archive types from a small fixture twice with different clocks, directory mtimes and umasks. Include a script with its executable bit set.
- In `scripts/assemble-release.py`, use one timestamp derived from the selected source commit, deterministic ordering, explicit ZIP/TAR member metadata and a deterministic gzip header. Preserve intended executable bits, directory structure and the inner IPK bytes.
- Compare both archive hashes and extracted file modes and contents. A changed input byte must still change the corresponding digest. Use the fixture for this test without dispatching a candidate.

### 10. Follow the catalog rule for conflicting SDK and platform versions

The catalog specifies that an explicit SDK determines the group when the owner supplies conflicting versions. The shared parser reads only the first numeric token. For the synthetic input `25; SDK 11.2.0` it returned `25`; by the project's own mapping SDK 11 belongs to `26`. Both the README generator and the site consume this function. The probe establishes a parser mismatch, without attributing a wrong result to a particular device. [Catalog rule](../../../docs/COMPATIBILITY.md#user-reported-working-tvs) · [Parser](../../../website/src/lib/webos.mjs#L2)

- Add a small table in `website/scripts/verify.mjs` for `25; SDK 11.2.0` → `26`, `SDK 11.2.0` → `26`, `4.5` → `4.5-5` and a missing value → `unknown`.
- In `website/src/lib/webos.mjs`, give a recognized explicit SDK precedence, then use the existing platform mapping when only a platform is supplied. Keep the original reported text visible in each entry.
- Run the table and the normal website build with `npm run build --prefix website`. Verify that the same fixture appears in the same group in the README and website, and that the existing catalog and anchor links still resolve.

## Follow-up findings from implementation review

These two offline checks used temporary directories and synthetic app inventories. They supplied the acceptance cases for the follow-up implementation.

1. **The source build can carry icons from the previous TV.** Run the actual sync twice in the same launcher directory, first with `alpha` as its only app and then with `beta`. The resulting `apps.js` contained only `beta`. The directory produced by the shell build's web staging function contained both `icons/alpha.png` and `icons/beta.png`. The filenames also carry app IDs. Generate app-owned artwork in a clean location or stage only the icons referenced by the current inventory. Test two successive devices, a failed second sync and preservation of built-in assets. [Source sync](../../../sync-apps.py) · [Shell build](../../../scripts/build.sh) · [Web staging](../../../scripts/tv_web_build.py)
2. **An interrupted web stage discards the last successful output.** Start with a complete output directory, compile two fixture files, and inject a write error on the second file. The previous output disappeared and only the first new file remained. This affects the intermediate staging directory. Build into a temporary sibling, restore the previous directory if replacement fails, and delete temporary files after success or failure. Test failure during a write and during the replacement, then compare the previous output byte for byte and verify that a successful retry installs the full new stage. [Web staging](../../../scripts/tv_web_build.py)

### Follow-up implementation and verification

**Source inventory and icons.** The source installer checks the mandatory launch-point and input replies before replacing the saved inventory. A rejected launch-point request followed by successful tuner discovery used to overwrite the old list with just the tuner. The regression cases distinguish this failure from a successful empty launch-point response with an installed tuner. Publishing the new inventory and reading it for staging now use the same per-source lock and recover an interrupted update. Even an older checkout with leftover icons contributes only artwork referenced by the current inventory.

The ordinary shell installer also holds a lock for the full run in a checkout. With the first run paused after sync, two fixture installers previously both submitted the second TV's inventory. The regression tests pause at build and at launch, check that the second installer exits before changing shared files, and check that it can retry after the first exits.

The combined check used the real source sync with two synthetic TV inventories, followed by `scripts/build.sh`, Zig 0.14.1 and LG CLI 3.2.6 on macOS. The Home IPK contained only the two generated icons for the second TV. The common app had the second TV's image, the bundled fallback matched the repository bytes, and an extra leftover icon placed in the source before the build was absent.

**Web staging.** Writes and compilation take place before promotion. A failed second file write or a failed promotion preserved the last complete output byte for byte. After a process exit in the gap between the two directory renames, the next invocation restored the old tree before compiling again. A concurrent writer was refused. Missing input directories and unreadable subdirectories now stop the build and preserve its previous output. The real CLI also replaced a 720p stage with a 1080p stage and removed a file present only in the previous stage. These checks cover local development builds and process interruption. Native Windows and sudden power loss were outside this run. [Staging behavior](../../TV-WEB-BUILD.md)

## Further audit on 21 November

| Priority | Observation | Next change and acceptance case |
| --- | --- | --- |
| 1 | The source installer's SSAP pairing store loses entries on overlapping saves. Two synthetic registrations both read a store containing one earlier TV. After both succeeded, the store contained the earlier TV and only the last new TV. A separate interrupted JSON write made the whole previous store unreadable. | Serialize the read, merge and replace while saving a successful registration. Write the replacement to a private temporary file and preserve the old file if the write fails. Keep interactive pairing outside the lock. A test should retain all three synthetic entries and compare the old file byte for byte after an injected failure. [Pairing store](../../../lgtv.py) |
| 2 | Android staging copies untracked Python modules from the checkout and retains obsolete files at the top of the generated Python and asset directories. In a temporary Git fixture, a local `cytv/local_notes.py` was copied on a clean stage. After a second run an obsolete test module and asset were still present in the directories consumed by Gradle. | Select maintained runtime sources explicitly and rebuild the generated inputs owned by the task. Check that clean and incremental staging have identical member lists, that removal of a source removes its generated copy, and that the packaged bridge still imports. This observation covers local staging. Published APK contents were outside this check. [Android stager](../../../android/stage.py) · [Gradle source sets](../../../android/app/build.gradle) |
| 3 | The two No-root Updater builders select different inputs from a working checkout. Two harmless untracked notes, one in the app and one in the service, appeared in the IPK produced by the shell script with LG CLI 3.2.6. The Python builder's IPK contained neither. The packages had 44 and 42 regular files respectively. | Give both builders a shared selection of maintained sources and required generated assets. Compare app and service members of both IPKs, including trust material and licensing files, with untracked notes present. This check used local development packages. [Shell builder](../../../scripts/build-updater.sh) · [Python builder](../../../scripts/build-cytv.py) |

### Repairs verified on 21 November

1. **TV pairing.** Successful source-installer registrations now reread and merge the saved keys under a process lock and atomically replace the JSON. Eight independent writers starting from one existing entry preserved all nine synthetic entries on macOS. The replacement had mode `0600`. Eight regression tests covered overlapping approvals, legacy key reuse, first pairing, and failures while reading, writing or replacing the store. Truncated JSON and valid JSON of the wrong type survived byte for byte. [Pairing regressions](../../../tests/cytv/test_lgtv.py)
2. **Android APK.** The previous incremental debug APK contained an untracked checkout module, an obsolete generated module and an obsolete asset. All three disappeared after rebuilding the same checkout with the fix. Adding the unchanged checkout module to the Git index included it in the next APK, and removing it from the index excluded it again. Adding stray files directly to the new generated directories also triggered cleanup. Clean and incremental APKs matched on asset and Python archive member names. The debug build used a synthetic TV payload. The packaged Python bridge, CLI dispatch and payload retention passed instrumentation on a local Android emulator. [Android build inputs](../../../android/DEVELOPMENT.md) · [Instrumentation](../../../android/tests/native.py)
3. **No-root Updater IPK.** Both entry points use the same maintained app, service, font and license list. LG CLI 3.2.6 packages the precompiled JavaScript without a second minification pass. With six extra local files present, including malformed app JSON, the two IPKs each contained 42 regular files. All 25 app files and 16 service files matched byte for byte, including the release key, CA bundle, licenses and fonts. The remaining file, `packageinfo.json`, differed only in whitespace. The packagers retained their respective control fields and archive attributes. The Python IPK also matched the clean baseline byte for byte. [Shared inputs](../../../scripts/no_root_assets.py) · [Packaging regression](../../../tests/setup/test_update_ui_package.py)
