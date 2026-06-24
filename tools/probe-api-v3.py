"""探针v3：从内容管理页点击视频的"数据分析"按钮，进入真实数据页抓 API。
用法: python probe-api-v3.py <aweme_id>
"""
import asyncio, sys, json
from pathlib import Path
from playwright.async_api import async_playwright

AUTH = Path("D:/cheat-tools/.auth")


async def main(aweme_id: str):
    all_api = []

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(AUTH), headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()

        async def catch_all(resp):
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype or "text/html" in ctype:
                try:
                    body = await resp.json()
                    all_api.append({"url": resp.url, "data": body})
                except Exception:
                    pass

        page.on("response", catch_all)

        # 1. 先去内容管理页
        print("[1] 打开内容管理页")
        await page.goto("https://creator.douyin.com/creator-micro/content/manage", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(6)

        # 2. 找目标视频并点击"数据分析"
        print(f"[2] 查找视频 {aweme_id} 的数据分析入口...")
        # 尝试通过 item_id 定位到视频行，点击"数据分析"或"查看数据"
        page_text = await page.evaluate("document.body.innerText")
        if "数据分析" not in page_text and "查看数据" not in page_text:
            print("   [注意] 页面上没找到数据分析按钮，可能需要在列表中找")

        # 尝试直接点可能的按钮/链接
        data_btns = await page.locator('text="数据分析"').all()
        view_data_btns = await page.locator('text="查看数据"').all()
        print(f"   找到 {len(data_btns)} 个'数据分析'按钮，{len(view_data_btns)} 个'查看数据'按钮")

        if data_btns:
            await data_btns[0].click(force=True)
            print("   ✓ 点击了数据分析")
            await asyncio.sleep(8)
        elif view_data_btns:
            await view_data_btns[0].click(force=True)
            print("   ✓ 点击了查看数据")
            await asyncio.sleep(8)
        else:
            # 尝试直接导航到数据页面
            alt_url = f"https://creator.douyin.com/creator-micro/data-center/content/video/single?aweme_id={aweme_id}"
            print(f"   尝试备选URL: {alt_url}")
            await page.goto(alt_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(10)

        # 3. 分析结果
        print(f"\n=== 共拦截 {len(all_api)} 个响应 ===")
        # 找含视频数据的
        data_keys = ["播放", "点赞", "traffic", "source", "flow", "recommend", "search",
                      "follow", "homepage", "share", "comment", "play", "like",
                      "overview", "trend", "demographic", "portrait", "audience",
                      "total_play", "video_data", "item_data", "traffic_source",
                      "flow_source", "recommend_rate", "search_rate"]
        found = []
        for entry in all_api:
            ds = json.dumps(entry["data"], ensure_ascii=False)
            for kw in data_keys:
                if kw.lower() in ds.lower():
                    found.append(entry)
                    break

        print(f"含视频数据关键词: {len(found)}")
        for f in found:
            print(f"\n🔑 {f['url'][:150]}")
            print(json.dumps(f["data"], ensure_ascii=False)[:800])

        # 保存
        out = Path(f"D:/cheat-tools/video-frames/probe-{aweme_id}.json")
        out.write_text(json.dumps({"all": all_api, "found": found}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[保存] {out}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "7641829650947149091"))
