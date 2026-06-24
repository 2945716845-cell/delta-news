"""探针v4：从作品管理页点击目标视频 → 进入详情 → 拦截所有 API。
"""
import asyncio, sys, json, re
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

        async def catch_json(resp):
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype:
                try:
                    body = await resp.json()
                    all_api.append({"url": resp.url, "data": body})
                except Exception:
                    pass

        page.on("response", catch_json)

        # 1. 打开作品管理页
        print("[1] 打开作品管理页")
        await page.goto("https://creator.douyin.com/creator-micro/content/manage", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(6)

        # 2. 在列表中找到对应视频并点击
        print(f"[2] 查找视频 {aweme_id}...")
        # 尝试多种方式定位视频
        clicked = False
        # 方式a: 通过链接
        links = await page.locator(f'a[href*="{aweme_id}"]').all()
        if links:
            await links[0].click(force=True)
            clicked = True
            print(f"   ✓ 通过链接点击")
        else:
            # 方式b: 点击列表中第一个视频（兜底）
            items = await page.locator('[class*="video"] a, [class*="item"] a, [class*="card"] a, [class*="list"] img').all()
            for item in items[:10]:
                try:
                    href = await item.get_attribute("href")
                    if href and aweme_id in href:
                        await item.click(force=True)
                        clicked = True
                        print(f"   ✓ 通过元素点击: {href}")
                        break
                except Exception:
                    pass

        if not clicked:
            # 方式c: 直接点第一个看起来像视频的元素
            imgs = await page.locator('img[src*="tos-cn"]').all()
            if imgs:
                await imgs[0].click(force=True)
                clicked = True
                print("   ✓ 点了第一张封面图（兜底）")

        await asyncio.sleep(8)

        # 3. 检查当前页面URL
        current_url = page.url
        print(f"[3] 当前页面: {current_url[:150]}")

        # 4. 如果进了详情页，找"数据分析"入口
        page_text = await page.evaluate("document.body.innerText")
        if "数据分析" in page_text:
            print("   [√] 页面上有'数据分析'，尝试点击")
            data_link = await page.locator('text="数据分析"').first
            await data_link.click(force=True)
            await asyncio.sleep(6)
            print(f"   当前页面: {page.url[:150]}")

        # 5. 分析拦截结果
        print(f"\n=== 共拦截 {len(all_api)} 个 JSON 响应 ===")

        # 搜视频相关数据
        target_keywords = ["traffic_source", "flow_source", "play_source", "recommend",
                           "search", "follow", "homepage", "traffic", "source",
                           "播放来源", "流量来源", "overview", "video_data",
                           "item_data", "stat_data", "analytics", "data_overview",
                           "total_play", "share_count", "comment_count", "digg_count",
                           "favorite_count", "download_count"]

        key_apis = []
        for entry in all_api:
            ds = json.dumps(entry["data"], ensure_ascii=False)
            for kw in target_keywords:
                if kw.lower() in ds.lower():
                    key_apis.append(entry)
                    break

        print(f"含视频数据关键词: {len(key_apis)}")
        for k in key_apis:
            print(f"\n🔑 {k['url'][:150]}")
            data_str = json.dumps(k["data"], ensure_ascii=False)
            print(data_str[:1000])

        # 保存
        out = Path(f"D:/cheat-tools/video-frames/probe-v4-{aweme_id}.json")
        out.write_text(json.dumps({"all": all_api, "key": key_apis, "final_url": current_url}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[保存] {out}")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "7641829650947149091"))
