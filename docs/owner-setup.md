# Start a game for your group

[Home](../README.md) · [Operations and reset](operations.md) · [Player guide](playing.md)

This is the human-game setup path: **one dedicated repository, one referee
GitHub App, and two or more people using their normal GitHub accounts**. Player
Apps are only for bot testing; the [old four-App bootstrap](history/bot-bootstrap.md)
is historical, not a prerequisite.

The supported baseline is a **public repository owned by a personal GitHub
account**, default branch `main`, standard GitHub-hosted Ubuntu runners. Private
repositories need different plan/access considerations: the current test runner
fetches source anonymously, so changing visibility alone will break it. The reset
workflow checks a personal owner login; organization repositories need a different
operator policy. Do not present either as a tested drop-in configuration.

## Before you begin

You need:

- Owner access to the new repository and permission to register/install an App.
- Git, Python 3.12+ and a way to push commits as yourself; GitHub CLI (`gh`) is
  useful for user-ID lookup and manual workflow dispatch.
- A roster and turn order agreed with your group.
- Agreement that accepted code can break the game, plus who may perform an
  out-of-game reset or repair. The owner retains unavoidable administrative power.

Use a repository containing **only the game**. Public means source, proposals,
reviews and score history are public. Do not add unrelated secrets, self-hosted
runners or confidential material. Forks and third-party contributions should not
be assumed equivalent to the tested same-repository player flow.

## 1. Create and prepare your own repository

Create an **empty public repository** under your personal account. Do not copy the
demonstration's repository name, bot roster or current score ledger as your game.

The commands below use a new local directory. Replace `OWNER/NEW-GAME` before
running them. They copy source/history but not GitHub settings, secrets or Apps.

```sh
git clone https://github.com/UgoLouche/git-nomic-test.git my-git-nomic
cd my-git-nomic
git remote rename origin upstream
git remote add origin https://github.com/OWNER/NEW-GAME.git
git remote -v
```

Verify `origin` points to **your new empty repository**, not the demonstration.
Keep Actions' referee disabled/unconfigured until the rest of setup is ready.
Missing `PROOF_ENABLED` prevents the baseline referee job from executing.

### Register actual people

For each GitHub login, retrieve the numeric **user ID**:

```sh
gh api users/ALICE --jq .id
gh api users/BOB --jq .id
```

You can also open `https://api.github.com/users/LOGIN` and read `id`. User IDs are
not App IDs, installation IDs, login strings or email addresses.

Edit `game.json`: retain `base: "main"`, replace `players` with your ordered list
of distinct positive IDs (at least two), and choose the initial durations/awards.
For an ordinary first game keep 604800-second windows, `points_per_accept: 1`,
`points_to_win: 5`, and `require_pytest: true`.

