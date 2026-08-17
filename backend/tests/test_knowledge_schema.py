import uuid

import pytest
from pydantic import ValidationError

from app.schemas.knowledge import KnowledgeCategoryCreate
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate


def test_category_create_supports_nested_parent() -> None:
    parent_id = uuid.uuid4()
    payload = KnowledgeCategoryCreate(
        name="  宋代  ", parent_id=parent_id, domain="history"
    )

    assert payload.name == "宋代"
    assert payload.parent_id == parent_id
    assert payload.domain == "history"


def test_scenario_create_normalizes_knowledge_metadata() -> None:
    category_id = uuid.uuid4()
    payload = ScenarioCreate(
        title="王安石变法",
        description="讨论变法的背景、措施与影响。",
        language="zh",
        difficulty="intermediate",
        domain="history",
        scenario_mode="guided_discussion",
        estimated_minutes=20,
        tags=[" 政策 ", "宋代", "政策"],
        category_ids=[category_id],
    )

    assert payload.tags == ["政策", "宋代"]
    assert payload.category_ids == [category_id]


def test_scenario_create_rejects_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        ScenarioCreate(
            title="测试",
            description="测试说明",
            language="zh",
            difficulty="beginner",
            scenario_mode="unknown",
        )


def test_scenario_update_allows_clearing_estimated_minutes() -> None:
    payload = ScenarioUpdate(estimated_minutes=None)

    assert payload.estimated_minutes is None
