"""三角洲日报 — 多源抓取 → DeepSeek分析 → 微信"""
import os, json, urllib.request, datetime, re, traceback

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def safe_fetch(url, headers=None, timeout=10):
    """安全请求"""
    if headers is None:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def fetch_all_news() -> list[str]:
    items = []

    # 1. B站 API（最稳定，GitHub Actions 能访问）
    try:
        for kw in ["三角洲行动+更新+赛季", "三角洲行动+新版本", "三角洲行动+活动"]:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate"
            html = safe_fetch(url, {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
            if html:
                data = json.loads(html)
                for v in data.get("data", {}).get("result", [])[:4]:
                    title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                    play = v.get("play", 0)
                    if play > 300 and len(title) > 8 and title not in items:
                        items.append(f"[B站] {title}")
    except Exception:
        pass

    # 2. 17173 三角洲专区
    try:
        html = safe_fetch("https://news.17173.com/z/deltaforce/")
        for m in re.finditer(r'<a[^>]*?title="([^"]*)"[^>]*?>', html):
            title = m.group(1).strip()
            if len(title) > 8 and "三角洲" in title and title not in items:
                items.append(f"[17173] {title}")
    except Exception:
        pass

    return items[:8]


def ai_analyze(titles: list[str]) -> str:
    prompt = f"""今天是{today}。以下是《三角洲行动》最新资讯标题：

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(titles))}

请以三角洲行动游戏分析师身份，总结今天最重要的3-5条资讯。格式：
**资讯标题** + 一句话分析。
重点标注版更/枪械/赛季/活动变动。
最后加「每日10:00自动推送」。
总字数<500。"""

    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def send_wechat(title, content):
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{SERVER_KEY}.send",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


try:
    titles = fetch_all_news()
    if not titles:
        titles = ["三角洲行动每日资讯 - 今日无重大更新"]
    analysis = ai_analyze(titles)
    send_wechat(f"🎯 三角洲日报 | {today}", analysis)
except Exception as e:
    send_wechat(f"🎯 三角洲日报 | {today}",
        f"抓取异常：{str(e)[:150]}\n\n> [官方公告](https://df.qq.com) | [17173专区](https://news.17173.com/z/deltaforce/)")