Generate a matching clean state **only in this new-game bootstrap checkout**:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from reset_game import fresh_state
rules = json.loads(Path("game.json").read_text())
Path("state.json").write_text(json.dumps(fresh_state(rules), indent=2) + "\n")
PY
```

This writes a local file; it does not contact GitHub or reset another game. Inspect
it: zero scores for your players, empty history/winners, turn 1, first player,
phase `new`, and no deadline. `python reset_game.py` is a preview of a JSON
**wrapper** containing that state; do not redirect that wrapper into `state.json`.

Run the [local checks](extending.md#local-development), then seed the new repo:

```sh
git add game.json state.json
git commit -m "Bootstrap our player roster and fresh game"
git push -u origin HEAD:main
```

Set GitHub's default branch to `main`, keep **merge commits enabled**, and allow
the repository's pinned Actions. This initial owner seed is an explicit
**pre-game bootstrap**, not permission to push normal game amendments directly.
After step 3, ordinary direct-main writes must stop working.

## 2. Register and install one referee App

In your personal GitHub **Settings → Developer settings → GitHub Apps → New
GitHub App**, choose a unique name and use your game repository URL as Homepage URL.

- Disable webhook **Active**; there is no webhook server to host.
- No OAuth callback, user authorization flow, or webhook subscriptions are needed.
- Choose **Only on this account** for installation availability.
- Set exactly these repository permissions:

| Permission | Access | Why |
| --- | --- | --- |
| Contents | Read and write | Read game data and commit state |
| Pull requests | Read and write | Read reviews, close and merge proposals |
| Workflows | Read and write | Adopt amendments to `.github/workflows/` |
| Actions | Read-only | Inspect proposal run/job/step results |
| Metadata | Read-only (implicit) | Repository metadata |
| Administration, Secrets, everything else | No access | Not needed for gameplay |

Create the App, then **Install App → Only select repositories → your game**.
Never select all repositories or share an App with unrelated work. Record the
App's **Client ID** for step 4. Generate a private key and store the downloaded PEM
outside the clone; never commit it, paste it into an issue, or share it with players.

GitHub Actions will mint short-lived installation tokens from this key. The
referee requests only this repository and the permissions it needs; reset requests
only Contents write. The workflow token action revokes its token after the job.
Players do not need any of these credentials.

## 3. Restrict `main` to the referee

In repository **Settings → Rules → Rulesets**, create a **branch ruleset**:

| Setting | Required baseline |
| --- | --- |
| Name | For example `referee-only-main` |
| Enforcement | **Active** |
| Target | Exactly branch `main` |
| Bypass | **Only your referee App**, **Always allow** |
| Rules | **Restrict creations**, **Restrict updates**, **Restrict deletions**, **Block force pushes** |

Do not add humans, player Apps, repository roles or GitHub Actions to bypass.
Do not enable a fork synchronization exception. If the App is not selectable,
verify its installation rather than allowing everyone to bypass.

Do **not** add native required approval counts, mandatory status checks, a merge
queue or linear-history requirements as substitute game rules. The installed
referee decides adoption, including test and majority policy. It needs ordinary
merge commits and state writes, so a fixed native gate can obstruct the game.
Audit overlapping inherited rulesets/branch protection too.

The owner can change repository settings and therefore cannot be made powerless
by this design. Treat changing protections as out-of-game administration, never
as a normal player's way to get a proposal merged.

## 4. Isolate the key before enabling anything

Create repository environment **`referee-main`**:

1. Deployment branches/tags: **Selected branches and tags**.
2. Add exactly **Branch: `main`**—not a tag, wildcard, “Protected branches only,”
   or a `refs/pull/*/merge` allowance.
3. No required reviewer/wait timer for ordinary autonomous operation.
4. Leave it without a real secret until the isolation check below passes.

Add repository **Actions variables**:

| Variable | Value |
| --- | --- |
| `REFEREE_CLIENT_ID` | Your referee App's Client ID |
| `PROOF_ENABLED` | `false` during setup |

Despite its historical name, `PROOF_ENABLED` is the general referee enable
switch. It is not a sandbox and does not disable the separate owner-reset job.

### Check that a non-main job cannot enter the environment

Before adding the real key, create a temporary branch `setup/environment-probe`
with `.github/workflows/environment-probe.yml` containing only:

```yaml
name: Environment isolation probe
on:
  push:
    branches: [setup/environment-probe]
permissions: {}
jobs:
  probe:
    runs-on: ubuntu-latest
    timeout-minutes: 1
    environment: referee-main
    steps:
      - run: echo 'No secrets are referenced by this probe.'
```

Push that branch, without opening a game PR. Its job must be **rejected by the
environment branch policy before any step executes**. A skipped job, a YAML error,
or an echo that ran successfully is not that proof. Do not bypass the rejection.
Do not merge this probe into `main`; delete the temporary remote branch afterward.

Only after this succeeds, add **environment secret** `REFEREE_PRIVATE_KEY` with
the **complete PEM contents**, including its BEGIN/END lines. Do not enter its
filename. Never store it as a repository/organization-wide secret: same-repository
proposals can alter their workflows, so their jobs must not inherit that key.

The baseline Proposal tests workflow has `permissions: {}`, no environment, no
shared cache, and an anonymous head fetch. The privileged referee reads only
GitHub metadata before adoption; it must not execute a proposed head or consume
its artifacts with this key available.

## 5. Invite players and check human permissions

Invite the registered people as repository collaborators with **write access**,
not administrative access/bypass. They should work on same-repository branches.
Authentication must permit their intended Git pushes; token users may need the
relevant workflow-file permission to propose workflow amendments. Do not solve
that by sharing the referee identity.

Before enabling normal play, use a real **non-owner** collaborator for a short,
explicit setup rehearsal:

- Create a harmless branch and PR; another registered person can submit reviews.
- Confirm proposal pytest runs on the expected head without protected credentials.
- Try a direct-main write and manual merge of a genuinely mergeable harmless PR.
  Both must fail **because of main restrictions**, not because a token is invalid
  or the PR conflicts. A successful bypass is a setup failure: stop and correct it.
- Close the rehearsal PR without adopting it; do not mistake it for a turn proposal.

Treat this as an agreed pre-game permission test in the new disposable setup, not
routine attempts to bypass an active game. The published live campaigns used bot
identities, so owner-account success alone does not establish ordinary human behavior.

## 6. Start the clock

Review the checklist:

- [ ] `main` contains your actual player IDs and fresh `phase: new` state.
- [ ] Referee App selects only this repository, with exactly the required grants.
- [ ] Main restrictions block ordinary writers and mergers.
- [ ] The main-only environment rejected the harmless branch probe.
- [ ] Referee key is an **environment** secret; no unrelated/player secrets exist.
- [ ] Player permission rehearsal passed; merge commits and Actions are enabled.
- [ ] Players know how voting, frozen revisions and agreed recovery work.

Set `PROOF_ENABLED=true`, then **Actions → Referee → Run workflow → main**.
Changing a variable is not itself a workflow trigger; this manual run starts the
game immediately rather than waiting for the schedule.

Expect a `started` result, a state commit with a full proposal window, and a
follow-up push run reporting `waiting-for-proposal`. Read actual output from
**Run only the installed referee**, including `installed_sha`; a green badge or
an echoed command alone is not enough. Share the [player guide](playing.md) and
let the first player open a **new** PR after the recorded start time.

## Reusing an existing demo instead

You can reuse the demonstration repository, but it is not fresh configuration.
Agree an out-of-game preparation window; preserve old history, replace bot IDs
with humans, and install a matching fresh state **together**. Updating only the
roster can leave the stored current player/proposal invalid. Reset alone clears
scores but **does not replace the roster or restore starter code**.

For a coordinated setup the owner can temporarily set `PROOF_ENABLED=false` and
let active jobs finish. This skips future referee execution but is not a lock
against an already-running job or owner reset. Install the agreed roster/state
through an explicitly authorized referee operation or tightly controlled owner
bootstrap, then reverify restrictions before enabling. Do not leave a human
bypass behind. Remove the old **player-App installations** from the game, retain
the referee installation, and perform the human smoke test above.

These are owner decisions, not actions players should take through ordinary
manual merges. A separate new repository avoids mixing initial human play with
the demo ledger, but is optional rather than a new game rule.

## GitHub references

- [Registering an App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)
- [Installing an App](https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app)
- [Rulesets and bypass](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Available rules, including Restrict updates](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Environments, secrets and branch policies](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)

For resets, pauses, failed runs and agreed repairs, continue to [operations](operations.md).
