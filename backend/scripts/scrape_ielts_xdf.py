"""全量抓取新东方雅思口语真题 Topic，产出 seeds/ielts_speaking.json 同构的 JSON。

已验证的接口（免登录，带 FromURL header 即可）：
    GET https://ieltscat.xdf.cn/api/list/ielts/3/sppt?value={partParentId}_{categoryKeyCode}
    → data[].sectionList[] = {title: 册数, subTitle: 题名, questionId, totalNum, doneNum, ...}

注意：
  - 路径里的 3 是 funCode（口语）；列表用的是 label 的 **keyCode**，不是 id
  - 题目详情接口 /api/question//{id} 需要登录（匿名返回 data:null），
    所以 questions/cue_card 暂缺，由 LLM 基于真实 Topic 标题生成，或用
    --cookie 登录后重抓补齐

分类 id 来自 /api/label/query/all（免登录）：
    Part 1 parent=1318  个人喜好类 keyCode=1322 / 技能类 1323 / 休闲活动类 1324 / 抽象类 1325
                        （个人信息类 1321）
    Part 2 parent=1319  人物 1326 / 事件 1327 / 物品 1328 / 地点 1329
    Part 3 parent=1320  人物 1331 / 事件 1332 / 物品 1333 / 地点 1334
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

LIST_API = "https://ieltscat.xdf.cn/api/list/ielts/3/sppt"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {"FromURL": "ieltscat.xdf.cn", "Referer": "https://ieltscat.xdf.cn/practice/speak/topic/1"}

# part -> parent label id
PART_PARENT = {1: 1318, 2: 1319, 3: 1320}
# (part, keyCode) -> 类别中文名，与站点分类一致
CATEGORIES: dict[int, dict[int, str]] = {
    1: {1321: "个人信息类", 1322: "个人喜好类", 1323: "技能类", 1324: "休闲活动类", 1325: "抽象类"},
    2: {1326: "人物", 1327: "事件", 1328: "物品", 1329: "地点"},
    3: {1331: "人物", 1332: "事件", 1333: "物品", 1334: "地点"},
}
DEFAULT_DIFFICULTY = {1: "B1", 2: "B2", 3: "C1"}


CODE_TITLE = re.compile(r"^C(\d+)T(\d+)S(\d+)$")


def readable_title(raw_title: str, book: str, part: int) -> str:
    """站点部分题目没填话题名，subTitle 是自编编码（C20T1S1）。

    这类标题直接进库里用户看不懂，按「剑桥册数 + Part 序号」重写成可读形式。
    """
    matched = CODE_TITLE.match(raw_title)
    if not matched:
        return raw_title
    book_no, test_no, section_no = matched.groups()
    # book 形如 "剑雅20 Test 1"，编码与其同源，取册数拼一个可读名
    return f"剑桥{book_no} Test{test_no} 口语 Part {part} 第 {section_no} 题"


def fetch_category(part: int, key_code: int, retries: int = 3) -> list[dict]:
    """抓一个类别下的全部 Topic。"""
    import httpx

    url = f"{LIST_API}?value={PART_PARENT[part]}_{key_code}"
    for attempt in range(retries):
        try:
            resp = httpx.get(url, headers=HEADERS, timeout=20.0, follow_redirects=True)
            payload = resp.json()
        except Exception as exc:
            print(f"    ! 请求失败（{attempt + 1}/{retries}）：{exc}", file=sys.stderr)
            time.sleep(1.5)
            continue

        if payload.get("code") != 200:
            print(f"    ! code={payload.get('code')} {payload.get('msg')}", file=sys.stderr)
            return []

        sections = payload.get("data") or []
        topics: list[dict] = []
        for section in sections:
            for item in section.get("sectionList") or []:
                raw_title = (item.get("subTitle") or "").strip()
                book = (item.get("title") or "").strip()
                title = readable_title(raw_title, book, part) if raw_title else book
                topics.append(
                    {
                        "title": title,
                        # 真实出处与站点原始标题，留档便于人工校对
                        "_book": book,
                        "_raw_title": raw_title,
                        "_question_id": item.get("questionId"),
                        "_sub_questions": item.get("totalNum"),
                        # 站点已给出完整句式的（Part 2 题卡）直接可用，否则留空后续补
                        "cue_card": raw_title if raw_title.startswith("Describe") else None,
                        "difficulty": DEFAULT_DIFFICULTY[part],
                    }
                )
        return [t for t in topics if t["title"]]
    return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="抓取雅思口语真题 Topic 列表")
    parser.add_argument("--out", type=Path, default=Path("seeds/ielts_scraped.json"))
    parser.add_argument("--parts", default="1,2,3", help="要抓的 Part，逗号分隔")
    args = parser.parse_args(argv)

    parts = [int(p) for p in args.parts.split(",") if p.strip()]
    bank: dict[str, dict[str, list]] = {}

    for part in parts:
        key = f"part{part}"
        bank[key] = {}
        for key_code, name in CATEGORIES[part].items():
            print(f"抓取 Part {part} / {name} (keyCode={key_code}) ...", file=sys.stderr)
            topics = fetch_category(part, key_code)
            bank[key][name] = topics
            print(f"  → {len(topics)} 题", file=sys.stderr)

    # 站点分类有重叠（同一话题会同时挂在两个类别下），同一 Part 内按标题去重
    seen: set[str] = set()
    dropped = 0
    for part_bucket in bank.values():
        for cat_name in list(part_bucket):
            kept = []
            for item in part_bucket[cat_name]:
                if item["title"] in seen:
                    dropped += 1
                    continue
                seen.add(item["title"])
                kept.append(item)
            part_bucket[cat_name] = kept

    total = sum(len(v) for part in bank.values() for v in part.values())
    print(f"\n合计 {total} 个真题 Topic（去重丢弃 {dropped}）", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已写入 {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
