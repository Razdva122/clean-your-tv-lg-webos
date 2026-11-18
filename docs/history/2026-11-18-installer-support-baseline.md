# Installer support baseline, 2026-11-18

**Provisional cohort.** Issues opened in the UTC window
`[2026-11-04 00:00, 2026-11-18 00:00)`, with public follow-up through
2026-11-18 11:00 UTC.
The first batch of installer changes has no named public delivery date yet.
For its before/after comparison, let D be the UTC date of verified public
availability of the selected installer artifacts. Use `[D−14, D)` and
`[D+1, D+15)` at UTC midnight and omit publication day. Recollect the two
cohorts using the same rules. For visits and outcomes, cap each cohort’s
follow-up at the same elapsed time after the window ends. Report threads already
open at publication separately from new reports. For new reports, give counts
for the changed installer, older installers and unknown versions.

## Source and coding

Query both open and closed issues by **creation** time. For each result, read the
opening post and all comment pages, retaining their chronological order through
the evidence cutoff. Read any canonical issue linked as a duplicate before
deciding whether it describes the same owner and operation. This query also
returns maintainer work items so the exclusion can be checked.

```sh
repo=Razdva122/clean-your-tv-lg-webos
gh api --method GET --paginate search/issues \
  -f "q=repo:$repo is:issue created:2026-11-04..2026-11-17" \
  -F per_page=100 --jq '.items[].number'
# Repeat these two queries for each returned issue number.
number=409
gh api "repos/$repo/issues/$number"
gh api --paginate "repos/$repo/issues/$number/comments?per_page=100"
# Release exposure is based on published_at:
gh api --paginate "repos/$repo/releases?per_page=100"
```

