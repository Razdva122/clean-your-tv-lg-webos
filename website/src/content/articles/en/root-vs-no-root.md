---
lang: en
topic: root-vs-no-root
title: Root vs No-root for an LG webOS launcher
description: Choose the right Clean Your TV edition for your LG webOS TV. Compare access requirements, Developer Mode upkeep, Home control and recovery before installing.
updated: '2026-11-09'
---

Choose No-root if your LG TV uses Developer Mode. Choose Root only if it already has working root access and compatible services. Both Clean Your TV editions provide the same Home interface and run on the TV after installation. The installer does not obtain root access or flash firmware.

## What does No-root require?

No-root uses LG Developer Mode, Key Server and local pairing during setup. Home Helper runs on the television and handles the Home button where the device and firmware support it. You do not need to leave a computer or phone running for daily use.

The ongoing requirement is Developer Mode: extend its session before expiry. LG warns that apps installed through Developer Mode can be removed when it is disabled or expires. The project's automatic renewal option is optional beta and off by default; do not treat it as a guarantee. Read the [Developer Mode guide](/clean-your-tv-lg-webos/en/articles/lg-developer-mode/) before relying on this edition.

## What does Root require?

Root uses existing root SSH access, compatible TV services and supported input/runtime capabilities. Root access alone does not establish compatibility. The installer checks the environment; do not bypass a rejected prerequisite or replace system runtimes to force a pass.

Root has separate packages and Home routing. Do not enable Developer Mode on top of an existing rooted setup, and stop No-root Home Helper before using Root routing. Choosing an edition is about the access you already have, not choosing a button that will root the television.

## Compare upkeep and recovery

- **Daily use:** both editions run on the TV, with apps and themes in the launcher.
- **No-root upkeep:** keep Developer Mode active and preserve the Helper's required pairing and connectivity.
- **Root upkeep:** keep independent recovery services and their required runtime available. Update availability depends on the installed edition and supported update path; root access alone does not enable OTA.
- **Emergency exit:** current supported editions use three short Home presses within two seconds. Home Helper through 0.6.13 instead uses a two-second hold.

After an emergency stop, restarting persistent routing is an explicit action. In No-root, open Home Helper and choose Start Helper; in Root, use Change Home in Home settings. See the [edition comparison](/clean-your-tv-lg-webos/en/editions/) and [recovery help](/clean-your-tv-lg-webos/en/help/#home-button).

## Check your television before installing

Read the [compatibility page](/clean-your-tv-lg-webos/en/compatibility/) with your exact model, firmware, webOS and remote in hand. Reported results belong to a specific configuration. Test Home, app launching, sound, standby and cold boot separately after setup. A package installation is not proof that all of them work.

Use the [published installer and installation guide](/clean-your-tv-lg-webos/en/install/). If you already have a working setup and want to switch editions, follow the documented transition and removal steps instead of installing one over the other.

## Sources and next steps

- [Project edition comparison](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Project requirements and known limits](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [What a different home screen changes](/clean-your-tv-lg-webos/en/articles/change-lg-webos-home-screen/)
