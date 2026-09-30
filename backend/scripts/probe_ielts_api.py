"""抓取新东方雅思口语真题，产出 seeds/ielts_speaking.json 同构的 JSON。

2026-09-30 从"解析 DOM"改为"拦截网络请求"：
直接读页面真实调用的接口响应，拿到的是结构化完整数据（题目标题、所属剑雅册数、
全部追问问题），不用依赖 DOM class 名——站点改版时后者极易失效。

站点是 Vue SPA，curl 只能拿到空壳 HTML；而 /api/question/* 系列接口带登录态
校验（返回 {"status":42,"message":"非法请求"}），所以必须用无头浏览器渲染。

依赖（单独安装，不写入 pyproject）：
    pip install playwright
    playwright install chromium

用法：
    # 第一步：探测。打开页面、记录所有接口，看清真实参数后再抓
    python scripts/probe_ielts_api.py

    # 第二步：确认无误后全量抓取
    python scripts/scrape_ielts_xdf.py --out seeds/ielts_scraped.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

BASE = "https://ieltscat.xdf.cn"
# 口语话题练习页，路径参数为 part(1/2/3) 与 label id
TOPIC_PAGE = "/practice/speak/topic/{part}"

# 分类 id 来自站点 /api/label/query/all（免登录，已实测）
# Part 1: 1302 下的 133-137；Part 2: 1319 下的 138-141(+291 娱乐)；Part 3: 1320 下的 217-220(+292 娱乐)
PART_CATEGORIES = {
    1: [133, 134, 135, 136, 137],
    2: [138, 139, 140, 141],
    3: [217, 218, 219, 220],
}
CATEGORY_NAMES = {
    133: "个人信息类", 134: "个人喜好类", 135: "技能类",
    136: "休闲活动类", 137: "抽象类",
    138: "人物", 139: "事件", 140: "物品", 141: "地点",
    217: "人物", 218: "事件", 219: "物品", 220: "地点",
}

# 只关心返回 JSON 的接口；静态资源与图片直接忽略
_SKIP_SUFFIX = (".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2", ".gif", ".webp")


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "未安装 playwright。执行：\n"
            "    pip install playwright\n"
            "    playwright install chromium"
        )
    return sync_playwright


def interesting(url: str) -> bool:
    if "/api/" not in url and "/list/" not in url:
        return False
    return not url.lower().split("?")[0].endswith(_SKIP_SUFFIX)


def probe(sync_playwright, part: int, category_id: int, headful: bool = False) -> list[dict]:
    """打开某 part 的练习页，记录所有 XHR/fetch 接口及其响应。"""
    captured: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headful)
        page = browser.new_page()

        def on_response(response):
            url = response.url
            if not interesting(url):
                return
            content_type = response.headers.get("content-type", "")
            if "json" not in content_type:
                return
            try:
                body = response.json()
            except Exception:
                return
            captured.append({"url": url, "status": response.status, "body": body})

        page.on("response", on_response)

        url = f"{BASE}{TOPIC_PAGE.format(part=part)}"
        print(f"打开 {url}", file=sys.stderr)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            print(f"  ! 打不开：{exc}", file=sys.stderr)
            browser.close()
            return captured

        # 等 SPA 渲染并发出数据请求
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)
        browser.close()

    return captured


def summarise(captured: list[dict]) -> None:
    """把抓到的接口按响应结构归类，方便判断哪个是题目列表。"""
    print(f"\n共捕获 {len(captured)} 个 JSON 接口：\n")
    for item in captured:
        url = item["url"]
        body = item["body"]
        kind = "?"
        count = "-"
        if isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, dict):
                for key in ("speakList", "list", "records", "rows", "items"):
                    if isinstance(data.get(key), list):
                        kind = f"data.{key}"
                        count = len(data[key])
                        break
                if kind == "?" and isinstance(data.get("total"), int):
                    kind = "data.total"
                    count = data["total"]
            elif isinstance(data, list):
                kind = "data[]"
                count = len(data)
            elif isinstance(body.get("list"), list):
                kind = "list[]"
                count = len(body["list"])
        elif isinstance(body, list):
            kind = "[]"
            count = len(body)

        print(f"  [{kind:14s}] n={count:<5} {url[:150]}")

        # 有内容的列表接口，打印第一条的字段名——这是写解析器的依据
        sample = None
        if isinstance(body, dict):
            data = body.get("data")
            if isinstance(data, dict):
                for key in ("speakList", "list", "records", "rows", "items"):
                    if isinstance(data.get(key), list) and data[key]:
                        sample = data[key][0]
                        break
            elif isinstance(data, list) and data:
                sample = data[0]
        if isinstance(sample, dict):
            print(f"      字段: {list(sample.keys())}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="探测雅思口语练习页的真实接口")
    parser.add_argument("--part", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--headful", action="store_true", help="显示浏览器窗口")
    parser.add_argument("--dump", type=Path, help="把完整响应写到该文件")
    args = parser.parse_args(argv)

    sync_playwright = ensure_playwright()
    captured = probe(sync_playwright, args.part, 0, headful=args.headful)
    summarise(captured)

    if args.dump and captured:
        args.dump.parent.mkdir(parents=True, exist_ok=True)
        args.dump.write_text(json.dumps(captured, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n完整响应已写入 {args.dump}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
