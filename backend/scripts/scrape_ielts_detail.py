"""用登录态抓取新东方雅思口语真题的完整问题文本。

列表接口（免登录）已能拿到全部真题 Topic；但题目详情
``/api/question//{questionId}`` 匿名请求只返回 ``data:null``，必须带登录态。

用法：
    # 1. 浏览器登录 https://ieltscat.xdf.cn ，F12 → 应用 → Cookie，复制 SESSION 的值
    # 2. 带着 cookie 跑本脚本
    python scripts/scrape_ielts_detail.py --session "<SESSION 值>"

    # 也支持整串 cookie 或 cookie 文件
    python scripts/scrape_ielts_detail.py --cookie "SESSION=abc; other=def"
    python scripts/scrape_ielts_detail.py --cookie-file cookies.txt

输出与 seeds/ielts_speaking.json 同构，questions/cue_card 填真题原文。
"""

import argparse
import json
import sys
import time
from pathlib import Path

BASE = "https://ieltscat.xdf.cn"
DETAIL_API = f"{BASE}/api/question/"

# 与 scrape_ielts_xdf.py 保持一致
PART_PARENT = {1: 1318, 2: 1319, 3: 1320}
CATEGORIES: dict[int, dict[int, str]] = {
    1: {1321: "个人信息类", 1322: "个人喜好类", 1323: "技能类", 1324: "休闲活动类", 1325: "抽象类"},
    2: {1326: "人物", 1327: "事件", 1328: "物品", 1329: "地点"},
    3: {1331: "人物", 1332: "事件", 1333: "物品", 1334: "地点"},
}


def parse_cookie_string(cookie_str: str) -> list[dict]:
    """把整串 Cookie 拆成 playwright 的 add_cookies 结构。

    2026-10-01 实测：只把 JSESSIONID 塞进 Header 会被拒（status 42 非法请求），
    必须整套 cookie 通过 add_cookies 注入浏览器上下文才认。
    domain 用 .ieltscat.xdf.cn 才能同时覆盖主站与子域请求。
    """
    pairs = []
    for segment in cookie_str.split(";"):
        segment = segment.strip()
        if "=" not in segment:
            continue
        name, value = segment.split("=", 1)
        name = name.strip()
        if name:
            pairs.append({"name": name, "value": value.strip(), "domain": ".ieltscat.xdf.cn", "path": "/"})
    return pairs


def build_cookie_header(session: str | None, cookie: str | None, cookie_file: Path | None) -> str:
    if cookie_file and cookie_file.is_file():
        return cookie_file.read_text(encoding="utf-8").strip()
    if cookie:
        return cookie.strip()
    if session:
        return f"JSESSIONID={session.strip()}"
    sys.exit("必须提供 --session / --cookie / --cookie-file 之一")


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("未安装 playwright：pip install playwright && playwright install chromium")
    return sync_playwright


