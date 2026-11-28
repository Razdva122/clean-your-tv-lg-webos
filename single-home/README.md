# Single-package Home pilot

The private 1080p package installs one tile and one bundled JavaScript service under the development ID `io.github.razdva122.cytvhomepilot`. Its main screen uses the product launcher in `launcher/`, including application artwork, bundled themes, wallpaper and the Home layout editor. The Russian/English setup screen explains that approving the first pairing also starts the service when the TV turns on. The launcher can also open before pairing. Its app catalog becomes available after the TV owner approves the native prompt.

Homebrew Update retains the pilot's pairing. On the first successful catalog read the product Home imports the old pilot tile order, including a deliberately empty selection, if the user has no product layout yet. Later launches use the product's regular layout and theme storage. Other package IDs have their own application data. The physical Home button retains its system behavior.

After installing the project dependencies, build from the checkout root using the project Python environment. Runtime sources must be in the Git index. Select a new output path for each build.

```sh
.venv-cytv/bin/python single-home/build.py build --output build/single-home/pilot.ipk
.venv-cytv/bin/python single-home/build.py catalog --ipk build/single-home/pilot.ipk --base-url https://example.org/private-home --output build/single-home/feed
```

Use the base URL actually serving the private feed. Add its `apps.json` in Homebrew Channel, install the card, then open Home. After pairing, Home shows installed applications. The owner can stop or resume background startup in Settings. Pairing again and updating the package preserve that choice, including an existing pairing with startup off. A service callback can run while HDMI stays in the foreground. Use a distinct numeric `--version` for a selected update test.

For physical acceptance, verify the actual packaged service's harmless storage canary across service exit, upgrade, restart and power loss before submitting a real pairing request. Check a boot-scoped callback receipt before crediting background startup. The [design and acceptance cases](../docs/superpowers/specs/2026-11-28-single-package-home-design.md) define the evidence required for publication.


## Desktop No-root parity

The desktop installer is the reference for the product files and setup. The pilot has a different application ID and controller. A successful pilot install does not qualify the desktop product for publication.

For a private component comparison, run the following with the unpersonalized payload extracted from the verified desktop installer and the URL that will serve the feed. Select the TV's resolution. The feed carries the original Home, native Helper and Screensaver IPKs. Installing the cards individually does not perform the desktop setup steps.

```sh
.venv-cytv/bin/python single-home/build.py desktop-catalog --desktop-payload /path/to/desktop/payload --resolution 1920x1080 --base-url https://example.org/private-home --output build/desktop-reference-feed
```

The [one-tile installer build](../homebrew/build.py) accepts `--desktop-payload` for both offline payload assembly and final packaging. With a compatible single-tile desktop build, it copies both Home resolutions, Helper, Screensaver and the fallback image directly from that build. Release assembly compares the packaged No-root files to the selected desktop installer's payload before including the Homebrew candidate. Retain the existing signed update and rollback contracts.

The public v1.30.0 desktop release uses visible Home and Helper packages. The one-tile installer expects the second-generation product and supervisor. Hiding the v1.30.0 apps would change their IPKs. A single installer entry that deploys those original packages and configures them on an unrooted TV remains an open requirement. Acceptance also requires matching installed files after the per-TV app catalog and connection type are applied, real pairing, Home control, startup and durable Stop.
