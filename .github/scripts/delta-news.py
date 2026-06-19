"""三角洲日报 — 从官网+资讯站抓更新 → DeepSeek AI分析 → 微信"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def fetch_all_news() -> list[str]:
    items = []

    # 1. 国服官网公告
    try:
        req = urllib.request.Request("https://df.qq.com/web202206/news.html",
            headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            # 提取公告标题
            for m in re.finditer(r'<a[^>]*?title="([^"]*)"[^>]*?>', html):
                title = m.group(1).strip()
                if len(title) > 6 and title not in items:
                    items.append(f"[官网公告] {title}")
    except Exception:
        pass

    # 2. 17173 三角洲专区
    try:
        for kw in ["三角洲行动", "deltaforce"]:
            url = f"https://search.17173.com/s?q={urllib.request.quote(kw)}&type=news&from=deltaforce"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                for m in re.finditer(r'<a[^>]*?title="([^"]*三角洲[^"]*)"[^>]*?>', html):
                    title = m.group(1).strip()
                    if len(title) > 8 and title not in items:
                        items.append(f"[17173] {title}")
    except Exception:
        pass

    # 3. 360游戏 三角洲频道
    try:
        url = "https://360game.360.cn/article/list?keyword=三角洲行动"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            for m in re.finditer(r'<a[^>]*?title="([^"]*[三角洲|更新|赛季|枪械|版本][^"]*)"[^>]*?>', html):
                title = m.group(1).strip()
                if len(title) > 8 and title not in items:
                    items.append(f"[360游戏] {title}")
    except Exception:
        pass

    # 4. B站搜最新（备选）
    try:
        url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=三角洲行动+更新+赛季&order=pubdate"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for v in data.get("data", {}).get("result", [])[:5]:
                title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                play = v.get("play", 0)
                if play > 1000 and len(title) > 8 and title not in items:
                    items.append(f"[B站] {title}（{play}播放）")
    except Exception:
        pass

    return items[:10]


def ai_analyze(titles: list[str]) -> str:
    prompt = f"""今天是{today}。以下是关于《三角洲行动》游戏从官网和游戏资讯站抓取的最新内容：

{chr(10).join(f'- {t}' for t in titles)}

请作为三角洲行动游戏分析师，提炼今天最重要的3-5条资讯，用简洁中文总结。
每条格式：**资讯标题** + 一句话分析。
重点标注：版本更新、枪械调整、赛季变动、新活动、新武器。
总字数控制在500字以内。最后加一行「每日10:00自动推送」"""

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
        r = json.loads(resp.read())
        return r["choices"][0]["message"]["content"]


def send_wechat(title, content):
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{SERVER_KEY}.send",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


# 主逻辑
try:
    titles = fetch_all_news()
    if titles:
        analysis = ai_analyze(titles)
        send_wechat(f"🎯 三角洲日报 | {today}", analysis)
    else:
        send_wechat(f"🎯 三角洲日报 | {today}",
            f"今日暂未抓取到资讯。\n\n> 手动查看 [官网](https://df.qq.com) | [17173](https://news.17173.com/z/deltaforce/)")
except Exception as e:
    send_wechat(f"🎯 三角洲日报 | {today}", f"日报异常：{str(e)[:100]}")
