import copy
import json
import subprocess
import unittest
from unittest.mock import patch

from referee import GitHub, decision, reconcile, validate_rules

# Historical no-turns proof fixture explicitly opts out of the later pytest gate.
RULES = {"base": "main", "players": [11, 22, 33], "require_pytest": False}
PR = {"number": 1, "state": "open", "draft": False, "merged": False,
      "user": {"id": 11}, "base": {"ref": "main"},
      "head": {"sha": "head-1"}, "mergeable": True}


def review(user, state="APPROVED", sha="head-1", sequence=1):
    return {"id": sequence, "user": {"id": user}, "state": state,
            "commit_id": sha, "submitted_at": f"2026-01-01T00:00:{sequence:02d}Z"}


class FakeGitHub:
    def __init__(self):
        self.pr = copy.deepcopy(PR)
        self.votes = [review(22), review(33)]
        self.base = "installed"
        self.merges = []
        self.pull_reads = self.vote_reads = self.base_reads = 0
        self.on_pull = self.on_reviews = self.on_base = lambda api: None

    def base_sha(self, branch):
        self.base_reads += 1
        self.on_base(self)
        return self.base

    def pulls(self, branch):
        return [{"number": 1}, {"number": 2}] if self.pr["state"] == "open" else []

    def pull(self, number):
        self.pull_reads += 1
        self.on_pull(self)
        return copy.deepcopy(self.pr)

    def reviews(self, number):
        self.vote_reads += 1
        self.on_reviews(self)
        return copy.deepcopy(self.votes)

    def merge(self, number, sha):
        assert sha == self.pr["head"]["sha"]
        self.merges.append((number, sha))
        self.base = "adopted"
        self.pr["state"] = "closed"
        return {"merged": True, "sha": "adopted"}


class VotingTests(unittest.TestCase):
    def decide(self, votes, **changes):
        pr = copy.deepcopy(PR)
        pr.update(changes)
        return decision(pr, votes, RULES)[0]

    def test_both_other_players_approve(self):
        self.assertEqual(self.decide([review(22), review(33)]), "approved")

    def test_missing_vote_author_and_outsiders_do_not_count(self):
        for votes in ([], [review(22)], [review(11), review(22)],
                      [review(22), review(44)], [review(22), review(22, sequence=2)]):
            with self.subTest(votes=votes):
                self.assertNotEqual(self.decide(votes), "approved")

    def test_old_revision_votes_do_not_count(self):
        self.assertNotEqual(self.decide([review(22, sha="old"), review(33)]), "approved")

    def test_latest_decisive_review_wins_even_if_input_unordered(self):
        self.assertNotEqual(self.decide([review(22, "CHANGES_REQUESTED", sequence=3),
                                        review(33), review(22)]), "approved")
        self.assertEqual(self.decide([review(22, "CHANGES_REQUESTED"), review(33),
                                     review(22, sequence=3)]), "approved")

    def test_dismissal_revokes_and_comment_does_not_revoke(self):
        for state, approved in [("DISMISSED", False), ("COMMENTED", True), ("PENDING", True)]:
            with self.subTest(state=state):
                votes = [review(22), review(33), review(22, state, sequence=2)]
                self.assertEqual(self.decide(votes) == "approved", approved)

    def test_inactive_wrong_base_ineligible_and_conflicted(self):
        for change in ({"state": "closed"}, {"merged": True}, {"draft": True},
                       {"base": {"ref": "other"}}, {"user": {"id": 99}},
                       {"mergeable": False}, {"mergeable": None}):
            with self.subTest(change=change):
                self.assertNotEqual(self.decide([review(22), review(33)], **change), "approved")

    def test_invalid_player_configuration_fails_closed(self):
        for players in ([], [11], [11, 22, 22], [11, 22, 0], [11, 22, True],
                        [11, 22, "33"]):
            with self.subTest(players=players), self.assertRaises(ValueError):
                validate_rules({**RULES, "players": players})

    def test_base_configuration_matches_workflow(self):
        with self.assertRaises(ValueError):
            validate_rules({**RULES, "base": "other"})


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGitHub()
        self.output = []

    def run_referee(self, apply=True, installed="installed"):
        return reconcile(self.api, RULES, installed, apply=apply, emit=self.output.append)

    def test_merge_pins_head_and_stops_after_one_adoption(self):
        self.assertEqual(self.run_referee(), "merged")
        self.assertEqual(self.api.merges, [(1, "head-1")])
        self.assertEqual(json.loads(self.output[-1])["commit"], "adopted")

    def test_dry_run_never_writes(self):
        self.assertEqual(self.run_referee(apply=False), "idle")
        self.assertEqual(self.api.merges, [])

    def test_stale_installed_rules(self):
        self.api.base = "changed"
        self.assertEqual(self.run_referee(), "stale")
        self.assertEqual(self.api.merges, [])

    def test_base_moves_before_adoption(self):
        def move(api):
            if api.base_reads == 2:
                api.base = "changed"
        self.api.on_base = move
        self.assertEqual(self.run_referee(), "stale")
        self.assertEqual(self.api.merges, [])

    def test_revision_changes_before_adoption(self):
        def revise(api):
            if api.pull_reads == 2:
                api.pr["head"]["sha"] = "revised"
        self.api.on_pull = revise
        self.assertEqual(self.run_referee(), "head-changed")
        self.assertEqual(self.api.merges, [])

    def test_vote_changes_before_adoption(self):
        def withdraw(api):
            if api.vote_reads == 2:
                api.votes.append(review(22, "CHANGES_REQUESTED", sequence=3))
        self.api.on_reviews = withdraw
        self.assertEqual(self.run_referee(), "votes-or-pr-changed")
        self.assertEqual(self.api.merges, [])

    def test_duplicate_run_does_not_merge_twice(self):
        self.run_referee()
        self.assertEqual(self.run_referee(installed="adopted"), "idle")
        self.assertEqual(len(self.api.merges), 1)

    def test_unsuccessful_merge_is_not_reported_as_success(self):
        self.api.merge = lambda *args: {"merged": False}
        with self.assertRaises(RuntimeError):
            self.run_referee()
        self.assertFalse(any(json.loads(line).get("result") == "merged" for line in self.output))

    def test_api_failure_is_not_retried_as_a_blind_write(self):
        def fail(*args):
            raise RuntimeError("ambiguous merge response")
        self.api.merge = fail
        with self.assertRaises(RuntimeError):
            self.run_referee()


