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


# 2026-09-30 新建界面不再收集难度，未提供时应按输出语言取合理默认
@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("en", ScenarioDifficulty.B1),
        ("ja", ScenarioDifficulty.N4),
        ("zh", ScenarioDifficulty.INTERMEDIATE),
    ],
)
def test_scenario_create_defaults_difficulty_by_language(language: str, expected) -> None:
    payload = ScenarioCreate.model_validate(
        {"title": "Cooking", "description": "Do you cook?", "language": language}
    )

    assert payload.difficulty == expected


def test_scenario_create_still_honours_explicit_difficulty() -> None:
    """显式传入时仍按用户的值，不被默认值覆盖。"""
    payload = ScenarioCreate.model_validate(
        {
            "title": "Cooking",
            "description": "Do you cook?",
            "language": "en",
            "difficulty": "C1",
        }
    )

    assert payload.difficulty == ScenarioDifficulty.C1


def test_scenario_update_still_rejects_unknown_difficulty() -> None:
    """难度放开为可空后，非法枚举值仍要被拒。"""
    with pytest.raises(ValidationError):
        ScenarioUpdate.model_validate({"difficulty": "easy"})
