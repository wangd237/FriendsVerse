"""One-location, two-character evening encounter: minimal autonomous action loop."""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol
from uuid import uuid4

from friendsverse.models import Action, Event, Episode, LOCATIONS, MemoryEntry, WorldState

PERSONAS = {
    "joey": (
        "Joey: warm, direct, loyal, an aspiring actor; sometimes impulsive but "
        "not unintelligent. You value Chandler's friendship. You are preparing "
        "for an audition and might appreciate rehearsal help."
    ),
    "chandler": (
        "Chandler: loyal and observant, uses self-deprecating humor to ease "
        "awkward moments, but can be genuinely supportive. You value Joey's "
        "friendship and have office-work responsibilities. Not every line "
        "needs to be a joke."
    ),
}


class DecisionClient(Protocol):
    def choose(self, actor: str, perception: dict) -> Action: ...


class ActionRejected(ValueError):
    pass


def view_for(state: WorldState, actor: str, events: list[Event]) -> dict:
    """Return strictly local scene state plus only actor's witnessed history."""
    here = state.positions[actor]
    present = sorted(name for name, loc in state.positions.items() if loc == here)
    return {
        "actor": actor,
        "persona": PERSONAS[actor],
        "episode": state.episode_no + 1,
        "period": "evening",
        "location": here,
        "present": present,
        "goal": ("prepare for an acting audition" if actor == "joey"
                 else "balance office work with friendship"),
        "own_memory": [m.model_dump() for m in state.memories[actor][-24:]],
        "recent_scene": [
            {"speaker": e.actor, "text": e.text}
            for e in events if e.type == "speak" and actor in e.witnesses
        ][-8:],
        "available_actions": [
            "speak (text): one spoken line",
            "wait: do not interact",
            "move_to (target): apt_chandler_joey, hallway, or central_perk",
            "do (target=help_rehearse): help roommate rehearse if in same room",
        ],
    }


def resolve_action(state: WorldState, actor: str, action: Action) -> Event | None:
    """Only the resolver may turn an intention into world facts."""
    if actor not in state.positions:
        raise ActionRejected("Unknown character")
    here = state.positions[actor]
    witnesses = sorted(name for name, place in state.positions.items() if place == here)
    if action.type == "wait":
        return None
    if action.type == "move_to":
        if action.target not in LOCATIONS:
            raise ActionRejected("Unknown destination")
        if action.target == here:
            raise ActionRejected("Already at destination")
        state.positions[actor] = action.target
        return Event(id=str(uuid4()), actor=actor, type="move_to",
                     text=f"{actor} moved to {action.target}", location=here,
                     witnesses=witnesses)
    if action.type == "speak":
        if len(witnesses) < 2:
            raise ActionRejected("Cannot speak to a roommate when alone")
        return Event(id=str(uuid4()), actor=actor, type="speak",
                     text=action.text or "", location=here, witnesses=witnesses)
    if action.type == "do":
        if len(witnesses) < 2:
            raise ActionRejected("Cannot help rehearse when alone")
        if action.target != "help_rehearse":
            raise ActionRejected("Unsupported activity")
        return Event(id=str(uuid4()), actor=actor, type="do",
                     text=f"{actor} helped their roommate rehearse.",
                     location=here, witnesses=witnesses)
    raise ActionRejected("Unsupported action")


def remember(state: WorldState, event: Event) -> None:
    """Only characters present during the event receive it as personal memory."""
    for witness in event.witnesses:
        if witness in state.memories:
            state.memories[witness].append(MemoryEntry(
                event_id=event.id, actor=event.actor, text=event.text
            ))


def format_episode(number: int, events: list[Event]) -> tuple[str, str]:
    """A transparent transcript renderer; not a generative editorial Agent yet."""
    title = f"EP{number:02d} — An Evening at Home"
    lines = [f"# {title}", "", "## SCENE 01 · Chandler & Joey's Apartment · Evening", ""]
    if not events:
        lines.append("*A quiet evening. No conversation occurred.*")
    for event in events:
        if event.type == "speak":
            lines.append(f"**{event.actor.upper()}**: {event.text}")
        else:
            lines.append(f"*{event.text}*")
        lines.append("")
    return title, "\n".join(lines).rstrip() + "\n"


def simulate(
    original: WorldState, client: DecisionClient, provider: str, turns: int = 4
) -> tuple[WorldState, Episode]:
    """Generate a candidate episode; leave the committed input untouched."""
    if turns < 1:
        raise ValueError("turns must be positive")
    work = deepcopy(original)
    events: list[Event] = []
    rejected: list[str] = []
    for index in range(turns):
        actor = ("joey", "chandler")[index % 2]
        action = client.choose(actor, view_for(work, actor, events))
        if not isinstance(action, Action):
            raise TypeError("LLM client must return a validated Action")
        try:
            event = resolve_action(work, actor, action)
        except ActionRejected as exc:
            rejected.append(f"{actor}: {exc}")
            continue
        if event:
            events.append(event)
            remember(work, event)
    title, script = format_episode(original.episode_no + 1, events)
    episode = Episode(
        number=original.episode_no + 1, title=title, script=script,
        events=events, world_version_from=original.version,
        world_version_to=original.version + 1,
        provider=provider, rejected_actions=rejected
    )
    work.version += 1
    work.episode_no += 1
    return work, episode
