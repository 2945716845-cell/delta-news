"""改进版：打开抖音创作者中心视频数据页，从页面 DOM 提取流量来源等分析数据。
用法: python analyze-video-data.py <aweme_id>
"""
import asyncio, sys, json, re
from pathlib import Path
from playwright.async_api import async_playwright

AUTH = Path("D:/cheat-tools/.auth")


async def main(aweme_id: str):
    api_data = []

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=str(AUTH), headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = await ctx.new_page()

        # 拦截所有 JSON 响应（不加 URL 过滤，全捕）
        async def catch_json(resp):
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype:
                try:
                    body = await resp.json()
                    api_data.append({"url": resp.url, "data": body})
                except Exception:
                    pass

        page.on("response", catch_json)

        # 导航到视频数据页
        url = f"https://creator.douyin.com/creator-micro/data/following/media?item_id={aweme_id}"
        print(f"[打开] {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(12)

        # 尝试从页面提取所有可见文本
        page_text = await page.evaluate("document.body.innerText")
        # 也尝试从 React fiber / state 提取
        react_data = await page.evaluate("""
            () => {
                const results = [];
                // 尝试从 React root 提取
                const root = document.getElementById('root');
                if (root && root._reactRootContainer) {
                    results.push({source: 'react_root', data: Object.keys(root._reactRootContainer)});
                }
                // 尝试 window.__INITIAL_STATE__
                if (window.__INITIAL_STATE__) {
                    results.push({source: 'initial_state', data: window.__INITIAL_STATE__});
                }
                // 尝试查找所有可见卡片/面板文本
                const panels = document.querySelectorAll('[class*="card"], [class*="panel"], [class*="data"], [class*="stat"], [class*="traffic"]');
                panels.forEach(p => {
                    const text = p.innerText?.trim();
                    if (text && text.length > 10) results.push({source: 'panel', class: p.className, text: text.substring(0, 300)});
                });
                return results;
            }
        """)

        # 分析 API 数据
        traffic_apis = []
        for entry in api_data:
            u = entry["url"]
            d = entry["data"]
            ds = json.dumps(d, ensure_ascii=False)
            # 搜流量/推荐/搜索相关
            if any(kw in ds for kw in ["traffic", "source", "recommend", "search", "follow", "homepage", "播放来源", "流量来源", "推荐", "搜索", "关注", "个人主页"]):
                traffic_apis.append(entry)

        print(f"\n=== 共拦截 {len(api_data)} 个 API 调用 ===")
        print(f"=== 其中 {len(traffic_apis)} 个含流量关键词 ===")

        for t in traffic_apis:
            print(f"\n🔑 {t['url']}")
            print(json.dumps(t["data"], ensure_ascii=False)[:500])

        # 保存完整结果
        out_path = Path(f"D:/cheat-tools/video-frames/analysis-{aweme_id}.json")
        out_path.write_text(json.dumps({
            "api_data": api_data,
            "traffic_apis": traffic_apis,
            "react_data": react_data,
            "page_text": page_text[:5000]
        }, ensure_ascii=False, indent=2), encoding="utf-8")

        # 打印页面关键区域
        print(f"\n=== 页面文本前 3000 字 ===")
        print(page_text[:3000])

        await ctx.close()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "7641829650947149091"))
