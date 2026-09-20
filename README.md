# Git-nomic

PRs propose executable rule changes; reviews vote; the installed referee adopts
accepted proposals. **Code is law:** rules, ledger, referee, and workflows are all
amendable. An adopted bug can legitimately stop the game. Tests are not mandatory
merge gates. Platform permissions and owner administration remain outside game law.

The first live permission/adoption proof passed; see [evidence](docs/live-results.md).
The playable slice adds turns, deadlines, scoring and a mutable state ledger.
See [playable mechanics and validation](docs/playable-game.md) for exact semantics,
testing boundaries, and the bounded live campaign protocol.

## Starting game

- Three players rotate in the order of GitHub **user IDs** in `game.json`.
- One week to propose. The first eligible, open, non-draft PR created during the
  current player's proposal window is selected, ordered by creation time then PR
  number. No eligible proposal means a pass. Out-of-turn/extra PRs are ignored;
  they are not carried into a later turn.
- Voting opens when the referee selects the PR and lasts one week. The selected
  revision is frozen; revisions invalidate the proposal, including a force push
  back to the original SHA. Conflicts fail; unknown mergeability waits.
- At the deadline, a strict majority of all eligible non-author players must
  approve the frozen revision. With three players, both others must approve.
  Abstentions are not approvals; ties fail. No early acceptance.
- An accepted proposal earns one point; first to five wins. `state.json` contains
  scores, active turn/proposal, and outcome history. It too can be amended.
- After a merge, a **fresh checkout of the adopted code** settles its award and
  starts the next turn. The award/electorate were frozen by the old rules;
  adopted scoring code, ledger, rotation, and victory threshold govern settlement.

These are starting conventions, not an immutable constitution. A player can
propose changing any of them. A normal state amendment must still merge cleanly
with the referee's intervening state commits.

## Run and test

Python 3.12+ and Git suffice for local tests. Live operations also need `gh` and
an explicitly repository-scoped referee installation token.

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q referee.py game_engine.py tests
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
PR/review change → unprivileged Vote signal → default-branch Referee
main push / manual dispatch / 03:17, 11:17, 19:17 UTC → Referee
Referee state commit or merge → main push → freshly installed Referee
```

The schedule reconciles every **eight hours**. Stored deadlines are vote cutoffs,
not promises of punctual execution; GitHub may delay/drop scheduled jobs. A late
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
