# Extending the game

[Home](../README.md) · [Mechanics](playable-game.md) · [Proposing and voting](playing.md)

A rule amendment is a normal pull request containing the code, data, tests and
documentation needed to describe a different game. There is no plugin interface
or protected core you must work around: you can edit the referee itself.

This guide explains how to make those changes understandable and deliberate.
Compatibility is useful when you want play to continue; it is not an immutable
requirement that forbids players from voting for a broken or radically different game.

## Local development

Work on your proposal branch in a clone of the group's repository. Use a trusted
local environment for known code; tests execute arbitrary Python. Review others'
changes before running them, and use a disposable environment with no credentials
for unfamiliar proposals.

The runtime is Python standard library plus the existing `gh` command for GitHub
API calls. Local tests need Python **3.12+**, Git, and pytest. CI uses 3.12.

```sh
python3 -m venv .venv
# POSIX shell:
. .venv/bin/activate
# Windows PowerShell alternative: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
python -m pytest -q
python -m compileall -q referee.py game_engine.py reset_game.py tests
git diff --check
```

If installed, run [actionlint](https://github.com/rhysd/actionlint) over changed
workflows (or `actionlint` from the repository root). No GitHub token/private key
is needed for the local test suite. Use `python` instead of `python3` where that
is your Python 3 launcher. Runtime packages remain separate from test dependencies.

Do **not** run a proposed `referee.py --apply` against the live repository.
Even without `--apply`, a modified Python program is arbitrary code; the CLI's
read-only default is not a sandbox. Simulate with fake inputs instead.

## Where changes belong

| File / area | Responsibility | Typical amendment |
| --- | --- | --- |
| [`game.json`](../game.json) | Player order, durations, award, winning threshold, pytest requirement | First to seven; shorter windows |
| [`state.json`](../state.json) | Ledger, current turn, frozen proposal, history | An explicit score adjustment or state migration |
| [`game_engine.py`](../game_engine.py) | Playable selection, tally, transitions, settlement | Different majority, turn system or scoring |
| [`referee.py`](../referee.py) | Rule validation, GitHub adapter, CLI; legacy proof mode | Different CI lookup or API behavior |
| [`reset_game.py`](../reset_game.py) | Explicit owner reset and fresh-state construction | Reset support for a new state schema |
| [`.github/workflows/`](../.github/workflows) | Test execution, wake-ups, privileged referee and owner reset | Different testing or scheduling |
| [`tests/`](../tests) | Executable examples of intended behavior | New expectations for the new rules |
| Documentation | Human explanation of consequences and operation | Keep players able to understand the adopted game |

Important functions in `game_engine.py`:

- `reconcile_game`: one invocation's state-machine decision.
- `tally` / `majority`: eligible review interpretation and threshold.
- `start_turn`: opens a full new proposal window.
- `finish`: records the outcome, applies the adopted scoring/rotation/victory logic.
- `validate`: assumptions about configuration and stored state.

`referee.validate_rules` validates roster/base/gate configuration before the CLI
runs the playable engine. `GitHub.pytest_status`, `merge` and `save_state` contain
the current platform-adapter behavior. The older `decision` / `reconcile` path is
for configurations without `turns`; changing it alone does not change playable
voting. Conversely, a shared-rule change may need both paths and their tests updated.

## The key design question: when does the change take effect?

```text
current main: decide whether this proposal is accepted
                     ↓ merge
new main: settle this very proposal, then continue the game
```

The existing referee does not load your proposed Python to decide adoption.
After merge, however, the **new** code reads the **merged** state. This is the
most important boundary to reason about in a proposal.

The pending proposal normally still carries the old electorate, head and award.
New configuration/code can change the ledger, winning threshold and rotation
used to settle it. If you change settlement itself, that change runs immediately;
there is no protected “finish the old turn with the old engine” stage.

State your activation semantics in the PR. “Future proposals only” and “including
this proposal” are different changes, and both are possible.

## Worked amendment: future proposals earn two points

Change just `turns.points_per_accept` in `game.json` from `1` to `2`, update docs,
and test the intended boundary. Under the unchanged engine, the accepting proposal
still receives its old frozen award. The **next selected proposal** snapshots 2.

The test suite provides an in-memory `World` in `tests/test_game.py`. A new pytest
test placed alongside it can demonstrate adoption without any live API call:

```python
from test_game import World


def test_award_change_starts_with_next_selected_proposal():
    w = World()
    w.voting()  # Starts a game, selects a PR, and gives it all eligible approvals.
    w.on_merge = lambda: w.rules["turns"].update(points_per_accept=2)

    assert w.tick() == "merged"    # Installed rules authorize adoption.
    assert w.tick() == "accepted"  # A new invocation settles adopted state.
    assert w.state["scores"]["11"] == 1

    w.propose()                   # The next player's proposal.
    assert w.tick() == "voting-opened"
    assert w.state["proposal"]["award"] == 2
```

The fixture's IDs (11, 22, 33) are synthetic, not your live players. Its on-merge
callback simulates adoption, not execution of GitHub Actions. For actual code
replacement and Git merge behavior, see the fresh-process test below.

Changing only `points_to_win` is different: the new threshold is read during
settlement, so lowering it can make someone win as soon as this amendment settles.
Changing window lengths does not retroactively rewrite an already stored deadline.

## Worked amendment: change scoring code

To add a bonus at acceptance, inspect the `outcome == "accepted"` block in
`finish`. That is where the frozen award is added to the **adopted ledger**. A bonus
implemented there would affect the amendment's own settlement as well as later
acceptances, unless you explicitly code an activation boundary.

Design and test at least:

1. The new score calculation and how the history explains it.
2. Whether a simultaneous ledger amendment is preserved.
3. Whether the new score causes victory, including more than one possible winner.
4. A fresh invocation after settlement, proving the bonus is not added twice.
5. Any conditions that should leave rejected/passed turns unawarded.

Changing the award in configuration is simpler if you only want future selected
proposals to carry a different fixed amount. Editing scoring code is appropriate
when you want a different calculation, not a different constant.

## Worked amendment: change the roster or turn order

`players` controls eligibility and rotation, but it is **not all of player state**.

- Reordering the list changes who follows the current player at settlement.
- New players need appropriate repository access as well as registration. A
  roster amendment does not invite a collaborator or change GitHub permissions.
- The selected proposal's electorate stays frozen unless your amendment changes
  the pending state or the code that uses it.
- The current player must remain registered under the baseline validator. Simply
  removing the author of the adopting proposal can stop the fresh invocation
  before it settles.
- Scores use string keys. The baseline adds a missing author's score from zero,
  but migrating a new scoring schema may require more than adding a player ID.

For a normal continuing game, test rotation and eligibility across the adoption
boundary, including wraparound and the pending author. For replacing the whole
roster between games, agree an owner bootstrap of matching rules and fresh state
rather than disguising a reset as an ordinary edit. See [setup](owner-setup.md#reusing-an-existing-demo-instead).

## Editing live state without losing the turn

A proposal can change `state.json`, but voting selection also commits that file
on `main`. Git merges the proposal with those intervening writes.

Prefer a narrow edit to the intended ledger entry. Replacing the entire file
with an old snapshot can conflict, erase pending metadata, or alter the game more
than intended. A conflict after selection cannot be repaired by pushing another
commit without violating the frozen-head rule.

[`tests/test_playable_adoption.py`](../tests/test_playable_adoption.py) demonstrates
the important case with a real disposable Git repository: a proposed score edit
and scoring-code change merge with the referee's intervening voting-state commit;
a **fresh Python process** then runs adopted code, preserves the edited score,
and adds the frozen award once.

For a new schema, include an explicit migration strategy in adopted code, or a
carefully compatible state edit, and update validation plus `fresh_state`/reset
as appropriate. Test an old valid state entering the new implementation. There
is no automatic schema versioning framework or rollback engine to do this for you.

## Changing tests and workflows

Tests are examples of the intended game, not an unchangeable constitution. If a
proposal changes a rule, update obsolete assertions and add tests for the new
behavior. Do not make production behavior lie just to satisfy historical fixture
expectations. Existing fixture version labels are scenario markers, not installed
release requirements.

The test workflow can change **in the same PR** as the game and its tests. There
is no installed-file equality check or mandatory two-proposal process. A reviewer
must assess whether the proposed testing still says anything useful.

There are nevertheless technical adoption dependencies:

- The **installed** gate looks for workflow `proposal-tests.yml`, a PR/SHA-bound
  run title, job `pytest`, and step `Run pytest`. Renaming/removing these only in
  the proposed head may leave the current gate unable to recognize your success,
  even if your proposed referee also changes the lookup. Provide a compatible
  result for the adopting PR, or design another transition that the installed
  rules can actually accept. This is current code behavior, not a ban on renaming.
- A proposal setting `require_pytest: false` is still admitted under the current
  setting. A passing adopting proposal can disable the gate for subsequent turns.
- The baseline workflow installs pytest directly; it does not install an arbitrary
  proposed requirements file. Adding test/runtime dependencies requires the
  corresponding workflow installation changes as well as dependency declarations.
- Tests run on PR head, not the final merge result. Passing tests cannot prove a
  state amendment will merge cleanly or that adopted code will remain healthy.
- `workflow_run` subscriptions identify the upstream workflow names. Changing
  those names or event wiring can stop automatic wake-ups; update dependencies
  coherently and explain any reliance on scheduled/manual reconciliation.

Keep the security distinction clear: proposed code runs without referee credentials;
adopted code has the scoped game identity. Do not “fix CI” by moving proposed
code into a privileged `pull_request_target` job, exposing the environment key to
PR refs, granting unrelated permissions or consuming untrusted artifacts in the
privileged job. Mutable game rules do not justify endangering unrelated resources.

## Test map and recommended coverage

| Test file | What it demonstrates |
| --- | --- |
| `test_game.py` | Simulated clock/state transitions, votes, deadlines, faults and awards |
| `test_roster_checks_reset.py` | Variable rosters, mocked CI metadata, actual pytest subprocesses, reset and workflow source assertions |
| `test_playable_adoption.py` | Real Git merge + fresh-process adopted scoring/ledger settlement |
| `test_referee.py` | Original decision/adapter path and API checks |
| `test_adoption.py` | Original executable referee-adoption fixture |
| `test_v6_live_gate.py` | Small repaired test retained from the live gate experiment; not broad coverage by itself |

Use fake time and fake GitHub responses to explore a whole game without waiting a
week or spending Actions runs. `World.due()` advances to the cutoff; `vote`,
`propose`, `tick`, and `on_merge` help express scenarios. Include negative cases,
not just your intended winning path. Real-Git tests are especially useful for
state edits, and fresh-process tests for changes to the referee itself.

The tests are deliberately layered. A mocked API success is not proof of actual
GitHub permissions or workflow delivery. A manual successful run is not proof of
automatic continuation. Consult [validation](validation.md) for existing live
evidence rather than repeating it or claiming it covers a new boundary.

## Before asking others to vote

- [ ] Explain the new rule and when it takes effect, including this proposal.
- [ ] Include code/config, any migration, tests and player-facing documentation.
- [ ] Test adoption followed by settlement—not only a game already using new code.
- [ ] Preserve state/CI compatibility where continued play is intended.
- [ ] Explain any new dependency, privilege, runner/cost impact, or intentional risk.
- [ ] Run local checks, then observe the actual PR-head CI result.
- [ ] Once the referee selects the revision, stop editing it.

A maintainer can contribute an improvement to a separate development copy as an
ordinary software PR. Installing that improvement into an **active game** is
still a game proposal (or an explicitly agreed owner intervention), not an
excuse for a silent upstream synchronization that bypasses votes.
