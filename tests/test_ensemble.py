"""T2 full-slice fake provider tests; never claim quality or autonomy from these."""

from friendsverse.ensemble import (
    ACTORS, EnsembleFakeClient, new_ensemble, perceive, simulate_day, execute
)
from friendsverse.models import Action
from friendsverse.store import Store


def test_six_people_full_day_and_grounded_relationship_evidence():
    state = new_ensemble()
    client = EnsembleFakeClient()
    next_state, episode = simulate_day(state, client, "fake")
    assert len(next_state.positions) == 6
    assert next_state.virtual_day == 1 and next_state.episode_no == 1
    assert state.virtual_day == 0
    assert len({event.actor for event in episode.events if event.type == "speak"}) >= 4
    assert all(period in episode.script for period in ("Morning", "Afternoon", "Evening"))
    assert "Central Perk" in episode.script
    assert episode.relationship_changes
    all_ids = {event.id for event in episode.events}
    assert all(
        set(change["source_event_ids"]) <= all_ids
        for change in episode.relationship_changes
    )
    assert any(e.type == "opportunity" for e in episode.events)
    assert len(client.calls) >= 18


def test_two_days_persist_memories_and_relationships(tmp_path):
    with Store(tmp_path / "world.db") as store:
        previous = store.initialize(mode="ensemble")
        for day in range(2):
            updated, ep = simulate_day(previous, EnsembleFakeClient(), "fake")
            store.commit(previous, updated, ep)
            previous = store.load()
        assert previous.virtual_day == 2
        assert len(store.episodes()) == 2
        first_ids = {e.id for e in store.episodes()[0].events}
        assert any(first_ids.intersection(ids) for ids in store.episodes()[1].prior_memory_ids.values())
        assert previous.relationships["joey"]["chandler"]["trust"] > 74
        assert previous.mode == "ensemble"
    with Store(tmp_path / "world.db") as reopened:
        assert reopened.load().episode_no == 2


def test_private_opportunity_is_not_visible_to_other_character():
    state = new_ensemble()
    updated, ep = simulate_day(state, EnsembleFakeClient(), "fake")
    secret = next(e for e in ep.events if e.type == "opportunity")
    assert secret.witnesses == ["joey"]
    assert any(m.event_id == secret.id for m in updated.memories["joey"])
    assert not any(m.event_id == secret.id for m in updated.memories["chandler"])


def test_move_and_social_action_reject_impossible_contact():
    state = new_ensemble()
    from friendsverse.ensemble import execute
    try:
        execute(state, "ross", Action(type="do", target="share_food", recipient="joey"), "morning", [])
    except ValueError:
        pass
    else:
        assert False, "cross-location interaction must be rejected"
    assert state.relationships["joey"]["ross"]["closeness"] == 56


def test_memory_input_is_local_and_no_false_promise():
    state = new_ensemble()
    view = perceive(state, "joey", "morning", [])
    assert "own_memory" in view and "own_relationships" in view
    assert "private_memory" not in view
    changes = []
    action = Action(type="do", target="promise_help", recipient="chandler")
    event = execute(state, "joey", action, "morning", changes)
    assert event is not None
    assert len(state.commitments) == 1
    assert state.commitments[0]["status"] == "open"
    assert not changes  # Promise made is not the same as a promise fulfilled.
