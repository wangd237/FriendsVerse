"""T0 rule, memory and persistence tests; fake is NOT real LLM validation."""

import pytest

from friendsverse.llm import FakeClient, parse_action
from friendsverse.models import Action, WorldState
from friendsverse.runtime import ActionRejected, resolve_action, simulate, view_for, remember
from friendsverse.store import ConflictError, Store


def test_schema():
    with pytest.raises(ValueError):
        Action(type="speak", text="")
    with pytest.raises(ValueError):
        Action(type="do", target="unsupported")
    assert parse_action('{"type":"wait"}') == Action(type="wait")


def test_illegal_move_does_not_change_state():
    state = WorldState()
    with pytest.raises(ActionRejected):
        resolve_action(state, "joey", Action(type="move_to", target="moon"))
    assert state.positions["joey"] == "apt_chandler_joey"


def test_no_remote_conversation():
    state = WorldState()
    state.positions["chandler"] = "hallway"
    with pytest.raises(ActionRejected, match="alone"):
        resolve_action(state, "joey", Action(type="speak", text="Hello"))


def test_visibility_memory():
    state = WorldState()
    state.positions["ross"] = "central_perk"
    state.memories["ross"] = []
    event = resolve_action(state, "joey", Action(type="speak", text="I need help"))
    assert event is not None
    assert event.witnesses == ["chandler", "joey"]
    remember(state, event)
    assert state.memories["ross"] == []
    assert len(state.memories["chandler"]) == 1
    assert "I need help" in view_for(state, "joey", [])["own_memory"][0]["text"]


def test_candidate_simulation_preserves_original():
    before = WorldState()
    after, episode = simulate(before, FakeClient(), "fake")
    assert before.episode_no == 0
    assert before.memories["joey"] == []
    assert after.episode_no == 1
    assert len(episode.events) == 4
    assert all(e.text in episode.script for e in episode.events)


def test_memory_reappears_next_episode_and_survives_restart(tmp_path):
    db = tmp_path / "test.db"
    with Store(db) as store:
        store.initialize()
        before = store.load()
        after, ep1 = simulate(before, FakeClient(), "fake")
        store.commit(before, after, ep1)
        fresh_client = FakeClient()
        before = store.load()
        after, ep2 = simulate(before, fresh_client, "fake")
        store.commit(before, after, ep2)
        assert ep2.number == 2
        prior_ids = {e.id for e in ep1.events}
        assert prior_ids
        for actor in ("joey", "chandler"):
            assert set(ep2.prior_memory_ids[actor]) & prior_ids
        assert any("试镜" in m["text"] for m in fresh_client.calls[0]["own_memory"])
        assert len(store.episodes()) == 2
    with Store(db) as reopened:
        assert reopened.load().episode_no == 2
        assert reopened.episodes()[0].script == ep1.script


def test_stale_commit_is_rejected_without_duplicate(tmp_path):
    with Store(tmp_path / "test.db") as store:
        old = store.initialize()
        after, ep = simulate(old, FakeClient(), "fake")
        store.commit(old, after, ep)
        with pytest.raises(ConflictError):
            store.commit(old, after, ep)
        assert store.load().version == 1
        assert len(store.episodes()) == 1


def test_provider_failure_never_publishes(tmp_path):
    class BrokenClient:
        def choose(self, actor, perception):
            raise RuntimeError("API unavailable")
    with Store(tmp_path / "test.db") as store:
        original = store.initialize()
        with pytest.raises(RuntimeError):
            simulate(original, BrokenClient(), "live")
        assert store.load().version == 0
        assert store.episodes() == []


def test_bad_actions_only_reject_without_state_change():
    class BadMoves:
        def choose(self, actor, perception):
            return Action(type="move_to", target="moon")
    original = WorldState()
    after, episode = simulate(original, BadMoves(), "fake")
    assert after.positions == original.positions
    assert not episode.events
    assert len(episode.rejected_actions) == 4
