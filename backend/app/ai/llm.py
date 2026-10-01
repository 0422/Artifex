import json
import logging
from typing import Any

from openai import AsyncOpenAI, BadRequestError

from app.ai import llm_config

logger = logging.getLogger(__name__)

# 2026-10-01 LLM 供应商连接方式抽离到 app/ai/llm_config.py（请求地址 / API Key / 模型
# 存于 backend/config/llm_providers.json，可在「LLM Select」中切换与新增）。
# 本文件只保留 prompt 与返回解析的业务逻辑，按当前激活供应商取连接参数。
# 客户端按「供应商 id + api_key」缓存，改 Key 或切换供应商都会拿到新实例。
_clients: dict[str, AsyncOpenAI] = {}

# 2026-10-01 随内容捕获/记忆卡片/学习路径功能下线，以下三个提示词及其生成函数已删除：
#   CONCEPT_EXTRACTION_SYSTEM_PROMPT + extract_concepts（LLM 提取摘要 + 概念）
#   CARD_GENERATION_SYSTEM_PROMPT   + generate_cards（概念生成记忆卡片）
#   PATH_GENERATION_SYSTEM_PROMPT   + generate_learning_path（引导生成学习路径）
# 原先这三个 prompt 用 string.Template 注入产品名，删除后 Template / PRODUCT_NAME 导入也不再需要。


def _normalize_base_url(base_url: str) -> str:
    """SDK 自行拼接 /chat/completions；各家示例有的带 /v1 有的不带，统一去掉尾部斜杠即可。"""
    return base_url.rstrip("/")


def _get_client(provider: dict[str, Any]) -> AsyncOpenAI:
    api_key = (provider.get("api_key") or "").strip()
    if not api_key:
        raise ValueError(f"LLM「{provider.get('name')}」尚未填写 API Key，请在「LLM Select」中补全")

    base_url = _normalize_base_url(provider["base_url"])
    # 缓存键带上 base_url：编辑供应商改了地址但 Key 不变时，才不会复用连向旧地址的客户端
    cache_key = f"{provider['id']}|{base_url}|{api_key}"
    client = _clients.get(cache_key)
    if client is None:
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        _clients[cache_key] = client
    return client


def _extract_json_text(text: str) -> str:
    """去掉可能的 ```json ... ``` 代码块包裹。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        text = text.removeprefix("json")
        text = text.strip().rstrip("`").strip()
    return text


async def _chat_json(
    system_prompt: str, user_content: str, max_tokens: int
) -> dict[str, Any]:
    return await _chat_messages_json(
        system_prompt,
        [{"role": "user", "content": user_content}],
        max_tokens=max_tokens,
    )


async def _chat_messages_json(
    system_prompt: str,
    messages: list[dict[str, str]],
    max_tokens: int,
) -> dict[str, Any]:
    provider, model = llm_config.get_active()
    client = _get_client(provider)

    request: dict[str, Any] = {
        "model": model["name"],
        "max_tokens": max_tokens,
        # 强制返回合法 JSON，避免 LLM 输出尾随逗号/代码块包裹导致解析失败
        "messages": [
            {"role": "system", "content": system_prompt},
            *messages,
        ],
    }
    # 部分模型（如 deepseek-reasoner）不支持 JSON Output，按模型开关决定是否传
    if model.get("json_mode", True):
        request["response_format"] = {"type": "json_object"}

    try:
        response = await client.chat.completions.create(**request)
    except BadRequestError:
        # 供应商/模型不支持 response_format 时，去掉该参数重试一次，
        # 避免整个对话或报告直接降级；重试仍失败则照常抛给调用方处理。
        if "response_format" not in request:
            raise
        del request["response_format"]
        response = await client.chat.completions.create(**request)

    content = response.choices[0].message.content or ""

    # 2026-10-01 不少供应商会忽略 response_format（请求不报错但返回纯文本），
    # 此前直接 json.loads 会抛 JSONDecodeError，被调用点当成"调用失败"走备用回复，
    # 用户只看到占位句、看不出真实原因。这里改成把原文包进 reply 字段：
    # 对话至少能正常进行，只是拿不到 correction 这类结构化字段。
    try:
        return json.loads(_extract_json_text(content))
    except json.JSONDecodeError:
        logger.warning(
            "LLM %s/%s 未返回 JSON（response_format 可能被忽略），按纯文本处理：%r",
            provider["name"],
            model["name"],
            content[:200],
        )
        return {"reply": content.strip(), "_unparsed": True}


async def generate_chat_turn(
    system_prompt: str,
    history: list[dict[str, str]],
    user_content: str,
) -> dict[str, Any]:
    """Generate one scenario reply and an optional progressive correction."""
    return await _chat_messages_json(
        system_prompt,
        [*history, {"role": "user", "content": user_content}],
        max_tokens=1200,
    )


SESSION_REPORT_SYSTEM_PROMPT = """\
你是外语对话学习分析师。根据一次完整的场景对话生成客观、可执行的中文学情报告。

规则：
1. summary 概括对话内容和学习者表现，不夸大也不贬低。
2. weak_points 只记录有对话证据的问题，不得为了凑数编造。最多 5 个；不足 3 个时设置 no_prominent_issues=true。
3. category 只能是 vocabulary、grammar、expression、pragmatics。
4. tag 必须是稳定的 ASCII 聚合标签，格式为 vocab:slug、grammar:slug、expression:slug 或 pragmatics:slug。
5. example 引用或紧密改写本次对话证据；suggestion 给出针对该问题的具体练习方法。
6. suggestions 提供 1-5 条下一步建议。
7. performance_score 为 0-100 的整数，综合准确度、表达完整度、场景任务完成度；不要因单个轻微错误大幅扣分。

只返回严格 JSON：
{
  "summary": "...",
  "weak_points": [
    {
      "category": "grammar",
      "tag": "grammar:past-tense",
      "description": "...",
      "example": "...",
      "suggestion": "..."
    }
  ],
  "suggestions": ["..."],
  "performance_score": 80,
  "no_prominent_issues": false
}
"""


async def generate_session_report(report_input: dict[str, Any]) -> dict[str, Any]:
    return await _chat_json(
        SESSION_REPORT_SYSTEM_PROMPT,
        json.dumps(report_input, ensure_ascii=False),
        max_tokens=2500,
    )
