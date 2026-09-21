# Playable-game live evidence

This report records evidence collected before the final weekly-default restoration
proposal. The final proposal and subsequent settlement are independently visible
in [the mutable state ledger](../state.json), PR history and Actions. Full operator
read-backs and filtered referee output are preserved locally in
`docs/playable-evidence.json` (no credentials).

## Observed

| Scenario | Evidence |
| --- | --- |
| Voted upgrade | [PR #4](https://github.com/UgoLouche/git-nomic-test/pull/4): A authored, B/C approved. [Installed v2 run](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543635039) adopted the playable implementation at `a3d156c2b8250ef18c31024a970ebff1a5c375ff`. |
| Automatic state initialization | [Push run](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543646685) executed v3 and committed the first proposal window. The next [push run](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543655741) was idle, without another state write. |
| No early merge | [PR #5](https://github.com/UgoLouche/git-nomic-test/pull/5) had both approvals by 23:07:12 UTC. Its frozen cutoff was 23:10:27 UTC. [Run 35543709019](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543709019) waited for the deadline; merge occurred at 23:10:57 UTC. |
| Adopted code + ledger + award amendment | [PR #5](https://github.com/UgoLouche/git-nomic-test/pull/5) changed v3→v4, A's ledger to 3, and future awards to 2. [Installed v3](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543866989) merged it. [Automatic v4 push run](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543880159) preserved the voted ledger and added the frozen old-rule award of 1: A=4, B's turn. |
| Settlement not repeated | The next [push run](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543894294) waited for B without scoring again. |
| Frozen revision invalidation | [PR #6](https://github.com/UgoLouche/git-nomic-test/pull/6) was frozen at `67553033808e7fcde2de37b2e34b9c75d2909202`; B then revised it to `febffc6a72fdac5806f5ff28237fc60b253634b3`. [Run 35543972161](https://github.com/UgoLouche/git-nomic-test/actions/runs/35543972161) closed it, recorded `revised`, awarded nothing and advanced to C. |

- C's proposal cutoff was 23:17:58 UTC. [Run 35544240933](https://github.com/UgoLouche/git-nomic-test/actions/runs/35544240933) recorded exactly one pass at 23:18:22 and gave A a new full 300-second window. The following push was idle.
- The operator was then interrupted by quota. A's turn-4 window elapsed without a proposal. [Run 35557972672](https://github.com/UgoLouche/git-nomic-test/actions/runs/35557972672) recorded its pass at 03:35:14 UTC, without rewinding time, and gave B a fresh full window. The final restoration/winner scenario moves to B's turn 5; B proposes a ledger value of 3 plus restoration of weekly durations, so its frozen 2-point award should produce B=5.

## Validation boundaries

- **57 local tests pass**, including a near-26-week/13-turn game, lost-response
  recovery, voting edge cases and real-Git/fresh-process code+ledger adoption.
  Tests, compilation and actionlint also pass on the actually adopted v4 source.
- This is a disposable short-deadline game: proposal 300 seconds, voting 180
  seconds. The final amendment restores weekly durations and one-point future
  awards. The preceding voted two-point award still applies to that proposal;
  the proposed B=3 ledger amendment is expected to finish the game at B=5, A=4.
  This demonstrates victory under voted ledger amendments, not five unamended
  live accepted proposals; the latter progression is covered locally.
- Short-deadline wake-ups are explicit COMMENTED reviews, not votes. The actual
  installed Actions referee uses real time; the operator does not override its
  clock. These runs **do not establish cron delivery**. To retain headroom within
  the run cap after the interruption, final deadline evaluation may instead run
  the exact installed referee locally with a repo-scoped referee token; adopted
  settlement must still execute automatically on main push. The resumed guest's
  clock is stale, so any local evaluation must use GitHub's current HTTPS Date,
  not the guest clock or an artificially advanced simulation time.
- The installed schedule is 03:17/11:17/19:17 UTC, approved by Ugo. No scheduled
  tick was observed during this evidence window, including after the interruption;
  schedule delivery remains unverified rather than inferred from valid YAML.
- Some pending notifications were canceled by GitHub concurrency coalescing.
  Other runs completed the transitions; no mutation was blindly retried and no
  manual merge/state repair was used.
- The initial scope/identity/restriction proof remains in [live-results.md](live-results.md).
  No App grant/environment/credential boundary was broadened for this game.
- Human/fork play, destructive amendments, full historical review reconstruction,
  and exhaustive race/retry recovery remain untested. A changed or broken referee
  can legitimately stop the game; no immutable recovery engine is claimed.

Owner-side pause remains `PROOF_ENABLED=false`. That skips execution but not
scheduled workflow records; disabling the workflow also stops those. The campaign
ceiling is 50 additional runs beyond the original 33, monitored rather than a
technical lifetime spending limiter.
