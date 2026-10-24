"""Evidence-first seven-episode review: engineering checks are not story-quality ratings."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from friendsverse.models import Episode, WorldState

PERIOD_ORDER = {"morning": 0, "afternoon": 1, "evening": 2}


def analyze(episodes: list[Episode], state: WorldState) -> dict:
    """Summarize traceable facts from committed episodes, without an LLM judge."""
    seen: dict[str, set[str]] = {}
    arcs: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    rows = []
    all_speakers: set[str] = set()
    problems: list[str] = []
    expected_number = 1
    expected_world_version = 0
    for ep in episodes:
        if ep.number != expected_number or ep.world_version_from != expected_world_version:
            problems.append(f"EP{ep.number}: episode number or version gap")
        if ep.world_version_to != ep.world_version_from + 1:
            problems.append(f"EP{ep.number}: invalid snapshot progression")
        if state.mode == "ensemble" and ep.virtual_day != ep.number:
            problems.append(f"EP{ep.number}: virtual day does not match episode number")
        expected_number = ep.number + 1
        expected_world_version = ep.world_version_to

        own_events = {ev.id: ev for ev in ep.events}
        speakers = sorted({e.actor for e in ep.events if e.type == "speak"})
        all_speakers.update(speakers)
        for action in ep.relationship_changes:
            ids = action.get("source_event_ids", [])
            if not ids or not all(eid in own_events for eid in ids):
                problems.append(f"EP{ep.number}: relationship update missing executed evidence")
            key = (action.get("from_id", ""), action.get("to_id", ""),
                   action.get("dimension", ""))
            arcs[key].add(ep.number)

        for actor, references in ep.prior_memory_ids.items():
            for event_id in references:
                if event_id not in seen:
                    problems.append(f"EP{ep.number}: unknown prior memory ID for {actor}")
                elif actor not in seen[event_id]:
                    problems.append(f"EP{ep.number}: {actor} received an event not witnessed")

        period_ordinals = [PERIOD_ORDER.get(e.period, -1) for e in ep.events]
        if period_ordinals != sorted(period_ordinals):
            problems.append(f"EP{ep.number}: event periods out of order")
        for event in ep.events:
            if event.id in seen or not event.id:
                problems.append(f"EP{ep.number}: missing or duplicate event ID")
            seen[event.id] = set(event.witnesses)
        rows.append({
            "episode": ep.number,
            "day": ep.virtual_day,
            "provider": ep.provider,
            "events": len(ep.events),
            "dialogue_events": sum(e.type == "speak" for e in ep.events),
            "action_events": sum(e.type == "do" for e in ep.events),
            "characters_speaking": speakers,
            "relationship_changes": len(ep.relationship_changes),
            "rejected_actions": len(ep.rejected_actions),
            "received_prior_memories": {a: len(ids) for a, ids in ep.prior_memory_ids.items()},
        })
    if episodes and state.version != episodes[-1].world_version_to:
        problems.append("Final snapshot version does not match last episode")
    if episodes and state.episode_no != episodes[-1].number:
        problems.append("Final snapshot episode number mismatch")

    evidence_arcs = [
        {"from": pair[0], "to": pair[1], "dimension": pair[2],
         "episode_numbers": sorted(days)}
        for pair, days in sorted(arcs.items())
        if len(days) >= 3
    ]
    return {
        "universe_id": state.universe_id,
        "mode": state.mode,
        "published_episodes": len(episodes),
        "final_day": state.virtual_day,
        "unique_speakers": sorted(all_speakers),
        "total_events": sum(row["events"] for row in rows),
        "total_dialogue_events": sum(row["dialogue_events"] for row in rows),
        "total_relationship_changes": sum(row["relationship_changes"] for row in rows),
        "total_rejected_actions": sum(row["rejected_actions"] for row in rows),
        "evidence_based_multiepisode_relationship_patterns": evidence_arcs,
        "engineering_issues": problems,
        "engineering_checks_passed": not problems,
        "episodes": rows,
        "important_limitations": [
            "A relation changing on three days does not prove a coherent three-episode story arc.",
            "Dialogue length and character coverage do not prove humor, character identity or viewer retention.",
            "Fake provider output is scripted and cannot establish autonomous behavior.",
        ],
    }


def export_review(episodes: list[Episode], state: WorldState, output_dir: str | Path) -> dict:
    """Export JSON provenance plus full unmodified scripts for human story review."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    report = analyze(episodes, state)
    (path / "season-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (path / "episode-evidence.json").write_text(
        json.dumps(
            [ep.model_dump(mode="json") for ep in episodes],
            ensure_ascii=False, indent=2
        ), encoding="utf-8"
    )
    lines = [
        "# FriendsVerse Story Prototype — Season Review",
        "",
        f"Universe: {state.universe_id} | Episodes: {len(episodes)} | Provider: "
        + ", ".join(sorted({ep.provider for ep in episodes})),
        "",
        "## Engineering observations",
        "",
        f"- Total grounded events: {report['total_events']}",
        f"- Actual dialogue events: {report['total_dialogue_events']}",
        f"- Relationship updates: {report['total_relationship_changes']}",
        f"- Rejected actions: {report['total_rejected_actions']}",
        f"- Distinct characters who spoke: {', '.join(report['unique_speakers'])}",
        f"- Evidence check: {'PASS' if report['engineering_checks_passed'] else 'FAIL'}",
        f"- Relations with changes in 3+ episodes: "
        f"{len(report['evidence_based_multiepisode_relationship_patterns'])}",
        "",
        "**The preceding counts do not establish compelling storytelling.**",
        "",
        "## Human review checklist (not automatically passed)",
        "",
        "- [ ] Can viewers distinguish personalities without name labels?",
        "- [ ] Are the jokes and everyday situations entertaining rather than repetitive?",
        "- [ ] Do prior commitments and misunderstandings causally affect later choices?",
        "- [ ] Is at least one relationship narrative genuinely developed over 3+ episodes?",
        "- [ ] Do readers want to watch the next episode?",
        "",
        "## Generated episodes — raw, unedited and event-grounded",
        "",
    ]
    for ep in episodes:
        lines.extend([ep.script, "", "---", ""])
    (path / "season-scripts.md").write_text("\n".join(lines), encoding="utf-8")
    return report
