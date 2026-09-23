# Historical v3/v4 playable campaign plan

> Historical protocol, not current rules or a new authorization to run a campaign.
> See [current mechanics](../playable-game.md) and [observed results](../playable-results.md).

Repository: `UgoLouche/git-nomic-test` only; existing four isolated Apps.
Ugo approved **50 additional workflow runs** after the initial 33-run proof, and
an **eight-hour** schedule (03:17/11:17/19:17 UTC). Standard public hosted runners
only; no broader credentials. The cap is operational and applies during this
supervised campaign, not an enforced lifetime limit on subsequent scheduled jobs.

Preflight read-back found the original main SHA unchanged, no open PRs/active
runs, all four installations restricted to this repository, player bypass never,
referee bypass always, the main-only environment policy, and readable PR timeline.
Ugo confirmed `PROOF_ENABLED=true`; the Apps cannot inspect/change that variable.

Planned bounded scenarios, all upgrades/amendments adopted through player votes:

1. A proposes the playable upgrade; B/C approve under the installed proof rules.
   Test profile uses 300-second proposal and 180-second voting windows, with an
   explicitly initialized ledger. This is a disposable test profile, not the
   human game's one-week defaults.
2. A proposes a visible referee marker change plus a ledger/award amendment. B/C
   vote. Require no early merge, then deadline merge and automatic adopted-code
   settlement/state commit, preserving the voted ledger edit.
3. B proposes and revises after selection; require closure, no award and rotation.
4. C misses its proposal window; require exactly one pass and a full new A window.
5. A proposes restoring weekly durations and one-point future awards. After B/C
   approval and cutoff, verify settlement/victory under the preceding voted ledger
   and award amendment; repeat reconciliation without duplicate points.

For short-deadline tests, the operator may submit a clearly labeled COMMENTED
review (not a vote) to wake the existing unprivileged signal at/after a real-time
cutoff. This exercises the actual Actions/referee path without changing its clock
or requiring Actions-write permission. It does **not** prove the cron trigger.
A scheduled run, if one occurs during observation, is separate evidence; otherwise
scheduled delivery remains pending rather than waiting eight hours for a test.

Stop at the cap, unexpected permissions/workflow behavior, or an actual blocker.
Observe canceled/coalesced notifications by reading authoritative PR/main state;
never resubmit mutations blindly. Store PRs, SHAs, run IDs and outcomes, never
credentials. Revoke temporary operator tokens after each use.

Afterward stop initiating campaign runs. Pausing `PROOF_ENABLED` is optional
owner housekeeping, not a required security step; leaving it enabled is consistent
with the separately approved recurring schedule. Scheduled records continue while
paused; owner workflow disablement stops them. Do not mark the overall task
complete without Ugo's agreement. Human UI and destructive game-over tests remain
outside this campaign.
