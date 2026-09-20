# Playable game: mechanics and bounded QA

## State transitions

`new → proposing → voting → merged PR → adopted settlement → proposing/finished`

A missed proposal window records `passed`. A revised/conflicted/ineligible PR is
closed without points; insufficient votes at the cutoff record `rejected`.
A manually closed PR records `closed`. Only the selected PR is closed; unrelated,
extra, or ineligible PRs are ignored. Reopening an old PR does not reset its
creation time or make it eligible in a later turn.

The selection check uses current open/non-draft eligibility and original PR
creation time within the proposal window. A timely PR can therefore be selected
on a delayed tick and receive a full voting window. This is not a historical
snapshot of draft/readiness status at the proposal cutoff.

`game.json` sets player order, durations, award and victory threshold. `state.json`
contains the mutable ledger and progress. Opening voting commits the selected PR,
head SHA, electorate, award, cutoff and existing force-push event IDs. Changing
head or adding a force-push timeline event after selection invalidates it. New
force-push events catch returning to the original head, subject to GitHub API
consistency and the final non-atomic check/merge race.

The latest decisive eligible review submitted **before** the deadline counts if
it matches the selected head. Comments/pending reviews are ignored; dismissal
revokes a vote. Reviews submitted before the selection run can count on that same
head. Current GitHub dismissal state is authoritative, even after cutoff, because
the review endpoint is not a historical vote database.

At an approved deadline, the installed referee merges the pinned head and exits.
The next main-push invocation loads adopted code and state, observes the merged
PR, applies the frozen award to the adopted ledger, records the merge, checks the
adopted victory rule, and uses the adopted rotation for the next turn. Nothing
protects that settlement mechanism against an amendment. Removing its pending
state or breaking the code can legitimately stop/change the game.

Each invocation performs at most one state commit or merge. A state commit is a
new Git tree based on the exact installed parent followed by a non-force ref
update. Concurrent divergent main changes fail closed. A lost merge/state-write
response is recovered by rereading the new main/PR in a fresh invocation. A lost
close response advances on the next tick with outcome `closed` (the finer reason
may be lost); it does not award points or repeat a completed turn.

## Local validation

Run `python3 -m unittest discover -s tests -v`.

- Full 13-turn game over almost 26 simulated weeks, first to five; idempotent idle
  and finished ticks, missed turns and delayed notifications.
- Earliest eligible selection, out-of-turn/draft/late/competing proposals; no early
  merge; strict majority, abstentions, ties, changed/stale/dismissed/late reviews.
- Revisions, force-push restoration, conflicts, unknown mergeability and closed PRs.
- Dry runs, stale checkouts, failed writes and lost state/merge/close responses.
- Amendments to score ledger, award, rotation and victory threshold.
- Real disposable Git merges plus fresh Python processes: old code accepts a code
  and ledger amendment; the three-way merge preserves both voting state and the
  proposed ledger; freshly adopted scoring code settles the award once.
- API adapter tests assert installed-parent tree construction and non-force ref
  updates. These are not a live concurrency or transactional-merge guarantee.

Original first-proof regression tests remain. Tests themselves are amendable.
No local result alone proves GitHub scheduling, token attribution, or event flow.

## Authorized live campaign

Repository: `UgoLouche/git-nomic-test` only; existing four isolated Apps.
Ugo approved **50 additional workflow runs** after the initial 33-run proof, and
an **eight-hour** schedule (03:17/11:17/19:17 UTC). Standard public hosted runners
only; no broader credentials. The cap is operational and applies during this
supervised campaign, not an enforced lifetime limit on subsequent scheduled jobs.

Preflight read-back found the original main SHA unchanged, no open PRs/active
runs, all four installations restricted to this repository, player bypass never,
referee bypass always, the main-only environment policy, and readable PR timeline.
Ugo confirmed `PROOF_ENABLED=true`; the Apps cannot inspect/change that variable.

Planned bounded scenarios, all upgrades/amendments adopted through player votes:

1. A proposes the playable upgrade; B/C approve under the installed proof rules.
   Test profile uses 300-second proposal and 180-second voting windows, with an
   explicitly initialized ledger. This is a disposable test profile, not the
   human game's one-week defaults.
2. A proposes a visible referee marker change plus a ledger/award amendment. B/C
   vote. Require no early merge, then deadline merge and automatic adopted-code
   settlement/state commit, preserving the voted ledger edit.
3. B proposes and revises after selection; require closure, no award and rotation.
4. C misses its proposal window; require exactly one pass and a full new A window.
5. A proposes restoring weekly durations and one-point future awards. After B/C
   approval and cutoff, verify settlement/victory under the preceding voted ledger
   and award amendment; repeat reconciliation without duplicate points.

For short-deadline tests, the operator may submit a clearly labeled COMMENTED
review (not a vote) to wake the existing unprivileged signal at/after a real-time
cutoff. This exercises the actual Actions/referee path without changing its clock
or requiring Actions-write permission. It does **not** prove the cron trigger.
A scheduled run, if one occurs during observation, is separate evidence; otherwise
scheduled delivery remains pending rather than waiting eight hours for a test.

Stop at the cap, unexpected permissions/workflow behavior, or an actual blocker.
Observe canceled/coalesced notifications by reading authoritative PR/main state;
never resubmit mutations blindly. Store PRs, SHAs, run IDs and outcomes, never
credentials. Revoke temporary operator tokens after each use.

Afterward ask Ugo to pause `PROOF_ENABLED` (owner-only). Scheduled records continue
while paused; owner workflow disablement stops them. Do not mark the overall task
complete without Ugo's agreement. Human UI and destructive game-over tests remain
outside this campaign.
