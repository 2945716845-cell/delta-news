"""打开抖音创作者中心页面，截图后用 DashScope AI 识别所有数据。
用法: python read-page.py <aweme_id>
"""
import asyncio, sys, json, base64, urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

AUTH = Path("D:/cheat-tools/.auth")
API_KEY = "sk-8c646774f9b04bdb83d665b7d38e67ef"


def ai_read_image(path: str, prompt: str) -> str:
    """用 DashScope Qwen-VL 识别图片内容"""
    with open(path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    body = json.dumps({
        "model": "qwen-vl-max",
        "input": {"messages": [{"role": "user", "content": [
            {"image": f"data:image/png;base64,{img_b64}"},
            {"text": prompt}
        ]}]}
    }).encode()
    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        data=body,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
        content = result["output"]["choices"][0]["message"]["content"]
        if isinstance(content, list):
            return "\n".join(t.get("text", "") for t in content if isinstance(t, dict))
        return content


async def main(aweme_id: str):
    shots_dir = Path("D:/cheat-tools/video-frames")
    shots_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(AUTH), headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()

        # 1. 作品管理页 → 截图所有视频数据
        print("[1] 作品管理页")
        await page.goto("https://creator.douyin.com/creator-micro/content/manage", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
        await page.evaluate("window.scrollBy(0, 3000)")
        await asyncio.sleep(3)
        shot1 = str(shots_dir / f"manage_{aweme_id}.png")
        await page.screenshot(path=shot1, full_page=False)
        print(f"  截图: {shot1}")

        # 2. 尝试点击 KC17 进入详情
        # 方式：点封面图
        imgs = await page.locator('img[src*="tos-cn"]').all()
        if imgs:
            await imgs[0].click(force=True)
            await asyncio.sleep(6)
            current = page.url
            print(f"[2] 点击后页面: {current[:120]}")
            shot2 = str(shots_dir / f"detail_{aweme_id}.png")
            await page.screenshot(path=shot2, full_page=False)
            print(f"  截图: {shot2}")

            # 看看有没有"数据分析"按钮
            btns = await page.locator('text="数据分析"').all()
            if btns:
                await btns[0].click(force=True)
                await asyncio.sleep(6)
                shot3 = str(shots_dir / f"analytics_{aweme_id}.png")
                await page.screenshot(path=shot3, full_page=False)
                print(f"  数据分析页截图: {shot3}")

        await ctx.close()

    # 3. AI 读图
    print("\n=== AI 识别 ===")
    for name in ["manage", "detail", "analytics"]:
        p = shots_dir / f"{name}_{aweme_id}.png"
        if p.exists():
            print(f"\n--- {name} ---")
            result = ai_read_image(str(p),
                "这是抖音创作者中心页面截图。请逐行列出所有可见数据：播放量、点赞、评论、分享、收藏数、"
                "以及流量来源占比（搜索、推荐页、个人主页、其他各占百分之多少）、"
                "完播率、2s跳出率、5s完播率、平均播放时长等所有数字。不要遗漏任何数据。用中文回答。")
            print(result)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "7641829650947149091"))
