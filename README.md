# Git-nomic

PRs propose executable rule changes; reviews vote; the installed referee adopts
accepted proposals. **Code is law:** rules, ledger, referee, and workflows are all
amendable. An adopted bug can legitimately stop the game. Passing pytest is a
starting rule, not immutable branch protection: proposals can amend their own
tests, test workflow and the gate itself. Platform permissions and owner
administration remain outside game law.

The first live permission/adoption proof passed; see [evidence](docs/live-results.md).
The playable slice adds turns, deadlines, scoring and a mutable state ledger;
see its [live evidence](docs/playable-results.md).
See [playable mechanics and validation](docs/playable-game.md) for exact semantics,
testing boundaries, and the bounded live campaign protocol.

**Local v6 changes:** early approving/rejecting majorities, arbitrary rosters of
2+ players, a pytest gate before voting and merging, and an explicit owner reset.
These are locally validated only; the finished live game still runs v4's original
deadline-only rule. Historical live evidence does not prove these newer features.

## Starting game

- Two or more registered players rotate in the order of GitHub **user IDs** in
  `game.json`; there is no fixed upper player limit.
- One week to propose. The first eligible, open, non-draft PR created during the
  current player's proposal window is selected, ordered by creation time then PR
  number, **after its current revision passes pytest**. Failing/pending proposals
  can be fixed until selected; no eligible proposal means a pass. Out-of-turn/extra
  PRs are ignored and are not carried into a later turn.
- Voting opens when the referee selects the PR and lasts **up to** one week. The
  selected revision is frozen; revisions invalidate the proposal, including a
  force push back to the original SHA. Conflicts fail; unknown mergeability
  prevents adoption until GitHub resolves it.
- A strict approving majority of all eligible non-author players merges early;
  a strict rejecting majority (`Request changes`) closes early without points.
  Either outcome advances the turn. For N registered players, the threshold is
  `floor((N - 1) / 2) + 1`: with 2/3/4/5 players, require 1/2/2/3 votes.
  The denominator is the whole registered non-author roster, not votes cast.
  Abstentions/dismissals are neither approvals nor rejections.
  With no majority, voting stays open until cutoff; insufficient approvals then
  fail. A majority acts when the referee observes and rechecks it, not atomically
  when a review is submitted.
- An accepted proposal earns one point; first to five wins. `state.json` contains
  scores, active turn/proposal, and outcome history. It too can be amended.
- After a merge, a **fresh checkout of the adopted code** settles its award and
  starts the next turn. The award/electorate were frozen by the old rules;
  adopted scoring code, ledger, rotation, and victory threshold govern settlement.

These are starting conventions, not an immutable constitution. A player can
propose changing any of them. A normal state amendment must still merge cleanly
with the referee's intervening state commits.

## Run and test

