import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.scenarios import router
from app.core.database import get_db
from app.models.enums import ScenarioDifficulty, ScenarioLanguage


@pytest.fixture
def current_user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def client(current_user: SimpleNamespace) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: MagicMock()
    return TestClient(app)


def make_scenario(user_id: uuid.UUID, *, active: bool = True) -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        title="面试自我介绍",
        description="介绍工作经验并回答追问。",
        language=ScenarioLanguage.JA,
        difficulty=ScenarioDifficulty.N3,
        is_active=active,
        created_at=now,
        updated_at=now,
    )


def test_list_scenarios_forwards_inactive_filter(
    client: TestClient, current_user: SimpleNamespace
) -> None:
    scenario = make_scenario(current_user.id)
    with patch(
        "app.api.v1.scenarios.scenario_service.list_scenarios",
        AsyncMock(return_value=[scenario]),
    ) as list_scenarios:
        response = client.get("/api/v1/scenarios?include_inactive=true")

    assert response.status_code == 200
    assert response.json()[0]["title"] == scenario.title
    assert list_scenarios.await_args.args[1:] == (current_user.id, True)


def test_create_scenario_returns_created_card(
    client: TestClient, current_user: SimpleNamespace
) -> None:
    scenario = make_scenario(current_user.id)
    with patch(
        "app.api.v1.scenarios.scenario_service.create_scenario",
        AsyncMock(return_value=scenario),
    ):
        response = client.post(
            "/api/v1/scenarios",
            json={
                "title": scenario.title,
                "description": scenario.description,
                "language": "ja",
                "difficulty": "N3",
            },
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(scenario.id)


def test_update_unknown_or_unowned_scenario_returns_404(client: TestClient) -> None:
    with patch(
        "app.api.v1.scenarios.scenario_service.get_scenario",
        AsyncMock(return_value=None),
    ):
        response = client.put(
            f"/api/v1/scenarios/{uuid.uuid4()}",
            json={"title": "新标题"},
        )

    assert response.status_code == 404


def test_delete_scenario_soft_deactivates(
    client: TestClient, current_user: SimpleNamespace
) -> None:
    scenario = make_scenario(current_user.id)
    with (
        patch(
            "app.api.v1.scenarios.scenario_service.get_scenario",
            AsyncMock(return_value=scenario),
        ),
        patch(
            "app.api.v1.scenarios.scenario_service.deactivate_scenario",
            AsyncMock(),
        ) as deactivate,
    ):
        response = client.delete(f"/api/v1/scenarios/{scenario.id}")

    assert response.status_code == 204
    deactivate.assert_awaited_once_with(ANY, scenario)


def test_create_scenario_rejects_unsupported_language(client: TestClient) -> None:
    response = client.post(
        "/api/v1/scenarios",
        json={
            "title": "机场值机",
            "description": "办理登机手续。",
            "language": "fr",
            "difficulty": "A2",
        },
    )

    assert response.status_code == 422
