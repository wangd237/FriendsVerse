"""CLI entry for manually progressing one candidate episode."""

from __future__ import annotations

import argparse
import sys

from friendsverse.llm import FakeClient, OpenAIClient
from friendsverse.runtime import simulate
from friendsverse.store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="FriendsVerse Story Prototype T0–T2")
    parser.add_argument("command", choices=["init", "next", "inspect"])
    parser.add_argument("--db", default="friendsverse.db")
    parser.add_argument("--universe", default="default")
    parser.add_argument("--provider", choices=["live", "fake"], default="live")
    parser.add_argument("--mode", choices=["duo", "ensemble"], default="duo", help="init only: ensemble creates all six friends")
    args = parser.parse_args()
    try:
        with Store(args.db) as store:
            if args.command == "init":
                state = store.initialize(args.universe, mode=args.mode)
                print(f"Created universe={state.universe_id} version={state.version}")
                return
            if args.command == "inspect":
                state = store.load(args.universe)
                print(f"Universe={state.universe_id}, mode={state.mode}, day={state.virtual_day}, version={state.version}, episodes={state.episode_no}")
                for episode in store.episodes(args.universe):
                    print(f" EP{episode.number:02d} events={len(episode.events)} [{episode.provider}]")
                return

            before = store.load(args.universe)
            if before.mode == "ensemble":
                from friendsverse.ensemble import EnsembleFakeClient, simulate_day
                client = EnsembleFakeClient() if args.provider == "fake" else OpenAIClient()
                after, episode = simulate_day(before, client, args.provider)
            else:
                client = FakeClient() if args.provider == "fake" else OpenAIClient()
                after, episode = simulate(before, client, args.provider)
            store.commit(before, after, episode)
            if args.provider == "fake":
                print("FAKE DEMO — deterministic dialogue, not real LLM evidence\n")
            print(episode.script)
            print(f"Committed EP{episode.number:02d}; events={len(episode.events)}; rejected={len(episode.rejected_actions)}")
            if args.provider == "live":
                print(f"Calls={client.total_calls}, input tokens={client.input_tokens}, output tokens={client.output_tokens}")
    except (ValueError, LookupError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
