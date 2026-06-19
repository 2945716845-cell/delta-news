"""三角洲日报 — B站资讯 → DeepSeek AI分析 → 微信推送"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def fetch_titles() -> list[str]:
    items = []
    for kw in ["三角洲行动+更新+赛季", "三角洲行动+新版本", "三角洲行动+活动"]:
        try:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate"
            req = urllib.request.Request(url,
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                for v in data.get("data", {}).get("result", [])[:4]:
                    title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                    play = v.get("play", 0)
                    if play > 300 and len(title) > 8 and title not in items:
                        items.append(title)
        except Exception:
            pass
    return items[:8]


def ai_analyze(titles: list[str]) -> str:
    prompt = f"""今天是{today}。以下是《三角洲行动》最新相关视频标题（来自B站搜索）：

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(titles))}

请作为三角洲行动游戏分析师，从标题中提炼今天最重要的3-5条资讯趋势。每条格式：
**资讯标题** + 一句话分析。
重点标注：版本更新、枪械调整、赛季变动、新活动迹象。
总字数<500字。末尾加「每日10:00自动推送」"""

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


titles = fetch_titles()
if not titles:
    titles = ["三角洲行动今日无重大更新"]

analysis = ai_analyze(titles)
send_wechat(f"🎯 三角洲日报 | {today}", analysis)
