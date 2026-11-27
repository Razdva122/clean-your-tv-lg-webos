# Issue 830 edition transition verification

Development base: `da99072c` (`release/next`). This record covers the
Root SSH installer path from a completed Root removal, through No-root and its
resumed removal, to fresh Root setup. Published failure evidence comes from
[#830](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/830#issuecomment-7184494697).
The affected TV is an LG OLED48A19LA with firmware 03.53.45, SDK 6.5.3 and
Magic Remote. On Windows 11, CYTV 0.24.1 installed Home 1.20.7 and Helper 0.9.4.
Removal first stopped at `home-readback`. CYTV 0.24.3 resumed the same operation
and stopped before removing packages, now with `ValueError`.

## Cases

| Case | Expected result | Evidence and disposition |
| --- | --- | --- |
| T01. No-root after verified Root removal | The installer starts the No-root successor using a bound completion record. | The existing installer handoff cases passed with modeled TV state. The owner previously reported a working No-root install on the affected TV, with the screensaver off. |
| T02. Resume the original failed uninstall | Keep the removal identity, prove stock routing, and reach `verified-clean`. | Replayed the two released failure points and the corrected coordinator and finalizer. The predecessor contains real-shaped cancellation markers and locks. Unknown files, unfinished successor proof, foreign filters and unrelated LS2 failures still block. |
| T03. Verify LG Home on the affected firmware | Capture the factory native route and verify it again after package cleanup. | The actual finalizer passed capture, completion and readback using the extracted LG Home ELF, manifest and `systemUi.js`. LS2 replies, mount metadata and the config service response were modeled. Physical Home readback awaits a matching device and candidate. |
| T04. Fresh Root after the same removal | The installer accepts the completed cleanup, rechecks the route and starts a new Root operation. | The native installer coordinator regression refuses changed routing, then accepts the same removal receipt with valid routing and passes the new clean predecessor to installation. Native deployment is modeled. Independent Root admission, installation and recovery suites passed. |
| T05. Root Home, Settings, standby, reboot and return to LG Home | Root starts and restores stock control through the intended physical and network input paths. | C1 runtime cases passed with modeled input and boot state. On the affected TV these checks depend on T02 and T04. The locally verified payload has no corresponding installed hardware candidate. |
| T06. Project C3 baseline | Read the initial edition, Helper state and actual network Home destination before a candidate run. | OLED55C3RLA, 43.21.71 / SDK 11.2.0, No-root Home present, Root Home absent, Helper 0.11.0. Starting at Media Player, one network Home opened and stayed on LG Home. Helper reported enabled startup but no running controller. Bounded log readback showed a terminal Stop and a successful LG Home launch. The Stop remained in effect. No install, removal or restart was performed. C3 exposes `defaultApps`; it cannot supply the missing-setting device acceptance in T03. |

## Firmware and fix

LG publishes [03.53.45 for OLED48A19LA.AVS](https://www.lg.com/de/support/produkt-hilfe/cs-OLED48A19LA.AVS/).
The official ZIP passed integrity testing, SHA-256
`41dbd700479bea137fb0b3aa4bc9f18923ea9f9a9f1275025b259dc89a32f20f`.
Pinned epk2extract
[`a0ccd8a4`](https://github.com/openlgtv/epk2extract/tree/a0ccd8a4b4f48d05675a4cddd233f8780ee36767)
ran with networking disabled and reported successful segment verification.
The extracted build is `03.53.45.01-HE_DTV_W21U_AFADATAA`. The native ARM
LG Home SHA-256 `3e9430ae83644fda1a6cb8c052f121ffb2b0a53054154fe15f554795f3824755`
matches the hash reported in [#615](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/615).
Factory files establish the executable, app descriptor and vendor filter
implementation. The owner's standard diagnostic supplies the live LS2 reply.
The test does not run the full firmware or reproduce the live LS2 database.

The v1.29.1 settings classifier already recognizes the missing setting.
A resumed removal from a No-root successor was still rejected by the
stock-profile eligibility check. The coordinator and finalizer now authenticate
the completed predecessor/successor relationship and admit only exact inert
cancellation markers and checked lock files. Audit compaction preserves the
difference between those markers, absent journals and malformed journals.
Package, startup, routing and foreign-state checks remain in force.

The offline pass accounts for all six cases. The remaining device portions
require a selected QA artifact, an operational starting state on the project
test set and the affected A1 for the firmware-specific check. The current
reporter diagnostic is sufficient for this offline reproduction.
