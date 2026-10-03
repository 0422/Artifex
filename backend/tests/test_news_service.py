import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NewsDomain
from app.models.news import NewsArticle, NewsSource
from app.services import news_service

# 2026-10-03 世势洞察（M6）服务层测试，仿 test_report_service.py 的 mock 手法：
# db 用 MagicMock(spec=AsyncSession)，LLM 走 patch.object(news_service.llm, ...)。

RSS_BYTES = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>test</description>
    <item>
      <title>OpenAI launches a new model</title>
      <link>https://openai.com/index.php?p=1&amp;utm_source=twitter</link>
      <description>&lt;p&gt;A &lt;b&gt;big&lt;/b&gt; launch.&lt;/p&gt;</description>
      <pubDate>Wed, 01 Oct 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Anthropic publishes safety report</title>
      <link>https://anthropic.com/news/report-1</link>
      <description>Safety first.</description>
      <pubDate>Wed, 01 Oct 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Duplicate link item</title>
      <link>https://openai.com/index.php?p=1</link>
      <description>same article, different params</description>
    </item>
  </channel>
</rss>
"""


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(spec=AsyncSession)


def make_source() -> NewsSource:
    return NewsSource(
        id=uuid.uuid4(),
        name="Test Feed",
        url="https://example.com/feed.xml",
        domain=NewsDomain.AI,
        is_enabled=True,
    )


def make_article(title: str = "OpenAI 发布新模型") -> NewsArticle:
    return NewsArticle(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        domain=NewsDomain.AI,
        title=title,
        url="https://openai.com/news/1",
        fingerprint="fp-known",
        excerpt="摘要",
        published_at=datetime(2026, 10, 3, 2, 0, tzinfo=timezone.utc),
    )


class FakeResponse:
    content = RSS_BYTES

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    """替身 httpx.AsyncClient：异步上下文 + get 返回预置 RSS。"""

    last_instance: "FakeClient | None" = None

    def __init__(self, *args, **kwargs) -> None:
        FakeClient.last_instance = self

    async def __aenter__(self) -> "FakeClient":
        return self

    async def __aexit__(self, *args) -> bool:
        return False

    async def get(self, url: str, headers: dict | None = None) -> FakeResponse:
        return FakeResponse()


def set_existing_fingerprints(db: MagicMock, fingerprints: list[str]) -> None:
    result = MagicMock()
    result.scalars.return_value.all.return_value = fingerprints
    db.execute = AsyncMock(return_value=result)


class FakeSessionContext:
    """替身 async_session_factory()： yields 一个假 session。"""

    def __init__(self, session: MagicMock) -> None:
        self._session = session

    async def __aenter__(self) -> MagicMock:
        return self._session

    async def __aexit__(self, *args) -> bool:
        return False


def patch_session_factory(monkeypatch: pytest.MonkeyPatch, session: MagicMock) -> None:
    factory = MagicMock(side_effect=lambda: FakeSessionContext(session))
    monkeypatch.setattr(news_service, "async_session_factory", factory)


# ---------- 抓取 ----------


@pytest.mark.asyncio
async def test_fetch_source_parses_dedups_and_persists(db: MagicMock) -> None:
    source = make_source()
    set_existing_fingerprints(db, [])

    with patch.object(news_service.httpx, "AsyncClient", FakeClient):
        new_count = await news_service.fetch_source(db, source)

    # 3 条 entry，两条指向同一文章（utm 参数不同），去重后 2 篇新文章
    assert new_count == 2
    added = db.add_all.call_args.args[0]
    assert len(added) == 2
    assert all(isinstance(article, NewsArticle) for article in added)
    # HTML 摘要被剥成纯文本
    assert added[0].excerpt == "A big launch."
    # pubDate 被转成带时区的 UTC 时间
    assert added[0].published_at == datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    assert source.last_fetched_at is not None
    assert source.last_error is None
    db.commit.assert_awaited()


@pytest.mark.asyncio
async def test_fetch_source_skips_existing_fingerprints(db: MagicMock) -> None:
    source = make_source()
    set_existing_fingerprints(db, [news_service._fingerprint("https://openai.com/index.php?p=1")])

    with patch.object(news_service.httpx, "AsyncClient", FakeClient):
        new_count = await news_service.fetch_source(db, source)

    # 重复的那篇已在库里；另一篇仍然入库
    assert new_count == 1
    added = db.add_all.call_args.args[0]
    assert len(added) == 1
    assert added[0].title == "Anthropic publishes safety report"


@pytest.mark.asyncio
async def test_fetch_source_records_error_without_raising(db: MagicMock) -> None:
    source = make_source()

    class FailingClient(FakeClient):
        async def get(self, url: str, headers: dict | None = None) -> FakeResponse:
            raise httpx.ConnectError("connection refused")

    with patch.object(news_service.httpx, "AsyncClient", FailingClient):
        new_count = await news_service.fetch_source(db, source)

    assert new_count == 0
    assert source.last_error is not None
    assert "ConnectError" in source.last_error
    db.add_all.assert_not_called()


@pytest.mark.asyncio
async def test_fingerprint_ignores_tracking_params() -> None:
    assert news_service._fingerprint(
        "https://Example.com/a?utm_source=x&utm_medium=y"
    ) == news_service._fingerprint("https://example.com/a")
    assert news_service._fingerprint("https://example.com/a") != news_service._fingerprint(
        "https://example.com/b"
    )


# ---------- 日报生成 ----------


@pytest.mark.asyncio
async def test_generate_digest_upserts_llm_content(
    monkeypatch: pytest.MonkeyPatch, db: MagicMock
) -> None:
    monkeypatch.setattr(
        news_service, "_load_articles_for_digest", AsyncMock(return_value=[make_article()])
    )
    upsert = AsyncMock(return_value="digest-row")
    monkeypatch.setattr(news_service, "_upsert_digest", upsert)
    llm_output = {
        "title": "AI 日报 · 10月3日",
        "summary": "今日总分述。",
        "items": [
            {
                "headline": "OpenAI 发布新模型",
                "summary_zh": "OpenAI 发布了新一代模型。",
                "why_matters": "影响行业格局。",
                "importance": 9,
                "url": "https://openai.com/news/1",
                "source_name": "OpenAI News",
            }
        ],
    }

    with patch.object(
        news_service.llm, "generate_news_digest", AsyncMock(return_value=llm_output)
    ):
        result = await news_service.generate_digest(db, NewsDomain.AI)

    assert result == "digest-row"
    content = upsert.call_args.args[3]
    assert content.items[0].importance == 9
    assert content.items[0].why_matters == "影响行业格局。"
    assert upsert.call_args.kwargs["degraded"] is False


@pytest.mark.asyncio
async def test_generate_digest_returns_none_without_articles(
    monkeypatch: pytest.MonkeyPatch, db: MagicMock
) -> None:
    monkeypatch.setattr(news_service, "_load_articles_for_digest", AsyncMock(return_value=[]))
    upsert = AsyncMock()
    monkeypatch.setattr(news_service, "_upsert_digest", upsert)

    with patch.object(
        news_service.llm, "generate_news_digest", AsyncMock()
    ) as generate:
        result = await news_service.generate_digest(db, NewsDomain.AI)

    assert result is None
    generate.assert_not_awaited()
    upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_digest_falls_back_when_llm_fails(
    monkeypatch: pytest.MonkeyPatch, db: MagicMock
) -> None:
    articles = [make_article("OpenAI 发布新模型"), make_article("DeepMind 论文")]
    monkeypatch.setattr(
        news_service, "_load_articles_for_digest", AsyncMock(return_value=articles)
    )
    upsert = AsyncMock(return_value="digest-row")
    monkeypatch.setattr(news_service, "_upsert_digest", upsert)

    with patch.object(
        news_service.llm,
        "generate_news_digest",
        AsyncMock(side_effect=OpenAIError("503")),
    ):
        result = await news_service.generate_digest(db, NewsDomain.AI)

    assert result == "digest-row"
    content = upsert.call_args.args[3]
    assert upsert.call_args.kwargs["degraded"] is True
    # 降级稿直出原始标题，不含编造内容
    assert [item.headline for item in content.items] == ["OpenAI 发布新模型", "DeepMind 论文"]


@pytest.mark.asyncio
async def test_generate_all_digests_uses_child_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    patch_session_factory(monkeypatch, session)
    generate = AsyncMock(return_value="digest-row")
    monkeypatch.setattr(news_service, "generate_digest", generate)

    digests = await news_service.generate_all_digests()

    assert digests == ["digest-row"] * len(NewsDomain)
    assert generate.await_count == len(NewsDomain)


@pytest.mark.asyncio
async def test_generate_all_digests_isolates_single_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    patch_session_factory(monkeypatch, session)

    async def fake_generate(_session, domain, digest_date=None):
        if domain is NewsDomain.AI:
            raise RuntimeError("boom")
        return f"digest-{domain.value}"

    monkeypatch.setattr(news_service, "generate_digest", fake_generate)

    digests = await news_service.generate_all_digests()

    assert "digest-ai" not in digests
    assert "digest-tech" in digests
