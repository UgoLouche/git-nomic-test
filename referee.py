"""Mutable Git-nomic referee. Only execute the installed default-branch copy."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

VERSION = "v6"  # Variable rosters, amendable pytest gate and owner reset support.


def validate_rules(rules):
    players = rules["players"]
    if (not isinstance(players, list) or len(players) < 2
            or any(type(p) is not int or p <= 0 for p in players)
            or len(set(players)) != len(players)):
        raise ValueError("Configure at least two distinct positive GitHub user IDs")
    if type(rules.get("require_pytest", True)) is not bool:
        raise ValueError("require_pytest must be a boolean")
    if rules["base"] != "main":
        raise ValueError("This game's workflows and environment are scoped to main")
    return rules


def decision(pr, reviews, rules):
    """Return a reason plus the current vote snapshot, without executing PR code."""
    author = pr["user"]["id"]
    if pr["state"] != "open" or pr.get("merged") or pr.get("draft"):
        return "inactive", {}
    if pr["base"]["ref"] != rules["base"]:
        return "wrong-base", {}
    if author not in rules["players"]:
        return "ineligible-author", {}
    if pr.get("mergeable") is not True:
        return "conflict-or-pending-mergeability", {}
    voters = set(rules["players"]) - {author}
    latest = {}
    for review in sorted(reviews, key=lambda r: (r.get("submitted_at") or "", r["id"])):
        user = (review.get("user") or {}).get("id")
        # Comments/pending drafts are not votes. Dismissal revokes a vote.
        if user in voters and review["state"] in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest[user] = review
    votes = {user: (latest[user]["state"] if user in latest
                   and latest[user].get("commit_id") == pr["head"]["sha"]
                   else "ABSTAIN") for user in sorted(voters)}
    return ("approved" if sum(v == "APPROVED" for v in votes.values()) > len(votes) / 2
            else "waiting-for-majority-current-reviews"), votes


class GitHub:
    """Use gh's existing authentication and pagination rather than another SDK."""
    def __init__(self, repository):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Expected owner/repository")
        self.prefix = f"repos/{repository}"

    def api(self, suffix, *, method="GET", body=None, paginate=False, collection=None):
        command = ["gh", "api", "--hostname", "github.com", "--method", method,
                   f"{self.prefix}/{suffix}", "-H", "Accept: application/vnd.github+json",
                   "-H", "X-GitHub-Api-Version: 2022-11-28"]
        if paginate:
            command += ["--paginate", "--slurp"]
        if body is not None:
            command += ["--input", "-"]
        result = subprocess.run(command, input=json.dumps(body) if body is not None else None,
                                capture_output=True, text=True, timeout=60)
        if result.returncode:
            # Do not relay arbitrary response bodies or credential-bearing diagnostics.
            raise RuntimeError(f"GitHub {method} {suffix} failed (gh exit {result.returncode})")
        data = json.loads(result.stdout)
        if paginate:
            return [item for page in data for item in (page[collection] if collection else page)]
        return data

    def base_sha(self, branch):
        return self.api(f"git/ref/heads/{branch}")["object"]["sha"]

    def pulls(self, branch):
        return self.api(f"pulls?state=open&base={branch}&sort=created&direction=asc&per_page=100",
                        paginate=True)

    def pull(self, number):
        # GitHub computes mergeability asynchronously. Bound the wait; unknown
        # after three reads stays ineligible until a later event/manual retry.
        for attempt in range(3):
            pr = self.api(f"pulls/{number}")
            if pr.get("mergeable") is not None or pr["state"] != "open":
                return pr
            if attempt < 2:
                time.sleep(2)
        return pr

    def reviews(self, number):
        return self.api(f"pulls/{number}/reviews?per_page=100", paginate=True)

    def merge(self, number, sha):
        return self.api(f"pulls/{number}/merge", method="PUT",
                        body={"sha": sha, "merge_method": "merge"})

    def pytest_status(self, number, sha):
        """Require the latest matching PR run/attempt and its pytest step to pass.

        This checks GitHub's report, not test quality. The PR's tests and workflow
        are intentionally amendable; no installed-file equality rule is imposed.
        """
        if type(number) is not int or number < 1 or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Expected PR number and full head SHA")
        runs = self.api("actions/workflows/proposal-tests.yml/runs"
                        f"?event=pull_request&head_sha={sha}&per_page=100",
                        paginate=True, collection="workflow_runs")
        matching = [r for r in runs
                    if r.get("head_sha") == sha and r.get("event") == "pull_request"
                    and r.get("path", "").split("@", 1)[0] == ".github/workflows/proposal-tests.yml"
                    and r.get("display_title") == f"Pytest PR #{number} @ {sha}"]
        if not matching:
            return "pending"
        run = max(matching, key=lambda r: (r.get("run_started_at") or r.get("created_at") or "",
                                            r["run_number"], r["run_attempt"]))
        if run["status"] != "completed":
            return "pending"
        if run["conclusion"] != "success":
            return "failed"
        jobs = self.api(f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs?per_page=100",
                        paginate=True, collection="jobs")
        pytest_jobs = [j for j in jobs if j.get("name") == "pytest"]
        if len(pytest_jobs) != 1:
            return "failed"
        job = pytest_jobs[0]
        steps = [s for s in job.get("steps", []) if s.get("name") == "Run pytest"]
        passed = (job.get("status") == "completed" and job.get("conclusion") == "success"
                  and len(steps) == 1 and steps[0].get("status") == "completed"
                  and steps[0].get("conclusion") == "success")
        return "passed" if passed else "failed"

    def timeline(self, number):
        return self.api(f"issues/{number}/timeline?per_page=100", paginate=True)

    def close(self, number):
        return self.api(f"pulls/{number}", method="PATCH", body={"state": "closed"})

    def save_state(self, state, installed_sha, branch, *, message=None):
        # Build on exactly the installed commit, then advance main without force.
        # A concurrent unrelated main change makes this non-fast-forward, unlike
        # a Contents PUT guarded only by a file SHA. Failed writes are not retried.
        parent = self.api(f"git/commits/{installed_sha}")
        blob = self.api("git/blobs", method="POST",
                        body={"content": json.dumps(state, indent=2) + "\n", "encoding": "utf-8"})
        tree = self.api("git/trees", method="POST", body={
            "base_tree": parent["tree"]["sha"],
            "tree": [{"path": "state.json", "mode": "100644", "type": "blob", "sha": blob["sha"]}]})
        commit = self.api("git/commits", method="POST", body={
            "message": message or f"Referee: turn {state['turn']} {state['phase']}",
            "tree": tree["sha"], "parents": [installed_sha]})
        self.api(f"git/refs/heads/{branch}", method="PATCH",
                 body={"sha": commit["sha"], "force": False})
        return commit["sha"]


