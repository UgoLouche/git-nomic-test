"""Real Git merges/state commits and fresh referee processes; no live APIs."""
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_game import RULES, STATE, START, WEEK
from game_engine import utc

ROOT = Path(__file__).resolve().parents[1]
DRIVER = '''import json, os, subprocess
from pathlib import Path
from referee import VERSION
from game_engine import reconcile_game, timestamp

def git(*args):
    return subprocess.run(["git", *args], check=True, text=True, capture_output=True).stdout.strip()

class API:
    def __init__(self):
        self.path = Path(os.environ["SIM_API"])
        self.data = json.loads(self.path.read_text())
    def base_sha(self, branch):
        return git("rev-parse", "HEAD")
    def pulls(self, branch):
        return [self.data["pr"]] if self.data["pr"]["state"] == "open" else []
    def pull(self, number):
        return self.data["pr"]
    def reviews(self, number):
        return self.data["reviews"]
    def timeline(self, number):
        return []
    def save_state(self, state, installed, branch):
        assert self.base_sha(branch) == installed
        Path("state.json").write_text(json.dumps(state, indent=2) + "\\n")
        git("add", "state.json")
        git("commit", "-m", "Referee state")
    def close(self, number):
        self.data["pr"]["state"] = "closed"
        self.path.write_text(json.dumps(self.data))
    def merge(self, number, sha):
        assert sha == self.data["pr"]["head"]["sha"]
        git("merge", "--no-ff", "-m", "Adopt proposal", sha)
        self.data["pr"].update(merged=True, state="closed", merge_commit_sha=git("rev-parse", "HEAD"))
        self.path.write_text(json.dumps(self.data))
        return {"merged": True, "sha": git("rev-parse", "HEAD")}

api = API()
print(json.dumps({"version": VERSION, "installed": git("rev-parse", "HEAD")}))
print(json.dumps({"result": reconcile_game(api, json.loads(Path("game.json").read_text()),
    json.loads(Path("state.json").read_text()), git("rev-parse", "HEAD"),
    now=timestamp(os.environ["SIM_NOW"]), apply=True)}))
'''


class PlayableAdoptionTests(unittest.TestCase):
    def test_git_merge_preserves_ledger_amendment_and_fresh_process_runs_new_scoring(self):
        with tempfile.TemporaryDirectory(prefix="nomic-playable-") as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("GH_", "GITHUB_", "GIT_"))}
            env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                       SIM_API=str(root / "api.json"), SIM_NOW=utc(START),
                       PYTHONDONTWRITEBYTECODE="1")
            def git(*args):
                return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                                      text=True, capture_output=True).stdout.strip()
            def state():
                return json.loads((repo / "state.json").read_text())
            def run():
                result = subprocess.run([sys.executable, "-B", "driver.py"], cwd=repo, env=env,
                                        check=True, text=True, capture_output=True)
                return [json.loads(s) for s in result.stdout.splitlines()]

            git("init", "-b", "main")
            git("config", "user.name", "Disposable game")
            git("config", "user.email", "test@example.invalid")
            for name in ("referee.py", "game_engine.py"):
                source = (ROOT / name).read_text()
                if name == "referee.py":
                    source = re.sub(r'^VERSION = "[^"]+"[^\n]*$', 'VERSION = "v3"',
                                    source, count=1, flags=re.M)
                (repo / name).write_text(source)
            (repo / "driver.py").write_text(DRIVER)
            (repo / "game.json").write_text(json.dumps(RULES, indent=2) + "\n")
            (repo / "state.json").write_text(json.dumps(STATE, indent=2) + "\n")
            git("add", ".")
            git("commit", "-m", "Installed playable game")
            api = {"pr": {"number": 1, "state": "closed"}, "reviews": []}
            (root / "api.json").write_text(json.dumps(api))
            self.assertEqual(run()[-1]["result"], "started")
            git("checkout", "-b", "proposal")
            # Amend code AND the score ledger before the voting state commit.
            # A real three-way merge must preserve both independent changes.
            s = state()
            s["scores"]["11"] = 3
            (repo / "state.json").write_text(json.dumps(s, indent=2) + "\n")
            source = (repo / "referee.py").read_text()
            (repo / "referee.py").write_text(source.replace('VERSION = "v3"', 'VERSION = "v4"'))
            engine = (repo / "game_engine.py").read_text()
            engine = engine.replace('record.update(award=proposal["award"],',
                                    'record.update(adopted_scoring="v4", award=proposal["award"],')
            (repo / "game_engine.py").write_text(engine)
            git("commit", "-am", "Propose scoring code and ledger amendment")
            head = git("rev-parse", "HEAD")
            git("checkout", "main")
            api["pr"] = {"number": 1, "state": "open", "merged": False, "draft": False,
                         "user": {"id": 11}, "base": {"ref": "main"}, "head": {"sha": head},
                         "created_at": utc(START), "mergeable": True}
            api["reviews"] = [{"id": u, "user": {"id": u}, "state": "APPROVED",
                               "submitted_at": utc(START), "commit_id": head} for u in (22, 33)]
            (root / "api.json").write_text(json.dumps(api))
            self.assertEqual(run()[-1]["result"], "voting-opened")
            self.assertEqual(run()[-1]["result"], "waiting-for-deadline")
            env["SIM_NOW"] = utc(START + WEEK)
            before = git("rev-parse", "HEAD")
            adoption = run()
            self.assertEqual(adoption[0]["version"], "v3")
            self.assertEqual(adoption[-1]["result"], "merged")
            merge = git("rev-parse", "HEAD")
            self.assertEqual(git("show", "-s", "--format=%P", "HEAD"), f"{before} {head}")
            self.assertEqual(state()["scores"]["11"], 3)
            settled = run()
            self.assertEqual(settled[0]["version"], "v4")
            self.assertEqual(settled[0]["installed"], merge)
            self.assertEqual(settled[-1]["result"], "accepted")
            self.assertEqual(state()["scores"]["11"], 4)
            self.assertEqual(state()["history"][0]["adopted_scoring"], "v4")
            self.assertEqual(state()["player"], 22)
            self.assertEqual(run()[-1]["result"], "waiting-for-proposal")
            self.assertEqual(state()["scores"]["11"], 4)


if __name__ == "__main__":
    unittest.main()
