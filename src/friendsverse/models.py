"""Validated boundaries for T0/T1. No data from other characters' private memory."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, model_validator

CHARACTERS = ("joey", "chandler")
LOCATIONS = ("apt_chandler_joey", "hallway", "central_perk")


class Action(BaseModel):
    type: Literal["speak", "wait", "move_to", "do"]
    text: str | None = None
    target: str | None = None
    recipient: str | None = None

    @model_validator(mode="after")
    def valid_arguments(self) -> "Action":
        if self.type == "speak" and not (self.text or "").strip():
            raise ValueError("speak requires text")
        if self.type == "move_to" and not self.target:
            raise ValueError("move_to requires a destination")
        if self.type == "do" and self.target not in (
            "help_rehearse", "help_friend", "apologize", "share_food",
            "promise_help", "fulfill_promise"
        ):
            raise ValueError("unknown social action")
        if self.type == "do" and self.target != "help_rehearse" and not self.recipient:
            raise ValueError("social action requires recipient")
        return self


class Event(BaseModel):
    id: str
    actor: str
    type: Literal["speak", "move_to", "do", "opportunity"]
    text: str
    location: str
    witnesses: list[str]
    period: str = "evening"


class MemoryEntry(BaseModel):
    event_id: str
    actor: str
    text: str


class WorldState(BaseModel):
    universe_id: str = "default"
    version: int = 0
    episode_no: int = 0
    mode: Literal["duo", "ensemble"] = "duo"
    virtual_day: int = 0
    relationships: dict[str, dict[str, dict[str, int]]] = Field(default_factory=dict)
    commitments: list[dict] = Field(default_factory=list)
    positions: dict[str, str] = Field(default_factory=lambda: {
        name: "apt_chandler_joey" for name in CHARACTERS
    })
    memories: dict[str, list[MemoryEntry]] = Field(default_factory=lambda: {
        name: [] for name in CHARACTERS
    })


class Episode(BaseModel):
    number: int
    title: str
    script: str
    events: list[Event]
    world_version_from: int
    world_version_to: int
    provider: str
    rejected_actions: list[str] = Field(default_factory=list)
    # Prior committed event IDs actually made visible to each character.
    prior_memory_ids: dict[str, list[str]] = Field(default_factory=dict)
    relationship_changes: list[dict] = Field(default_factory=list)
    virtual_day: int = 0

