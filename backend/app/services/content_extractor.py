"""内容清洗提取：把 text/URL/PDF 三种来源统一转成纯文本。

对应技术架构 §3.2.2 Input Handler 子模块。
"""

import io

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

MAX_CONTENT_CHARS = 20000  # 传给 LLM 前的截断上限，控制 token 成本


class ContentExtractionError(Exception):
    pass


def _truncate(text: str) -> str:
    text = text.strip()
    return text[:MAX_CONTENT_CHARS]


async def extract_from_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (LinguaLearner)"})
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise ContentExtractionError(f"URL 抓取失败: {exc}") from exc

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    if not text:
        raise ContentExtractionError("URL 页面未提取到正文")
    return _truncate(text)


def extract_from_pdf(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # pypdf 抛的异常类型较杂，统一兜住
        raise ContentExtractionError(f"PDF 解析失败: {exc}") from exc

    if not text.strip():
        raise ContentExtractionError("PDF 未提取到文本（可能是扫描件）")
    return _truncate(text)


def extract_from_text(text: str) -> str:
    if not text.strip():
        raise ContentExtractionError("内容为空")
    return _truncate(text)
