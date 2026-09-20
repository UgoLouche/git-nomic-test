"""Weeks of deterministic play; API faults are simulated, not live GitHub proof."""
import copy
import json
import unittest
from unittest.mock import patch

from game_engine import reconcile_game, tally, timestamp, utc
from referee import GitHub

START = timestamp("2026-01-01T00:00:00Z")
WEEK = 7 * 24 * 60 * 60
RULES = {"base": "main", "players": [11, 22, 33], "turns": {
    "proposal_seconds": WEEK, "voting_seconds": WEEK,
    "points_per_accept": 1, "points_to_win": 5}}
STATE = {"scores": {"11": 0, "22": 0, "33": 0}, "history": [],
         "turn": 1, "player": 11, "phase": "new", "started_at": None,
         "deadline": None, "proposal": None, "winners": []}


class World:
    def __init__(self):
        self.rules = copy.deepcopy(RULES)
        self.state = copy.deepcopy(STATE)
        self.base = "base-0"
        self.prs, self.votes, self.events = {}, {}, {}
        self.writes, self.merges, self.closed = [], [], []
        self.clock = START
        self.lost_save = self.lost_merge = self.lost_close = False
        self.failed_save = self.failed_merge = self.failed_close = False
        self.on_merge = lambda: None

    def base_sha(self, branch):
        return self.base

    def save_state(self, state, installed, branch):
        assert installed == self.base, "Non-fast-forward state write"
        if self.failed_save:
            raise RuntimeError("write failed before commit")
        self.state = copy.deepcopy(state)
        self.writes.append(self.state)
        self.base = f"state-{len(self.writes)}"
        if self.lost_save:
            self.lost_save = False
            raise RuntimeError("lost response after commit")

    def pulls(self, branch):
        return copy.deepcopy([p for p in self.prs.values() if p["state"] == "open"])

    def pull(self, number):
        return copy.deepcopy(self.prs[number])

    def reviews(self, number):
        return copy.deepcopy(self.votes[number])

    def timeline(self, number):
        return copy.deepcopy(self.events[number])

    def close(self, number):
        if self.failed_close:
            raise RuntimeError("close failed")
        self.prs[number]["state"] = "closed"
        self.closed.append(number)
        if self.lost_close:
            self.lost_close = False
            raise RuntimeError("lost response after close")

    def merge(self, number, sha):
        assert sha == self.prs[number]["head"]["sha"]
        if self.failed_merge:
            raise RuntimeError("merge failed")
        self.base = f"merge-{number}"
        self.prs[number].update(merged=True, state="closed", merge_commit_sha=self.base)
        self.merges.append(number)
        self.on_merge()
        if self.lost_merge:
            self.lost_merge = False
            raise RuntimeError("lost response after merge")
        return {"merged": True, "sha": self.base}

    def propose(self, author=None, created=None, **changes):
        n = len(self.prs) + 1
        p = {"number": n, "state": "open", "draft": False, "merged": False,
             "user": {"id": self.state["player"] if author is None else author},
             "base": {"ref": "main"}, "head": {"sha": f"head-{n}"},
             "mergeable": True, "created_at": utc(self.clock if created is None else created)}
        p.update(changes)
        self.prs[n], self.votes[n], self.events[n] = p, [], []
        return n

    def vote(self, number, user, state="APPROVED", at=None, sha=None):
        self.votes[number].append({"id": len(self.votes[number]) + 1,
                                  "user": {"id": user}, "state": state,
                                  "commit_id": sha or self.prs[number]["head"]["sha"],
                                  "submitted_at": utc(self.clock if at is None else at)})

    def tick(self, apply=True, installed=None):
        return reconcile_game(self, self.rules, self.state, installed or self.base,
                              now=self.clock, apply=apply, emit=lambda _: None)

    def due(self):
        self.clock = timestamp(self.state["deadline"])

    def voting(self):
        self.tick()
        n = self.propose()
        assert self.tick() == "voting-opened"
        for p in self.state["proposal"]["voters"]:
            self.vote(n, p)
        return n


