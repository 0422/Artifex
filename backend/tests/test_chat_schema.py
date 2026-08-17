import uuid

import pytest
from pydantic import ValidationError

from app.schemas.chat import (
    ChatCorrection,
    ChatTurnOutput,
    StartSessionMessage,
    TextMessage,
    chat_command_adapter,
)


def test_chat_command_adapter_dispatches_by_type() -> None:
    scenario_id = uuid.uuid4()

    command = chat_command_adapter.validate_python(
        {
            "type": "start_session",
            "scenario_id": str(scenario_id),
            "difficulty": "N3",
        }
    )

    assert isinstance(command, StartSessionMessage)
    assert command.scenario_id == scenario_id


def test_text_message_strips_content() -> None:
    command = chat_command_adapter.validate_python(
        {"type": "text_message", "content": "  こんにちは  "}
    )

    assert isinstance(command, TextMessage)
    assert command.content == "こんにちは"


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "unknown"},
        {"type": "text_message", "content": "   "},
        {"type": "start_session", "scenario_id": "not-a-uuid"},
    ],
)
def test_chat_command_adapter_rejects_invalid_messages(payload: dict) -> None:
    with pytest.raises(ValidationError):
        chat_command_adapter.validate_python(payload)


def test_chat_turn_output_validates_correction() -> None:
    output = ChatTurnOutput.model_validate(
        {
            "reply": "もう一度言ってみてください。",
            "correction": {
                "original": "水を一つください",
                "corrected": "水を一杯ください",
                "severity": "minor",
                "explanation": "饮料使用量词「杯」。",
            },
        }
    )

    assert isinstance(output.correction, ChatCorrection)


def test_chat_correction_rejects_unchanged_text() -> None:
    with pytest.raises(ValidationError):
        ChatCorrection(
            original="I would like water.",
            corrected="I would like water.",
            severity="minor",
            explanation="无需修改。",
        )
