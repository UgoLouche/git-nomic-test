# Git-nomic

**A game where changing the rules is how you play—and the rules are code.**

Git-nomic is a small collective programming game for friends and coworkers,
inspired by *Nomic*: a game whose rules can be changed by its players. Here,
GitHub is the table, pull requests are proposals, and code reviews are votes.
An automated **referee** counts the votes, merges accepted proposals, keeps
score, and moves the game to the next player.

The twist: the referee is part of the repository. You can propose changing how
votes count, how points are awarded, whose turn comes next, or the automation
itself. There is no immutable game engine underneath it all.

## What does a turn look like?

Imagine Alice, Bob and Charlie are playing:

1. **Alice proposes a change.** She opens a pull request: “Future accepted
   proposals should earn two points instead of one,” with the code and tests
   that implement it.
2. **Tests pass and voting opens.** The referee selects the proposal and freezes
   its revision. Alice must stop editing it at that point.
3. **Bob and Charlie review it.** `Approve` is a yes vote; `Request changes` is a
   no vote. Comments are discussion, not votes.
4. **The referee decides.** With both approving, it merges the change, awards
   Alice the one point promised when voting opened, and starts Bob's turn.
   Future proposals now carry the new two-point award.

That last detail matters: a proposal is accepted under the installed rules, then
its adopted code governs what happens next. Changing the scoring implementation
itself could change Alice's result too. That's part of the game.

## The starting rules, briefly

- **Two or more players**, taking turns in a registered order.
- **One week to propose**, then **up to one week to vote**.
- Passing tests are required before selection; selected proposals cannot change.
- A **strict majority of all registered players except the author** decides.
  An approving majority accepts early; a rejecting majority rejects early.
  No majority waits until the cutoff; insufficient approvals then lose.
- An accepted proposal normally earns **one point**. First to **five** wins.
- Only the referee merges game proposals. A green GitHub merge button is not
  permission for a player to merge one manually.

These are the starting rules, not permanent laws. The [installed code](game_engine.py),
[configuration](game.json), and [current state](state.json) govern each game.

## What could we change?

Start small: adjust the winning score, change the turn order, or introduce a
new scoring rule. Later, invent teams, change voting thresholds, or replace the
turn system entirely. Proposals can include tests, documentation, and workflows,
not just a settings change.

**Code is law, including mistakes.** An accepted amendment can deadlock the game
or break its automation. The group may agree to an out-of-game repair, but
recovery is not guaranteed by a hidden safety engine. This is an experiment
among trusted people, not a hostile multiplayer service.

## Join, host, or build

| I want to… | Start here |
| --- | --- |
| Play in a friend's game | [Player guide](docs/playing.md): finding your turn, proposing, voting, and reading results |
| Understand every decision | [Mechanics reference](docs/playable-game.md): eligibility, deadlines, votes, tests, scoring, and state |
| Start a game for my group | [Owner setup](docs/owner-setup.md): repository, players, referee App, permissions, and first launch |
| Implement a new rule | [Extending the game](docs/extending.md): code map, worked amendments, migration, and tests |
| Reset or troubleshoot a game | [Operations guide](docs/operations.md): controls, diagnostics, and agreed recovery |
| Know what has actually been tested | [Validation and history](docs/validation.md): live evidence versus remaining limits |

Players use their normal GitHub accounts; they do **not** need their own GitHub
Apps. The host configures one referee App. Familiarity with branches, pull
requests, and a little Python is helpful; reviews and discussion happen in GitHub.

## Before starting

This repository includes a **bot-played demonstration ledger and roster**, not a
fresh game for your group. Do not treat cloning it or pressing Reset as player
registration. Follow the setup guide to configure your own players and state.

The documented setup uses a **public repository owned by a personal GitHub
account**, hosted Actions runners, and tightly scoped credentials. Do not put
secrets or confidential work into game proposals. Human-account/fork behavior
still needs a short setup smoke test; the demonstrated live gameplay used bots.

For local development: install Python 3.12+, Git, and the dependencies in
[`requirements-test.txt`](requirements-test.txt). The [development guide](docs/extending.md#local-development)
walks through running the tests without live credentials.
