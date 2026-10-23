"""Mock only the transport: verifies live adapter's JSON validation and scoping."""

import json
from types import SimpleNamespace

from friendsverse.llm import OpenAIClient, parse_action
from friendsverse.models import Action


def test_parse_fenced_json():
    assert parse_action('''```json
{"type":"speak","text":"你好"}
```''') == Action(type="speak", text="你好")


def test_live_adapter_retries_invalid_json_once():
    answers = iter(["invalid-json", '{"type":"wait"}'])
    captured = []

    def create(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=next(answers)))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
        )

    # Use a mocked transport; does NOT claim a real external LLM was contacted.
    agent = OpenAIClient.__new__(OpenAIClient)
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    agent.model = "mocked-chat"
    agent.total_calls = 0
    agent.input_tokens = 0
    agent.output_tokens = 0

    action = agent.choose("joey", {
        "persona": "loyal roommate", "actor": "joey",
        "own_memory": [{"event_id": "e1", "text": "Old topic"}],
        "present": ["chandler", "joey"],
    })
    assert action == Action(type="wait")
    assert agent.total_calls == 2
    assert agent.input_tokens == 20 and agent.output_tokens == 6
    assert len(captured) == 2
    user_context = json.loads(captured[0]["messages"][1]["content"])
    assert user_context["own_memory"][0]["event_id"] == "e1"
