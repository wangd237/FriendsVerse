"""Manual episode progression and explicit seven-day experiment driver."""

from __future__ import annotations

import argparse
import sys

from friendsverse.llm import FakeClient, OpenAIClient
from friendsverse.runtime import simulate
from friendsverse.store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="FriendsVerse Story Prototype T0–T3")
    parser.add_argument("command", choices=["init", "next", "inspect", "season", "report"])
    parser.add_argument("--db", default="friendsverse.db")
    parser.add_argument("--universe", default="default")
    parser.add_argument("--provider", choices=["live", "fake"], default="live")
    parser.add_argument("--mode", choices=["duo", "ensemble"], default="duo", help="init only")
    parser.add_argument("--days", type=int, default=7, help="season: explicit number of days to run")
    parser.add_argument("--actors-per-period", type=int, default=None,
                        help="ensemble: 1–6 active actors per period; season defaults to 3")
    parser.add_argument("--out", default="season-review", help="review output directory")
    args = parser.parse_args()
    try:
        with Store(args.db) as store:
            if args.command == "init":
                state = store.initialize(args.universe, mode=args.mode)
                print(f"Created universe={state.universe_id} mode={state.mode} version={state.version}")
                return
            if args.command == "inspect":
                state = store.load(args.universe)
                print(f"Universe={state.universe_id}, mode={state.mode}, day={state.virtual_day}, "
                      f"version={state.version}, episodes={state.episode_no}")
                for episode in store.episodes(args.universe):
                    print(f" EP{episode.number:02d} events={len(episode.events)} [{episode.provider}]")
                return
            if args.command == "report":
                from friendsverse.review import export_review
                state = store.load(args.universe)
                review = export_review(store.episodes(args.universe), state, args.out)
                print(f"Exported {review['published_episodes']} episodes to {args.out}, "
                      f"engineering issues={len(review['engineering_issues'])}")
                return

            before = store.load(args.universe)
            if args.command == "season" and (before.mode != "ensemble" or not 1 <= args.days <= 7):
                raise ValueError("season requires an ensemble universe and --days from 1 to 7")
            if args.command == "season" and before.episode_no + args.days > 7:
                raise ValueError("season would exceed seven episodes; reduce --days")
            if args.actors_per_period is not None and not 1 <= args.actors_per_period <= 6:
                raise ValueError("--actors-per-period must be from 1 to 6")

            if before.mode == "ensemble":
                from friendsverse.ensemble import EnsembleFakeClient, simulate_day
                client = EnsembleFakeClient() if args.provider == "fake" else OpenAIClient()
            else:
                client = FakeClient() if args.provider == "fake" else OpenAIClient()
            steps = args.days if args.command == "season" else 1
            # 'season' is an explicitly started evaluation batch. Ordinary 'next'
            # continues to publish exactly ONE episode on each invocation.
            for _ in range(steps):
                before = store.load(args.universe)
                if before.mode == "ensemble":
                    selected = (3 if args.command == "season" else 6) if args.actors_per_period is None else args.actors_per_period
                    after, episode = simulate_day(before, client, args.provider,
                                                  actors_per_period=selected)
                else:
                    after, episode = simulate(before, client, args.provider)
                store.commit(before, after, episode)
                print(f"Committed EP{episode.number:02d} day={episode.virtual_day} "
                      f"events={len(episode.events)} dialogue={sum(e.type == 'speak' for e in episode.events)} "
                      f"relation_changes={len(episode.relationship_changes)} "
                      f"rejected={len(episode.rejected_actions)}", flush=True)
                if args.command == "next":
                    if args.provider == "fake":
                        print("FAKE DEMO — deterministic actions, not LLM evidence")
                    print(episode.script)
            if args.command == "season":
                from friendsverse.review import export_review
                review = export_review(store.episodes(args.universe),
                                       store.load(args.universe), args.out)
                print(f"Seven-day evaluation export: {args.out}, "
                      f"committed={review['published_episodes']}, "
                      f"engineering issues={len(review['engineering_issues'])}")
                if review["engineering_issues"]:
                    raise RuntimeError("Season engineering consistency check failed; see report")
            if args.provider == "live":
                print(f"LLM calls={client.total_calls}, "
                      f"input tokens={client.input_tokens}, output tokens={client.output_tokens}")
    except (ValueError, LookupError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