class GameTests(unittest.TestCase):
    def setUp(self):
        self.w = World()

    def test_start_and_wait_do_not_write_on_idle_ticks(self):
        w = self.w
        self.assertEqual(w.tick(), "started")
        self.assertEqual(w.state["deadline"], utc(START + WEEK))
        for _ in range(5):
            self.assertEqual(w.tick(), "waiting-for-proposal")
        self.assertEqual(len(w.writes), 1)

    def test_dry_run_start_selection_merge_and_rejection_never_write(self):
        w = self.w
        self.assertEqual(w.tick(False), "dry-run:started")
        self.assertEqual(w.state["phase"], "new")
        w.tick()
        n = w.propose()
        snapshot = copy.deepcopy(w.state)
        self.assertEqual(w.tick(False), "dry-run:voting-opened")
        self.assertEqual(w.state, snapshot)
        w.tick()
        w.vote(n, 22)
        w.vote(n, 33)
        w.due()
        self.assertEqual(w.tick(False), "dry-run:merge")
        self.assertFalse(w.merges)
        w.votes[n] = []
        self.assertEqual(w.tick(False), "dry-run:rejected")
        self.assertFalse(w.closed)
        self.assertEqual(w.state["phase"], "voting")

    def test_full_week_to_vote_even_with_all_approvals(self):
        w = self.w
        w.voting()
        self.assertEqual(w.tick(), "waiting-for-deadline")
        w.clock += WEEK - 1
        self.assertEqual(w.tick(), "waiting-for-deadline")
        w.clock += 1
        self.assertEqual(w.tick(), "merged")
        self.assertEqual(w.state["scores"]["11"], 0)
        self.assertEqual(w.tick(), "accepted")
        self.assertEqual(w.state["scores"]["11"], 1)
        self.assertEqual(w.state["player"], 22)
        self.assertEqual(w.state["turn"], 2)
        self.assertEqual(w.state["history"][0]["merge"], "merge-1")

    def test_thirteen_turns_first_to_five_with_weekly_windows(self):
        w = self.w
        w.tick()
        for turn in range(1, 14):
            w.clock += WEEK - 1
            n = w.propose()
            self.assertEqual(w.tick(), "voting-opened")
            for p in w.state["proposal"]["voters"]:
                w.vote(n, p)
            w.due()
            self.assertEqual(w.tick(), "merged")
            self.assertEqual(w.tick(), "accepted")
            count = len(w.writes)
            self.assertIn(w.tick(), {"waiting-for-proposal", "finished"})
            self.assertEqual(len(w.writes), count)
        self.assertEqual(w.state["phase"], "finished")
        self.assertEqual(w.state["winners"], [11])
        self.assertEqual(w.state["scores"], {"11": 5, "22": 4, "33": 4})
        self.assertEqual(len(w.state["history"]), 13)
        self.assertGreater(w.clock - START, 25 * WEEK)

    def test_missed_turn_and_delayed_tick_give_next_player_full_window(self):
        w = self.w
        w.tick()
        w.clock += 4 * WEEK
        self.assertEqual(w.tick(), "passed")
        self.assertEqual(w.state["turn"], 2)
        self.assertEqual(w.state["deadline"], utc(w.clock + WEEK))
        self.assertEqual(w.tick(), "waiting-for-proposal")

    def test_old_out_of_turn_draft_and_wrong_base_not_selected(self):
        w = self.w
        w.tick()
        w.propose(created=START - 1)
        w.propose(author=22)
        w.propose(author=99)
        w.propose(draft=True)
        w.propose(base={"ref": "elsewhere"})
        self.assertEqual(w.tick(), "waiting-for-proposal")
        w.due()
        self.assertEqual(w.tick(), "passed")
        self.assertEqual(w.closed, [])

    def test_competing_proposals_oldest_created_then_number(self):
        w = self.w
        w.tick()
        w.propose(created=START + 1)
        n = w.propose(created=START)
        w.propose(created=START)
        w.clock += 2
        w.tick()
        self.assertEqual(w.state["proposal"]["number"], n)

    def test_timely_proposal_selected_on_delayed_tick_with_full_vote_week(self):
        w = self.w
        w.tick()
        n = w.propose(created=START + WEEK - 1)
        w.clock += 2 * WEEK
        self.assertEqual(w.tick(), "voting-opened")
        self.assertEqual(w.state["deadline"], utc(w.clock + WEEK))
        self.assertEqual(w.state["proposal"]["number"], n)

    def test_submission_at_deadline_is_too_late(self):
        w = self.w
        w.tick()
        w.due()
        w.propose()
        self.assertEqual(w.tick(), "passed")

    def test_selection_head_race_does_not_freeze_inconsistent_snapshot(self):
        w = self.w
        w.tick()
        n = w.propose()
        original = w.pull
        calls = []
        def pull(number):
            calls.append(number)
            if len(calls) == 2:
                w.prs[n]["head"]["sha"] = "changed"
            return original(number)
        w.pull = pull
        self.assertEqual(w.tick(), "selection-changed")
        self.assertEqual(w.state["phase"], "proposing")

    def test_revisions_and_restored_sha_after_force_push_fail(self):
        for force in (False, True):
            with self.subTest(force=force):
                w = World()
                n = w.voting()
                if force:
                    w.events[n].append({"id": 1, "event": "head_ref_force_pushed"})
                else:
                    w.prs[n]["head"]["sha"] = "revised"
                self.assertEqual(w.tick(), "revised")
                self.assertEqual(w.state["turn"], 2)
                self.assertEqual(w.closed, [n])
                self.assertFalse(w.merges)

    def test_preselection_force_pushes_do_not_invalidate(self):
        w = self.w
        w.tick()
        n = w.propose()
        w.events[n].append({"id": 7, "event": "head_ref_force_pushed"})
        w.tick()
        self.assertEqual(w.tick(), "waiting-for-deadline")

    def test_conflict_draft_base_change_and_closed_pr(self):
        for change, result in [({"mergeable": False}, "conflicted"),
                               ({"draft": True}, "ineligible"),
                               ({"base": {"ref": "other"}}, "ineligible"),
                               ({"state": "closed"}, "closed")]:
            with self.subTest(change=change):
                w = World()
                n = w.voting()
                w.prs[n].update(change)
                self.assertEqual(w.tick(), result)
                self.assertEqual(w.state["turn"], 2)
                self.assertEqual(sum(w.state["scores"].values()), 0)

    def test_unknown_mergeability_waits_but_does_not_award(self):
        w = self.w
        n = w.voting()
        w.prs[n]["mergeable"] = None
        w.due()
        self.assertEqual(w.tick(), "waiting-for-mergeability")
        self.assertFalse(w.merges)
        w.prs[n]["mergeable"] = True
        self.assertEqual(w.tick(), "merged")

    def test_tie_abstention_rejection_and_stale_vote(self):
        for votes in ([], [(22, "APPROVED")], [(22, "APPROVED"), (33, "CHANGES_REQUESTED")],
                      [(11, "APPROVED"), (99, "APPROVED")]):
            with self.subTest(votes=votes):
                w = World()
                n = w.voting()
                w.votes[n] = []
                for user, value in votes:
                    w.vote(n, user, value)
                w.due()
                self.assertEqual(w.tick(), "rejected")
                self.assertEqual(w.state["scores"]["11"], 0)
        w = World()
        n = w.voting()
        w.vote(n, 22, sha="old")
        w.due()
        self.assertEqual(w.tick(), "rejected")

    def test_changed_votes_and_dismissal(self):
        for value, expected in [("CHANGES_REQUESTED", "rejected"),
                                ("DISMISSED", "rejected"),
                                ("COMMENTED", "merged"), ("PENDING", "merged")]:
            with self.subTest(value=value):
                w = World()
                n = w.voting()
                w.vote(n, 22, value)
                w.due()
                self.assertEqual(w.tick(), expected)

    def test_late_votes_and_changes_do_not_rewrite_deadline_tally(self):
        w = self.w
        n = w.voting()
        w.due()
        w.vote(n, 22, "CHANGES_REQUESTED")
        self.assertEqual(w.tick(), "merged")
        w = World()
        n = w.voting()
        w.votes[n] = []
        w.due()
        w.vote(n, 22)
        w.vote(n, 33)
        self.assertEqual(w.tick(), "rejected")

    def test_general_majority_is_not_hardcoded_unanimity(self):
        proposal = {"head": "h", "voters": [22, 33, 44]}
        reviews = [{"id": u, "user": {"id": u}, "state": "APPROVED",
                    "commit_id": "h", "submitted_at": utc(START)} for u in (22, 33)]
        self.assertTrue(tally(reviews, proposal, utc(START + WEEK))[0])
        proposal["voters"].append(55)
        self.assertFalse(tally(reviews, proposal, utc(START + WEEK))[0])

    def test_stale_checkout_never_writes_or_closes(self):
        w = self.w
        n = w.voting()
        w.prs[n]["head"]["sha"] = "revised"
        self.assertEqual(w.tick(installed="obsolete"), "stale")
        self.assertFalse(w.closed)

    def test_failed_state_write_can_be_retried_with_fresh_state(self):
        w = self.w
        w.failed_save = True
        with self.assertRaises(RuntimeError):
            w.tick()
        self.assertEqual(w.state["phase"], "new")
        w.failed_save = False
        self.assertEqual(w.tick(), "started")

    def test_lost_state_write_response_does_not_repeat_transition(self):
        w = self.w
        w.lost_save = True
        with self.assertRaises(RuntimeError):
            w.tick()
        self.assertEqual(w.tick(), "waiting-for-proposal")
        self.assertEqual(len(w.writes), 1)

    def test_lost_merge_response_settles_once_on_next_checkout(self):
        w = self.w
        w.voting()
        w.due()
        w.lost_merge = True
        with self.assertRaises(RuntimeError):
            w.tick()
        self.assertEqual(w.tick(), "accepted")
        self.assertEqual(w.tick(), "waiting-for-proposal")
        self.assertEqual(w.state["scores"]["11"], 1)
        self.assertEqual(len(w.merges), 1)

    def test_failed_merge_never_scores(self):
        w = self.w
        w.voting()
        w.due()
        w.failed_merge = True
        with self.assertRaises(RuntimeError):
            w.tick()
        self.assertEqual(w.state["scores"]["11"], 0)
        self.assertEqual(w.state["phase"], "voting")
        w.failed_merge = False
        self.assertEqual(w.tick(), "merged")

    def test_lost_settlement_write_response_does_not_double_score(self):
        w = self.w
        w.voting()
        w.due()
        w.tick()
        w.lost_save = True
        with self.assertRaises(RuntimeError):
            w.tick()
        self.assertEqual(w.tick(), "waiting-for-proposal")
        self.assertEqual(w.state["scores"]["11"], 1)
        self.assertEqual(len(w.state["history"]), 1)

    def test_lost_close_response_advances_once_without_points(self):
        w = self.w
        n = w.voting()
        w.votes[n] = []
        w.due()
        w.lost_close = True
        with self.assertRaises(RuntimeError):
            w.tick()
        self.assertEqual(w.tick(), "closed")
        self.assertEqual(w.tick(), "waiting-for-proposal")
        self.assertEqual(w.state["turn"], 2)
        self.assertEqual(w.closed, [n])

    def test_failed_close_does_not_consume_turn(self):
        w = self.w
        n = w.voting()
        w.votes[n] = []
        w.due()
        w.failed_close = True
        with self.assertRaises(RuntimeError):
            w.tick()
        self.assertEqual(w.state["turn"], 1)
        w.failed_close = False
        self.assertEqual(w.tick(), "rejected")

    def test_amended_ledger_preserved_and_next_award_uses_new_rule(self):
        w = self.w
        w.voting()
        w.due()
        def amendment():
            w.rules["turns"]["points_per_accept"] = 2
            w.state["scores"]["11"] = 3
            w.rules["players"] = [11, 33, 22]
        w.on_merge = amendment
        self.assertEqual(w.tick(), "merged")
        self.assertEqual(w.tick(), "accepted")
        self.assertEqual(w.state["scores"]["11"], 4)  # old frozen award, new ledger
        self.assertEqual(w.state["player"], 33)  # new rotation
        w.propose()
        w.tick()
        self.assertEqual(w.state["proposal"]["award"], 2)

    def test_amended_victory_threshold_applies_in_adopted_settlement(self):
        w = self.w
        w.voting()
        w.due()
        w.on_merge = lambda: w.rules["turns"].update(points_to_win=1)
        w.tick()
        self.assertEqual(w.tick(), "accepted")
        self.assertEqual(w.state["phase"], "finished")

    def test_invalid_configuration_fails_without_writes(self):
        for value in (0, -1, True, "604800"):
            with self.subTest(value=value):
                w = World()
                w.rules["turns"]["proposal_seconds"] = value
                with self.assertRaises(ValueError):
                    w.tick()
                self.assertFalse(w.writes)


