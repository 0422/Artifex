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


# 2026-10-03 新增世势洞察（M6）模块：把当日一个板块的原始文章策展成中文日报。
# 输入 payload: {domain_label, digest_date, max_items, articles: [{title, source_name, url, published_at, excerpt}]}
# 与学情报告的区别：这里做「筛选 + 排序」而不是「全部点评」，items 允许少于输入甚至为空。
NEWS_DIGEST_SYSTEM_PROMPT = """\
你是科技新闻主编，为一份中文每日简报筛选当日值得关注的事件。

规则：
1. 从输入的候选文章里筛选真正值得关注的条目，不是所有文章都入选；没有值得关注的条目时 items 返回空数组。
2. items 数量上限见输入 max_items，按 importance 从高到低排列。
3. importance 是 1-10 的整数，判定标准：
   - 9-10：改变行业格局的事件、重大产品/模型发布、重大政策与监管；
   - 7-8：大厂重要动作、重要研究或商业进展；
   - 5-6：值得了解但影响有限；
   - 1-4：常规更新、小型融资、传闻——这类不要入选。
4. headline 用中文表述，专有名词（产品、公司、模型、人名）保留英文。
5. summary_zh 用 2-3 句中文概括事件本身，只依据输入文章的摘要，不得补充文章里没有的事实。
6. why_matters 用一句中文说明这件事为何值得读者花时间。
7. 专业术语首次出现时保留英文并附中文注释，例如「LLM（大语言模型）」「AGI（通用人工智能）」——读者在用本产品学英语。
8. url 必须逐字取自输入文章，严禁编造或改写链接。

只返回严格 JSON：
{
  "title": "AI 日报 · 10月3日",
  "summary": "今日总述，2-4 句中文。",
  "items": [
    {
      "headline": "OpenAI 发布新模型",
      "summary_zh": "……",
      "why_matters": "……",
      "importance": 9,
      "url": "原文链接，原样复制",
      "source_name": "来源名，原样复制"
    }
  ]
}
"""


async def generate_news_digest(payload: dict[str, Any]) -> dict[str, Any]:
    """把一个板块当日的候选文章交给 LLM 策展为中文日报。

    2026-10-03 max_tokens 定为 16000：step-3.7-flash 是 reasoning 模型，
    reasoning_content 能吃掉 7000-8000 tokens（输入 33 篇文章约 15K 字符时
    实测 reasoning ~7600 tokens）。3000 时 content 直接空返；8000 时 JSON 写一半
    被截断（finish_reason=length）；16000 才留足「思考 + 完整 JSON」的双份预算。
    """
    return await _chat_json(
        NEWS_DIGEST_SYSTEM_PROMPT,
        json.dumps(payload, ensure_ascii=False),
        max_tokens=16000,
    )
