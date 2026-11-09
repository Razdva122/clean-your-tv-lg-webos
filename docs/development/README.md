# Development and technical references

- [Focused CI checks](CI-CHECKS.md): routing boundaries, safety gates and measurements.

[User documentation](../README.md) · [Contributing](../../CONTRIBUTING.md) ·
[Historical records](../history/README.md)

These references are for source builds, diagnosis and maintenance. You do not need
to run their commands to use the graphical installer. Read the current user guide
before using a low-level recovery or installation procedure.

## Build and run from source

- [Fast TV development](TV-DEVELOPMENT.md): compiled UI feedback, direct signed
  TV artifacts and explicit device preflight without waiting for desktop builds.
- [Build requirements and packages](../BUILD.md), [TV web compatibility](../TV-WEB-BUILD.md), and [desktop build/previews](DESKTOP-BUILD.md).
- [CLI reference](../CLI.md), [manual installation](../MANUAL_INSTALL.md), [Android development](../../android/DEVELOPMENT.md).
- [Root bundle](../../root-edition/package/README.md), [Root development](../../root-edition/DEVELOPMENT.md), [Root runtime contract](../../root-edition/runtime/README.md).
- [Contribute a theme](CONTRIBUTING-THEMES.md): PC preview, LAN testing, fixed distributions and Showcase PRs.
- [Home CSS styling surface](THEME-CSS.md): visual hooks, engine geometry and trusted dialog boundaries.
- [Video wallpapers and Wallpapers settings](WALLPAPERS.md): next-release media contract, automatic quality, local cache ownership and acceptance limits.
- [Homebrew Installer](../../homebrew/README.md) is **unreleased**; [packaging and promotion gates](../../homebrew/DEVELOPMENT.md).

## Understand behavior and diagnose failures

- [Early Root admission and connection guidance](INSTALLER-PREFLIGHT-HELP.md): existing Home-interface contract before runtime preparation, typed localized advice and unchanged recovery/trust authority.

- [Root native startup input](ROOT-NATIVE-INPUT.md): owned EIM lifecycle and acceptance limits.
- [Experimental C1 native gate](C1-NATIVE-GATE.md): separate backend, independent native recovery and physical acceptance limits.
- [Theme development status](THEMES.md), [Home styling parts and CSS rules](THEME-CSS.md).

- [Home settings transport](HOME-CONTROL-TRANSPORT.md): service-owned IPC, packaging and rollback requirements.
- [Helper relay cleanup outcomes](HELPER-RELAY-CLEANUP.md): relay failure reporting, blocked recovery and synthetic evdev verification.
- [Home installation gates](HOME-INSTALL-GATES.md): control-file ownership and Root firmware preflight fixes, packaging requirements and retained-recovery limits.
- [Home graphics resolution](HOME-GRAPHICS-RESOLUTION.md) and [passive remote diagnostic](PASSIVE-REMOTE-DIAGNOSTICS.md): candidate 720p layout/build support and read-only evidence; physical IR mapping remains unverified.
- [Companion entry points](../COMPANION-APPS.md), [Helper diagnostics](../HELPER-DIAGNOSTICS.md), [Home/settings diagnostics](../SETTINGS-DIAGNOSTICS.md).
- [Root doctor](../../root-edition/DOCTOR.md), [current Root limits](../../root-edition/STATUS.md), [Root validation](../../root-edition/TESTING.md).
- [Separate installer outcomes](INSTALLER-OUTCOMES.md): package proofs, launch/runtime evidence and explicitly owner-reported Home.
- [Installer recovery journey](INSTALLER-RECOVERY.md): separately confirmed recovery, existing authority guards and frontend outcome semantics.
- [Clean removal and reinstallation](CLEAN-REMOVAL-REINSTALLATION.md): final cleanup fences, read-only completed retries and a bound Root-SSH No-root successor.
- [Installer diagnostic evidence](INSTALLER-DIAGNOSTICS.md): primary-error retention, safe status/check projections and private host correlation.
- [Individual Root recovery handoffs](ROOT-RECOVERY-HANDOFFS.md): per-issue decisions, authentication blockers and pending-operation diagnostic boundaries.
- [Read-only Root admission](ROOT-READONLY-ADMISSION.md): private owner handoff, isolated inspection and unsupported firmware boundaries.
- [Passive Root worker diagnostics](ROOT-PASSIVE-DIAGNOSTICS.md): bounded saved-error categories without code staging, routing calls or cancellation admission.
- [No-root package authority](NO-ROOT-PACKAGE-AUTHORITY.md): #201 endpoint distinctions, preserved pending receipts and unsupported reconciliation.
- [No-root parent-directory packaging and real opkg lab](../history/2026-11-04-opkg-parent-reproduction.md): next-cycle extraction fix, isolated reproduction and retail acceptance limits.
- [Interrupted Root installation](../ROOT-INSTALL-CANCELLATION.md), [private Python](../OPTIONAL-PYTHON.md), [native cache cleanup](../WAM-CLEANUP.md).
- [Firmware update control](../LG-FIRMWARE-UPDATES.md), [experimental HDMI sound recovery](ROOT-AUDIO-RECOVERY.md), [Developer Mode renewal Beta](../DEVELOPER-MODE-BETA.md).
- [TLS trust](../TLS-TRUST.md), [icons](../../assets/icons/README.md), [brand assets](../../assets/brand/README.md), [published Helper baseline](../../native/published/README.md).

