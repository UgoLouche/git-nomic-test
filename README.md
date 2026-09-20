# Git-nomic: first permission proof

PRs propose executable rule changes; reviews vote; the installed referee adopts
an approved proposal. The referee and workflows are themselves amendable. A broken
adopted rule can end the game. There is no immutable engine or required test gate.

**Status:** local tests pass; App scope and live environment isolation are
validated. Source bootstrap and the live adoption proof are in progress in
`UgoLouche/git-nomic-test`. This is not yet the full turn/scoring game.

## Small starting slice

- Three eligible players, configured by **GitHub user ID** in `game.json`.
- Any eligible player can propose. Both other players must approve the current
  head commit. Latest decisive review wins; comments/pending reviews are not
  votes; dismissed votes no longer count. Missing votes abstain.
- Eligible, open, non-draft, mergeable PRs targeting `main` are considered oldest
  first. Unapproved proposals remain open. There are no turns/deadlines yet.
- One merge per invocation; a new invocation must load the newly installed code.
  This avoids applying yesterday's referee to a second proposal after an amendment.
- The GitHub merge request pins the approved head SHA. Code is never loaded from
  a proposed revision during voting. `--apply` is opt-in; the CLI defaults to reads.

These are proof conventions, not protected constitutional rules. Even the
three-player validation and `main` convention can be amended along with their
workflows/environment configuration as appropriate. Platform permissions and
owner administration are outside executable game law.

## Run locally

Python 3.12+ and Git are sufficient for tests. Actual API operations also need
GitHub CLI (`gh`) and a repository-scoped installation token.

```sh
python3 -m unittest discover -s tests -v
python3 referee.py --help
# Once game.json has real player IDs and this checkout matches installed main:
GH_TOKEN=... python3 referee.py --repo OWNER/REPO --installed-sha "$(git rev-parse HEAD)"
```

`game.json` contains the three verified test-App bot user IDs. The referee
fails closed if this list is empty, duplicated, or malformed. Do not put real tokens in shell history; the command above only
illustrates the environment interface. Prefer securely supplied credentials.

`tests/test_adoption.py` uses real disposable Git commits, fake GitHub responses,
and fresh Python processes. It proves local code adoption, **not** actual GitHub
merging, App identities, environment isolation, or Actions triggering.

## Workflows and credential boundary

```text
proposal opened/revised/reopened/ready, or review submitted/dismissed
  → Vote signal (no checkout, no secrets, no token permissions)
  → workflow_run on default branch
  → Referee checks installed main against current GitHub reviews
  → App-token merge
  → push on main
  → next Referee loads the adopted code
```

Manual dispatch on `main` is also available for the initial permission test and
recovering missed signals. No cron jobs or continuous service are installed.
No proposed workflow artifacts/caches are consumed by the privileged job. All
external Actions are pinned to commit SHAs; checkout does not persist credentials.

**Before enabling:** follow [owner setup](docs/owner-setup.md). The referee key
must be an **environment** secret in `referee-main`, restricted to the branch
`main` only. A repository secret would let an unadopted same-repository workflow
access it. A YAML `if` condition is not a substitute for this platform boundary.
Install every test App on the disposable game repository only. Player credentials
never belong in the game runtime. No unrelated secrets or self-hosted runners.

`PROOF_ENABLED=true` enables referee jobs; it is initially absent/false. This is
an out-of-game setup switch, not a security boundary. Adopted code can remove the
check; changing the variable itself needs separate platform permissions. Use
standard public-repository Linux runners, no paid runner classes; start with a
supervised campaign of at most 50 workflow runs and stop if
unexpected runs appear. This is an operational cap, not an immutable spending
limiter. Owner-side Actions disablement / App suspension is available if needed.

## Known limits

- GitHub does not atomically snapshot custom reviews and merge. Reviews and the
  base are checked again immediately before merging, but a final review/base race
  remains; only the head SHA is atomically guarded by the merge API. Serial
  workflow execution and referee-only main updates reduce, not eliminate, races.
- Unknown mergeability gets three reads with two-second waits, then stays pending.
  A later event or manual dispatch can retry. Failed writes are not blindly retried;
  a fresh invocation reads authoritative state (including a possibly successful
  merge whose response was lost).
- GitHub concurrency/event delivery can coalesce or miss work. Reconciliation
  reads all open PRs rather than trusting an event payload; this is not guaranteed
  scheduling/progress. Changing/removing the signal or referee can stop the game.
- Bot reviews, workflow-file adoption, ordinary-player restrictions, protected
  environment behavior, and automatic event chaining still require the
  [live proof](docs/live-proof.md). Bot results will not prove human/fork behavior.
- State commits/scoring, turn order, timers, victory rules, and deliberate
  destructive amendments are deferred.