class StateAdapterTests(unittest.TestCase):
    def test_git_database_write_pins_parent_preserves_tree_and_never_forces(self):
        api = GitHub("owner/repo")
        with patch.object(api, "api", side_effect=[{"tree": {"sha": "old-tree"}},
                                                   {"sha": "blob"}, {"sha": "tree"},
                                                   {"sha": "commit"}, {}]) as call:
            self.assertEqual(api.save_state(STATE, "installed", "main"), "commit")
        calls = call.call_args_list
        self.assertEqual(calls[0].args[0], "git/commits/installed")
        self.assertEqual(json.loads(calls[1].kwargs["body"]["content"]), STATE)
        self.assertEqual(calls[2].kwargs["body"]["base_tree"], "old-tree")
        self.assertEqual(calls[2].kwargs["body"]["tree"][0]["path"], "state.json")
        self.assertEqual(calls[3].kwargs["body"]["parents"], ["installed"])
        self.assertEqual(calls[4].kwargs["body"], {"sha": "commit", "force": False})

    def test_ref_update_failure_not_blindly_retried(self):
        api = GitHub("owner/repo")
        with patch.object(api, "api", side_effect=[{"tree": {"sha": "old"}},
                                                   {"sha": "b"}, {"sha": "t"},
                                                   {"sha": "c"}, RuntimeError("409")]) as call:
            with self.assertRaises(RuntimeError):
                api.save_state(STATE, "installed", "main")
            self.assertEqual(call.call_count, 5)

    def test_timeline_pagination_and_close(self):
        api = GitHub("owner/repo")
        with patch.object(api, "api", return_value=[]) as call:
            api.timeline(7)
            call.assert_called_with("issues/7/timeline?per_page=100", paginate=True)
            api.close(7)
            call.assert_called_with("pulls/7", method="PATCH", body={"state": "closed"})


if __name__ == "__main__":
    unittest.main()