## Release and update maintenance

- [Release integration flow](../RELEASE-FLOW.md), [release checklist](../RELEASE_CHECKLIST.md), [packaging/signing/publication](../RELEASE-PROCESS.md).
- [Update storage retention](UPDATE-STORAGE.md): terminal-only cache and product staging cleanup, with recovery limits.
- [Current update guidance](../UPDATES.md), [Root updater](../../root-edition/UPDATES.md), [legacy Home-only updater procedures](LEGACY-HOME-UPDATES.md).
- [Private signed Root candidate acceptance](SIGNED-ROOT-CANDIDATE-ACCEPTANCE.md): explicit pre-publication admission without changing the installed supervisor or stable feed.
- [Original 1.3.0 OTA contract correction](ROOT-OTA-13-COMPATIBILITY.md), [update lab runbook](UPDATE-LAB-RUNBOOK.md), [remaining transaction work](UPDATE-TRANSACTION-REMAINING.md).
- [Root cold-boot investigation](ROOT-COLD-BOOT.md), [Home readback boundary](ROOT-HOME-READBACK.md), [AOD preservation](ROOT-AOD-PRESERVATION.md), [Homebrew acceptance matrix](HOMEBREW-INSTALL-ACCEPTANCE.md).

## Evidence and old designs

Dated validation, investigation, design and implementation records describe their
original scope. They are not an alternative set of current instructions. Find them
through [history](../history/README.md); preserve their links and results when
updating a current guide.

Do not append release-by-release stories to user guides. Update the current task
instruction and link a dated record when its evidence matters. Keep unpublished
features clearly separate and retain recovery safeguards. Agent-assisted reports
follow [explicit user consent](../../AGENTS.md#installation-results-and-user-consent).

## Main Home browser preview

After `npm ci`, run `python3 scripts/preview.py` and open `http://127.0.0.1:8765/`.
The **Themes** row above Home contains the 1.7.0 built-ins Classic, Liquid Glass
and Ribbon, plus the active reviewed Showcase versions, including Alpine 1.4.4. Selecting a card applies it in the same Home canvas, including
when switching Root/No-root editions. Community packages are generated from the
hash-verified showcase snapshot and validated by the ordinary ThemeManager;
no author scripts or theme-repository code is executed. Static exports include
the same selector and packages, so selection also works without internet access.
This previews fixed reviewed versions rather than unpublished toolkit edits.
Browser simulations do not establish physical-TV compatibility.

- [Root Node 0.12.2 prototype](ROOT-NODE-PROTOTYPE.md): opt-in host builds and generated-closure tests; Node 8+ gate retained.

## Product website

[Multilingual GitHub Pages development](../../website/README.md) covers Astro,
shared Markdown installation guides, translations, SEO checks and the embedded
launcher demo.

- [Ribbon presentation](RIBBON-PRESENTATION.md): the single full-screen Home lifecycle, own wallpaper and acceptance scope.

- [Single Home C3 regression QA, 2026-11-05](../history/2026-11-05-single-home-regressions.md)

- [Home weather and theme integration](WEATHER.md) — formats, trusted data flow, author styling and fork provenance.
