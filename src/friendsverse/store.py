"""SQLite-backed world snapshots and atomic episode publication."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from friendsverse.models import Episode, WorldState


class ConflictError(RuntimeError):
    pass


class Store:
    def __init__(self, path: str | Path) -> None:
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS universes (
                universe_id TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                snapshot TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episodes (
                universe_id TEXT NOT NULL,
                number INTEGER NOT NULL,
                payload TEXT NOT NULL,
                PRIMARY KEY (universe_id, number),
                FOREIGN KEY (universe_id) REFERENCES universes(universe_id)
            );
        """)

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_args) -> None:
        self.conn.close()

    def initialize(self, universe_id: str = "default", mode: str = "duo") -> WorldState:
        if mode == "ensemble":
            from friendsverse.ensemble import new_ensemble
            state = new_ensemble(universe_id)
        elif mode == "duo":
            state = WorldState(universe_id=universe_id)
        else:
            raise ValueError("mode must be duo or ensemble")
        with self.conn:
            self.conn.execute(
                "INSERT INTO universes(universe_id,version,snapshot) VALUES (?,?,?)",
                (universe_id, state.version, state.model_dump_json())
            )
        return state

    def load(self, universe_id: str = "default") -> WorldState:
        row = self.conn.execute(
            "SELECT snapshot FROM universes WHERE universe_id=?",
            (universe_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"Universe {universe_id!r} missing; run init first")
        return WorldState.model_validate_json(row[0])

    def commit(self, before: WorldState, after: WorldState, episode: Episode) -> None:
        if before.universe_id != after.universe_id:
            raise ValueError("Universe IDs must match")
        if after.version != before.version + 1:
            raise ValueError("Invalid version progression")
        if episode.number != before.episode_no + 1 or after.episode_no != episode.number:
            raise ValueError("Invalid episode progression")
        if episode.world_version_from != before.version or episode.world_version_to != after.version:
            raise ValueError("Invalid episode snapshot binding")
        try:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute(
                "SELECT version FROM universes WHERE universe_id=?",
                (before.universe_id,)
            ).fetchone()
            if row is None or row[0] != before.version:
                raise ConflictError("Stale universe version; reload and retry")
            self.conn.execute(
                "INSERT INTO episodes(universe_id,number,payload) VALUES (?,?,?)",
                (before.universe_id, episode.number, episode.model_dump_json())
            )
            changed = self.conn.execute(
                "UPDATE universes SET version=?,snapshot=? WHERE universe_id=? AND version=?",
                (after.version, after.model_dump_json(), before.universe_id, before.version)
            )
            if changed.rowcount != 1:
                raise ConflictError("World snapshot update conflict")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def episodes(self, universe_id: str = "default") -> list[Episode]:
        rows = self.conn.execute(
            "SELECT payload FROM episodes WHERE universe_id=? ORDER BY number",
            (universe_id,)
        ).fetchall()
        return [Episode.model_validate_json(row[0]) for row in rows]
