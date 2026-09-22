"""Variable rosters, mutable CI gate and explicit out-of-game resets."""
import base64
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from referee import GitHub, validate_rules
from reset_game import fresh_state, reset
from test_game import World, RULES, WEEK

ROOT = Path(__file__).resolve().parents[1]
SHA = "a" * 40
RUN = {"id": 100, "run_number": 1, "run_attempt": 1, "head_sha": SHA,
       "event": "pull_request", "path": ".github/workflows/proposal-tests.yml@main",
       "display_title": f"Pytest PR #7 @ {SHA}", "status": "completed", "conclusion": "success"}
JOB = {"name": "pytest", "status": "completed", "conclusion": "success",
       "steps": [{"name": "Run pytest", "status": "completed", "conclusion": "success"}]}


class RosterTests(unittest.TestCase):
    def test_two_or_more_players_and_validation(self):
        for count in (2, 3, 4, 5, 10, 100):
            rules = {**RULES, "players": list(range(1, count + 1))}
            self.assertEqual(validate_rules(rules), rules)
        for players in ([], [1], [1, 1], [1, True], [1, -1], [1, "2"], "12", None):
            with self.subTest(players=players), self.assertRaises(ValueError):
                validate_rules({**RULES, "players": players})
        for value in (None, 0, 1, "true"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_rules({**RULES, "require_pytest": value})

    def test_majority_counts_entire_registered_non_author_roster(self):
        for count in (2, 3, 4, 5, 6, 10, 100):
            for choice in ("APPROVED", "CHANGES_REQUESTED"):
                with self.subTest(count=count, choice=choice):
                    w = World()
                    w.rules["players"] = list(range(1, count + 1))
                    w.state = fresh_state(w.rules)
                    w.tick()
                    n = w.propose()
                    w.tick()
                    voters = w.state["proposal"]["voters"]
                    self.assertEqual(voters, w.rules["players"][1:])
                    needed = len(voters) // 2 + 1
                    for voter in voters[:needed - 1]:
                        w.vote(n, voter, choice)
                    self.assertEqual(w.tick(), "waiting-for-votes")
                    w.vote(n, voters[needed - 1], choice)
                    self.assertEqual(w.tick(), "merged" if choice == "APPROVED" else "rejected")
                    if choice == "APPROVED":
                        self.assertEqual(w.tick(), "accepted")
                    self.assertEqual(w.state["player"], 2)
                    self.assertEqual(w.state["turn"], 2)

    def test_rotation_wraps_for_arbitrary_rosters(self):
        for count in (2, 4, 9):
            w = World()
            w.rules["players"] = list(range(1, count + 1))
            w.state = fresh_state(w.rules)
            w.tick()
            for index in range(count):
                self.assertEqual(w.state["player"], index + 1)
                w.due()
                self.assertEqual(w.tick(), "passed")
            self.assertEqual(w.state["player"], 1)
            self.assertEqual(w.state["turn"], count + 1)


class GateEngineTests(unittest.TestCase):
    def test_missing_running_or_failed_tests_prevent_voting(self):
        for status in ("pending", "failed"):
            with self.subTest(status=status):
                w = World()
                w.tick()
                n = w.propose()
                w.test_results[n, f"head-{n}"] = status
                before = copy.deepcopy(w.state)
                self.assertEqual(w.tick(), "waiting-for-proposal")
                self.assertEqual(w.state, before)
                self.assertFalse(w.merges or w.closed)
                w.due()
                self.assertEqual(w.tick(), "passed")

    def test_author_can_fix_failing_tests_before_selection_but_not_after(self):
        w = World()
        w.tick()
        n = w.propose()
        w.test_results[n, "head-1"] = "failed"
        self.assertEqual(w.tick(), "waiting-for-proposal")
        w.prs[n]["head"]["sha"] = "fixed"
        w.test_results[n, "fixed"] = "passed"
        self.assertEqual(w.tick(), "voting-opened")
        self.assertEqual(w.state["proposal"]["head"], "fixed")
        w.prs[n]["head"]["sha"] = "changed-after-freeze"
        self.assertEqual(w.tick(), "revised")

    def test_first_valid_candidate_may_follow_a_failing_candidate(self):
        w = World()
        w.tick()
        n = w.propose()
        w.test_results[n, "head-1"] = "failed"
        second = w.propose()
        self.assertEqual(w.tick(), "voting-opened")
        self.assertEqual(w.state["proposal"]["number"], second)

    def test_rerun_not_passing_blocks_early_merge_and_fails_at_cutoff(self):
        for status in ("pending", "failed"):
            with self.subTest(status=status):
                w = World()
                n = w.voting()
                w.test_results[n, "head-1"] = status
                self.assertEqual(w.tick(), "waiting-for-tests")
                self.assertFalse(w.merges or w.closed)
                w.due()
                self.assertEqual(w.tick(), "pytest-" + status)
                self.assertFalse(w.merges)
                self.assertEqual(w.closed, [n])
                self.assertEqual(w.state["turn"], 2)

    def test_passing_rerun_allows_early_merge(self):
        w = World()
        n = w.voting()
        w.test_results[n, "head-1"] = "pending"
        self.assertEqual(w.tick(), "waiting-for-tests")
        w.test_results[n, "head-1"] = "passed"
        self.assertEqual(w.tick(), "merged")
        self.assertGreaterEqual(w.test_reads.count((n, "head-1")), 4)

    def test_check_changes_on_final_read_fail_closed(self):
        w = World()
        w.voting()
        with patch.object(w, "pytest_status", side_effect=["passed", "pending"]):
            self.assertEqual(w.tick(), "tests-changed")
        self.assertFalse(w.merges or w.closed)

    def test_rejecting_majority_does_not_wait_for_test_rerun(self):
        w = World()
        n = w.voting()
        w.test_results[n, "head-1"] = "pending"
        w.vote(n, 22, "CHANGES_REQUESTED")
        w.vote(n, 33, "CHANGES_REQUESTED")
        self.assertEqual(w.tick(), "rejected")

    def test_test_requirement_is_an_amendable_rule(self):
        w = World()
        w.rules["require_pytest"] = False
        n = w.voting()
        w.test_results[n, "head-1"] = "failed"
        self.assertEqual(w.tick(), "merged")
        self.assertEqual(w.test_reads, [])


class GateAdapterTests(unittest.TestCase):
    def status(self, runs, jobs=None):
        api = GitHub("owner/repo")
        with patch.object(api, "api", side_effect=[runs, jobs or [copy.deepcopy(JOB)]]) as call:
            result = api.pytest_status(7, SHA)
        return result, call.call_args_list

    def test_exact_head_workflow_and_pr_run_with_passing_pytest_step(self):
        result, calls = self.status([copy.deepcopy(RUN)])
        self.assertEqual(result, "passed")
        self.assertIn("head_sha=" + SHA, calls[0].args[0])
        self.assertEqual(calls[0].kwargs, {"paginate": True, "collection": "workflow_runs"})
        self.assertEqual(calls[1].args[0], "actions/runs/100/attempts/1/jobs?per_page=100")

    def test_stale_head_wrong_pr_event_or_workflow_cannot_satisfy_gate(self):
        for change in ({"head_sha": "b" * 40}, {"event": "push"},
                       {"display_title": f"Pytest PR #8 @ {SHA}"},
                       {"path": ".github/workflows/other.yml"}):
            with self.subTest(change=change):
                result, calls = self.status([{**RUN, **change}])
                self.assertEqual(result, "pending")
                self.assertEqual(len(calls), 1)
        self.assertEqual(self.status([])[0], "pending")

    def test_latest_run_and_attempt_win_over_old_success(self):
        for status, conclusion, expected in (("queued", None, "pending"),
                                             ("completed", "failure", "failed"),
                                             ("completed", "cancelled", "failed")):
            with self.subTest(status=status, conclusion=conclusion):
                newer = {**RUN, "id": 101, "run_number": 2, "status": status,
                         "conclusion": conclusion}
                self.assertEqual(self.status([newer, RUN])[0], expected)
                rerun = {**RUN, "run_attempt": 2, "status": status, "conclusion": conclusion}
                self.assertEqual(self.status([RUN, rerun])[0], expected)
        rerun = {**RUN, "run_attempt": 2}
        self.assertIn("/attempts/2/", self.status([rerun])[1][1].args[0])

    def test_new_attempt_of_older_run_takes_precedence_over_later_run_number(self):
        previous_success = {**RUN, "id": 101, "run_number": 2,
                            "run_started_at": "2026-01-01T00:00:00Z"}
        rerun = {**RUN, "run_attempt": 2, "run_started_at": "2026-01-01T01:00:00Z",
                 "status": "in_progress", "conclusion": None}
        self.assertEqual(self.status([previous_success, rerun])[0], "pending")

    def test_missing_skipped_neutral_or_failed_pytest_is_not_success(self):
        for change in ({"name": "other"}, {"status": "in_progress"},
                       {"conclusion": "skipped"}, {"conclusion": "neutral"},
                       {"conclusion": "failure"}, {"steps": []},
                       {"steps": [{"name": "Run pytest", "status": "completed",
                                   "conclusion": "skipped"}]}):
            with self.subTest(change=change):
                self.assertEqual(self.status([RUN], [{**JOB, **change}])[0], "failed")
        self.assertEqual(self.status([RUN], [JOB, JOB])[0], "failed")

    def test_api_failure_does_not_become_a_passing_check(self):
        api = GitHub("owner/repo")
        with patch.object(api, "api", side_effect=RuntimeError("API unavailable")):
            with self.assertRaises(RuntimeError):
                api.pytest_status(7, SHA)

    def test_dict_collection_pagination_flattens_all_pages(self):
        api = GitHub("owner/repo")
        with patch("referee.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0,
                '[{"workflow_runs":[{"id":1}]},{"workflow_runs":[{"id":2}]}]', '')
            self.assertEqual(api.api("actions/runs", paginate=True, collection="workflow_runs"),
                             [{"id": 1}, {"id": 2}])


class ResetTests(unittest.TestCase):
    def api(self, rules=RULES):
        api = GitHub("owner/repo")
        api.base_sha = lambda _: SHA
        api.api = lambda _: {"content": base64.b64encode(json.dumps(rules).encode()).decode()}
        return api

    def test_reset_clears_state_preserving_current_rules_and_order(self):
        rules = copy.deepcopy(RULES)
        rules.update(players=[44, 11, 33, 22, 55], require_pytest=False, custom="retain me")
        rules["turns"].update(points_per_accept=7, points_to_win=100)
        before = copy.deepcopy(rules)
        s = fresh_state(rules)
        self.assertEqual(rules, before)
        self.assertEqual(s["scores"], {str(p): 0 for p in rules["players"]})
        self.assertEqual((s["player"], s["turn"], s["phase"]), (44, 1, "new"))
        self.assertEqual(s["history"], [])
        self.assertEqual(s["winners"], [])
        self.assertIsNone(s["proposal"])
        self.assertIsNone(s["deadline"])
        self.assertIsNone(s["started_at"])

    def test_reset_writes_one_state_commit_not_a_git_history_reset(self):
        api = self.api()
        with patch.object(api, "save_state", return_value="new-commit") as save:
            self.assertEqual(reset(api, RULES, SHA), "new-commit")
        save.assert_called_once_with(fresh_state(RULES), SHA, "main",
                                     message="Owner reset: clear ledger and start a new game")

    def test_reset_refuses_stale_main_mismatched_rules_and_bad_sha(self):
        for case in ("stale", "rules", "sha"):
            with self.subTest(case=case):
                api = self.api({**RULES, "players": [99, 88]} if case == "rules" else RULES)
                if case == "stale":
                    api.base_sha = lambda _: "b" * 40
                with patch.object(api, "save_state") as save, self.assertRaises(ValueError):
                    reset(api, RULES, "invalid" if case == "sha" else SHA)
                save.assert_not_called()

    def test_ambiguous_reset_write_is_not_retried(self):
        api = self.api()
        with patch.object(api, "save_state", side_effect=RuntimeError("lost response")) as save:
            with self.assertRaises(RuntimeError):
                reset(api, RULES, SHA)
            self.assertEqual(save.call_count, 1)

    def test_default_cli_is_offline_preview_and_apply_requires_confirmation(self):
        state_before = (ROOT / "state.json").read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / "reset_game.py")], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)["result"], "preview")
        self.assertEqual((ROOT / "state.json").read_bytes(), state_before)
        for args in (["--apply"], ["--apply", "--repo", "owner/repo", "--installed-sha", SHA],
                     ["--apply", "--repo", "owner/repo", "--installed-sha", SHA,
                      "--confirm-reset", "wrong/repo"]):
            result = subprocess.run([sys.executable, str(ROOT / "reset_game.py"), *args],
                                    cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("matching --confirm-reset", result.stderr)
        self.assertEqual((ROOT / "state.json").read_bytes(), state_before)

    def test_fresh_game_starts_with_full_window_and_cannot_adopt_old_pr(self):
        w = World()
        n = w.voting()
        old = copy.deepcopy(w.state)
        w.clock += WEEK
        w.state = fresh_state(w.rules)
        self.assertEqual(w.tick(), "started")
        self.assertEqual(w.tick(), "waiting-for-proposal")
        self.assertEqual(w.state["turn"], 1)
        self.assertEqual(w.prs[n]["state"], "open")  # reset does not mutate PRs
        self.assertNotEqual(w.state["started_at"], old["started_at"])


class WorkflowBaselineTests(unittest.TestCase):
    """Source assertions for these baseline workflows, not immutable game gates."""
    def test_pytest_runner_is_unprivileged_and_proposed_revision_is_bound(self):
        text = (ROOT / ".github/workflows/proposal-tests.yml").read_text()
        self.assertIn("permissions: {}", text)
        self.assertIn("pull_request:", text)
        self.assertNotIn("pull_request_target", text)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("environment:", text)
        self.assertNotIn("actions/cache", text)
        self.assertIn('test "$(git -C proposal rev-parse FETCH_HEAD)" = "$PR_HEAD_SHA"', text)
        self.assertIn("run: python -m pytest -q", text)
        self.assertIn((ROOT / "requirements-test.txt").read_text().strip(), text)
        referee = (ROOT / ".github/workflows/referee.yml").read_text()
        self.assertIn("workflows: [Vote signal, Proposal tests]", referee)
        self.assertIn("permission-actions: read", referee)

    def test_reset_requires_owner_dispatch_and_owner_rerun_on_main(self):
        text = (ROOT / ".github/workflows/reset-game.yml").read_text()
        for required in ("github.actor == github.repository_owner",
                         "github.triggering_actor == github.repository_owner",
                         "github.ref == 'refs/heads/main'", "inputs.confirm == 'RESET'",
                         "environment: referee-main", "group: git-nomic-referee",
                         "persist-credentials: false", "--confirm-reset"):
            self.assertIn(required, text)
        self.assertNotIn("PROOF_ENABLED", text)  # reset is independently explicit
        self.assertNotIn("permission-pull-requests: write", text)


class PytestExecutionTests(unittest.TestCase):
    def test_real_pytest_accepts_valid_modified_tests_and_rejects_failures_or_none(self):
        # Exercise the actual runner, not fabricated GitHub statuses. Test content
        # is deliberately different in each candidate; no baseline equality rule.
        cases = [("def test_example():\n    assert 2 + 2 == 4\n", 0),
                 ("def test_rewritten():\n    assert True\n", 0),
                 ("def test_failure():\n    assert False\n", 1),
                 ("# candidate removed all tests\n", 5),
                 ("def test_broken(:\n", 2)]
        with tempfile.TemporaryDirectory(prefix="nomic-pytest-") as directory:
            path = Path(directory) / "test_candidate.py"
            env = {k: v for k, v in os.environ.items()
                   if not k.startswith(("GH_", "GITHUB_", "PYTEST_"))}
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            for code, expected in cases:
                with self.subTest(expected=expected, code=code):
                    path.write_text(code)
                    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "--assert=plain",
                                             "-p", "no:cacheprovider"], cwd=directory, env=env,
                                            text=True, capture_output=True, timeout=30)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
