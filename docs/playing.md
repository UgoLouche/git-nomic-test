# Player guide

[Home](../README.md) · [Exact mechanics](playable-game.md) · [Writing amendments](extending.md)

This guide assumes the host has completed [setup](owner-setup.md), registered your
GitHub user ID, and invited you with write access. You use your own GitHub account;
never ask for the referee's private key or use its identity to play.

## 1. Find out what is happening

Open **`state.json` on the game's `main` branch**, not the copy on your proposal
branch. It is the scoreboard and turn record. There is no separate game dashboard
or automatic proposal label to rely on.

| Field | What to look for |
| --- | --- |
| `phase` | `new` (waiting to start), `proposing`, `voting`, or `finished` |
| `player` | Numeric GitHub user ID of the current proposer |
| `turn` | Turn number, starting at one |
| `deadline` | Current proposal/voting cutoff, in UTC (`Z` means UTC) |
| `proposal.number` | Selected PR while voting |
| `proposal.head` | Exact frozen commit; compare it with the PR's latest commit |
| `scores` | Scores keyed by user ID; map those IDs to players in your group |
| `history` | Completed turns and their outcomes |
| `winners` | Winning user IDs when the game finishes |

`game.json` lists player order and configurable rules. The host can share a
human-readable ID/name list in the group's discussion. Ask which rules have
already changed: the README describes the baseline, not every possible game.

## 2. Prepare your proposal

You can discuss and prepare a branch at any time. **Open the actual PR during
your own proposal window.** An old PR does not become eligible merely because
your turn starts; converting an old draft to ready does not change its creation
time either. Use an issue or group discussion for ideas before your turn.

A good first proposal changes one understandable rule. For example:

> Raise `turns.points_to_win` from 5 to 7, leaving votes and awards unchanged.

Use [the amendment guide](extending.md) to identify the relevant code and tests.
For a same-repository branch, the usual flow is:

```sh
# In your clone of YOUR group's game repository:
git switch main
git pull --ff-only origin main
git switch -c proposal/raise-winning-score
# Edit the relevant files, then run the local tests.
git add game.json
git commit -m "Propose first to seven points"
git push -u origin proposal/raise-winning-score
```

In GitHub, create a PR targeting `main`. Confirm that its **author is the player
whose turn it is**. Write the proposal yourself rather than asking a bot or
another person to open it on your behalf: eligibility uses the PR author's ID,
not commit authorship.

Explain:

- What rule changes, and why the game would be more interesting.
- Which files implement it and which tests demonstrate it.
- Whether it affects this proposal's own settlement, later turns, or both.
- Any state migration, automation risk, or intentional possibility of game-over.

A draft created during your turn is useful while you work: the referee ignores
it. The default test job skips drafts, so run tests locally first. When ready,
select **Ready for review**; that triggers the test workflow.

## 3. Watch tests, then stop editing at selection

The **Proposal tests** workflow tests the exact proposed commit. A failed or
pending result prevents selection. Before selection, fix the code/tests and push
another commit; the new head will be tested again.

When tests pass, the referee may select the PR immediately. Look for
`phase: "voting"` and your PR number/head in `state.json`, or a `voting-opened`
result in the Referee Actions log. **That selection, not the first review, is
when editing must stop.**

After selection:

- Do not push commits, amend/rebase, or click **Update branch**. These change the
  head and invalidate the proposal—even a harmless typo fix.
- A force push back to the frozen commit does not rescue a revised proposal.
- Discuss clarifications in comments without changing the proposed revision.
- If you need to withdraw, closing the selected PR consumes the turn without
  points when the referee next observes it.

Fix conflicts **before** selection. Once frozen, a conflicted proposal fails;
there is no special exception to edit it back into eligibility.

## 4. Review and vote

On the selected PR, read **Files changed**, including tests and workflow changes.
Then use **Review changes → Submit review**:

| GitHub review | Game meaning |
| --- | --- |
| **Approve** | Yes |
| **Request changes** | No; this can immediately end the proposal if it makes a rejecting majority |
| **Comment** | Discussion only; does not replace your prior vote |
| No submitted review | Abstention |

A comment saying “approved,” a reaction, or an unfinished/pending review is not a
vote. The author and unregistered accounts are excluded from the electorate.
Submit against the frozen revision; reviews of another commit do not count.

You can submit a later decisive review to change your vote **until the referee
acts**. A later approval replaces a rejection and vice versa. Adding a comment
does not withdraw either. Dismissals follow the current review state exposed by
GitHub; see the [precise tally rules](playable-game.md#votes-and-deadlines).

### How many votes are needed?

A strict majority of **all registered non-authors**, not just respondents:

| Players in the game | Eligible voters | Yes votes to accept, or no votes to reject |
| --- | --- | --- |
| 2 | 1 | 1 |
| 3 | 2 | 2 |
| 4 | 3 | 2 |
| 5 | 4 | 3 |
| 6 | 5 | 3 |

With five players, two approvals and two abstentions are not enough. With three,
one approval and one rejection do not decide early. The game waits until the
cutoff, then rejects if approving votes are still insufficient.

## 5. Let the referee resolve it

**Do not click Merge**, enable an alternative automatic merger, or push to
`main`. Native GitHub approval/check indicators are not the game's verdict.
The repository should prevent ordinary players from bypassing the referee.

An observed approving majority merges early. An observed rejecting majority
closes early without points. After acceptance, a separate invocation of the
newly installed code awards points and advances the turn. There can be a short
interval where the PR is merged but the scoreboard still shows voting.

Check the next `state.json` commit for the result. A green workflow means that
workflow succeeded—not necessarily that your proposal passed. A successful
Referee run may simply say `waiting-for-votes`.

## Common surprises

**“Tests passed, but voting hasn't opened.”** Is it your turn? Was the PR created
inside that turn's window? Is it non-draft, open and targeting `main`? Has another
eligible proposal already been selected? Check the latest Referee log.

**“My ready PR lost to another one.”** The referee chooses the earliest currently
eligible PR, ordered by creation time then PR number. A failing earlier PR can
be skipped in favor of a later passing one. Avoid multiple competing PRs in your
turn unless that is deliberate.

**“The deadline passed but nothing happened.”** Cutoffs are not exact execution
times. Review/test events normally wake the referee; scheduled reconciliation
also runs, but GitHub can delay it. The host can inspect or manually run the
installed referee. Do not push a dummy commit to a frozen PR to wake it.

**“Can I vote before the referee selects the PR?”** The baseline can count a
current-head review submitted before selection, provided it is before the voting
cutoff. Waiting for selection makes it clearer what revision you are voting on.

**“Tests started failing after voting opened.”** That blocks acceptance. The
frozen revision cannot be edited; a passing rerun can unblock it. An approving
proposal still lacking passing tests at cutoff fails when reconciled. A rejecting
majority can close it without waiting for tests.

**“Can I change the tests so my new rule passes?”** Yes. Tests and their workflow
are amendable too. Explain why the new expectations are right; passing pytest is
not evidence that an amendment is good or harmless. Reviewers decide that.

**“The game is broken.”** That can be a legitimate adopted outcome. Agree with
the group whether to accept game-over or ask the owner for an explicitly
out-of-game repair/reset. See [operations](operations.md); do not silently repair
or bypass votes yourself.