Python 3.12+, Git and pytest are needed for local tests; the game runtime remains
stdlib-only. Live operations also need `gh` and an explicitly repository-scoped
referee installation token.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest -q
python -m compileall -q referee.py game_engine.py reset_game.py tests
python3 referee.py --help
# Read-only preview; supply credentials securely, never paste them in commands:
python3 referee.py --repo OWNER/REPO --installed-sha "$(git rev-parse HEAD)"
# Add --apply to write. --now 2026-01-01T00:00:00Z is for local clock simulations.
```

Always run the installed main revision, not a proposed branch. The CLI defaults
to read-only. It makes at most one main commit or merge per invocation, then stops.
The original no-`turns` proof configuration remains supported for the historical
code-adoption fixture; the actual playable configuration contains `turns`.

## Automation and credentials

```text
PR change → unprivileged Proposal tests (pytest on exact PR head)
PR/review change → unprivileged Vote signal
Vote signal / Proposal tests completion → default-branch Referee
main push / manual dispatch / 03:17, 11:17, 19:17 UTC → Referee
Referee state commit or merge → main push → freshly installed Referee
```

The schedule reconciles every **eight hours**. Stored deadlines are vote cutoffs,
not promises of punctual execution; GitHub may delay/drop scheduled jobs. Review
signals normally trigger early decisions without waiting for the schedule. A late
turn transition gives the next player a full new window from processing time.

Idle/finished invocations do not write, preventing state-commit loops. No proposed
code, artifacts, or caches enter the privileged job. Actions are pinned; checkout
does not persist credentials. See [owner setup](docs/owner-setup.md): only the
referee App bypasses main restrictions, and its key is an environment secret
restricted to branch `main`. Player credentials stay outside the game runtime.

`PROOF_ENABLED=true` enables the referee. Setting it to `false` skips execution,
but scheduled workflow records still appear. Disable the workflow/remove the
schedule to stop those too. This owner switch is not an immutable security guard;
adopted code can change/remove it. Standard hosted runners on this public repo
are free; no paid/self-hosted runners or unrelated credentials are authorized.

## Reset a game

Once the new workflows are deployed to main, the personal repository owner can
use **Actions → Reset game → Run workflow**, choose `main` and enter `RESET`.
Equivalent command, using the owner's normal authenticated GitHub CLI:

```sh
gh workflow run reset-game.yml --ref main -f confirm=RESET
```

This is an explicit **out-of-game** operation: keep current code/rules/players,
clear scores/history/winner/active proposal, and restart at turn one with the
first registered player. Previous games remain in Git history. No PRs or branches
are deleted; old PRs do not become new-turn proposals. An enabled referee starts
the new window automatically from the reset's main push; a paused referee leaves
it ready to start. It does not restore original code or starter rules.

Both dispatch and re-run must be by the personal repository owner. The job uses
the existing main-only environment and serializes with reconciliation. No reset
is automatic on game-over. Organization repositories need a separately agreed
operator authorization policy; this owner-login check targets personal repos.

`python reset_game.py` previews fresh state locally **without API calls or writes**.
For a direct live reset, an operator with a repo-scoped referee token can run the
installed main copy with `--repo OWNER/REPO --installed-sha SHA --apply
--confirm-reset OWNER/REPO`. It verifies installed rules and main freshness, then
makes a normal non-force state commit; it never rewrites Git history. Ordinary
player tokens cannot bypass main restrictions. Reset implementation is local
only for now; no actual game has been reset by this change.

## Pytest baseline

`require_pytest: true` in `game.json` requires the latest matching PR-head pytest
run/attempt and its pytest step to succeed before selection and again before
adoption. Missing/running checks wait; failures can be fixed before freezing.
If a selected revision's check ceases to pass, approving votes cannot merge it;
it waits for passing checks until cutoff, then fails. A rejecting majority can
still close it immediately. Test completion wakes reconciliation automatically.

The baseline runner executes `python -m pytest -q` on the exact proposed head,
not the merge result, on a disposable hosted runner without credentials,
environments, secrets or shared caches. Failing tests, collection errors and
no collected tests produce nonzero exits. The referee only reads GitHub run/job
metadata; it never executes proposed code. Its App token additionally requests
Actions read (already present in the existing installation grants).

**Tests and the test workflow are themselves amendable.** No comparison against
installed test/runner files, fixed test suite, or two-step runner restriction is
imposed. The gate trusts the modifiable CI report; it does not prove tests are
meaningful or prevent a voted change from disabling it. The current result lookup
uses `proposal-tests.yml`, its PR/SHA run-name, job `pytest`, and step `Run pytest`;
those identifiers and the lookup logic are amendable game code too.

## Limits

- Custom review checks and PR closing/merging are not atomic. Only the merge head
  SHA is atomically pinned. Final review/base/force-push races remain possible.
- State commits use the installed parent and a non-force ref update, rejecting a
  concurrent divergent main update instead of overwriting adopted code/state.
- Writes are never blindly retried. A new checkout reads authoritative state after
  an ambiguous response. Ordinary retry paths are simulated; exhaustive recovery
  is not guaranteed, and state/logic amendments can deliberately break it.
- Review dismissal is represented by GitHub's current review state, not a complete
  historical snapshot. A currently dismissed review does not count, even if it
  was dismissed after the cutoff. Other reviews submitted at/after cutoff are
  excluded. Timeline consistency can also delay detection of force pushes.
- Human/fork behavior and deliberate game-breaking amendments remain untested.
