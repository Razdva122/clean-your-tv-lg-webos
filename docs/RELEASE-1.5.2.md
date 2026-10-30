# Unpublished issue #152 test build

This branch is only a draft build for initial EF950V feedback on Node 0.10.25.
It is not a release candidate, signed OTA approval or public stable release.

Test metadata: cytv 0.6.1, Home 1.6.1 and Home Helper 0.6.21.
The implementation is PR #181, based on the published 1.5.1 source.
Other component versions and all historical signed rollback pins remain unchanged.
Use the No-root installer only; this build does not add Root support.

The compiled Helper has host regression coverage for exact Node 0.10.25 and
0.12.2 alongside current Node. Initial installation, launcher rendering, Home,
Back, held-key release, triple-Home emergency escape, sound, standby, cold boot,
OTA and rollback remain untested on the EF950V. A successful install alone does
not establish these behaviors. Stop on an installer error; do not bypass gates.
