"""Explicit out-of-game owner reset, optionally with a replacement roster.

No arguments: preview fresh state locally, without API calls or file writes.
--players-json: use an ordered JSON array of numeric GitHub user IDs.
--apply: requires repository confirmation and the exact installed main SHA.
Use the owner-only Reset game workflow for a convenient authenticated live reset.
"""
import argparse
import base64
import json
from pathlib import Path
import re

from game_engine import validate
from referee import GitHub, validate_rules


def fresh_state(rules):
    validate_rules(rules)
    state = {"scores": {str(p): 0 for p in rules["players"]}, "history": [],
             "turn": 1, "player": rules["players"][0], "phase": "new",
             "started_at": None, "deadline": None, "proposal": None, "winners": []}
    validate(rules, state)
    return state


def parse_player_ids(value):
    """Parse an optional ordered JSON array for argparse/workflow input."""
    if value is None or not value.strip():
        return None
    try:
        players = json.loads(value)
    except json.JSONDecodeError as error:
        raise argparse.ArgumentTypeError("players must be a JSON array of numeric user IDs") from error
    if (not isinstance(players, list) or len(players) < 2
            or any(type(player) is not int or player <= 0 for player in players)
            or len(set(players)) != len(players)):
        raise argparse.ArgumentTypeError(
            "players must contain at least two distinct positive numeric user IDs")
    return players


def rules_for_reset(rules, players=None):
    """Return validated installed rules with an optional replacement roster."""
    updated = json.loads(json.dumps(rules))
    if players is not None:
        updated["players"] = players
    return validate_rules(updated)


def reset(api, rules, installed_sha, players=None):
    """One CAS-style reset commit; no branch reset, blind retry or PR mutations."""
    updated_rules = rules_for_reset(rules, players)
    state = fresh_state(updated_rules)
    if not re.fullmatch(r"[0-9a-f]{40}", installed_sha):
        raise ValueError("Expected full installed main SHA")
    if api.base_sha(rules["base"]) != installed_sha:
        raise ValueError("Main changed; reload the installed rules before resetting")
    stored = api.api(f"contents/game.json?ref={installed_sha}")
    if json.loads(base64.b64decode(stored["content"])) != rules:
        raise ValueError("Local rules differ from installed game.json; reload before resetting")
    if players is not None:
        return api.save_rules_and_state(
            updated_rules, state, installed_sha, rules["base"],
            message="Owner reset: replace roster and start a new game")
    return api.save_state(state, installed_sha, rules["base"],
                          message="Owner reset: clear ledger and start a new game")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", default="game.json")
    parser.add_argument("--repo", help="Owner/repository to reset")
    parser.add_argument("--installed-sha", help="Exact main commit whose rules are loaded")
    parser.add_argument("--players-json", type=parse_player_ids,
                        help="Ordered JSON array of numeric user IDs; omitted keeps current players")
    parser.add_argument("--apply", action="store_true", help="Actually commit the reset")
    parser.add_argument("--confirm-reset", help="Repeat owner/repository to confirm the reset")
    args = parser.parse_args()
    rules = json.loads(Path(args.rules).read_text())
    updated_rules = rules_for_reset(rules, args.players_json)
    state = fresh_state(updated_rules)
    if args.apply:
        if not args.repo or not args.installed_sha or args.confirm_reset != args.repo:
            parser.error("--apply requires --repo, --installed-sha and matching --confirm-reset")
        # API permissions/main restrictions enforce write access. The workflow
        # additionally permits only the personal repository owner to invoke it.
        commit = reset(GitHub(args.repo), rules, args.installed_sha, args.players_json)
        print(json.dumps({"result": "reset", "commit": commit,
                          "players": updated_rules["players"], "state": state}))
    else:
        print(json.dumps({"result": "preview", "players": updated_rules["players"],
                          "state": state}, indent=2))


if __name__ == "__main__":
    main()
