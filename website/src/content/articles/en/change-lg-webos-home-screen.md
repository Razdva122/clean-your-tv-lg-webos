---
lang: en
topic: change-lg-webos-home-screen
title: How to change the home screen on an LG webOS TV
description: Customize your LG webOS home screen with Clean Your TV. Learn what a launcher changes, how to choose an edition and what to check before installation.
updated: '2026-11-09'
---

Clean Your TV is an alternative home screen for LG webOS TVs. It puts your apps in your preferred order and offers themes and a customizable dock. It runs on the TV after setup, so you can turn your computer off. Whether it can handle the Home button depends on your TV, firmware, remote and installation method.

## What can you customize?

The launcher changes the screen you use to find and open TV apps. You can arrange favorites and choose a layout such as Classic, Liquid Glass or Ribbon. Try the [browser demo](/clean-your-tv-lg-webos/demo/) to compare layouts before installing anything. TV controls in the demo are simulated; it cannot test compatibility with your television.

An alternative launcher does not replace webOS firmware, unlock paid streaming or remove advertising inside other apps. Picture settings, inputs and streaming services remain separate parts of your TV. Read [what changes about advertising](/clean-your-tv-lg-webos/en/articles/lg-tv-home-screen-ads/) if a quieter home screen is your main goal.

## Which installation method should you choose?

Use No-root on a TV with active LG Developer Mode. Its on-TV Home Helper handles the Home button where supported. Developer Mode must remain active; expired sessions can cause sideloaded apps to be removed.

Use Root only if the television already has working root access and meets the runtime and service requirements. The Clean Your TV installer does not root the TV. Do not enable Developer Mode over an existing rooted setup or run both Home routing methods together. The [edition guide](/clean-your-tv-lg-webos/en/articles/root-vs-no-root/) explains the trade-offs.

## Before changing your working setup

1. Record your exact model, firmware, webOS version and remote type. Compare them with the [requirements and reported TV results](/clean-your-tv-lg-webos/en/compatibility/); a report applies to its recorded configuration.
2. Follow the [installation guide](/clean-your-tv-lg-webos/en/install/) and use the published installer linked there. Keep the TV and installer device on a network where they can communicate during setup.
3. After setup, check app launching and Home, then sound, standby/resume and cold boot separately. Installing a package successfully does not verify those behaviors.

## How do you return to LG Home?

In current supported editions, three short Home presses within two seconds trigger the emergency exit. Older Home Helper through 0.6.13 uses a two-second Home hold. Opening LG Home once and disabling persistent Home routing are different actions; use the [recovery instructions](/clean-your-tv-lg-webos/en/help/#home-button) for your installed edition. Keep a recovery route available before changing startup behavior.

## Sources and next steps

- [Project edition and control reference](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Project installation and prerequisites](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode: keeping a No-root setup available](/clean-your-tv-lg-webos/en/articles/lg-developer-mode/)
