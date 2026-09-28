"""Synthetic scenarios test multi-turn integration, not LLM accuracy."""

import json
from pathlib import Path

import pytest

from state_lab.router import SupportRouter
from state_lab.service import SupportService
from state_lab.store import MemoryStore

CASES = [json.loads(line) for line in (Path(__file__).parent / "conversation_cases.jsonl")
         .read_text(encoding="utf-8").splitlines() if line.strip()]


class ScriptedGenerator:
    def __init__(self, turns):
        self.outputs = iter(turn["proposal"] for turn in turns)

    def generate(self, *, instructions, user_input):
        output = next(self.outputs)
        return output if isinstance(output, str) else json.dumps(output)


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_synthetic_conversation(case):
    assert len(CASES) >= 25
    service = SupportService(MemoryStore(), SupportRouter(ScriptedGenerator(case["turns"])))
    sid = service.start(owner_id="synthetic-user")["session_id"]
    for turn in case["turns"]:
        result = service.turn(owner_id="synthetic-user", session_id=sid,
                              message=turn["message"], approved_policy=case.get("approved_policy", ""))
        assert result.status == turn["expected_status"]
        assert result.route == turn["expected_route"]
    state = service.review(owner_id="synthetic-user", session_id=sid)
    assert {k: fact["value"] for k, fact in state["current_facts"].items()} == case["expected_facts"]
    assert state["session_id"] == sid
