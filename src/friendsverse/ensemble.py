"""T2 vertical slice: six friends, three periods, local agency, grounded relations.

This deliberately uses the T1 DecisionClient, SQLite snapshot and episode schema.
There is no additional planner agent, queue, vector DB or autonomous scriptwriter.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Protocol
from uuid import uuid4

from friendsverse.models import Action, Episode, Event, MemoryEntry, WorldState

ACTORS = ("monica", "rachel", "phoebe", "ross", "chandler", "joey")
PERIODS = ("morning", "afternoon", "evening")
PLACES = (
    "apt_monica_rachel",
    "apt_chandler_joey",
    "central_perk",
    "hallway",
    "offstage_work",
)
LABELS = {
    "apt_monica_rachel": "Monica & Rachel's Apartment",
    "apt_chandler_joey": "Chandler & Joey's Apartment",
    "central_perk": "Central Perk",
    "hallway": "Hallway",
    "offstage_work": "Work",
}
PERSONAS = {
    "monica": "Monica: organized, caring, competitive chef; wants to look after friends but can over-control details.",
    "rachel": "Rachel: warm, fashion-minded, growing independent in her career; dislikes being treated as incapable.",
    "phoebe": "Phoebe: compassionate, individualistic musician with surprising ideas; values freedom and honesty.",
    "ross": "Ross: thoughtful and academic paleontologist, often over-explains; wants to be understood.",
    "chandler": "Chandler: loyal, quick-witted office worker, uses irony to cover awkwardness; cares about his friends.",
    "joey": "Joey: direct, generous aspiring actor; loyal to friends and eager to improve his auditions.",
}
GOALS = {
    "monica": "balance cooking plans and friendships",
    "rachel": "make progress at work while staying connected",
    "phoebe": "make music and care about friends",
    "ross": "balance research and friendship",
    "chandler": "finish office tasks and be a reliable friend",
    "joey": "practice acting and find auditions",
}
# Only a small objective opportunity, never a predetermined character response.
OPPORTUNITIES = (
    ("joey", "You received a notice for an upcoming acting audition."),
    ("monica", "A friend has asked about an informal dinner this week."),
    ("rachel", "A new fashion-related opportunity was posted."),
    ("phoebe", "There is an opportunity to play a short café music set."),
    ("ross", "You encountered a question related to your research."),
    ("chandler", "An office deadline is approaching."),
    ("joey", "There is a reminder about your ongoing audition preparation."),
)


def new_ensemble(universe_id: str = "default") -> WorldState:
    positions = {
        "monica": "apt_monica_rachel",
        "rachel": "apt_monica_rachel",
        "chandler": "apt_chandler_joey",
        "joey": "apt_chandler_joey",
        "ross": "central_perk",
        "phoebe": "central_perk",
    }
    # Directed relationships. Family/roommate anchors influence only starting values.
    special = {
        frozenset(("monica", "rachel")),
        frozenset(("chandler", "joey")),
        frozenset(("monica", "ross")),
    }
    relationships = {
        a: {
            b: {
                "closeness": 76 if frozenset((a, b)) in special else 56,
                "trust": 74 if frozenset((a, b)) in special else 59,
                "tension": 5,
            }
            for b in ACTORS if b != a
        }
        for a in ACTORS
    }
    return WorldState(
        universe_id=universe_id, mode="ensemble",
        positions=positions, memories={a: [] for a in ACTORS},
        relationships=relationships,
    )


class DecisionClient(Protocol):
    def choose(self, actor: str, perception: dict) -> Action: ...


def perceive(state: WorldState, actor: str, period: str, events: list[Event]) -> dict:
    place = state.positions[actor]
    local = [a for a in ACTORS if state.positions[a] == place]
    return {
        "actor": actor,
        "persona": PERSONAS[actor],
        "goal": GOALS[actor],
        "virtual_day": state.virtual_day + 1,
        "period": period,
        "location": place,
        "present": local,
        "own_memory": [m.model_dump() for m in state.memories[actor][-35:]],
        "own_relationships": state.relationships.get(actor, {}),
        "my_commitments": [v for v in state.commitments if actor in (v["actor"], v["recipient"])],
        "recent_scene": [
            {"speaker": e.actor, "text": e.text, "type": e.type}
            for e in events if e.period == period and actor in e.witnesses
        ][-10:],
        "available_actions": [
            "speak: text (only when another character is present)",
            "wait",
            "move_to: target one of " + ", ".join(PLACES),
            "do: target one of help_friend, help_rehearse, apologize, share_food, promise_help, fulfill_promise; recipient is a present character",
        ],
    }


def _event(actor: str, event_type: str, text: str, location: str, period: str,
           witnesses: list[str]) -> Event:
    return Event(
        id=str(uuid4()), actor=actor, type=event_type, text=text,
        location=location, period=period, witnesses=witnesses,
    )


def _remember(state: WorldState, event: Event) -> None:
    for witness in event.witnesses:
        if witness in state.memories:
            state.memories[witness].append(
                MemoryEntry(event_id=event.id, actor=event.actor, text=event.text)
            )


def execute(
    state: WorldState, actor: str, action: Action, period: str,
    changes: list[dict],
) -> Event | None:
    if actor not in ACTORS:
        raise ValueError("unknown character")
    here = state.positions[actor]
    witnesses = [a for a in ACTORS if state.positions[a] == here]
    if action.type == "wait":
        return None
    if action.type == "move_to":
        if action.target not in PLACES or action.target == here:
            raise ValueError("invalid destination")
        state.positions[actor] = action.target
        return _event(actor, "move_to", f"{actor} went to {action.target}.", here, period, witnesses)
    if action.type == "speak":
        if len(witnesses) < 2:
            raise ValueError("no one is present to hear the dialogue")
        return _event(actor, "speak", action.text or "", here, period, witnesses)
    if action.type != "do":
        raise ValueError("invalid action")
    recipient = action.recipient
    if recipient not in witnesses or recipient == actor:
        raise ValueError("social action needs a distinct co-present recipient")
    kind = action.target
    if kind == "fulfill_promise":
        candidates = [c for c in state.commitments if c["actor"] == actor
                      and c["recipient"] == recipient and c["status"] == "open"]
        if not candidates:
            raise ValueError("no existing promise to fulfil")
        candidates[0]["status"] = "fulfilled"
    verbs = {
        "help_rehearse": "helped rehearse with",
        "help_friend": "helped",
        "apologize": "apologized to",
        "share_food": "shared food with",
        "promise_help": "promised to help",
        "fulfill_promise": "fulfilled a promise to",
    }
    if kind not in verbs:
        raise ValueError("unsupported social action")
    event = _event(actor, "do", f"{actor} {verbs[kind]} {recipient}.", here, period, witnesses)
    if kind == "promise_help":
        state.commitments.append({
            "id": event.id, "actor": actor, "recipient": recipient,
            "status": "open", "created_day": state.virtual_day + 1,
        })
    else:
        # A small, evidence-backed change in the RECIPIENT's opinion of the actor.
        delta = {
            "apologize": ("tension", -2),
            "help_rehearse": ("trust", 2),
            "help_friend": ("trust", 2),
            "share_food": ("closeness", 1),
            "fulfill_promise": ("trust", 3),
        }[kind]
        dimension, amount = delta
        rel = state.relationships[recipient][actor]
        before = rel[dimension]
        after = max(0, min(100, before + amount))
        rel[dimension] = after
        changes.append({
            "from_id": recipient, "to_id": actor, "dimension": dimension,
            "before": before, "after": after,
            "reason": kind, "source_event_ids": [event.id],
        })
    return event


def _format_episode(number: int, day: int, events: list[Event], changes: list[dict]) -> tuple[str, str]:
    title = f"EP{number:02d} — A Day with Friends"
    lines = [f"# {title}", "", f"*Virtual Day {day}*", ""]
    scene = 0
    current = None
    for event in events:
        scene_key = (event.period, event.location)
        if scene_key != current:
            scene += 1
            current = scene_key
            lines.append(f"## SCENE {scene:02d} · {LABELS.get(event.location, event.location)} · {event.period.title()}")
            lines.append("")
        if event.type == "speak":
            lines.append(f"**{event.actor.upper()}**: {event.text}")
        else:
            lines.append(f"*{event.text}*")
        lines.append("")
    if not events:
        lines.append("*A quiet day.*")
    if changes:
        lines.append("### Relationship updates (from executed events)")
        for change in changes:
            lines.append(
                f"- {change['from_id']} → {change['to_id']}: {change['dimension']} "
                f"{change['before']} → {change['after']} ({change['reason']}) "
                f"[event {change['source_event_ids'][0]}]"
            )
    return title, "\n".join(lines).rstrip() + "\n"


def simulate_day(
    original: WorldState, client: DecisionClient, provider: str,
    actors_per_period: int = 6,
) -> tuple[WorldState, Episode]:
    if original.mode != "ensemble":
        raise ValueError("not an ensemble universe")
    if not 1 <= actors_per_period <= len(ACTORS):
        raise ValueError("actors_per_period must be from 1 to 6")
    work = deepcopy(original)
    events: list[Event] = []
    changes: list[dict] = []
    rejected: list[str] = []
    actor_order = ACTORS[original.virtual_day % len(ACTORS):] + ACTORS[:original.virtual_day % len(ACTORS)]
    affected, stimulus = OPPORTUNITIES[original.virtual_day % len(OPPORTUNITIES)]
    stimulus_event = _event(
        affected, "opportunity", stimulus,
        work.positions[affected], "morning", [affected]
    )
    events.append(stimulus_event)
    _remember(work, stimulus_event)

    for period_index, period in enumerate(PERIODS):
        # T3 can activate fewer characters per period to control live model cost.
        # Rotate opportunities across characters; all six may act during each day.
        scheduled = [
            actor_order[(period_index * actors_per_period + i) % len(ACTORS)]
            for i in range(actors_per_period)
        ]
        for phase in ("intent", "encounter"):
            for actor in scheduled:
                if phase == "encounter" and sum(v == work.positions[actor] for v in work.positions.values()) < 2:
                    continue
                perception = perceive(work, actor, period, events)
                perception["phase"] = phase
                action = client.choose(actor, perception)
                if not isinstance(action, Action):
                    raise TypeError("character decision must be a validated Action")
                try:
                    event = execute(work, actor, action, period, changes)
                except ValueError as exc:
                    rejected.append(f"day {work.virtual_day + 1}, {period}, {actor}: {exc}")
                    continue
                if event:
                    events.append(event)
                    _remember(work, event)

    work.version += 1
    work.episode_no += 1
    work.virtual_day += 1
    title, script = _format_episode(work.episode_no, work.virtual_day, events, changes)
    episode = Episode(
        number=work.episode_no, title=title, script=script, events=events,
        world_version_from=original.version, world_version_to=work.version,
        provider=provider, rejected_actions=rejected,
        relationship_changes=changes, virtual_day=work.virtual_day,
        prior_memory_ids={
            actor: [m.event_id for m in original.memories[actor][-35:]]
            for actor in ACTORS
        },
    )
    # Every relationship event must cite a real event in this episode.
    evidence_ids = {e.id for e in events}
    if any(eid not in evidence_ids for change in changes for eid in change["source_event_ids"]):
        raise ValueError("orphaned relationship change")
    return work, episode


class EnsembleFakeClient:
    """Deterministic test fixture for the WHOLE T2 execution path, not story quality."""

    def __init__(self):
        self.calls: list[dict] = []

    def choose(self, actor: str, perception: dict) -> Action:
        self.calls.append(perception)
        period = perception["period"]
        present = perception["present"]
        day = perception["virtual_day"]
        if period == "afternoon" and perception["phase"] == "intent" and actor in ("rachel", "joey"):
            if perception["location"] != "central_perk":
                return Action(type="move_to", target="central_perk")
        if period == "morning" and actor == "chandler" and "joey" in present:
            if perception["phase"] == "encounter":
                return Action(type="do", target="help_rehearse", recipient="joey")
        if len(present) < 2:
            return Action(type="wait")
        return Action(
            type="speak", text=f"Day {day}, {period}: {actor} shares a thought with friends."
        )
