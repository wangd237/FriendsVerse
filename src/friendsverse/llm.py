"""OpenAI-compatible character decisions and an explicit deterministic fake."""

from __future__ import annotations

import json
import os

from pydantic import ValidationError

from friendsverse.models import Action


class FakeClient:
    """Fixed dialogue for T0 smoke tests. This is NOT an autonomous LLM."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def choose(self, actor: str, perception: dict) -> Action:
        self.calls.append(perception)
        if actor == "joey":
            line = ("Chandler，我明天有试镜，能帮我排练吗？"
                    if perception["episode"] == 1
                    else "你还记得我上次提到的试镜吗？")
        else:
            line = ("当然，我希望台词没有我的报告长。"
                    if perception["episode"] == 1
                    else "记得，今天可以练一遍。")
        return Action(type="speak", text=line)


def parse_action(raw: str) -> Action:
    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:-1]).strip()
    return Action.model_validate(json.loads(text))


class OpenAIClient:
    """One JSON action per call via OpenAI-compatible chat completions."""

    def __init__(self) -> None:
        key = os.getenv("LLM_API_KEY")
        model = os.getenv("LLM_MODEL_ID")
        if not key or not model:
            raise RuntimeError("live mode requires LLM_API_KEY and LLM_MODEL_ID")
        from openai import OpenAI
        self.client = OpenAI(
            api_key=key, base_url=os.getenv("LLM_BASE_URL") or None,
            timeout=45.0, max_retries=1
        )
        self.model = model
        self.total_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def choose(self, actor: str, perception: dict) -> Action:
        system = (
            f"You are {actor} in a private fan-made, lighthearted character simulation. "
            f"{perception['persona']} "
            "Play ONLY your own character, without inventing the other speaker's lines. "
            "Use natural conversational Chinese with distinct personality. "
            "Do not quote existing TV dialogue. Only use supplied perception; "
            "you cannot know another person's private thoughts. "
            "An intention is not an executed action. "
            "Return exactly one JSON action, no markdown. Examples: "
            '{"type":"speak","text":"嗨"} or {"type":"wait"} or '
            '{"type":"move_to","target":"hallway"} or '
            '{"type":"do","target":"help_rehearse"}. '
            "You may initiate a natural conversation, decline or stay quiet."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(perception, ensure_ascii=False)},
        ]
        # Not all compatible providers support response_format=json_object.
        # We validate locally and allow ONE JSON repair request.
        for attempt in range(2):
            response = self.client.chat.completions.create(
                model=self.model, messages=messages, temperature=0.7
            )
            self.total_calls += 1
            if response.usage:
                self.input_tokens += response.usage.prompt_tokens or 0
                self.output_tokens += response.usage.completion_tokens or 0
            raw = response.choices[0].message.content or ""
            try:
                return parse_action(raw)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                if attempt:
                    raise RuntimeError(f"invalid LLM action twice: {exc}") from exc
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": (
                    "Return exactly one valid JSON object for the declared action schema. "
                    "No markdown or extra text."
                )})
        raise RuntimeError("unreachable")
