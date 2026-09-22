"""Amendable turn/deadline/ledger rules. Never import a proposal's code.

Each invocation makes at most one main commit or merge, then stops. In particular,
merged proposals are settled by a fresh invocation of the adopted referee.
"""
import copy
from datetime import datetime, timezone
import json


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include a timezone")
    return parsed.timestamp()


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate(rules, state):
    turns = rules["turns"]
    for field in ("proposal_seconds", "voting_seconds", "points_to_win", "points_per_accept"):
        if type(turns[field]) is not int or turns[field] <= 0:
            raise ValueError(f"turns.{field} must be a positive integer")
    if state["phase"] not in {"new", "proposing", "voting", "finished"}:
        raise ValueError("Unknown game phase")
    if type(state["turn"]) is not int or state["turn"] < 1:
        raise ValueError("Invalid turn")
    if state["player"] not in rules["players"]:
        raise ValueError("Current player must be eligible")
    if any(type(n) is not int for n in state["scores"].values()):
        raise ValueError("Scores must be integers")
    if state["phase"] in {"proposing", "voting"}:
        timestamp(state["deadline"])
        timestamp(state["started_at"])
    if state["phase"] == "voting":
        p = state["proposal"]
        if p["author"] != state["player"] or p["author"] in p["voters"]:
            raise ValueError("Invalid frozen electorate")
        if not p["voters"] or len(set(p["voters"])) != len(p["voters"]):
            raise ValueError("Invalid frozen electorate")
    return state


def majority(votes, choice):
    return sum(v == choice for v in votes.values()) > len(votes) / 2


def tally(reviews, proposal, deadline):
    """Latest decisive current-revision vote submitted before the deadline.

    Dismissal is read from GitHub's current review state, so a currently dismissed
    review never counts, even if dismissal happened after the deadline.
    """
    latest = {}
    for r in sorted(reviews, key=lambda r: (r.get("submitted_at") or "", r["id"])):
        user = (r.get("user") or {}).get("id")
        if (user in proposal["voters"] and r.get("submitted_at")
                and timestamp(r["submitted_at"]) < timestamp(deadline)
                and r["state"] in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}):
            latest[user] = r
    votes = {u: (latest[u]["state"] if u in latest
                 and latest[u].get("commit_id") == proposal["head"] else "ABSTAIN")
             for u in proposal["voters"]}
    return majority(votes, "APPROVED"), votes


def start_turn(state, now, rules):
    state.update(phase="proposing", started_at=utc(now),
                 deadline=utc(now + rules["turns"]["proposal_seconds"]), proposal=None)


def finish(state, now, rules, outcome, pr=None):
    """Apply one outcome to the currently adopted ledger, preserving amendments."""
    proposal = state.get("proposal")
    record = {"turn": state["turn"], "player": state["player"],
              "outcome": outcome, "at": utc(now)}
    if proposal:
        record.update(pr=proposal["number"], head=proposal["head"])
    if outcome == "accepted":
        author = str(proposal["author"])
        # The installed pre-adoption rules froze the award when voting opened.
        state["scores"][author] = state["scores"].get(author, 0) + proposal["award"]
        record.update(award=proposal["award"], merge=pr["merge_commit_sha"])
    state["history"].append(record)
    winners = [p for p in rules["players"]
               if state["scores"].get(str(p), 0) >= rules["turns"]["points_to_win"]]
    if winners:
        state.update(phase="finished", winners=winners, proposal=None, deadline=None)
    else:
        state["turn"] += 1
        state["player"] = rules["players"][(rules["players"].index(state["player"]) + 1)
                                           % len(rules["players"])]
        # Delayed ticks do not silently consume future players' entire windows.
        start_turn(state, now, rules)


def force_push_ids(api, number):
    return sorted(e["id"] for e in api.timeline(number)
                  if e.get("event") == "head_ref_force_pushed")


