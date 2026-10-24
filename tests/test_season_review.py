"""T3 tests for seven-day persistence, evidence and review artifacts."""

import json
import subprocess
import sys

import pytest

from friendsverse.ensemble import EnsembleFakeClient, new_ensemble, simulate_day
from friendsverse.review import analyze, export_review
from friendsverse.store import Store


def test_seven_days_across_same_universe_with_source_evidence(tmp_path):
    with Store(tmp_path / "season.db") as store:
        previous = store.initialize(mode="ensemble")
        for _ in range(7):
            after, episode = simulate_day(
                previous, EnsembleFakeClient(), "fake", actors_per_period=3
            )
            store.commit(previous, after, episode)
            previous = store.load()
        episodes = store.episodes()
        report = export_review(episodes, previous, tmp_path / "review")
        assert report["published_episodes"] == 7
        assert report["final_day"] == 7
        assert report["engineering_checks_passed"]
        assert set(report["unique_speakers"]) == set(previous.positions)
        assert report["total_dialogue_events"] > 0
        assert len(report["episodes"]) == 7
        assert len(json.loads((tmp_path / "review/episode-evidence.json").read_text())) == 7
        scripts = (tmp_path / "review/season-scripts.md").read_text()
        assert "EP01" in scripts and "EP07" in scripts
        assert "Human review checklist" in scripts


def test_source_event_across_three_episodes_is_observation_not_story_claim(tmp_path):
    with Store(tmp_path / "world.db") as store:
        state = store.initialize(mode="ensemble")
        for _ in range(3):
            next_state, ep = simulate_day(state, EnsembleFakeClient(), "fake")
            store.commit(state, next_state, ep)
            state = store.load()
        report = analyze(store.episodes(), state)
        assert report["engineering_checks_passed"]
        # The fake scenario is not forced to create a three-episode arc.
        # Absence of an arc is a valid experimental observation, not a bug.
        assert isinstance(report["evidence_based_multiepisode_relationship_patterns"], list)
        assert any("does not prove" in message for message in report["important_limitations"])


def test_seven_day_cli_can_resume_in_explicit_batches(tmp_path):
    db = tmp_path / "world.db"
    out = tmp_path / "artifacts"

    def run(*args, expect_success=True):
        result = subprocess.run(
            [sys.executable, "-m", "friendsverse", *args, "--db", str(db)],
            capture_output=True, text=True,
        )
        if expect_success:
            assert result.returncode == 0, result.stdout + result.stderr
        else:
            assert result.returncode != 0
        return result

    run("init", "--mode", "ensemble")
    run("season", "--provider", "fake", "--days", "3",
        "--actors-per-period", "3", "--out", str(out))
    run("season", "--provider", "fake", "--days", "4",
        "--actors-per-period", "3", "--out", str(out))
    run("report", "--out", str(out))
    report = json.loads((out / "season-summary.json").read_text())
    assert report["published_episodes"] == 7
    assert report["engineering_checks_passed"]
    run("season", "--provider", "fake", "--days", "1",
        expect_success=False)
    with Store(db) as store:
        assert store.load().episode_no == 7
        assert len(store.episodes()) == 7


def test_failed_episode_keeps_previous_days_committed(tmp_path):
    class FailingClient:
        def choose(self, actor, perception):
            raise RuntimeError("upstream failure")

    with Store(tmp_path / "season.db") as store:
        state = store.initialize(mode="ensemble")
        after, ep = simulate_day(state, EnsembleFakeClient(), "fake")
        store.commit(state, after, ep)
        with pytest.raises(RuntimeError, match="upstream failure"):
            simulate_day(store.load(), FailingClient(), "live")
        assert len(store.episodes()) == 1
        assert store.load().virtual_day == 1


def test_report_detects_unsupported_relation_evidence():
    state = new_ensemble()
    updated, ep = simulate_day(state, EnsembleFakeClient(), "fake")
    ep.relationship_changes.append({
        "from_id": "joey", "to_id": "chandler",
        "dimension": "trust", "source_event_ids": ["nonexistent-event"],
    })
    result = analyze([ep], updated)
    assert not result["engineering_checks_passed"]
    assert any("missing executed evidence" in x for x in result["engineering_issues"])
