"""Real local Git + fresh Python processes; GitHub itself remains simulated."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

# This executable replaces gh ONLY in the disposable test process. No network
# calls, credentials, Actions runners, or actual GitHub merge behavior are tested.
FAKE_GH = '''import json, os, subprocess, sys
from pathlib import Path
state_file = Path(os.environ["FAKE_GITHUB_STATE"])
s = json.loads(state_file.read_text())
endpoint = next(arg for arg in sys.argv if arg.startswith("repos/"))
if "/git/ref/" in endpoint:
    result = {"object": {"sha": s["base"]}}
elif "?state=open" in endpoint:
    result = [[{"number": 1}]] if not s["merged"] else [[]]
elif "/reviews?" in endpoint:
    result = [s["reviews"]]
elif endpoint.endswith("/merge"):
    body = json.load(sys.stdin)
    assert body["sha"] == s["head"] and not s["merged"]
    subprocess.run(["git", "merge", "--ff-only", s["head"]], check=True, capture_output=True)
    s["base"] = s["head"]
    s["merged"] = True
    state_file.write_text(json.dumps(s))
    result = {"merged": True, "sha": s["base"]}
else:
    result = {"number": 1, "user": {"id": 11}, "state": "open", "draft": False,
              "base": {"ref": "main"}, "head": {"sha": s["head"]}, "mergeable": True}
print(json.dumps(result))
'''


class LocalAdoptionTests(unittest.TestCase):
    def test_installed_v1_adopts_v2_and_next_process_executes_v2(self):
        with tempfile.TemporaryDirectory(prefix="git-nomic-adoption-") as directory:
            root = Path(directory)
            repo, bin_dir = root / "repo", root / "bin"
            repo.mkdir()
            bin_dir.mkdir()
            fake_gh = bin_dir / "gh"
            fake_gh.write_text(f"#!{sys.executable}\n" + FAKE_GH)
            fake_gh.chmod(0o700)
            # Strip unrelated credentials/config; the test's gh is entirely fake.
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("GH_", "GITHUB_", "GIT_"))}
            env.update(PATH=f"{bin_dir}:{os.environ['PATH']}",
                       GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                       FAKE_GITHUB_STATE=str(root / "state.json"))

            def git(*args):
                return subprocess.run(["git", *args], cwd=repo, env=env, check=True,
                                      text=True, capture_output=True).stdout.strip()

            git("init", "-b", "main")
            git("config", "user.name", "Disposable local test")
            git("config", "user.email", "test@example.invalid")
            shutil.copyfile(ROOT / "referee.py", repo / "referee.py")
            (repo / "game.json").write_text(json.dumps({"base": "main", "players": [11, 22, 33]}))
            git("add", ".")
            git("commit", "-m", "Installed v1")
            base = git("rev-parse", "HEAD")
            git("checkout", "-b", "proposal")
            code = (repo / "referee.py").read_text()
            self.assertIn('VERSION = "v1"', code)
            (repo / "referee.py").write_text(code.replace('VERSION = "v1"', 'VERSION = "v2"'))
            git("commit", "-am", "Propose v2")
            head = git("rev-parse", "HEAD")
            git("checkout", "main")
            state = {"base": base, "head": head, "merged": False, "reviews": []}
            state_path = root / "state.json"
            state_path.write_text(json.dumps(state))

            def run_referee():
                result = subprocess.run([sys.executable, "referee.py", "--repo", "local/proof",
                                         "--installed-sha", git("rev-parse", "HEAD"), "--apply"],
                                        cwd=repo, env=env, check=True, text=True, capture_output=True)
                return [json.loads(line) for line in result.stdout.splitlines()]

            self.assertEqual(run_referee()[-1]["result"], "idle")
            self.assertEqual(git("rev-parse", "HEAD"), base)
            state["reviews"] = [{"id": user, "user": {"id": user}, "state": "APPROVED",
                                 "commit_id": head, "submitted_at": "2026-01-01T00:00:00Z"}
                                for user in (22, 33)]
            state_path.write_text(json.dumps(state))
            adoption = run_referee()
            self.assertEqual(adoption[0]["referee"], "v1")
            self.assertEqual(adoption[-1]["result"], "merged")
            self.assertEqual(git("rev-parse", "HEAD"), head)
            next_run = run_referee()
            self.assertEqual(next_run[0]["referee"], "v2")
            self.assertEqual(next_run[0]["installed_sha"], head)
            self.assertEqual(next_run[-1]["result"], "idle")


if __name__ == "__main__":
    unittest.main()