def reconcile(api, rules, installed_sha, *, apply=False, emit=print):
    """At most one adoption: a new invocation must load the newly installed rules."""
    validate_rules(rules)
    emit(json.dumps({"referee": VERSION, "installed_sha": installed_sha, "apply": apply}))
    if api.base_sha(rules["base"]) != installed_sha:
        emit(json.dumps({"result": "stale-installed-rules"}))
        return "stale"
    for item in api.pulls(rules["base"]):
        number = item["number"]
        pr = api.pull(number)
        reason, votes = decision(pr, api.reviews(number), rules)
        emit(json.dumps({"pr": number, "head": pr["head"]["sha"], "result": reason, "votes": votes}))
        if reason != "approved" or not apply:
            continue
        if rules.get("require_pytest", True) and api.pytest_status(number, pr["head"]["sha"]) != "passed":
            continue
        # Re-read mutable inputs. The merge API then atomically checks the head SHA.
        current = api.pull(number)
        if current["head"]["sha"] != pr["head"]["sha"]:
            return "head-changed"
        if decision(current, api.reviews(number), rules)[0] != "approved":
            return "votes-or-pr-changed"
        if rules.get("require_pytest", True) and api.pytest_status(number, current["head"]["sha"]) != "passed":
            return "tests-changed"
        if api.base_sha(rules["base"]) != installed_sha:
            return "stale"
        result = api.merge(number, current["head"]["sha"])
        if not result.get("merged"):
            raise RuntimeError("GitHub did not merge the approved proposal")
        emit(json.dumps({"result": "merged", "pr": number, "commit": result["sha"]}))
        return "merged"
    return "idle"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--rules", default="game.json")
    parser.add_argument("--installed-sha", required=True)
    parser.add_argument("--apply", action="store_true", help="Write state/close/merge; default is read-only")
    parser.add_argument("--now", help="ISO-8601 clock override for local simulations")
    args = parser.parse_args()
    if not args.repo:
        parser.error("--repo or GITHUB_REPOSITORY is required")
    rules = validate_rules(json.loads(Path(args.rules).read_text()))
    if "turns" in rules:
        from game_engine import reconcile_game, timestamp
        state = json.loads(Path("state.json").read_text())
        now = timestamp(args.now) if args.now else time.time()
        print(json.dumps({"referee": VERSION, "installed_sha": args.installed_sha,
                          "apply": args.apply}))
        result = reconcile_game(GitHub(args.repo), rules, state, args.installed_sha,
                                now=now, apply=args.apply)
    else:
        # Original proof mode remains useful for the executable adoption fixture.
        result = reconcile(GitHub(args.repo), rules, args.installed_sha, apply=args.apply)
    print(json.dumps({"result": result}))


if __name__ == "__main__":
    main()
