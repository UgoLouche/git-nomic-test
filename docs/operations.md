# Operating a game

[Home](../README.md) · [Setup](owner-setup.md) · [Mechanics](playable-game.md)

This guide is for the repository owner and anyone helping diagnose the game.
Start with observation. An unexpected state may be an adopted rule, not a defect
to silently repair. Administrative intervention is outside ordinary play and
should be agreed with the group.

## Observe before acting

Read, in order:

1. `game.json` and `state.json` on **current main**: phase, player, selected PR/head,
   deadline, history and scores.
2. The selected PR's latest head, reviews, merge/closed state and test results.
3. **Actions → Referee → Run only the installed referee**: actual JSON output,
   especially `referee`, `installed_sha` and `result`.
4. The main commit history: selection, merge and settlement are separate commits.

A workflow record's `head_sha` can be older than the explicit checkout of main;
use `installed_sha` in the executed output to identify the code that made the
actual decision. Canceled pending concurrency runs are not necessarily failures
of progress: another run may already have reconciled the same event.

## Controls and what they do

| Control | Effect | What it does not do |
| --- | --- | --- |
| `PROOF_ENABLED=true` repository variable | Allows the baseline referee job to run | Start a run by itself |
| `PROOF_ENABLED=false` | Skips future baseline referee jobs | Cancel an already-running job, stop scheduled run records, disable owner reset, or freeze stored time |
| Actions → Referee → Run workflow → main | Reconcile using installed main and current time | Backdate reviews or undo a deadline |
| Disable the Referee workflow | Stop that workflow's future triggers | Disable other workflows or revoke App credentials |
| Actions → Reset game → main → `RESET` | Explicitly clear game state with current rules/players | Restore original code/rules or replace bot IDs with humans |

The schedule is 03:17/11:17/19:17 UTC but GitHub can delay/drop runs. A manual
Referee dispatch is useful for diagnosis or timely reconciliation; do not invent
clock overrides for live play. `--now` is a local simulation aid, not a legitimate
way to hide an expired turn.

**Pausing is optional administration, not a required post-test ritual.** Finished
games idle without state writes. In an active game, stored deadlines continue
passing while execution is paused; resuming processes current reality. Freezing
or extending game time requires an explicit rule/state change agreed by players.

## Reset: a new ledger under the current rules

The **personal repository owner** can run **Actions → Reset game → Run workflow**,
select `main`, enter **`RESET`**, and confirm. Or, with the owner's GitHub CLI login:

```sh
gh workflow run reset-game.yml --repo OWNER/GAME --ref main -f confirm=RESET
```

Replace `OWNER/GAME`. This is a real mutation, not a preview. Both the original
dispatch actor and any re-run actor must equal the personal repository owner in
the baseline workflow. App tokens with Actions read cannot dispatch it. The
owner-success path has live evidence; the negative actor conditions are locally
tested, not a demonstrated human permission matrix.

Reset retains **code, rules, players and their order**, but clears scores, history,
winners and active proposal, and sets turn one to the first registered player.
A normal state-only commit preserves all previous games in Git history. No PRs
or branches are closed/deleted; old PR creation times keep them from becoming new
turn proposals. An enabled referee starts the new window from the resulting
push; a paused one leaves `phase: new` ready for a later start.

Reset can be used on an active or finished game by agreement. A re-run can reset
again: do not casually use Re-run as a diagnostic. It does not undo the first
reset and is not an idempotent preview.

### Preview and lower-level operation

From a checkout you trust:

```sh
python reset_game.py
```

No arguments means **offline preview**, with no API calls or file writes. Its
output is `{ "result": "preview", "state": ... }`, not a bare `state.json`.

An experienced operator holding a securely supplied, repository-scoped referee
installation token can use the installed main copy directly:

```sh
# GH_TOKEN must already be supplied securely. Never put a literal token here.
python reset_game.py --repo OWNER/GAME --installed-sha FULL_MAIN_SHA \
  --apply --confirm-reset OWNER/GAME
```

It checks main freshness and that loaded rules match `game.json` at that SHA,
then writes a state-only commit without force. This CLI relies on credential/main
permissions; it does **not** independently enforce the workflow's owner-login
check. Do not share referee credentials with players. Inspect current main after
an ambiguous error instead of blindly repeating the write.

## Troubleshooting by observed result

| Result / symptom | Meaning and next check |
| --- | --- |
| Referee job skipped | Check `PROOF_ENABLED`, selected ref and workflow conditions. Green/skipped is not game execution. |
| `waiting-for-proposal` | Check player ID, PR author, original creation time, draft/base and current-head tests. |
| `pytest-pending` during selection | No recognized passing run yet. Check workflow/head/title/job identifiers and runner delivery. |
| `pytest-failed` during selection | Latest recognized attempt failed; read **Run pytest**, not just the overall badge. Fix before freezing. |
| `voting-opened` | Revision is frozen; stop pushes, rebases and Update branch. |
| `waiting-for-votes` | No decisive majority yet. Check full electorate, latest decisive current-head reviews and cutoff. |
| `waiting-for-tests` | An approving selected proposal no longer has passing CI. A rerun may help; editing the frozen head invalidates it. |
| `waiting-for-mergeability` | GitHub has not confirmed mergeability; reread later. An explicit conflict instead fails. |
| `revised`, `ineligible`, `conflicted` | Selected PR violated frozen-revision, draft/base or conflict rules. Read history; do not quietly revive it. |
| `stale`, `selection-changed`, `inputs-changed`, `tests-changed` | A recheck found different inputs. Observe new main/PR and let a fresh invocation reconcile. |
| PR merged but score unchanged | Look for the automatic main-push settlement run; it may be pending, failed or changed by the amendment. |
| `finished` | Normal idle state. Starting another game needs an explicit reset/preparation decision. |
| Environment rejects main | Check exact branch-vs-tag policy, workflow ref and environment name; do not widen it to all refs. |
| App token creation fails / `Invalid keyData` | Check Client ID, App installation and complete PEM formatting without logging secret contents. |
| GitHub API failure | Check permissions, installation scope, rate limits and current remote state. Do not grant unrelated access or retry writes blindly. |

In voting, `pytest-pending`/`pytest-failed` **outcomes** at cutoff differ from the
same diagnostic during proposal selection: the former closes/consumes the turn,
the latter leaves an unselected candidate available for repair.

If notifications seem idle, wait through the event chain: the signal/test run
can finish before GitHub creates its follow-up referee run. Multiple pending
referee notifications may be coalesced. Read authoritative state before generating
another event; do not push a dummy change to a frozen PR.

## Recovery is a group decision

An adopted amendment can stop scheduling, change the state format, break imports
or remove settlement. **Reset does not repair code**; it imports the installed
referee/engine and may fail too. Nor does it restore original player order/rules.

If the group wants recovery rather than accepting game-over:

1. Record the failing run, main SHA, pending PR and current state. Do not erase history.
2. Agree the intended repaired state/rules and whether this is continuation or a new game.
3. Stop concurrent automation if needed; wait for active writes to finish.
4. Have the owner perform a narrowly scoped, documented out-of-game repair using
   normal commits and the existing repository boundary. Do not casually force-reset
   history, broaden App scope or give players permanent bypass.
5. Validate the repaired state with that code, restore protections, and observe
   a real installed-main run before announcing recovery.

This is deliberately not an automatic rollback service. A universal repair
command cannot know what a self-amending game's players intended.
