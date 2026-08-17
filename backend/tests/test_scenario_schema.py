import pytest
from pydantic import ValidationError

from app.models.enums import ScenarioDifficulty, ScenarioLanguage
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate


def test_scenario_create_strips_text() -> None:
    payload = ScenarioCreate(
        title="  面试自我介绍  ",
        description="  练习介绍工作经历。  ",
        language="ja",
        difficulty="N3",
    )

    assert payload.title == "面试自我介绍"
    assert payload.description == "练习介绍工作经历。"
    assert payload.language == ScenarioLanguage.JA
    assert payload.difficulty == ScenarioDifficulty.N3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "   "),
        ("description", "   "),
        ("language", "fr"),
        ("difficulty", "easy"),
    ],
)
def test_scenario_create_rejects_invalid_fields(field: str, value: str) -> None:
    data = {
        "title": "面试",
        "description": "练习自我介绍。",
        "language": "ja",
        "difficulty": "N3",
    }
    data[field] = value

    with pytest.raises(ValidationError):
        ScenarioCreate.model_validate(data)


def test_scenario_update_requires_at_least_one_non_null_field() -> None:
    with pytest.raises(ValidationError):
        ScenarioUpdate()

    with pytest.raises(ValidationError):
        ScenarioUpdate(title=None)