class AdapterTests(unittest.TestCase):
    @patch("referee.subprocess.run")
    def test_paginated_reviews_flattened(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '[[{"id":1}],[{"id":2}]]', '')
        self.assertEqual(GitHub("owner/repo").reviews(1), [{"id": 1}, {"id": 2}])
        self.assertIn("--paginate", run.call_args.args[0])
        self.assertIn("--slurp", run.call_args.args[0])

    @patch("referee.subprocess.run")
    def test_merge_uses_expected_sha(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, '{"merged":true}', '')
        GitHub("owner/repo").merge(1, "expected")
        self.assertEqual(json.loads(run.call_args.kwargs["input"]),
                         {"sha": "expected", "merge_method": "merge"})
        self.assertIn("PUT", run.call_args.args[0])

    @patch("referee.subprocess.run")
    def test_failure_does_not_echo_response_secrets(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, 'secret', 'secret')
        with self.assertRaisesRegex(RuntimeError, "GitHub GET") as error:
            GitHub("owner/repo").pull(1)
        self.assertNotIn("secret", str(error.exception))

    @patch("referee.time.sleep")
    def test_unknown_mergeability_retried_but_bounded(self, sleep):
        api = GitHub("owner/repo")
        with patch.object(api, "api", side_effect=[{**PR, "mergeable": None}, PR]) as call:
            self.assertTrue(api.pull(1)["mergeable"])
            self.assertEqual(call.call_count, 2)
        with patch.object(api, "api", return_value={**PR, "mergeable": None}) as call:
            self.assertIsNone(api.pull(1)["mergeable"])
            self.assertEqual(call.call_count, 3)

    def test_conflicts_are_not_retried(self):
        api = GitHub("owner/repo")
        with patch.object(api, "api", return_value={**PR, "mergeable": False}) as call:
            self.assertFalse(api.pull(1)["mergeable"])
            call.assert_called_once()

    def test_repository_must_be_an_owner_repo_not_url(self):
        for name in ("https://example.org", "owner", "owner/repo/extra", "--flag"):
            with self.assertRaises(ValueError):
                GitHub(name)


if __name__ == "__main__":
    unittest.main()
