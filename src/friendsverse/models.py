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

    @model_validator(mode="after")
    def valid_arguments(self) -> "Action":
        if self.type == "speak" and not (self.text or "").strip():
            raise ValueError("speak requires text")
        if self.type == "move_to" and not self.target:
            raise ValueError("move_to requires a destination")
        if self.type == "do" and self.target != "help_rehearse":
            raise ValueError("only help_rehearse is supported")
        return self


class Event(BaseModel):
    id: str
    actor: str
    type: Literal["speak", "move_to", "do"]
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
