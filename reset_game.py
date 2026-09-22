"""Explicit out-of-game owner reset. Keeps rules/code; replaces only game state.

No arguments: preview fresh state locally, without API calls or file writes.
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


def reset(api, rules, installed_sha):
    """One CAS-style state commit; no branch reset, blind retry or PR mutations."""
    state = fresh_state(rules)
    if not re.fullmatch(r"[0-9a-f]{40}", installed_sha):
        raise ValueError("Expected full installed main SHA")
    if api.base_sha(rules["base"]) != installed_sha:
        raise ValueError("Main changed; reload the installed rules before resetting")
    stored = api.api(f"contents/game.json?ref={installed_sha}")
    if json.loads(base64.b64decode(stored["content"])) != rules:
        raise ValueError("Local rules differ from installed game.json; reload before resetting")
    return api.save_state(state, installed_sha, rules["base"],
                          message="Owner reset: clear ledger and start a new game")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", default="game.json")
    parser.add_argument("--repo", help="Owner/repository to reset")
    parser.add_argument("--installed-sha", help="Exact main commit whose rules are loaded")
    parser.add_argument("--apply", action="store_true", help="Actually commit the reset")
    parser.add_argument("--confirm-reset", help="Repeat owner/repository to confirm the reset")
    args = parser.parse_args()
    rules = json.loads(Path(args.rules).read_text())
    state = fresh_state(rules)
    if args.apply:
        if not args.repo or not args.installed_sha or args.confirm_reset != args.repo:
            parser.error("--apply requires --repo, --installed-sha and matching --confirm-reset")
        # API permissions/main restrictions enforce write access. The workflow
        # additionally permits only the personal repository owner to invoke it.
        commit = reset(GitHub(args.repo), rules, args.installed_sha)
        print(json.dumps({"result": "reset", "commit": commit, "state": state}))
    else:
        print(json.dumps({"result": "preview", "state": state}, indent=2))


if __name__ == "__main__":
    main()
