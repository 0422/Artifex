"""雅思口语 prompt 与开场白分支测试。

守住三种 part 的行为差异，以及"非雅思场景完全不受影响"这条底线。
"""

import uuid
from types import SimpleNamespace

import pytest

from app.models.enums import ScenarioDifficulty, ScenarioLanguage
from app.services.chat_service import _first_question, _opening_message
from app.services.scenario_engine import build_scenario_prompt


def make_scenario(
    *,
    ielts_part=None,
    cue_card=None,
    description="Do you like music?\nWhat kind of music do you enjoy?",
    title="Music",
    scenario_mode="role_play",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        user_id=None,
        title=title,
        description=description,
        language=ScenarioLanguage.EN,
        difficulty=ScenarioDifficulty.B1,
        domain="language",
        scenario_mode=scenario_mode,
        estimated_minutes=None,
        tags=["ielts"],
        ielts_part=ielts_part,
        cue_card=cue_card,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# 开场白
# ---------------------------------------------------------------------------


def test_first_question_returns_only_the_first_line() -> None:
    text = "Do you like music?\nWhat kind of music?\nWhen do you listen?"
    assert _first_question(text) == "Do you like music?"


def test_first_question_skips_leading_blank_lines() -> None:
    assert _first_question("\n\n  Do you like music?") == "Do you like music?"


def test_first_question_falls_back_to_whole_text() -> None:
    assert _first_question("  单行问题  ") == "单行问题"


def test_opening_part1_is_a_single_question() -> None:
    """Part 1 开场只能问第一题，不能把整库倒出来。"""
    opening = _opening_message(make_scenario(ielts_part=1))
    assert opening == "Do you like music?"
    assert "What kind of music" not in opening


def test_opening_part2_contains_full_cue_card_and_prep_instruction() -> None:
    card = "You should say:\nwho this person is\nand explain why you admire them."
    opening = _opening_message(
        make_scenario(ielts_part=2, cue_card=card, title="Describe a person you admire")
    )
    assert card in opening
    assert "1 minute" in opening
    assert "2 minutes" in opening


def test_opening_part3_is_a_single_discussion_question() -> None:
    text = "What makes a place attractive?\nShould governments limit tourists?"
    opening = _opening_message(make_scenario(ielts_part=3, description=text))
    assert opening == "What makes a place attractive?"


def test_opening_falls_back_to_generic_when_not_ielts() -> None:
    """非雅思场景的开场白必须保持原样，不能被打断。"""
    opening = _opening_message(make_scenario(ielts_part=None))
    assert opening == 'Hello! Let\'s practice "Music". Start when you are ready.'


def test_opening_non_role_play_unchanged() -> None:
    opening = _opening_message(
        make_scenario(ielts_part=None, scenario_mode="guided_discussion")
    )
    assert "我们来讨论" in opening


# ---------------------------------------------------------------------------
# prompt 分支
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("part", [1, 2, 3])
def test_ielts_prompt_declares_examiner_role(part: int) -> None:
    prompt = build_scenario_prompt(
        make_scenario(ielts_part=part), ScenarioDifficulty.B1
    )
    assert f"Part {part}" in prompt
    assert "IELTS Speaking examiner" in prompt


def test_part1_prompt_asks_one_question_at_a_time() -> None:
    prompt = build_scenario_prompt(make_scenario(ielts_part=1), ScenarioDifficulty.B1)
    assert "ONE short factual question" in prompt
    assert "Do not chain multiple questions" in prompt


def test_part2_prompt_keeps_silent_during_monologue() -> None:
    prompt = build_scenario_prompt(
        make_scenario(ielts_part=2, cue_card="You should say: who this person is"),
        ScenarioDifficulty.B2,
    )
    assert "DO NOT interrupt" in prompt
    assert "1 minute to prepare" in prompt
    # 题卡原文必须进 prompt，否则 AI 念不出来
    assert "You should say: who this person is" in prompt


def test_part3_prompt_disables_correction() -> None:
    """Part 3 重点在内容深度，不应纠正语言。"""
    prompt = build_scenario_prompt(make_scenario(ielts_part=3), ScenarioDifficulty.C1)
    assert "Always set `correction` to null in this part" in prompt


def test_ielts_prompt_outputs_json_shape_for_existing_parser() -> None:
    """输出结构必须和既有 correction schema 一致，chat_service 不用改。"""
    prompt = build_scenario_prompt(make_scenario(ielts_part=1), ScenarioDifficulty.B1)
    assert '"reply"' in prompt
    assert '"correction"' in prompt
    assert '"severity"' in prompt


def test_generic_prompt_unchanged_for_non_ielts() -> None:
    prompt = build_scenario_prompt(make_scenario(ielts_part=None), ScenarioDifficulty.B1)
    assert "foreign-language role-play" in prompt
    assert "IELTS" not in prompt


def test_ielts_prompt_treats_scenario_data_as_untrusted() -> None:
    """题目文本来自导入数据，仍按不可信内容注入，防 prompt 注入。"""
    prompt = build_scenario_prompt(make_scenario(ielts_part=1), ScenarioDifficulty.B1)
    assert "untrusted user data" in prompt
