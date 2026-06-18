"""三角洲行动日报 — 从多个来源抓最新资讯推送微信"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def fetch_all_news() -> list[str]:
    items = []

    # 1. B站搜索三角洲行动（按最新排序）
    try:
        url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=三角洲行动+更新&order=pubdate"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for v in data.get("data", {}).get("result", [])[:5]:
                title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                play = v.get("play", 0)
                if play > 1000 and len(title) > 6:
                    items.append(f"📺 {title}（{play}播放）")
    except Exception:
        pass

    # 2. 17173 三角洲专区
    try:
        url = "https://news.17173.com/z/deltaforce/"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            for m in re.finditer(r'<a[^>]*title="([^"]*三角洲[^"]*)"[^>]*>', html):
                title = m.group(1).strip()
                if len(title) > 8 and title not in "".join(items):
                    items.append(f"📰 {title}")
                    if len(items) >= 8:
                        break
    except Exception:
        pass

    return items[:6]


def send_wechat(title, content):
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{SERVER_KEY}.send",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


news = fetch_all_news()
if news:
    lines = [f"## 🎯 三角洲日报 | {today}\n"]
    for t in news:
        lines.append(f"- {t}")
    send_wechat(f"🎯 三角洲日报 | {today}", "\n".join(lines))
else:
    send_wechat(f"🎯 三角洲日报 | {today}",
        f"今日暂未抓取到更新内容。\n\n"
        f"• [抖音搜三角洲行动](https://www.douyin.com/search/三角洲行动)\n"
        f"• [B站搜三角洲攻略](https://search.bilibili.com/all?keyword=三角洲行动)")
