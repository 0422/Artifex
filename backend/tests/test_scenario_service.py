import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ScenarioDifficulty, ScenarioLanguage
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate
from app.services import scenario_service


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_create_seed_scenarios_adds_five_cards_without_committing(
    db: MagicMock,
) -> None:
    user_id = uuid.uuid4()

    scenarios = await scenario_service.create_seed_scenarios(db, user_id)

    assert len(scenarios) == 5
    assert all(scenario.user_id == user_id for scenario in scenarios)
    assert {scenario.title for scenario in scenarios} == {
        "餐厅点餐",
        "便利店购物",
        "问路",
        "自我介绍",
        "商务会议",
    }
    db.add_all.assert_called_once_with(scenarios)
    db.flush.assert_awaited_once()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_create_scenario_commits_and_refreshes(db: MagicMock) -> None:
    user_id = uuid.uuid4()
    payload = ScenarioCreate(
        title="面试自我介绍",
        description="介绍工作经验并回答追问。",
        language=ScenarioLanguage.JA,
        difficulty=ScenarioDifficulty.N3,
    )

    scenario = await scenario_service.create_scenario(db, user_id, payload)

    assert scenario.user_id == user_id
    assert scenario.title == payload.title
    db.add.assert_called_once_with(scenario)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(scenario)


@pytest.mark.asyncio
async def test_update_scenario_only_changes_supplied_fields(db: MagicMock) -> None:
    scenario = SimpleNamespace(title="旧标题", description="原描述", is_active=True)

    result = await scenario_service.update_scenario(
        db, scenario, ScenarioUpdate(title="新标题")
    )

    assert result.title == "新标题"
    assert result.description == "原描述"
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(scenario)


@pytest.mark.asyncio
async def test_deactivate_scenario_is_idempotent(db: MagicMock) -> None:
    scenario = SimpleNamespace(is_active=True)

    await scenario_service.deactivate_scenario(db, scenario)
    await scenario_service.deactivate_scenario(db, scenario)

    assert scenario.is_active is False
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_scenario_returns_none_when_query_finds_no_owned_card(
    db: MagicMock,
) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    scenario = await scenario_service.get_scenario(db, uuid.uuid4(), uuid.uuid4())

    assert scenario is None