def reconcile_game(api, rules, state, installed_sha, *, now, apply=False, emit=print):
    """Reconcile authoritative GitHub inputs with an explicit, controllable clock."""
    validate(rules, state)
    state = copy.deepcopy(state)

    def save(result):
        emit(json.dumps({"result": result, "state": state}))
        if not apply:
            return "dry-run:" + result
        if api.base_sha(rules["base"]) != installed_sha:
            return "stale"
        api.save_state(state, installed_sha, rules["base"])
        return result

    def end(outcome, pr=None):
        # Close before recording failure. If the response is lost, the next tick
        # observes the closed PR and advances once, with outcome 'closed'.
        if apply and pr and pr["state"] == "open":
            if api.base_sha(rules["base"]) != installed_sha:
                return "stale"
            api.close(pr["number"])
        finish(state, now, rules, outcome, pr)
        return save(outcome)

    if api.base_sha(rules["base"]) != installed_sha:
        return "stale"
    if state["phase"] == "finished":
        return "finished"
    if state["phase"] == "new":
        start_turn(state, now, rules)
        return save("started")
    if state["phase"] == "proposing":
        # Sort explicitly: fake inputs and API pagination must not affect choice.
        items = sorted(api.pulls(rules["base"]), key=lambda p: (p["created_at"], p["number"]))
        for item in items:
            if not (timestamp(state["started_at"]) <= timestamp(item["created_at"])
                    < timestamp(state["deadline"])):
                continue
            if item["user"]["id"] != state["player"] or item.get("draft"):
                continue
            pr = api.pull(item["number"])
            if (pr["state"] != "open" or pr.get("draft") or pr.get("merged")
                    or pr["base"]["ref"] != rules["base"]):
                continue
            if rules.get("require_pytest", True):
                tests = api.pytest_status(pr["number"], pr["head"]["sha"])
                if tests != "passed":
                    emit(json.dumps({"pr": pr["number"], "result": "pytest-" + tests}))
                    continue
            # Snapshot the force-push timeline too: returning to the original SHA
            # after a force push must not conceal a frozen-revision violation.
            pushes = force_push_ids(api, pr["number"])
            current = api.pull(pr["number"])
            if (current["head"]["sha"] != pr["head"]["sha"]
                    or current["state"] != "open" or current.get("merged")
                    or current.get("draft") or current["base"]["ref"] != rules["base"]):
                return "selection-changed"
            state.update(phase="voting", deadline=utc(now + rules["turns"]["voting_seconds"]),
                         proposal={"number": pr["number"], "head": pr["head"]["sha"],
                                   "author": state["player"], "opened_at": utc(now),
                                   "voters": [p for p in rules["players"] if p != state["player"]],
                                   "award": rules["turns"]["points_per_accept"],
                                   "force_push_ids": pushes})
            return save("voting-opened")
        if now >= timestamp(state["deadline"]):
            return end("passed")
        return "waiting-for-proposal"

    proposal = state["proposal"]
    pr = api.pull(proposal["number"])
    if pr.get("merged"):
        # This path runs only after a new checkout, including after a lost merge
        # response. Removing/replacing the pending state in an amendment can
        # deliberately change this behavior: the state is not protected law.
        if pr["head"]["sha"] != proposal["head"]:
            raise ValueError("Merged head differs from the selected revision")
        return end("accepted", pr)
    if pr["state"] != "open":
        return end("closed", pr)

    def invalid(current):
        if (current["head"]["sha"] != proposal["head"]
                or force_push_ids(api, current["number"]) != proposal["force_push_ids"]):
            return "revised"
        if current["base"]["ref"] != rules["base"] or current.get("draft"):
            return "ineligible"
        if current.get("mergeable") is False:
            return "conflicted"
        return None

    reason = invalid(pr)
    if reason:
        return end(reason, pr)
    approved, votes = tally(api.reviews(pr["number"]), proposal, state["deadline"])
    rejected = majority(votes, "CHANGES_REQUESTED")
    expired = now >= timestamp(state["deadline"])
    emit(json.dumps({"pr": pr["number"], "votes": votes, "approved": approved,
                     "rejecting_majority": rejected}))
    if not approved and not rejected and not expired:
        return "waiting-for-votes"
    if not approved:
        if apply:
            # Like acceptance, recheck before acting on a decisive vote. Closing
            # has no atomic vote/head guard; the final API race remains possible.
            current = api.pull(pr["number"])
            reason = invalid(current)
            if reason:
                return end(reason, current)
            fresh_approved, fresh_votes = tally(
                api.reviews(pr["number"]), proposal, state["deadline"])
            if (current["state"] != "open" or current.get("merged") or fresh_approved
                    or (not expired and not majority(fresh_votes, "CHANGES_REQUESTED"))):
                return "inputs-changed"
            pr = current
        return end("rejected", pr)
    if rules.get("require_pytest", True):
        tests = api.pytest_status(pr["number"], proposal["head"])
        if tests != "passed":
            return end("pytest-" + tests, pr) if expired else "waiting-for-tests"
    if pr.get("mergeable") is not True:
        return "waiting-for-mergeability"
    if not apply:
        return "dry-run:merge"
    current = api.pull(pr["number"])
    reason = invalid(current)
    if reason:
        return end(reason, current)
    if (current["state"] != "open" or current.get("merged")
            or current.get("mergeable") is not True
            or not tally(api.reviews(pr["number"]), proposal, state["deadline"])[0]):
        return "inputs-changed"
    if (rules.get("require_pytest", True)
            and api.pytest_status(pr["number"], proposal["head"]) != "passed"):
        return "tests-changed"
    if api.base_sha(rules["base"]) != installed_sha:
        return "stale"
    result = api.merge(pr["number"], proposal["head"])
    if not result.get("merged"):
        raise RuntimeError("GitHub did not merge the accepted proposal")
    emit(json.dumps({"result": "merged", "pr": pr["number"], "commit": result["sha"]}))
    # Never run old scoring/turn code against the just-adopted game.
    return "merged"
