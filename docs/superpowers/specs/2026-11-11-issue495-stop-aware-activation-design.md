# Simple Stop-aware setup (#495)

Owner-selected behavior: successful setup turns CYTV Home on; a new Stop during
setup wins. No legacy migration or private Stop journal integration is selected.

Use one fixed `state/stop-generation` file, atomically replaced with a fresh
128-bit random token at every Stop. An initialization token is distinguishable
from a Stop token. Missing, malformed or inaccessible state refuses activation;
it is never treated as permission to reset a Stop. This is nonsecret cancellation
state under existing Helper storage rules, not a new authority or endpoint.

New install plans/capsules bind the generation captured before package work.
Fresh installs with no state bind the empty-baseline condition and can adopt only
a fresh initialization token with no Stop. Configuration verifies package/state
readback and launches Helper with an explicit setup-start request carrying that
baseline. No historical package request is replayed.

Helper compares the baseline before/after clearing prior latch/control state,
turns Home On, then checks again before Home launch and relay startup. The relay
checks the same baseline immediately before/after input grab and before forwarding
input. Stop producers always replace the generation before publishing legacy
latches, so removing an old latch cannot erase a new generation. On mismatch,
release input and retain blocking; do not automatically retry setup activation.
Only explicit owner Start is a new intent. Existing unrelated input cleanup stays.

All C/controller/explicit Stop paths publish generations. The token file has
constant bounded size: no event history, rotation, private broker, legacy-state
migration or separate protocol enrollment. Reuse checked state storage and the
existing trusted-source staging; never execute TV-retained support code.

Report packages, launch request, observed startup and physical Home separately.
A new Stop is an activation cancellation, not a package failure or startup pass.
Actual activation needs process/readiness and Home On readback; an ACK alone is
not device acceptance. Lost-profile guidance retains explicit verified removal,
with separate #498 fixing execute-only tmp. Hold both changes for the next release.

Test old/new generation, identical consecutive Stops, races around latch removal,
relay acquisition, corrupted/missing generation, interrupted/closed operation,
Home initially Off, unknown replies, source staging and all locale projections.
Changed native consumers require C input/cleanup and legacy Node runtime checks;
no TV or full candidate dispatch is authorized by this development task.