The snapshot has 96 issues. Exclude 13 maintainer-authored internal issues
(`OWNER` in this sample). Of 83 external records, 60 are eligible after
excluding 22 unrelated or insufficiently specified records and one duplicate
operation (#296 → #295). A `CONTRIBUTOR` association alone never makes a report
internal. Include an owner's concrete desktop, CLI or Android setup, update,
reinstall, cleanup, or removal attempt, including positive installation
results and immediate Home acceptance. Exclude standalone feature proposals,
themes, runtime reports after established setup, TV-only Updater work and
posts where the install/removal goal cannot be established at all. Keep
different owners' reports of the same bug as separate threads. Count each
eligible thread once in each evidenced family, even when many reports or
versions show that family. Restrict later causes to the same support journey.

Published exposure changed throughout the window. Twenty-eight stable releases
were published, from v1.8.2 through v1.24.0. v1.7.1 was already public at the
start. v1.24.0 became public at 23:07:21 UTC on 17 November with desktop and
CLI cytv 0.21.2 and Android 0.20.2 (49). This is the investigation reference
release. No opening attempt identifies it. Of 60 threads, 52 identify an
installer version for the reported first-post attempt and 8 do not. Known cytv
versions span 0.3.0–0.21.1. Use a standard report's `cytv_version` or the
owner's explicit version for that attempt. A standard report has schema 1
and a `cytv_version`. Use the report's action, phase, reason and retained first
failure, where present, to distinguish the original attempt from a later
observation. For multiple distinct original versions retain them together.
The issue denominator is self-selected. Actual installs, usage by platform,
and adoption of any individual build are unknown.
[Public issue query](https://github.com/Razdva122/clean-your-tv-lg-webos/issues?q=is%3Aissue+created%3A2026-11-04..2026-11-17)
and [published releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases).
[Reference release and package versions](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.24.0).

## Results

| Reported family | Threads | Share of 60 | Installer version unknown |
| --- | ---: | ---: | ---: |
| Stalled removal, restore, restart proof or final cleanup (L) | 22 | 36.7% | 2 |
| Unverified package/operation or prior reservation (Q) | 16 | 26.7% | 1 |
| Activation, Helper launch or physical Home during setup (A) | 14 | 23.3% | 1 |
| Root Home compatibility or runtime prerequisites (P) | 12 | 20.0% | 1 |
| Connection, credentials, pairing or changed device identity (C) | 10 | 16.7% | 2 |
| Storage or observer preparation before package submission (S) | 7 | 11.7% | 1 |
| Helper configuration, retained files or Stop state (H) | 6 | 10.0% | 0 |
| Application/input inventory (V) | 4 | 6.7% | 0 |

Families overlap. A storage check can precede a retained `pending-operation`
message. That message alone does not establish a package submission. The four
inventory cases are observed Root installer cases in this sample. They do not
measure the No-root optional-input failure reproduced in integration.

**Repeat visits.** Count each distinct maintainer request that requires a new
TV, installer or TV-connected diagnostic action. Count a batch of compatible
actions as one visit and count a clarifying instruction for the same visit
once. Exclude pure shipping notices, questions answerable from existing
observations, requests to attach an already-saved report, and owner-initiated
attempts. A shipping comment with a new device request counts for that request.

Of 60 threads, the median is **1** request, **24/60** have two
or more and 14 have none. The total is 142 requests.

**Original goal.** Keep setup, reinstall/update and uninstall separate. Use
the owner's stated goal. A return to stock Home on the way to reinstall is an
intermediate outcome. Count completion only from an owner's positive report.
Partial means an original milestone was achieved but the final goal was not
verified. Failed records an explicit unresolved result or abandonment.
Unknown covers missing final owner evidence, even if the issue is closed.
Include a physical Home check only if the opening goal called for routing or
explicit stock-Home restoration. Count owner-described button input and the
actual destination. A package result, network command or inferred route
cannot stand in for it.

| Original goal | Threads | Confirmed | Partial | Failed | Unknown | Physical Home pass / fail / unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Install | 38 | 8 | 12 | 4 | 14 | 5 / 6 / 6 |
| Reinstall/update | 14 | 5 | 5 | 1 | 3 | 3 / 1 / 3 |
| Uninstall | 5 | 4 | 0 | 1 | 0 | 4 / 0 / 1 |
| Unclear | 3 | 0 | 0 | 0 | 3 | 0 / 0 / 1 |

43 threads have an unresolved or unknown original outcome at cutoff
(17 partial, 6 failed, 20 unknown). The cohort includes
new reports with less than a full day of follow-up.

**First post usefulness.** Code yes when the opening text and any opening
report identify the phase and a supported next action without a second
diagnostic to choose the action. A completed installation with the
verification described qualifies. A generic stop, a recover summary with no
discriminating failure fails this check. A report added in a reply cannot
change the opening-post score. A later request to verify the result of an already identified action does not
invalidate the opening post.

| Opening evidence | Threads | Sufficient |
| --- | ---: | ---: |
| Readable schema-1 installer diagnostic | 41 | 11 |
| Other opening attachment labelled diagnostic | 1 | 0 |
| No attached or embedded installer diagnostic | 18 | 7 |
| Total | 60 | 18 |

**Harm.** The baseline has no case attributable to the planned changes,
which were not delivered in the observation window. For the delivered batch,
record any public evidence of a duplicate package mutation, wrong-device
continuation, unintended Restore/Cancel change, loss of stock Home,
emergency-stop regression or lost preferences, together with the actual
affected build and prior action. Absence of reports leaves incidence unknown.

## Calibration and audit trail

- #409 failed during storage checking before package submission. Diagnostic
  and retest requests count. The notice that a fix shipped does not. The
  reporting owner later confirmed that setup completed. A physical Home result
  from a different owner in the thread is not evidence for that device.
  [Issue #409](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/409)
- #417 also reported the storage-check boundary. The evidence does not
  establish #409's underlying storage permission cause. The maintainer
  requested one new attempt. The owner's final result is unknown.
  [Issue #417](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/417)
- #440 began at application/input inventory. Later comments show completed
  removal, failed Root Home activation after fresh setup and confusion about
  continuing from Restore to removal. Each evidenced family counts once.
  The later attachment of an already-saved report is not a visit.
  [Issue #440](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/440)
- #472 requested removal. Follow-up included an unverified restart, further
  removal attempts and then the owner's confirmation of package absence,
  LG Home and a working remote. The owner's confirmation supplies the outcome.
  [Issue #472](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/472)
- #588 confirms verified cleanup but has no fresh Root installation result.
  #390 was closed with a common fix and still lacks confirmation on its own
  TV. These count as partial and unknown, respectively.
  [Issue #588](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/588),
  [issue #390](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/390)

The audit table retains issue numbers and coded fields only. Goals use I
(install), R (reinstall/update), U (uninstall) and ? (unclear). Outcomes use
C (confirmed), P (partial), F (failed) and ? (unknown). Home uses C, F and ?
for relevant physical results and — when outside the goal. Family codes
match the results table. — means no family was established. Opening evidence
uses D (readable standard diagnostic), O (other attachment labelled
diagnostic) and — (no opening report). Useful records sufficiency for the same
opening post. Visit numbers refer to the one-based chronological comment
positions in the snapshot, including release notices and reporter replies
when computing positions.

| Issue | Goal | Outcome | Home | Installer | Families | Opening report | Useful | Visit comments |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| [#288](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/288) | R | P | ? | 0.8.1 | A,L | D | N | — |
| [#295](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/295) | I | F | — | 0.8.1 | Q | D | N | — |
| [#304](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/304) | I | P | F | 0.8.1 | A | D | N | 1 |
| [#307](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/307) | I | P | — | 0.8.1 | Q | — | N | 13 |
| [#311](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/311) | I | P | F | 0.8.1 | P,A | D | Y | 9 |
| [#315](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/315) | I | P | ? | 0.8.1 | P | D | N | 1 |
| [#334](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/334) | I | P | ? | 0.8.1 | A,C | D | N | — |
| [#355](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/355) | I | P | ? | 0.8.0/0.8.1 | A,C,L | D | N | 12 |
| [#359](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/359) | I | ? | — | 0.10.0 | Q | D | Y | — |
| [#364](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/364) | I | ? | — | 0.10.0 | P | D | Y | — |
| [#368](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/368) | R | ? | — | 0.10.0 | C,L | D | N | — |
| [#376](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/376) | I | ? | — | 0.11.0 | Q | D | N | 4 |
| [#378](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/378) | I | C | C | 0.11.0 | S,Q | D | N | 3,6,12 |
| [#383](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/383) | I | ? | — | 0.11.0 | P | D | Y | 5 |
| [#389](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/389) | I | P | F | 0.11.0 | V,L,A | D | N | 4,6,8,12,16,18,25,28,31,34,36,38,40,48,50 |
| [#390](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/390) | I | ? | — | 0.11.0 | S,Q | — | Y | 4 |
| [#395](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/395) | I | ? | — | 0.11.0 | Q | D | N | 1 |
| [#397](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/397) | I | P | — | 0.11.0 | P,V,L | D | Y | 1,3,9,11,18,20,23,25 |
| [#406](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/406) | I | C | C | 0.11.0 | Q,L | — | Y | — |
| [#408](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/408) | ? | ? | — | 0.12.0 | H | D | Y | 1 |
| [#409](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/409) | I | C | — | 0.12.0 | S | D | N | 1,4,12 |
| [#410](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/410) | I | P | ? | 0.12.0 | P | D | N | 1,4,6,12,15,17 |
| [#417](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/417) | I | ? | — | 0.13.0 | S | D | N | 1 |
| [#418](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/418) | R | P | ? | 0.13.0 | A,L | D | N | 15,17,21,24,27,29,33,35,38,41,44,48,50 |
| [#420](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/420) | I | ? | — | 0.13.0 | C | D | N | 1 |
| [#434](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/434) | I | ? | — | 0.13.0 | S | D | N | 1,5 |
| [#437](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/437) | R | C | — | 0.13.1 | H | — | Y | 4 |
| [#438](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/438) | R | ? | — | 0.13.1 | L | O | N | 1,4 |
| [#440](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/440) | I | P | F | 0.13.1 | V,A,L | D | N | 1,3,5,9,11,13,18,21,23,25,27 |
| [#454](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/454) | R | F | — | 0.14.0 | V,P | D | N | 1,3,5,12,14,17,21,23,29,31 |
| [#467](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/467) | I | ? | ? | 0.15.0 | C,Q,A | D | N | 1,3 |
| [#469](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/469) | R | ? | — | ? | L | — | N | 1 |
| [#471](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/471) | ? | ? | ? | 0.15.0 | Q | D | N | — |
| [#472](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/472) | U | C | C | 0.15.0 | L | D | N | 1,3,8,16,19,27,32,36,41 |
| [#473](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/473) | I | C | C | 0.15.0 | — | — | Y | — |
| [#476](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/476) | I | ? | — | ? | P | — | N | — |
| [#486](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/486) | R | P | ? | 0.16.0 | H | D | N | 1 |
| [#495](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/495) | I | C | C | 0.17.0 | C,Q,L,A | D | Y | 3 |
| [#511](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/511) | I | ? | — | 0.3.0 | P | D | N | 1 |
| [#519](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/519) | I | F | — | 0.17.1 | P | D | N | 1,7,10 |
| [#529](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/529) | R | C | — | 0.17.1 | Q,L | D | N | 2,5,7,10 |
| [#534](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/534) | R | C | C | 0.17.1 | L | — | Y | 1,4,6 |
| [#541](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/541) | I | ? | — | ? | S | — | N | 1 |
| [#576](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/576) | U | C | C | 0.19.0 | L | D | N | — |
| [#587](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/587) | I | F | — | 0.20.0 | P | D | Y | 2,5 |
| [#588](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/588) | R | P | — | 0.20.0 | L | D | Y | 3,6 |
| [#599](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/599) | R | C | C | 0.13.1 | A | — | N | 1 |
| [#615](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/615) | I | P | F | 0.20.3 | A,L | D | N | 1,3,7,9,11,15,17,21 |
| [#626](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/626) | I | C | C | 0.20.4 | P,H,L | D | Y | 3,8 |
| [#635](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/635) | I | C | ? | 0.20.3 | S,Q,L | D | N | — |
| [#643](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/643) | U | C | C | ? | Q,L | — | N | 4,6,13,15 |
| [#647](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/647) | R | P | F | 0.20.7 | A,H | — | N | 1,5 |
| [#652](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/652) | I | P | F | ? | C,A | — | N | 3,5 |
| [#653](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/653) | R | C | C | 0.20.8 | H,Q | — | Y | 3 |
| [#654](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/654) | I | C | — | ? | — | — | N | — |
| [#663](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/663) | ? | ? | — | ? | C | — | N | 1 |
| [#664](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/664) | U | C | C | 0.20.5 | C,L | D | Y | 1,8 |
| [#678](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/678) | I | F | — | 0.21.0 | Q,C | D | N | 1,5 |
| [#679](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/679) | I | ? | — | ? | — | — | N | 1 |
| [#692](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/692) | U | F | ? | 0.21.1 | L | — | Y | — |
