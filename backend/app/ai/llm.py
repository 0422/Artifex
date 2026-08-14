import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings

settings = get_settings()

# 走中转站 OpenAI 兼容层（Bearer 认证）。当前可用模型为 GPT-5.x 系列（如 gpt-5.6-sol）。
_client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

CONCEPT_EXTRACTION_SYSTEM_PROMPT = """\
你是灵犀（LinguaLearner）的知识提取助手。用户会粘贴一段学习内容（外语文章/人文社科文本/技能教程等），
你需要：
1. 生成一句话摘要（summary）
2. 提取其中的关键概念（至少 3 个，最多 8 个），每个概念包含：
   - label：概念名称（简短，可含原文术语）
   - definition：概念的清晰定义（1-3 句话）

只返回严格的 JSON，格式如下，不要有任何多余文字：
{"summary": "...", "concepts": [{"label": "...", "definition": "..."}]}
"""

CARD_GENERATION_SYSTEM_PROMPT = """\
你是灵犀（LinguaLearner）的记忆卡片生成助手。用户会给你一个已提取的知识概念（label + definition）。
你需要为这个概念生成 1-2 张记忆卡片，用于间隔重复复习。每张卡片包含：
  - front_content：正面（问题/提示，引导回忆）
  - back_content：背面（答案/完整说明）

只返回严格的 JSON，格式如下，不要有任何多余文字：
{"cards": [{"front_content": "...", "back_content": "..."}]}
"""


def _extract_json_text(text: str) -> str:
    """去掉可能的 ```json ... ``` 代码块包裹。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    return text


async def _chat_json(system_prompt: str, user_content: str, max_tokens: int) -> dict[str, Any]:
    response = await _client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=max_tokens,
        # 强制返回合法 JSON，避免 LLM 输出尾随逗号/代码块包裹导致解析失败
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return json.loads(_extract_json_text(response.choices[0].message.content or ""))


async def extract_concepts(content: str) -> dict[str, Any]:
    """调用 LLM 从内容中提取摘要 + 概念列表。返回 {"summary": str, "concepts": [{"label", "definition"}]}"""
    return await _chat_json(CONCEPT_EXTRACTION_SYSTEM_PROMPT, content, max_tokens=2000)


async def generate_cards(label: str, definition: str) -> dict[str, Any]:
    """调用 LLM 为单个概念生成记忆卡片。返回 {"cards": [{"front_content", "back_content"}]}"""
    return await _chat_json(CARD_GENERATION_SYSTEM_PROMPT, f"概念：{label}\n定义：{definition}", max_tokens=1000)


PATH_GENERATION_SYSTEM_PROMPT = """\
你是灵犀（LinguaLearner）的学习路径规划师。用户完成了 5 分钟引导，你会收到 JSON 格式的引导答案
（包含学习领域 domain、目标 goal、当前水平 level、每日投入时间、动机等）。
你需要：
1. 生成一份"学习起点报告"（starting_point_report），包含：
   - level_summary：对用户当前水平的一句话判断
   - strengths：优势（数组，1-3 条）
   - gaps：待补齐的短板（数组，1-3 条）
   - recommendation：总体学习建议（一句话）
2. 生成一条初始学习路径：
   - title：路径标题（如"日语 N4 → N3 突破计划"）
   - milestones：4-6 个里程碑，每个含 title（阶段标题）、description（这一阶段做什么，1-2 句）

只返回严格的 JSON，格式如下，不要有任何多余文字：
{
  "starting_point_report": {
    "level_summary": "...",
    "strengths": ["..."],
    "gaps": ["..."],
    "recommendation": "..."
  },
  "path": {
    "title": "...",
    "milestones": [{"title": "...", "description": "..."}]
  }
}
"""


async def generate_learning_path(onboarding_answers: dict[str, Any]) -> dict[str, Any]:
    """根据引导答案生成起点报告 + 初始学习路径。"""
    return await _chat_json(
        PATH_GENERATION_SYSTEM_PROMPT,
        json.dumps(onboarding_answers, ensure_ascii=False),
        max_tokens=3000,
    )
