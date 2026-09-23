# V6 live validation — 2026-09-23

Repository: [UgoLouche/git-nomic-test](https://github.com/UgoLouche/git-nomic-test).
This campaign validates deployed v6; it supplements, rather than replaces, the
historical [first proof](live-results.md) and [playable proof](playable-results.md).

## Authorization and setup

The owner explicitly authorized an out-of-game v6 bootstrap, temporary short
windows, reset testing and a new cap of **50 additional workflow runs**. No new
App grants, paid runners, unrelated repositories or destructive amendments.

Preflight reconfirmed all four Apps select only this repository, the original
permission grants, player `never` / referee `always` ruleset bypass, and the
`referee-main` environment restricted to branch `main`. Existing direct-write and
manual-merge restriction probes were not repeated. Tokens were memory-only and
revoked after use; private keys stayed outside the game repository/runtime.

Deployment [5986b21](https://github.com/UgoLouche/git-nomic-test/commit/5986b21cf9126454beb55724fbad72ea82267232)
installed checkpoint v6 in a normal non-force commit, preserving the old finished
ledger. Temporary proposal/voting windows were 1800/900 seconds. The owner then
personally dispatched **Reset game → main → RESET**.

## Observed evidence

| Scenario | Evidence and outcome |
| --- | --- |
| V6 deployment without implicit reset | [Push run 35686328205](https://github.com/UgoLouche/git-nomic-test/actions/runs/35686328205) executed v6 at `5986b21` and reported `finished`; the old ledger was unchanged. |
| Owner reset | [Run 35863187628](https://github.com/UgoLouche/git-nomic-test/actions/runs/35863187628) succeeded with both actor and triggering actor `UgoLouche`. Commit `493877a` changed **only state.json**, cleared scores/history and retained the previous commit as its parent. |
| Automatic fresh start | [Push run 35863218972](https://github.com/UgoLouche/git-nomic-test/actions/runs/35863218972) initialized turn one at 12:52:14 UTC, with the full 1800-second proposal window. The next push reported `waiting-for-proposal`, without another state write. |
| Failed tests prevent selection | A's [PR #8](https://github.com/UgoLouche/git-nomic-test/pull/8) deliberately failed one test: [pytest run 35863505671](https://github.com/UgoLouche/git-nomic-test/actions/runs/35863505671), **1 failed, 91 passed, 109 subtests passed**. [Referee run 35863531829](https://github.com/UgoLouche/git-nomic-test/actions/runs/35863531829) reported `pytest-failed` and `waiting-for-proposal`; the PR was not frozen. |
| Repair and runner amendment in the same PR | A revised PR #8 to fix the test, add a harmless workflow step and restore weekly rules. [Run 35863688747](https://github.com/UgoLouche/git-nomic-test/actions/runs/35863688747) passed **92 tests + 109 subtests** on exact head `ebf71ff` and actually printed `pytest-workflow-v6-amended`. [Referee run 35863707296](https://github.com/UgoLouche/git-nomic-test/actions/runs/35863707296) froze that repaired head and opened voting. No installed-runner equality/two-step restriction was imposed. |
| Whole-electorate threshold | With B approving and C abstaining, [run 35863848490](https://github.com/UgoLouche/git-nomic-test/actions/runs/35863848490) waited. One of two registered non-authors was not a majority. |
| Early acceptance and adopted settlement | C then approved. [Run 35864000851](https://github.com/UgoLouche/git-nomic-test/actions/runs/35864000851) merged PR #8 at **12:59:38 UTC**, before its **13:11:41 UTC** cutoff. The referee App was the merger. [Automatic push run 35864039705](https://github.com/UgoLouche/git-nomic-test/actions/runs/35864039705) awarded A one point exactly once and opened B's full weekly window under the adopted rules. |
| Adopted pytest workflow | B's [PR #9](https://github.com/UgoLouche/git-nomic-test/pull/9) passed [run 35864191096](https://github.com/UgoLouche/git-nomic-test/actions/runs/35864191096), again printing the adopted workflow marker, then entered voting. |
| Early rejection | A's lone `Request changes` review left [run 35864409065](https://github.com/UgoLouche/git-nomic-test/actions/runs/35864409065) waiting. After C also requested changes, [run 35864529042](https://github.com/UgoLouche/git-nomic-test/actions/runs/35864529042) closed PR #9 at **2026-09-23 13:04:18 UTC**, before its **2026-09-30 13:01:18 UTC** cutoff, awarded nothing and advanced to C. Subsequent runs remained idle without repeated advancement. |
| Scheduled delivery | Four actual successful `schedule` runs occurred while waiting for the owner reset: [35705758425](https://github.com/UgoLouche/git-nomic-test/actions/runs/35705758425), [35748021648](https://github.com/UgoLouche/git-nomic-test/actions/runs/35748021648), [35791235865](https://github.com/UgoLouche/git-nomic-test/actions/runs/35791235865), [35838321219](https://github.com/UgoLouche/git-nomic-test/actions/runs/35838321219). Their logs executed v6 and reported `finished`. This proves delivery, not punctual scheduling. |

## Final read-back

At **2026-09-23 13:06:51 UTC**:

- Main: **`05c06127c5514a5b021f25fd761779bfc6fe9524`**.
- Phase `proposing`, turn **3**, player C; scores **A=1, B=0, C=0**.
- C's proposal deadline: **2026-09-30 13:04:13 UTC**.
- Original three-player order and weekly proposal/voting windows restored;
  `require_pytest: true`, one point per acceptance, first to five.
- **No open PRs or active runs.** Referee and approved recurring schedule remain enabled.
- **37/50 campaign runs**, baseline 86 → total 123: **34 success**, **1 intentional
  pytest failure**, **2 concurrency-coalesced cancellations**. No unexpected failed
  run, manual player merge, clock rewind or unapproved ledger repair.
- The campaign stopped after its agreed checks; unused budget was not filled with
  additional scenarios. The active game was not reset again or declared finished.

Local merge commit **`76ff3dc`** reconciles development history with that exact
live tree. **92 tests + 109 subtests**, compilation and actionlint 1.7.12 on all
four workflows pass locally. Subsequent documentation updates are local-only;
no extra live proposal was opened just to publish this report.

Full local operator evidence: `docs/v6-evidence.json`, alongside the preserved
older campaign JSON files. These evidence files are intentionally untracked.

## Remaining limits

- Reset success is live-proven; rejecting a non-owner dispatch/re-run is checked
  in source/tests, **not** live-proven. Apps lack Actions write and cannot exercise
  the owner workflow as human actors. No grants were broadened for that purpose.
- This campaign used three players. Other roster sizes (2–100), rerun-status
  races, frozen-revision edge cases and negative adapter metadata cases retain
  their local test evidence, not newly claimed live coverage.
- Human/fork permissions, destructive amendments, exhaustive race/retry recovery
  and guaranteed progress remain untested/not promised. Review/base/merge checks
  remain non-atomic. Tests/workflow/gate remain amendable game code.
- A successful campaign does not by itself mark the overall project complete.
