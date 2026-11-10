# Website candidate integration — 2026-11-11

[PR #470](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/470) merged into
`release/next` at `5253dd6dff0b8bcbef8504c5da73811ccacbbf60`. The candidate now includes
the redesigned landing, recorded animated previews and 52 articles across 13
languages, with localized indexes and search metadata. The interactive demo stays
on its own page. See the [design review](../../website/REVIEW-2026-11-10.md).

The checked PR head `4e516ac8b8de7271d62d5f8e174232cf3db6e4f3` and merge commit
have identical source trees (`3bdb5ea0d4a62c1dd98958226e6de2cd04af3e66`).
[Focused CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42885556867)
and [website build/browser acceptance](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42885556864)
passed. The earlier Root identity fixture failure was already corrected in the
integration branch; the PR was updated to that branch before these checks.
The final implementation diff contains only `website/` paths.

The committed inventory adds #470 and preserves #488, #492, #493 and #494 and
their existing issue associations. Candidate version selection remains pending;
no component versions or selected build were changed. This website integration
does not require new TV-package inputs or provide physical-device acceptance.
The unfrozen candidate's remaining gates remain in
[PR #491](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/491).
Production website deployment still follows the existing `main` workflow.
