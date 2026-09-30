"""探测题目详情页的真实接口。

列表接口已确认：
    GET /api/list/ielts/3/sppt?value={partParentId}_{categoryKeyCode}
    → data[].sectionList[] = {title: 册数, subTitle: 题名, questionId, totalNum, ...}

但题目详情接口（含完整追问问题文本）直接 curl 会返回 {"status":42,"message":"非法请求"}，
说明带登录态或附加校验。这里用无头浏览器真实点击题目，拦截其发出的请求。

依赖：playwright（pip install playwright && playwright install chromium）
国内网络装浏览器时加镜像：
    set PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
    python -m playwright install chromium
"""

import argparse
import json
import sys
from pathlib import Path

BASE = "https://ieltscat.xdf.cn"
_SKIP = (".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2", ".gif", ".webp")


def ensure_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("未安装 playwright：pip install playwright && playwright install chromium")
    return sync_playwright


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="探测雅思题目详情接口")
    parser.add_argument("--part", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--value", default="1318_1321", help="{partParentId}_{categoryKeyCode}")
    parser.add_argument("--dump", type=Path, required=True, help="输出文件")
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args(argv)

    sync_playwright = ensure_playwright()
    captured: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headful)
        page = browser.new_page()

        def on_response(response):
            url = response.url
            if "/api/" not in url:
                return
            if url.lower().split("?")[0].endswith(_SKIP):
                return
            if "json" not in response.headers.get("content-type", ""):
                return
            try:
                body = response.json()
            except Exception:
                return
            captured.append({"url": url, "status": response.status, "body": body})

        page.on("response", on_response)
        # 记录所有网络请求（含非 JSON），便于判断点击后到底发起了什么
        all_requests: list[str] = []
        page.on("request", lambda r: all_requests.append(f"{r.method} {r.url}"))

        # 「开始做题」是新标签页打开 /practice/detail/speak/{questionId}
        popups: list = []
        ctx = page.context
        ctx.on("page", lambda p: popups.append(p))

        page.goto(f"{BASE}/practice/speak/topic/{args.part}", wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:
            pass
        page.wait_for_timeout(2500)

        # 点题目前先挂上 popup 监听，漏掉第一条请求
        popup_requests: list[str] = []
        popup_responses: list[dict] = []

        def on_popup(popup) -> None:
            print(f"新标签页: {popup.url}", file=sys.stderr)

            def on_req(r) -> None:
                popup_requests.append(f"{r.method} {r.url}")

            def on_resp(resp) -> None:
                url = resp.url
                if "/api/" not in url:
                    return
                if url.lower().split("?")[0].endswith(_SKIP):
                    return
                if "json" not in resp.headers.get("content-type", ""):
                    return
                try:
                    body = resp.json()
                except Exception:
                    return
                popup_responses.append({"url": url, "status": resp.status, "body": body})

            popup.on("request", on_req)
            popup.on("response", on_resp)

        ctx.on("page", on_popup)

        # 点进列表里第一个题目
        clicked = False
        for selector in ("text=开始做题", "text=继续做题", "text=重新做题", "li:has-text('剑雅')"):
            try:
                el = page.locator(selector).first
                if el.count() > 0:
                    print(f"点击 {selector!r}", file=sys.stderr)
                    el.click(timeout=8000)
                    clicked = True
                    break
            except Exception as exc:
                print(f"  {selector!r} 失败：{exc}", file=sys.stderr)

        if not clicked:
            print("没找到可点击的题目入口", file=sys.stderr)
        else:
            # 等 popup 真正发起 /api/ 数据请求（它要先动态加载完路由 chunk）
            for _ in range(60):
                page.wait_for_timeout(500)
                if any("/api/" in r for r in popup_requests):
                    break
            page.wait_for_timeout(2000)
            if popups:
                try:
                    popups[0].wait_for_load_state("networkidle", timeout=12000)
                except Exception:
                    pass
                page.wait_for_timeout(2000)

        browser.close()

    print(f"\n详情页 JSON 接口 {len(popup_responses)} 个：")
    for item in popup_responses:
        print(f"  [{item['status']}] {item['url'][:170]}")
        body = item["body"]
        if isinstance(body, dict):
            print(f"      keys: {list(body.keys())}")

    print(f"\n详情页全部请求（前 20 条）：")
    for line in popup_requests[:20]:
        print(f"  {line[:180]}")

    new = captured[before:]
    new_reqs = all_requests[req_before:]
    print(f"\n点击后新增 {len(new)} 个 JSON 接口：")
    for item in new:
        print(f"  [{item['status']}] {item['url'][:160]}")
        body = item["body"]
        if isinstance(body, dict):
            print(f"      keys: {list(body.keys())}")

    print(f"\n点击后全部请求 {len(new_reqs)} 条（/api/ 只列前 15 条）：")
    for line in [r for r in new_reqs if "/api/" in r][:15]:
        print(f"  {line[:170]}")

    args.dump.parent.mkdir(parents=True, exist_ok=True)
    args.dump.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {args.dump}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