def clean_text(raw: str | None) -> str:
    """详情里的题目文本是带 HTML 的（<p>...</p>、&nbsp;），剥标签并反转义。

    题卡正文形如 "Describe ... You should say:  where you lived  who ..."，
    中间会有多个空行，压成单行后更适合直接当 prompt 与 cue_card 展示。
    """
    import html
    import re

    # <p> / <br> 视作换行，其余标签直接剥掉
    text = re.sub(r"(?i)<\s*(p|br|div|li)[^>]*>", "\n", raw or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    # 折叠连续空行，去掉每行首尾空白
    lines = [line.strip() for line in text.splitlines()]
    return " ".join(line for line in lines if line).strip()


def extract_question_text(detail: dict) -> tuple[str, str | None]:
    """从详情响应里抽出真题问题文本。

    已验证的返回结构（2026-10-01，questionId=6651 / Neighbours）：
        data.contentList[] -> .content 是 JSON 字符串
                            -> json["title"] 即题目文本（含 HTML）
    每题一问，Part 1 共 4 问、Part 3 共 6 问，与真实考试一致。

    返回 (questions, cue_card)。questions 一行一问，供 prompt 按需取用。
    """
    data = detail.get("data")
    if not isinstance(data, dict):
        return "", None

    questions: list[str] = []
    for item in data.get("contentList") or []:
        raw = item.get("content")
        try:
            obj = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        title = clean_text(obj.get("title"))
        # 站点有部分题卡的 content 里混着空段（"You should say:" 后的空行），
        # 不滤掉会让 questions 出现连续空行，prompt 里很难看
        if title:
            questions.append(title)

    # Part 2 题卡原文：article 字段常是 "Describe a person you admire" 这类完整句式。
    # 2026-10-01 但站点对部分题目把 subTitle 填成了自编编码（C19T2S2），article 为空，
    # 而题卡全文落在了 contentList[0].title 里，形如 "Describe ... You should say: ..."。
    # 这里两种来源都认，避免 12 道 Part 2 题漏掉题卡。
    cue_card = None
    article = (data.get("article") or "").strip()
    if article.startswith("Describe") or article.startswith("You should"):
        cue_card = article
    elif questions and questions[0].startswith("Describe"):
        cue_card = questions[0]
        # 题卡本身不该再作为"追问问题"重复一遍
        questions = questions[1:]

    return "\n".join(questions), cue_card


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="带登录态抓雅思真题的完整问题文本")
    parser.add_argument("--session", help="SESSION cookie 的值")
    parser.add_argument("--cookie", help="完整 cookie 串，或 SESSION 的值")
    parser.add_argument("--cookie-file", type=Path, help="cookie 文件路径")
    parser.add_argument("--topics", type=Path, default=Path("seeds/ielts_scraped.json"), help="scrape_ielts_xdf.py 的输出")
    parser.add_argument("--out", type=Path, default=Path("seeds/ielts_with_questions.json"))
    parser.add_argument("--limit", type=int, default=0, help="只抓前 N 个，0 表示全部（先用小数目验证）")
    args = parser.parse_args(argv)

    cookie_header = build_cookie_header(args.session, args.cookie, args.cookie_file)
    bank = json.loads(args.topics.read_text(encoding="utf-8"))

    sync_playwright = ensure_playwright()
    ok = fail = empty = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()
        # 整套 cookie 注入上下文（只塞 Header 会被服务端拒）
        ctx.add_cookies(parse_cookie_string(cookie_header))
        page = ctx.new_page()
        # 先访问站点，确认 cookie 生效
        page.goto(f"{BASE}/practice/speak/topic/1", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)

        # 用上下文请求发详情（共享浏览器 cookie）
        for part_key, categories in bank.items():
            for cat_name, items in categories.items():
                for item in items:
                    if args.limit and ok + fail + empty >= args.limit:
                        break
                    qid = item.get("_question_id")
                    if not qid:
                        continue
                    try:
                        resp = ctx.request.get(
                            f"{DETAIL_API}/{qid}",
                            headers={"FromURL": "ieltscat.xdf.cn"},
                            timeout=20000,
                        )
                        detail = resp.json()
                    except Exception as exc:
                        fail += 1
                        item["_detail_error"] = str(exc)[:120]
                        continue

                    questions, cue_card = extract_question_text(detail)
                    if not questions and not cue_card:
                        empty += 1
                        item["_detail_empty"] = True
                        continue

                    item["questions"] = questions
                    if cue_card:
                        item["cue_card"] = cue_card
                    ok += 1

                    if ok <= 2:
                        print(f"\n样例 [{part_key}/{cat_name}] {item['title']}", file=sys.stderr)
                        print(f"  questions:\n{questions[:600]}", file=sys.stderr)
                        if cue_card:
                            print(f"  cue_card: {cue_card[:300]}", file=sys.stderr)

                    if ok % 20 == 0:
                        print(f"  已抓 {ok} 题（失败 {fail}，空 {empty}）", file=sys.stderr)

        browser.close()

    print(f"\n完成：成功 {ok}，失败 {fail}，空响应 {empty}", file=sys.stderr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {args.out}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
