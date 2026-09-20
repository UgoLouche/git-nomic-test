# First live GitHub proof — 2026-09-20

Repository: [UgoLouche/git-nomic-test](https://github.com/UgoLouche/git-nomic-test).
This is a bounded three-player App proof, not a finished turn/scoring game.

| Check | Observed result / evidence |
| --- | --- |
| Identity and scope | Four distinct private Apps; each installation selects only this repository. No Administration or Secrets grant. |
| Main writes and manual merges | All three players received explicit repository-rule rejection: direct writes HTTP 409, merge attempts HTTP 405. Main stayed unchanged. |
| Environment isolation | [Run 35536659741](https://github.com/UgoLouche/git-nomic-test/actions/runs/35536659741) rejected the proposal branch before any step executed. The real key was added afterward. |
| Distinct reviews/self-review | [PR #1](https://github.com/UgoLouche/git-nomic-test/pull/1): A authors; B/C submit distinct reviews; A self-approval returns HTTP 422. |
| Insufficient approval | [Run 35539955606](https://github.com/UgoLouche/git-nomic-test/actions/runs/35539955606): installed v1 sees B approve/C request changes and leaves the proposal open. |
| Stale approval | [Run 35540145825](https://github.com/UgoLouche/git-nomic-test/actions/runs/35540145825): B old-head approval becomes abstention; C current-head approval alone does not merge. |
| Referee amendment | [Run 35540169414](https://github.com/UgoLouche/git-nomic-test/actions/runs/35540169414): v1 adopts PR #1 as `9fbc3f5046e1dc83cd251dcf68c5862d332d833a`. |
| Automatic new referee | [Push run 35540182689](https://github.com/UgoLouche/git-nomic-test/actions/runs/35540182689): executes v2 at that adopted SHA without manual dispatch. |
| Role rotation/one vote | [PR #2](https://github.com/UgoLouche/git-nomic-test/pull/2) is authored by B; [run 35540392804](https://github.com/UgoLouche/git-nomic-test/actions/runs/35540392804) leaves it open with only A approving. |
| Workflow amendment | A/C approve PR #2; [run 35540415826](https://github.com/UgoLouche/git-nomic-test/actions/runs/35540415826) merges `.github/workflows/referee.yml` as `2ad4a9848b9f3e33e31262ad234303c36c883414`. |
| Automatic changed workflow | [Push run 35540428529](https://github.com/UgoLouche/git-nomic-test/actions/runs/35540428529) prints the actual `workflow-v2` marker and executes v2 at the new SHA. |

The first enabled run failed with `Invalid keyData` before executing the referee.
Re-entering the complete referee PEM as the environment secret resolved it; later
App-token creation and adoption succeeded. No secret contents are included here.

Local tests use simulated GitHub responses. The disposable Git adoption fixture
normalizes its starting version so the real v2 amendment does not break a test
whose scenario deliberately begins at v1. Tests are not immutable merge gates.

Still outside this proof: human/fork permissions, weekly turns/deadlines, scores,
state-ledger updates, destructive amendments, and exhaustive race/retry testing.
No guarantee of progress or automatic recovery is introduced.
