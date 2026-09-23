# Mechanics reference

[Home](../README.md) · [Player guide](playing.md) · [Extending the game](extending.md)

This describes the **baseline v6 implementation**, not immutable rules. Read the
installed `main` revision when interpreting a particular game. Accepted changes
can alter every behavior below. Platform access controls and the owner's
administrative authority are outside executable game law.

## Configuration and state

[`game.json`](../game.json) is the configuration:

| Field | Baseline meaning / validation |
| --- | --- |
| `base` | `main`; code, workflow events and environment setup currently assume that name |
| `players` | Ordered list of at least two distinct positive integer **GitHub user IDs** |
| `require_pytest` | Boolean; defaults to `true` if omitted |
| `turns.proposal_seconds` | Proposal-window length; normally 604800 (one week) |
| `turns.voting_seconds` | Voting-window length; normally 604800 |
| `turns.points_per_accept` | Positive integer award; normally 1 |
| `turns.points_to_win` | Positive integer winning threshold; normally 5 |

All four `turns` values must be positive integers, not booleans or numeric
strings. Changing a validator is itself a possible amendment. A configuration
without `turns` invokes the older proof-only path in `referee.py`; removing that
key does **not** merely disable the timer for the playable game.

[`state.json`](../state.json) is mutable game data, versioned alongside code:

| Field | Meaning |
| --- | --- |
| `phase` | `new`, `proposing`, `voting`, or `finished` |
| `turn`, `player` | Positive turn number and current proposer's registered ID |
| `scores` | Integer scores keyed by **stringified** user IDs |
| `started_at` | Start of the proposal window; remains that value during voting |
| `deadline` | Current proposal or voting cutoff |
| `proposal` | Frozen snapshot while voting; otherwise normally `null` |
| `history` | Completed turn records, outcomes, PR/head and award/merge where relevant |
| `winners` | Eligible IDs reaching the winning threshold when the game finishes |

The frozen proposal contains `number`, `head`, `author`, `opened_at`, `voters`,
`award` and `force_push_ids`. Use `proposal.opened_at`, not `started_at`, for the
start of voting. UTC timestamps use ISO-8601. The `new` reset state has no active
deadline; initialization starts its first full window.

There is no hidden database. Runtime writes and adopted state amendments both
appear in Git history. An old `state.json` on a proposal branch is not the current
scoreboard. State validation is not a complete migration or corruption-recovery
system; authors must design compatible amendments.

## Lifecycle

```text
new ──initialize──> proposing ──select eligible PR──> voting
                       │                              │
                  no proposal                    reject/invalid
                       │                              │
                       └────── finish turn <──────────┘
                                      ▲
 voting ──approve──> merge ──fresh adopted invocation──┘
                                      │
                          next proposing / finished
```

There is no stored `merged` phase. Between merge and settlement the pending
proposal remains in `voting`, and the next invocation sees that its PR merged.
A `finished` game idles; it does not select new proposals or automatically reset.

## Selecting a proposal

During `proposing`, the referee lists open PRs targeting the configured base,
sorted by creation time and then PR number. A candidate must:

1. Be authored by the current player.
2. Have been **created at or after `started_at`, strictly before `deadline`**.
3. Be open, non-draft, unmerged and still targeting `main` when reread.
4. Have passing current-head pytest metadata when the gate is enabled.

Failing/pending candidates are skipped, not frozen. The author can revise them
before selection. The first qualifying candidate wins; ignored PRs are not
closed and are not queued for later turns. Reopening a PR or marking it ready
does not change its original creation time.

Selection snapshots the head, electorate (registered non-authors), current
award and existing force-push timeline IDs. It commits `phase: voting` and a
**full** voting window measured from this reconciliation. No majority is required
to open voting. A known conflict may still be selected; voting-phase validation
then rejects it rather than allowing conflicted adoption.

If a tick occurs after the proposal deadline, the referee still considers PRs
created on time **using their current readiness and test status**. It does not
reconstruct whether they were ready/passing exactly at cutoff. If none qualifies,
it records a pass. Thus late processing may select a timely-created PR that was
fixed late; players should not rely on that accidental grace period.

## Frozen revisions and invalidation

Once selected, these conditions end the proposal without points:

| Observation | Outcome |
| --- | --- |
| Head differs, or force-push timeline IDs changed | `revised` |
| Base changed or selected PR became draft | `ineligible` |
| GitHub explicitly reports non-mergeable | `conflicted` |
| PR is already closed and not merged | `closed` |

The referee closes an open invalid PR, then records the turn outcome. Force-push
history detects returning to the originally selected SHA, subject to GitHub's
timeline consistency. Unknown mergeability is different from a conflict: it
blocks acceptance but does not by itself end the turn. There is no guaranteed
upper bound if GitHub never resolves an unknown mergeability result.

## Votes and deadlines

For each frozen eligible voter, sort reviews by submission time and ID. Use the
latest decisive review submitted **strictly before the voting deadline**:
`APPROVED`, `CHANGES_REQUESTED`, or `DISMISSED`. It must refer to the frozen head;
otherwise that voter abstains. Comments and pending reviews do not replace a
previous decisive review. Authors and accounts outside the frozen electorate
never count. Reviews from before selection can count on that same revision.

A currently dismissed review does not count, even if the dismissal happened
later than the cutoff. This is the current GitHub review state, **not** a full
historical event reconstruction. A decisive review at/after cutoff is excluded;
its existence does not replace the last eligible pre-cutoff vote.

For `N` registered players, the majority threshold is:

