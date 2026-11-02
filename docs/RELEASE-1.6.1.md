# Preliminary Root QA for issue 171

Unpublished test branch based on v1.6.0, with only the reviewed power-stage
handler correction from PR #255. Root/infrastructure 0.7.1 and updater 0.4.1
are QA package identities. This does not select the next public release scope
or version, publish a feed, or accept the fix on hardware.

Retain shutdown proof only after explicit standby in a continuous observed ON
stream; preparation cancels prior proof/wake without erasing that ON baseline.
All existing intent, health, failsafe, emergency and foreground gates remain.

Signed-package standby, controls/audio, emergency, Off persistence, cold boot
and retained rollback acceptance remain pending. The original no-proof observer
exit is a separate unresolved acceptance boundary.
