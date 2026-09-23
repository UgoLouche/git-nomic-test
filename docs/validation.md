# Validation and history

[Home](../README.md) · [Setup](owner-setup.md) · [Mechanics](playable-game.md)

The main guides describe the current baseline. The reports below document what
was actually observed in the demonstration repository; they are not setup steps,
a guarantee about another repository, or instructions to repeat a campaign.

## What is established?

| Boundary | Evidence |
| --- | --- |
| Local game logic | Deterministic simulations cover turns, deadlines, early decisions, stale votes, failures/retries and adopted rules. |
| Variable roster | Local threshold/rotation cases cover 2–100 players; live gameplay used three. |
| Code/state adoption | Disposable real-Git merges and fresh processes, plus live voted referee/workflow/ledger changes. |
| CI gate | Live deliberate pytest failure blocked selection; repair opened voting; a workflow amendment ran in the same proposal before adoption. Negative metadata/rerun races also have local coverage. |
| Player isolation | Three player Apps were actually denied valid direct-main writes/manual merges by repository restrictions. This is not a human/fork proof. |
| Secret environment | A non-main job was rejected by deployment policy before secret placement in the original bootstrap. New repositories must verify their own configuration. |
| Owner reset | A real owner dispatch produced a state-only commit and automatic fresh start. Negative owner/re-run conditions have source/test coverage only. |
| Scheduled execution | Actual successful `schedule` runs executed the referee. Punctual delivery is not guaranteed. |

The v6 post-campaign tree passed **92 tests + 109 subtests**, compilation and
**actionlint 1.7.12** on all four workflows. These counts describe that checkpoint,
not a permanent requirement for future amendments. Local test instructions and
the test-file map are in [Extending the game](extending.md).

## Reports

1. [First live proof](live-results.md): distinct bot identities, ruleset/environment
   restrictions, referee/workflow adoption and automatic continuation.
2. [Original playable campaign](playable-results.md): v3/v4 turns, frozen revisions,
   real cutoffs, ledger/award amendments and victory. It used **deadline-only**
   voting; it is not evidence for v6 early decisions.
3. [V6 campaign](v6-results.md): reset, pytest gate/repair, mutable test workflow,
   early acceptance/rejection and scheduled delivery. It ended after **37 of 50**
   authorized runs, with weekly defaults restored.

Reports are dated snapshots. Follow current main/state to see a running game;
do not assume a reported score, turn or run count remains current indefinitely.
Local operator JSON evidence files may be available in a development checkout
but are intentionally untracked and not required to use the repository.

## Deliberate limits

This is a trusted-friends experiment. No claim is made that it is a hardened
service for adversarial players, that GitHub events arrive exactly once/on time,
or that any accepted amendment leaves a playable game.

Human/fork behavior, non-owner reset rejection and deliberate destructive
amendments still need separate validation if your group wants to rely on them.
Custom vote/base checks and merges are not atomic. Current-state review dismissal
and timeline consistency are not complete historical reconstruction. Tests cannot
prove all retries/races, and the mutable tests are not an integrity guarantee.

A proposed amendment changes the subject being tested. Existing evidence can
support the starting design without proving every newly adopted variation.

## Historical protocols

Retained for provenance, **not** the newcomer setup path:

- [Original four-App bot bootstrap](history/bot-bootstrap.md).
- [Original first-proof protocol](live-proof.md).
- [Original playable-campaign plan](history/playable-campaign.md).

Historical names, permissions context and operational instructions may differ
from the current guides. In particular, the referee enable switch is not a
mandatory post-test shutdown step, and human players do not require player Apps.
