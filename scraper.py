#!/usr/bin/env python3
"""
小猪求职信息爬虫 - 使用 Playwright + Chromium 抓取 JS 渲染的招聘页面
用法: python3 scraper.py <site_name> <url> [--keywords "AI,Product Manager"]
输出: JSON 格式的页面文本内容
"""
import sys
import json
import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

CHROME_PATH = os.path.expanduser(
    '~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'
)

def scrape(url, timeout_ms=20000):
    """抓取指定URL的页面文本内容"""
    result = {
        "success": False,
        "site": "",
        "url": url,
        "title": "",
        "text": "",
        "error": ""
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=CHROME_PATH,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--single-process',
                ]
            )
            # 小 viewport 减少内存
            page = browser.new_page(viewport={"width": 1280, "height": 720})

            page.goto(url, timeout=timeout_ms, wait_until='domcontentloaded')
            # 等待额外时间让 JS 执行
            page.wait_for_timeout(3000)

            result["title"] = page.title()
            result["text"] = page.inner_text('body')
            result["success"] = True

            browser.close()
    except PlaywrightTimeout:
        result["error"] = f"Timeout after {timeout_ms}ms"
        # 超时也尝试拿已有内容
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    executable_path=CHROME_PATH,
                    args=['--no-sandbox', '--disable-setuid-sandbox',
                          '--disable-dev-shm-usage', '--single-process']
                )
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                page.goto(url, timeout=timeout_ms)
                result["text"] = page.inner_text('body')
                result["title"] = page.title()
                result["success"] = True
                browser.close()
        except Exception as e2:
            result["error"] += f" | Fallback also failed: {str(e2)}"
    except Exception as e:
        result["error"] = str(e)

    return result


def extract_jobs_from_linkedin(text):
    """从 LinkedIn 搜索结果中提取岗位信息"""
    jobs = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        # LinkedIn 岗位通常包含这些关键词
        if any(kw in line.lower() for kw in ['product manager', 'ai ', 'pm ', 'product']):
            # 简单提取附近几行
            context = '\n'.join(lines[max(0, i-1):i+5])
            jobs.append({
                "matched_line": line[:200],
                "context": context[:500]
            })
    return jobs


def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: scraper.py <site_name> <url> [--keywords KWS]"}))
        sys.exit(1)

    site_name = sys.argv[1]
    url = sys.argv[2]

    keywords = "AI,Product Manager"
    if "--keywords" in sys.argv:
        idx = sys.argv.index("--keywords")
        if idx + 1 < len(sys.argv):
            keywords = sys.argv[idx + 1]

    result = scrape(url)
    result["site"] = site_name

    # 截断文本避免输出太大
    if len(result["text"]) > 50000:
        result["text"] = result["text"][:50000] + "\n... [truncated]"

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
