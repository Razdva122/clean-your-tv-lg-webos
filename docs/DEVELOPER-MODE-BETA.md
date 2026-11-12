# Developer Mode auto-renewal (Beta)

Introduced in Home 1.1.0 / release v0.7.0. New No-root installations through
existing root SSH hide the **Developer Mode** tab.
**Off by default.** On a TV set up through LG Developer Mode, open **Home settings →
Developer Mode → Turn on auto-renewal** to opt in. Older packages label this **Enable Beta**. The Settings panel also contains **TV settings** for the original LG settings screen.

This feature extends the Developer Mode **session**, not your LG account. It uses an on-TV JavaScript service and requests LG directly; it does not send your session token to a community server or need an always-on computer/router. Your TV must already have an active, readable Developer Mode session.

**Real renewal on unrooted TVs has not yet been confirmed. Keep monitoring the timer in the official Developer Mode app and extend manually when needed.** Enabling Beta is not proof that your session has been extended.

## What happens

- Enabling registers an hourly system activity and checks the session. The activity survives normal service termination/reboot on the tested setup; it is independent of Home Helper.
- Healthy sessions are checked at most once a day. When seven days or less remain, the service requests renewal and checks the remaining time again.
- Only a valid countdown increase of more than one minute produces **Renewal confirmed**. A generic successful response is insufficient.
- Network errors back off. The hourly activity means short retry delays are normally rounded up to the next hourly callback. **Check session** respects the same cooldown; it does not force repeated renewal.
- **Turn off auto-renewal** (formerly **Disable Beta**) saves the disabled setting and cancels its own activity. An already transmitted request cannot be undone, but subsequent requests are gated. If disabling cannot be saved, the UI warns you to retry.
- Triple Home continues to stop Home Helper only. Renewal does not resume the helper, clear emergency-stop markers, launch another app, or block launcher startup.

A TV that stays off/offline beyond the session limit cannot renew locally. Login expiry, account changes or LG API changes may require manual action. This feature does not bypass LG's separate offline-reboot restrictions. No wake-from-standby guarantee is made.

## Status and privacy

The panel displays enabled/off status, the last check, an estimated countdown and the last confirmed renewal. The service reads the local token per attempt; it does not include it in UI status, diagnostics or persisted state. HTTPS uses certificate verification and fixed LG endpoints; redirects are not followed.

**Diagnostics** displays a small report you can share in a [Beta feedback issue](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new?template=developer-mode-beta.yml). Add your TV model, firmware and what the official timer showed before/after. Never post account credentials, session tokens, token files or raw authenticated request URLs.

Next-candidate preparation adds bounded settings/renewal I/O and Home RPC failure
categories to that existing screen, with the actual service version. Unexpected
operation failures are distinguished from storage failures. See
[Home settings diagnostics](SETTINGS-DIAGNOSTICS.md) for collection and evidence
limits; this is not in published v1.2.0 and does not repair or verify C5 access.

## Validation so far

- Automated tests: renewal responses, countdown parsing, concurrent calls, rate limits, errors, disk writes, opt-out races, schedule failures and UI navigation.
- Isolated mock package on LG OLED55C3RLA / 43.21.71: JavaScript service execution, real disk state across process termination, a one-shot Activity Manager callback, and a persistent one-shot callback after software reboot.
- **Still awaiting community validation:** real LG renewal, stock no-root token permissions, the integrated hourly recurring schedule, missed deadlines/offline recovery, and power-loss behavior. The previously tested one-shot schedule is not evidence that every recurring schedule works on every firmware.

## Installation / updating

Install the complete Home IPK, which includes `com.gathin.tvhome.renewal`. A copied HTML/JS UI alone cannot provide this service. For a personalized build:

```sh
ares-package launcher renewal-service -o dist
```

The generic release Home package has an empty app inventory. Follow [installation](INSTALL.md) to sync and rebuild your own inventory; do not overwrite a personalized installation with the generic asset expecting its app list to remain.

If downgrading to Home 1.0.x, **disable Beta first**. Updating or reinstalling can reset opt-in/state depending on the installer; inspect the setting afterward. The fallback is always manual extension in Developer Mode.

## Implementation references

The Check/Reset endpoints are community-used LG endpoints, not a promised stable public API. See [webOS Dev Manager](https://github.com/webosbrew/dev-manager-desktop), [LG Developer Mode documentation](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app), and [Activity Manager scheduling](https://www.webosose.org/docs/reference/ls2-api/com-webos-service-activitymanager/). OSE documentation does not itself establish TV firmware compatibility.
