# Single-package Home pilot

The private 1080p pilot has one tile and one bundled JavaScript service. It runs alongside existing editions using the development ID `io.github.razdva122.cytvhomepilot`. The pilot has a separate Russian/English test interface in `single-home/app/`. The product interface in `launcher/`, including its themes, wallpaper and layout controls, still needs to be connected to the bundled service for release. Home opens from its tile. The physical Home button keeps its system behavior.

After installing the project dependencies, build from the checkout root using the project Python environment. Runtime sources must be in the Git index. Select a new output path for each build.

```sh
.venv-cytv/bin/python single-home/build.py build --output build/single-home/pilot.ipk
.venv-cytv/bin/python single-home/build.py catalog --ipk build/single-home/pilot.ipk --base-url https://example.org/private-home --output build/single-home/feed
```

Use the base URL actually serving the private feed. Add its `apps.json` in Homebrew Channel, install the card, then open Home. The owner can pair, view installed applications, and enable or stop the background service in Settings. A service callback can run while HDMI stays in the foreground. Use a distinct numeric `--version` for a selected update test.

For physical acceptance, verify the actual packaged service's harmless storage canary across service exit, upgrade, restart and power loss before submitting a real pairing request. Check a boot-scoped callback receipt before crediting background startup. The [design and acceptance cases](../docs/superpowers/specs/2026-11-28-single-package-home-design.md) define the evidence required for publication.
