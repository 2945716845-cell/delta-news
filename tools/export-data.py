"""一键导出抖音创作者中心数据 — 模拟点击"导出数据"按钮下载 Excel。
用法: python export-data.py
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

AUTH = Path("D:/cheat-tools/.auth")
DOWNLOAD_DIR = Path("D:/cheat-tools/video-frames")


async def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(AUTH), headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()

        # 接受下载（不弹确认框）
        async def handle_download(download):
            path = DOWNLOAD_DIR / download.suggested_filename
            await download.save_as(str(path))
            print(f"📥 下载完成: {path}")

        page.on("download", handle_download)

        # 1. 打开数据中心页面
        print("[1] 打开数据中心")
        data_url = "https://creator.douyin.com/creator-micro/data-center/content"
        await page.goto(data_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)

        # 2. 找"导出数据"按钮
        print("[2] 查找导出按钮...")
        export_clicked = False
        for text in ["导出数据", "导出", "下载数据", "下载"]:
            btn = page.locator(f'text="{text}"').first
            if await btn.count() > 0:
                await btn.click(force=True)
                print(f"   ✓ 点击了'{text}'")
                export_clicked = True
                break

        if export_clicked:
            await asyncio.sleep(10)  # 等待下载完成
        else:
            print("   ⚠️ 未找到导出按钮，尝试截屏查看页面状态")
            await page.screenshot(path=str(DOWNLOAD_DIR / "data_center_page.png"))
            # 尝试找其他可能的按钮
            page_text = await page.evaluate("document.body.innerText")
            print(f"   页面文本预览: {page_text[:500]}")

        # 3. 检查下载文件
        print("\n[3] 下载目录:")
        for f in sorted(DOWNLOAD_DIR.glob("*.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            size_kb = f.stat().st_size / 1024
            print(f"   {f.name} ({size_kb:.1f} KB)")

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main())
