> Historical four-App bot bootstrap, retained as evidence of the original setup.
> **For a new human game, use [Owner setup](../owner-setup.md), not this protocol.**

# Owner setup needed for live validation

This document records the original four-App bot bootstrap. For a human game,
create only a referee App, invite players with Write (not Admin) access, and put
2+ distinct human GitHub user IDs in `game.json` in turn order. The referee and
owner-reset workflows require the main-only environment; the proposal pytest
workflow must remain unprivileged and does not use that environment. See README
for current operation and reset instructions. Validate ordinary human restrictions
before relying on the historical bot-only proof.

The current agent installation token exposes only `UgoLouche/rustgame`. Do not
expand that App or put the mutable game under its credentials. GitHub App
registration/installation requires the owner's authenticated account; the agent
has no authenticated owner browser session here.

## 1. Disposable repository

Create **`UgoLouche/git-nomic-test`**, public, initialized with a README and default
branch `main`. If the name already exists, do not reuse it blindly; choose a new
empty disposable repository and adjust the URLs below.

Public is selected for the first proof because GitHub Free supports branch
rulesets, environment secrets/restrictions, and standard free Linux Actions on
public repositories. This is a new toy repository, not publication of an existing
private project. Do not put confidential material in it. Leave paid/larger and
self-hosted runners unused. No paid services or recurring schedule are needed.

## 2. Register four private GitHub Apps

These links use GitHub's documented form-prefill mechanism; no callback server,
OAuth user flow, webhooks, or custom manifest broker is required.

- [Player A](https://github.com/settings/apps/new?name=ugolouche-nomic-player-a&url=https%3A%2F%2Fgithub.com%2FUgoLouche%2Fgit-nomic-test&public=false&webhook_active=false&request_oauth_on_install=false&contents=write&pull_requests=write&workflows=write&actions=read)
- [Player B](https://github.com/settings/apps/new?name=ugolouche-nomic-player-b&url=https%3A%2F%2Fgithub.com%2FUgoLouche%2Fgit-nomic-test&public=false&webhook_active=false&request_oauth_on_install=false&contents=write&pull_requests=write&workflows=write&actions=read)
- [Player C](https://github.com/settings/apps/new?name=ugolouche-nomic-player-c&url=https%3A%2F%2Fgithub.com%2FUgoLouche%2Fgit-nomic-test&public=false&webhook_active=false&request_oauth_on_install=false&contents=write&pull_requests=write&workflows=write&actions=read)
- [Referee](https://github.com/settings/apps/new?name=ugolouche-nomic-referee&url=https%3A%2F%2Fgithub.com%2FUgoLouche%2Fgit-nomic-test&public=false&webhook_active=false&request_oauth_on_install=false&contents=write&pull_requests=write&workflows=write&actions=read)

Verify each form before submission:

| Setting | Value |
| --- | --- |
| Installation availability | Only on this account (private App) |
| Webhook | Inactive |
| Contents | Read and write |
| Pull requests | Read and write |
| Workflows | Read and write (API permission `workflows: write`) |
| Actions | Read-only, for inspecting proof runs |
| Metadata | Read-only (implicit) |
| Everything else, including Administration and Secrets | No access |

All players need workflow-write permission to propose workflow-file amendments;
this does not give them a bypass on `main`. Separate Apps are necessary: multiple
tokens from one App do not create separate reviewers.

For **each** App:
1. Create the App (if the name is taken, use a unique suffix).
2. Generate/download a private key. Keep it on the host in a private credential
   location **outside the repository, Obsidian, and shared game runtime**.
3. Select **Install App → UgoLouche → Only select repositories → git-nomic-test**.
4. Record the App slug, numeric App ID, Client ID, and installation ID (visible
   in the installation configuration URL). These IDs are not secrets.

Do not paste PEMs or tokens into chat. Do not install any of these Apps on
`rustgame` or choose “All repositories.” The referee runtime's token Action also
requests only this one repository and the three write permissions above. The
v6 pytest gate also requests Actions read to inspect run/job results; that
grant was already part of the dedicated App setup. The separate reset workflow
requests only Contents write. Neither change needs broader installation grants.

## 3. Restrict main updates to the referee

Repository **Settings → Rules → Rulesets → New branch ruleset**:

- Name: `referee-only-main`; enforcement: **Active**.
- Target branch: `main` (exact match).
- Bypass list: **only the referee App**, mode **Always allow**. This intentionally
  permits the referee's future state commits as well as PR merges.
- Enable **Restrict creations**, **Restrict updates**, **Restrict deletions**, and
  **Block force pushes**. Do not allow fork fetch-and-merge exceptions.
- Do not add player Apps, repository roles, GitHub Actions, or humans to bypass.
- Do not impose native approval counts or mandatory passing tests: the installed
  code, not a fixed GitHub review count/test gate, decides acceptance.
- Keep merge commits enabled in repository PR settings.

The owner can still edit/remove rules; that is the explicit out-of-game trust
assumption. Live probes must verify ordinary-player failures, not merely inspect
this settings page. If the referee App is unavailable in the bypass selector,
stop and report it rather than allowing everyone to bypass.

## 4. Protect the referee key, then enable only after agent preflight

Repository **Settings → Environments → New environment → `referee-main`**:

- Deployment branches/tags: **Selected branches and tags**.
- Add exactly **Branch: `main`**, not a tag rule, wildcard, or “Protected branches
  only.” No PR merge refs.
- No required reviewer or wait timer (normal adoption is autonomous).
- Initially leave the environment without a real key. The live preflight will
  attempt a harmless branch job using this environment and must observe rejection.

Repository **Settings → Secrets and variables → Actions → Variables**:

- `REFEREE_CLIENT_ID`: referee's Client ID.
- `PROOF_ENABLED`: `false`.

After the environment-isolation probe succeeds, add **environment secret**
`REFEREE_PRIVATE_KEY` to `referee-main` using the referee PEM. Never create it as
a repository/organization-wide secret. Do not add any player keys to GitHub Actions.

## Handoff

Send the repository URL and the four Apps' non-secret identifiers. Say where the
host keys are stored without sharing their contents. Agent-controlled access to
four separately scoped installation identities still needs to be established
through the host credential mechanism; the current single-App Gondolin token
cannot substitute for that. Keep private keys host-side; prefer short-lived
repo-scoped credentials for test operations. No general owner PAT is requested.

The agent can then finish source bootstrap, resolve each App bot's **user ID**,
write those three IDs into `game.json`, validate restrictions, and run the proof.
App ID, installation ID, and bot user ID are different numbers. Enabling
`PROOF_ENABLED` comes after configuration/isolation verification, not before.

## Primary documentation

- [App registration using URL parameters](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-using-url-parameters)
- [Installing your own App](https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app)
- [Installation authentication](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation)
- [Rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [Environment branch restrictions and secrets](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