```text
voters = N - 1
votes required = floor(voters / 2) + 1
```

The denominator is the **entire frozen electorate**, never votes cast.
Abstentions/dismissals are not approving or rejecting votes.

| Tally / time | Result |
| --- | --- |
| Approving majority before cutoff | Attempt early acceptance, subject to tests/revision/mergeability and final rechecks |
| Rejecting majority before cutoff | Close early without points after rechecks |
| Neither majority before cutoff | `waiting-for-votes` |
| At/after cutoff with insufficient approvals | Reject, even without a rejecting majority |
| At/after cutoff with enough pre-cutoff approvals | Attempt acceptance using those votes and current eligibility/tests |

Submission and resolution are not atomic. A vote can change before the referee
acts, and final API races remain. A majority is actionable when **observed and
rechecked**, not necessarily at the moment its last review was submitted.

## The pytest gate

[`proposal-tests.yml`](../.github/workflows/proposal-tests.yml) runs on ordinary
`pull_request` events. The baseline fetches the exact PR head without credentials
and runs `python -m pytest -q` using pinned pytest 9.0.2 on Python 3.12. The test
run is on the **proposed head**, not the eventual merge result. Test failures,
collection errors and no tests all produce a nonzero exit.

[`GitHub.pytest_status`](../referee.py) reads Actions metadata, requiring:

- A `pull_request` run for the exact head and workflow path
  `.github/workflows/proposal-tests.yml`.
- Run title `Pytest PR #NUMBER @ SHA`.
- The latest matching run/attempt, ordered by start/creation time, run number
  and attempt, completed successfully.
- Exactly one job named `pytest` and one step named `Run pytest`, both completed
  successfully. Missing/skipped/neutral results do not count as passing.

No matching run is pending. An API failure raises an error rather than inventing
success. A later rerun can remove the head's previously passing status.

The gate is checked before selection and again before merge, including a final
recheck. An approving proposal with nonpassing tests waits before cutoff and
fails at/after cutoff (`pytest-pending` or `pytest-failed`). A rejecting majority
does not wait for CI. With insufficient approvals at cutoff, the outcome is
`rejected` regardless of tests.

**Tests and the workflow are amendable in the proposal itself.** The gate trusts
a mutable CI report; it neither proves coverage quality nor enforces runner-file
integrity. `require_pytest: false` disables the baseline gate after adoption.
The currently installed gate still decides whether that amendment can be
adopted. See [CI changes and compatibility](extending.md#changing-tests-and-workflows).

## Adoption, scoring and victory

There are two distinct executions:

1. **Installed code decides adoption.** It checks current rules/state, frozen
   revision, eligible votes, test results, mergeability and base freshness, then
   asks GitHub to merge the exact head. It exits without scoring.
2. **Adopted code settles.** An App-generated main push starts a fresh checkout.
   That version sees the merged PR and updates the now-adopted ledger, history,
   victory condition and turn rotation.

With unchanged settlement code, the selected author's score gains the **frozen
award**, preserving any adopted ledger edits. The history records the merge and
award. Then all registered players whose scores reach the **adopted** winning
threshold become winners; multiple winners are possible after amendments.
Victory is checked when finishing any turn, not continuously on every idle tick.

If there is no winner, increment the turn, choose the player after the current
player in the **adopted order**, wrapping around, and start a full proposal window
from processing time. A delayed tick does not skip several players at once.

Consequences:

- Changing only `points_per_accept` affects subsequently selected proposals,
  not the award already frozen for this one.
- Changing `points_to_win`, the score ledger or settlement code can affect the
  adopting proposal's own outcome.
- Changing rotation can affect the very next player.
- Removing the current player without handling the pending state can fail
  validation before settlement. Removing/replacing the pending proposal can
  deliberately alter or break settlement.
- Syntax errors or disabled automation after adoption can stop the game. The
  old referee does not return to finish the job as a protected fallback.

## What wakes the referee?

```text
PR events ──> Proposal tests ──completion──┐
PR/review events ──> Vote signal ──completion──> Referee on installed main
main push / manual dispatch / schedule ───┘
                         │
                   state commit or merge
                         └──> main push ──> fresh Referee
```

`workflow_run` completion is a wake-up signal, not an instruction to trust that
PR's code or artifact. The referee reads authoritative GitHub data and explicitly
checks out current `main`; the triggering run's SHA may differ from the checkout's
`installed_sha`. Failed tests can wake it too, so it can report the failure.

The baseline schedule is **03:17, 11:17 and 19:17 UTC**. GitHub may delay/drop
scheduled runs. Referee and reset share a concurrency group; pending runs can
be coalesced/canceled. Idle and finished invocations do not write new commits.

## Writes, retries and limits

One invocation performs at most **one main state commit or one merge**. Rejection
may also close the PR before the state write. State writes create a tree from the
exact installed parent and move `main` without force; divergent concurrent
updates are rejected rather than overwritten. Only the merge's expected head
SHA is atomically guarded. Votes, base freshness, timelines and merge are not
one transaction.

After an ambiguous write response, the next fresh invocation rereads state:
committed state is not awarded again; a completed merge can still be settled.
If closing succeeded but its response was lost, the finer reason may become
`closed` on retry. Exhaustive recovery and progress are not guaranteed, especially
under amendments. See [operations](operations.md) before retrying a mutation.

The security boundary is explained in [owner setup](owner-setup.md): proposed
code is unprivileged; adopted code obtains a repository-scoped referee identity.
Game mutability is not permission to expose unrelated credentials or use
unrelated repositories/runners.
