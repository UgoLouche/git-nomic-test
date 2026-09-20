"""Mutable first-slice referee. Only execute the installed default-branch copy."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

VERSION = "v2"


def validate_rules(rules):
    players = rules["players"]
    if (len(players) != 3 or any(type(p) is not int or p <= 0 for p in players)
            or len(set(players)) != 3):
        raise ValueError("Configure exactly three distinct positive GitHub user IDs")
    if rules["base"] != "main":
        raise ValueError("This proof's workflow and environment are scoped to main")
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
    return ("approved" if all(v == "APPROVED" for v in votes.values())
            else "waiting-for-unanimous-current-reviews"), votes


class GitHub:
    """Use gh's existing authentication and pagination rather than another SDK."""
    def __init__(self, repository):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Expected owner/repository")
        self.prefix = f"repos/{repository}"

    def api(self, suffix, *, method="GET", body=None, paginate=False):
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
        return [item for page in data for item in page] if paginate else data

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
        # Re-read mutable inputs. The merge API then atomically checks the head SHA.
        current = api.pull(number)
        if current["head"]["sha"] != pr["head"]["sha"]:
            return "head-changed"
        if decision(current, api.reviews(number), rules)[0] != "approved":
            return "votes-or-pr-changed"
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
    parser.add_argument("--apply", action="store_true", help="Actually merge; default is read-only")
    args = parser.parse_args()
    if not args.repo:
        parser.error("--repo or GITHUB_REPOSITORY is required")
    rules = validate_rules(json.loads(Path(args.rules).read_text()))
    result = reconcile(GitHub(args.repo), rules, args.installed_sha, apply=args.apply)
    print(json.dumps({"result": result}))


if __name__ == "__main__":
    main()
