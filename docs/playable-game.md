# Playable game: mechanics and bounded QA

Local v6 supports 2+ registered players, early approving/rejecting majorities,
passing pytest before selection/merge, and explicit owner resets. This is locally
validated, not deployed to the finished live v4 game; its historical campaign
below used voting deadlines even when a majority was already present.

## State transitions

`new → proposing → voting → merged PR → adopted settlement → proposing/finished`

A missed proposal window records `passed`. A revised/conflicted/ineligible PR is
closed without points; a strict rejecting majority closes early and records
`rejected`. With neither majority, voting continues until cutoff, when insufficient
approvals also record `rejected`.
A manually closed PR records `closed`. Only the selected PR is closed; unrelated,
extra, or ineligible PRs are ignored. Reopening an old PR does not reset its
creation time or make it eligible in a later turn.

The selection check uses current open/non-draft eligibility and original PR
creation time within the proposal window. A timely PR can therefore be selected
on a delayed tick and receive a full voting window. This is not a historical
snapshot of draft/readiness/test status at the proposal cutoff.

With the baseline `require_pytest: true`, the selected head must have passing
pytest before voting opens. A failing/pending PR is not frozen and may be fixed
within the proposal window; select the earliest currently valid candidate. No
valid candidate at a reconciliation after cutoff means a pass. Checks are read
again before merging; pending/failing reruns block early approval and produce
`pytest-pending`/`pytest-failed` at cutoff. Early rejection does not wait for CI.

`game.json` sets player order (any list of 2+ unique IDs), durations, award, victory
threshold and the amendable pytest requirement. `state.json`
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

A strict majority is more than half of **all** eligible non-author voters, not
just votes cast: `floor((registered_count - 1) / 2) + 1`. The electorate remains
frozen for that proposal. As soon as reconciliation observes and rechecks an approving
majority, the installed referee merges the pinned head and exits; a rejecting
majority closes the PR and advances without points. Ties/abstentions cannot end
voting early. Reviews can change until a decisive outcome is acted on; submission
and resolution are not an atomic transaction. Both outcomes recheck votes and
installed-base freshness; merge additionally pins the head SHA. Unknown
mergeability delays an approved proposal but does not delay a rejecting majority.

The next main-push invocation after adoption loads adopted code and state, observes the merged
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

Install `requirements-test.txt`, then run `python -m pytest -q` (the unittest
suite also runs under `python -m unittest discover -s tests -v` in that environment).

- Full 13-turn game over almost 26 simulated weeks, first to five; idempotent idle
  and finished ticks, missed turns and delayed notifications.
- Earliest eligible selection, out-of-turn/draft/late/competing proposals; early
  approving/rejecting majorities, non-deciding abstentions/ties, and cutoff failure.
- Changed/stale/dismissed/late reviews, withdrawn majorities on final recheck,
  read-only early decisions, stale installed-base protection and early-close retries.
- Roster sizes from 2 to 100, whole-roster majority thresholds, and rotation wrap.
- Revisions, force-push restoration, conflicts, unknown mergeability and closed PRs.
- Missing/failed/stale/wrong-head or wrong-workflow checks, reruns and final-check
  changes, passing checks before freezing, pre-freeze repairs and gate amendments.
- Real pytest executions with valid rewritten tests, failing tests, syntax errors
  and no collected tests; passing/failing behavior is not inferred only from mocks.
- Reset state construction, unchanged rules/player order, explicit confirmation,
  installed-rule/main freshness checks, no blind retry and old-PR exclusion.
- Dry runs, stale checkouts, failed writes and lost state/merge/close responses.
- Amendments to score ledger, award, rotation and victory threshold.
- Real disposable Git merges plus fresh Python processes: old code accepts a code
  and ledger amendment; the three-way merge preserves both voting state and the
  proposed ledger; early approval adopts the change before cutoff and freshly
  adopted scoring code settles the award once.
- API adapter tests assert installed-parent tree construction and non-force ref
  updates. These are not a live concurrency or transactional-merge guarantee.

Original first-proof regression tests remain. Tests themselves are amendable.
No local result alone proves GitHub scheduling, token attribution, or event flow.

## CI and reset boundaries

`Proposal tests` uses ordinary `pull_request`, no token permissions, no secrets
or environment, no shared cache, and an unauthenticated fetch of the exact head.
No `pull_request_target` or privileged execution of proposed code is introduced.
The referee consumes run/job metadata only. The tests/runner may be changed in the
same proposal: the baseline gate is not an integrity lock on either. It checks
the latest PR/SHA-bound run attempt and a successful `pytest` job/`Run pytest`
step; it trusts that mutable report rather than proving test quality. Tests run
on the proposed head, not the eventual merge result. APIs and workflow wiring
are mocked/linted locally; real delivery and human/fork behavior remain untested.

`Reset game` is separately and explicitly dispatched by the personal repository
owner, with `RESET` confirmation; a different actor cannot re-run an owner reset.
It shares referee concurrency and the main-only environment, requests only App
Contents write, and calls `reset_game.py` from installed main. The CLI verifies
the loaded rules match that main SHA and makes a normal state-only, non-force
commit. Rules/code/player order and Git history remain; no PRs/branches are
closed or deleted. Scores/history/current proposal/winner are cleared and the
first player starts at turn one on the next enabled reconciliation. An explicit
reset may be used on a finished or active game; it is out-of-game administration,
not an ordinary proposal or an automatic game-over recovery mechanism.

The baseline reset workflow and API path have **not** been live-executed. Local
source tests check its owner/main/confirmation conditions, not actual GitHub
permission enforcement. No reset or deployment is authorized merely by testing
its implementation. See README for local preview and post-deployment usage.

## Authorized live campaign (historical: deadline-only voting)

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

Afterward stop initiating campaign runs. Pausing `PROOF_ENABLED` is optional
owner housekeeping, not a required security step; leaving it enabled is consistent
with the separately approved recurring schedule. Scheduled records continue while
paused; owner workflow disablement stops them. Do not mark the overall task
complete without Ugo's agreement. Human UI and destructive game-over tests remain
outside this campaign.
