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
