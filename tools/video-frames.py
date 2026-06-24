"""截取抖音视频逐帧截图，给 Claude 分析画面内容。
用法: python video-frames.py <douyin-url> [间隔秒数，默认2]
输出: .cheat-cache/video-frames/<video-id>/frame_*.jpg
"""
import asyncio, sys, re
from pathlib import Path
from playwright.async_api import async_playwright

PROJECT = Path.cwd()
OUT = Path("D:/cheat-tools/video-frames")
AUTH = Path("D:/cheat-tools/.auth")


async def main(url: str, interval: float = 2.0):
    vid = re.search(r"video/(\d+)", url)
    if not vid:
        # 短链接先resolve
        import urllib.request, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, method="HEAD")
        opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
        try:
            resp = opener.open(req, timeout=10)
            final = resp.url
        except Exception:
            final = url
        vid = re.search(r"video/(\d+)", final)
    aweme_id = vid.group(1) if vid else "unknown"
    out_dir = OUT / aweme_id
    out_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(AUTH),
            headless=False,
            viewport={"width": 540, "height": 960},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()
        print(f"[打开] {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # 尝试点击播放按钮
        play_btn = page.locator('[data-e2e="video-player-play"]')
        if await play_btn.count():
            await play_btn.first.click()
            print("[播放] 已点击播放")
        await asyncio.sleep(2)

        # 获取视频时长
        try:
            duration_text = await page.locator("text=/\\d+:\\d+/").first.text_content()
            print(f"[时长] {duration_text}")
        except Exception:
            duration_text = None

        # 逐秒截图
        frame = 0
        max_frames = 30  # 最多截30张
        while frame < max_frames:
            path = out_dir / f"frame_{frame:03d}.jpg"
            await page.screenshot(path=str(path), type="jpeg", quality=60)
            print(f"  frame {frame:03d} saved")
            frame += 1
            await asyncio.sleep(interval)

            # 检测视频是否播完
            ended = await page.locator('[data-e2e="video-replay"]').count()
            if ended:
                print("[结束] 视频已播完")
                break

        print(f"\n✅ {frame} 帧 → {out_dir}")
        await ctx.close()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else input("抖音链接: ")
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    asyncio.run(main(url, interval))
