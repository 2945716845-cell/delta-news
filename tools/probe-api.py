"""探针：打开抖音创作者中心数据分析页，拦截所有 API 请求，找出流量来源接口。
用法: python probe-api.py <aweme_id>
"""
import asyncio, sys, json
from pathlib import Path
from playwright.async_api import async_playwright

AUTH = Path("D:/cheat-tools/.auth")
OUT = Path("D:/cheat-tools/video-frames")


async def main(aweme_id: str):
    all_responses: list[dict] = []

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(AUTH), headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()

        # 拦截所有返回 JSON 的响应
        async def catch_all(resp):
            url = resp.url
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype and any(k in url for k in ("api", "aweme", "data", "janus", "stat")):
                try:
                    body = await resp.json()
                    all_responses.append({"url": url, "data": body})
                    print(f"  [拦截] {url[:120]}")
                except Exception:
                    pass

        page.on("response", catch_all)

        # 几个可能的视频数据页 URL
        urls = [
            f"https://creator.douyin.com/creator-micro/data/following/media?item_id={aweme_id}",
            f"https://creator.douyin.com/creator-micro/data-center/single/video?aweme_id={aweme_id}",
            f"https://creator.douyin.com/creator-micro/content/manage?tab=video",
        ]
        for u in urls:
            print(f"\n[打开] {u[:100]}")
            try:
                await page.goto(u, wait_until="domcontentloaded", timeout=60000)
            except Exception:
                pass
            await asyncio.sleep(10)  # 等 SPA 加载完
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(3)

        # 保存所有拦截结果
        out_dir = OUT / f"api-probe-{aweme_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "responses.json", "w", encoding="utf-8") as f:
            json.dump(all_responses, f, ensure_ascii=False, indent=2)

        print(f"\n共拦截 {len(all_responses)} 个 API 调用")
        for r in all_responses:
            url = r["url"]
            data = r["data"]
            keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
            summary = str(data)[:200]
            print(f"\n--- {url}")
            print(f"  keys: {keys}")
            print(f"  preview: {summary}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "7641829650947149091"))
