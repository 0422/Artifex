from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.ai import llm


@pytest.mark.asyncio
async def test_generate_chat_turn_sends_history_and_latest_message() -> None:
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content='{"reply":"Hello!","correction":null}')
            )
        ]
    )
    create = AsyncMock(return_value=response)

    with patch.object(llm._client.chat.completions, "create", create):
        result = await llm.generate_chat_turn(
            "system prompt",
            [{"role": "assistant", "content": "Welcome."}],
            "Hello.",
        )

    assert result == {"reply": "Hello!", "correction": None}
    messages = create.await_args.kwargs["messages"]
    assert messages == [
        {"role": "system", "content": "system prompt"},
        {"role": "assistant", "content": "Welcome."},
        {"role": "user", "content": "Hello."},
    ]


@pytest.mark.asyncio
async def test_generate_session_report_sends_structured_input() -> None:
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content='{"summary":"Good","weak_points":[],"suggestions":["Practice"],"performance_score":90,"no_prominent_issues":true}'
                )
            )
        ]
    )
    create = AsyncMock(return_value=response)

    with patch.object(llm._client.chat.completions, "create", create):
        result = await llm.generate_session_report({"scenario": "coffee shop"})

    assert result["performance_score"] == 90
    assert (
        '"scenario": "coffee shop"'
        in create.await_args.kwargs["messages"][1]["content"]
    )
