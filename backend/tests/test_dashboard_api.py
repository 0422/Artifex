import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.dashboard import router
from app.core.database import get_db
from app.schemas.dashboard import DashboardOverview, DashboardSessionPage


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


def test_overview_endpoint_returns_service_result(client: TestClient) -> None:
    overview = DashboardOverview(
        total_conversations=0,
        total_duration_seconds=0,
        scored_conversations=0,
        average_performance_score=None,
        scenario_distribution=[],
        frequent_weak_points=[],
    )
    with patch(
        "app.api.v1.dashboard.dashboard_service.get_overview",
        AsyncMock(return_value=overview),
    ):
        response = client.get("/api/v1/dashboard/overview")

    assert response.status_code == 200
    assert response.json()["total_conversations"] == 0


def test_sessions_endpoint_forwards_pagination(client: TestClient) -> None:
    page = DashboardSessionPage(items=[], total=0, page=2, page_size=5)
    with patch(
        "app.api.v1.dashboard.dashboard_service.get_sessions",
        AsyncMock(return_value=page),
    ) as get_sessions:
        response = client.get("/api/v1/dashboard/sessions?page=2&page_size=5")

    assert response.status_code == 200
    assert response.json()["page"] == 2
    assert get_sessions.await_args.args[2:] == (2, 5)


def test_session_detail_hides_unknown_or_unowned_session(client: TestClient) -> None:
    with patch(
        "app.api.v1.dashboard.dashboard_service.get_session_detail",
        AsyncMock(return_value=None),
    ):
        response = client.get(f"/api/v1/dashboard/sessions/{uuid.uuid4()}")

    assert response.status_code == 404
