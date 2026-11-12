# LJ622V Home trial

This manually started 60-second trial targets Root Beta on firmware that
renders the stock Home ribbon inside Surface Manager. The `32LJ622V-ZB` with
firmware `06.10.60` is the device that motivated the trial.
The trial uses Home Helper's ARM32 Magic Remote relay and starts the installed
Root Home app on the release of a short physical Home press. The relay reports emergency exit only
after releasing the grabbed input. A separate Python process waits for that
exit, finishes any outstanding launch request and opens the LG ribbon if needed.

On this firmware `showHome` toggles the ribbon and starts LG's auto-hide timer.
The trial checks Home focus before calling it and reads the focus again after
the call. A timeout does not cause a second toggle. If the check or open fails
after the relay exits, press the now-released physical Home key to open LG Home.

Build the relay from the repository root with Zig 0.14.1. The state definitions
isolate the relay lock and stop state. `CYTV_HOME_ON_RELEASE` makes the third
Home release end the relay without submitting another launcher request.

```sh
zig cc -target arm-linux-musleabi -Os -static -s \
  -DCYTV_HOME_ON_RELEASE \
  '-DCYTV_RELAY_STATE="/var/lib/clean-your-tv-lj622v-trial"' \
  '-DCYTV_GENERATION_DIRECTORY="/var/lib/clean-your-tv-lj622v-trial"' \
  native/prototype/relay.c native/prototype/filter.c -o relay
```

On an authorized test TV, use an existing root session, Python 3.9 or newer,
and an already installed, launchable `com.cleanyourtv.root.preview`. Turn off
other remote remappers before starting. Stage the relay and the trial script,
`transport.py` and `profile_plan.py` from `root-edition/runtime` in a new
root-owned directory with mode `0700` at `/var/lib/clean-your-tv-lj622v-trial`.
Give the relay mode `0700`. Run `lj622v_home_trial.py` using the available
Python interpreter in the foreground. The trial requires confirmed absence of
System Profile and KeyFilters, a registered Root web app and a readable ribbon
state. Root Beta selection has its own Node runtime policy. A timeout or
ambiguous rejection fails the check.
It then checks the Magic Remote input/output pair and the advertised Home key
before grabbing input. A failed check leaves normal input handling in place.
The controller emits structured `root-ribbon-relay` events on standard error
for each check, capture readiness, relay exit and ribbon restoration. These
events omit raw replies, paths and remote input history.

With the Magic Remote, confirm normal navigation, then press Home once from
another app and check for a visible LG ribbon frame. With the Root Home UI
unresponsive, press Home three times within two seconds and confirm the LG
ribbon appears and the next physical Home is handled by LG. Repeat from the
trial's stopped state only after the test TV is responsive. Ctrl+C or the
trial deadline ends the relay. Remove the private trial directory when done.

Physical Magic Remote behavior, the private Luna calls and the focus readback
still need verification on the target TV. The relay's standard IR path is
passive and cannot prevent a flash. The ordinary Root installer does not
select this trial.

Other projects illustrate the trade-off. [Lightkeeper](https://github.com/chiotas/lightkeeper#the-home-key-on-webos-2-and-3)
reads remote events passively on webOS 2 and 3. [Glasshouse](https://rorygallagher2024.github.io/glasshouse/development/TV-RESEARCH/)
reports opening the stock ribbon on webOS 4 through a synthesized Home event.
[LG Input Mapper](https://github.com/fivefold3/lginputmapper) grabs the Magic
Remote and forwards unmapped events. None of these observations establishes
compatibility with the LJ622V input pair or its private Luna services.
