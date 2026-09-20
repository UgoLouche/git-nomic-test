# Live proof protocol (not yet executed)

Run only in the new disposable repository, with independently scoped installation
identities. Stop on an unexpected permission success, identity collision, unsafe
secret placement, or unexplained workflow loop. Do not repair an adopted destructive
amendment automatically; those experiments are deferred from this first slice.

## Preflight and initial source bootstrap

1. For each identity, inspect `GET /installation/repositories`; require that the
   accessible repository set contains **only** the disposable game. Verify token
   permissions using installation metadata/host token issuance, not token strings.
2. Resolve `GET /users/APP-SLUG[bot]`. Record the distinct bot user IDs and confirm
   later PR/review authors actually match. Configure the three player IDs in
   `game.json`. Keep this outside the game until the baseline is ready.
3. Inspect ruleset enforcement and the referee-only bypass actor. Check that the
   protected environment matches branch `main` only, not tags or PR refs. App
   credentials must have no repository Administration/Secrets permissions.
4. While the environment contains **no real key** and `PROOF_ENABLED=false`, have
   player A push a branch with a small `push` workflow whose job references
   `referee-main` and merely echoes a harmless marker. The job must be rejected
   by deployment policy before executing. No secret-reading or exfiltration test
   is needed. Preserve the rejected run URL, then delete this test branch.
5. Bootstrap the configured source on `main` using the referee identity. This is
   explicitly pre-game setup, not a player vote bypass. Referee source/bootstrap
   commits also demonstrate its Contents-write capability. Do not merge unrelated
   user material or install anything into `rustgame`.
6. Ask the owner to place the referee key in the protected environment and enable
   the proof variable once the isolation check passed. Player credentials remain
   entirely outside the game. Optional initial **Run workflow → main** in the UI
   isolates baseline runtime/authentication from review-trigger wiring. The Apps'
   Actions-read grant does not permit manual workflow dispatch via their API tokens.

## Identity and ordinary-player restriction proof

1. A creates a proposal branch from current `main`, commits a harmless change, and
   opens a PR targeting `main` (`POST /repos/{owner}/{repo}/pulls`). Confirm author ID.
2. With a player token, attempt an actual new harmless file commit to `main` and
   an actual merge of that open PR. Both must fail with a ruleset-specific response;
   an invalid SHA or generic auth error does not prove main protection. Verify
   `main` and the PR remain unchanged after each probe. Stop if either succeeds.
3. Before voting, verify the referee leaves the proposal open with no approvals.
4. B creates a review using `POST .../pulls/{number}/reviews` with
   `{"event":"APPROVE","commit_id":"CURRENT_HEAD_SHA"}`. Verify returned author
   is B, not the referee or GitHub Actions. Wait for signal → referee completion;
   one vote must not merge. Record both run IDs.
5. A revises the proposal. C approves the new SHA while B's approval remains on
   the old SHA. Wait for reconciliation; it must still not merge. Then B approves
   the new SHA, completing the two current-revision votes. It should merge.
6. Confirm the review list contains distinct B/C user IDs and the final merge
   targets the approved SHA. A's attempt to approve its own PR should be rejected
   by GitHub; never use a spoofed author field as identity evidence.
7. Repeat small proposals with B then C as author and the other identities as
   reviewers, so every role is exercised. Keep this bounded; do not build a
   generalized bot framework before the first identity proof works.

## Referee mutation and automatic continuation

1. A proposes exactly `VERSION = "v1"` → `VERSION = "v2"` in `referee.py`.
2. B/C approve the current SHA. Confirm a referee log with `referee: v1` evaluates
   and merges the proposal. Capture the merge commit and PR URL.
3. **Without manually starting the next run**, wait for the App-generated `push`
   on `main`. Confirm a successful Referee run whose log reports `referee: v2`
   and `installed_sha` equal to the adopted main commit. Check the event is `push`,
   not a later manual dispatch that would conceal a broken automatic chain.
4. Separately propose a harmless observable workflow amendment: add
   `echo 'workflow-v2'` to the installed referee's run step. Approve/adopt it and
   confirm the next automatic `push` run emits `workflow-v2`. This tests workflow
   write/merge permissions as well as adoption of a changed workflow definition.
5. Repeat delivery/manual re-run once where available; a closed merged PR must
   not merge again. Check no unintended additional proposals were adopted.

## Evidence and finish boundary

Record a compact table: scenario, identities, PR URL, approved head SHA, merge SHA,
workflow run URL/event, expected outcome, actual outcome. Keep secrets and raw
authentication diagnostics out of logs. Preserve failure evidence; do not relabel
missing permissions as legitimate game-over.

Initial campaign cap: **50 workflow runs**, standard public Linux runners only.
The cap is operational, not technically enforced. If delivery delays consume the
cap, stop/report rather than adding recurring schedules or paying for capacity.
Disable `PROOF_ENABLED` after the campaign; that requires owner variable access.
If unexpectedly modified workflows ignore it, the owner can disable Actions or
suspend the dedicated referee App. Do not delete the repository/evidence without
Ugo's agreement.

Success here proves this minimal bot/App setup, not human/fork restrictions,
weekly timers, scoring, state-ledger updates, destructive amendments, or full-game
completion. Only Ugo can agree that the overall task is complete.

## Relevant primary sources

- [Review API and installation-token permission](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request)
- [SHA-pinned merge API](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
- [Workflow events and default-branch workflow_run context](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)
- [Token-generated workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [GitHub's App-token Action](https://github.com/actions/create-github-app-token)
