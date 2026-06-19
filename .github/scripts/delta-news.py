"""三角洲日报 — 全网络热点搜索 → DeepSeek AI分析 → 微信"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def fetch_all_hotspots() -> list[str]:
    items = []
    ua = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions)"}

    # 1. B站搜索（多关键词覆盖）
    for kw in ["三角洲行动+更新+赛季", "三角洲行动+新枪", "三角洲行动+活动", "三角洲行动+攻略"]:
        try:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate"
            req = urllib.request.Request(url, headers={**ua, "Referer": "https://www.bilibili.com"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                for v in data.get("data", {}).get("result", [])[:3]:
                    title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                    play = v.get("play", 0)
                    if play > 300 and len(title) > 8 and title not in items:
                        items.append(f"[B站] {title}")
        except Exception:
            pass

    # 2. 17173 三角洲专区
    try:
        req = urllib.request.Request("https://news.17173.com/z/deltaforce/", headers=ua)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            for m in re.finditer(r'<a[^>]*?title="([^"]*)"[^>]*?>', html):
                title = m.group(1).strip()
                if len(title) > 8 and "三角洲" in title and title not in items:
                    items.append(f"[17173] {title}")
    except Exception:
        pass

    # 3. 抖音热搜话题（用B站备选关键词补充）
    for kw in ["三角洲行动+版本更新", "三角洲行动+新赛季", "三角洲行动+改枪"]:
        try:
            url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate"
            req = urllib.request.Request(url, headers={**ua, "Referer": "https://www.bilibili.com"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                for v in data.get("data", {}).get("result", [])[:2]:
                    title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                    if len(title) > 8 and title not in items:
                        items.append(f"[抖音] {title}")
        except Exception:
            pass

    # 4. NGA 三角洲板块
    try:
        req = urllib.request.Request("https://bbs.nga.cn/thread.php?fid=820&rand=1", headers=ua)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("gbk", errors="ignore")
            for m in re.finditer(r'<a[^>]*?id="[^"]*?"[^>]*?class="[^"]*?"[^>]*?>(.*?)</a>', html):
                title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                if len(title) > 6 and title not in items:
                    items.append(f"[NGA] {title}")
    except Exception:
        pass

    return items[:12]


def ai_analyze(titles: list[str]) -> str:
    prompt = f"""今天是{today}。以下是《三角洲行动》全网络最新热点资讯（来源：B站/17173/抖音/NGA等）：

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(titles))}

请作为三角洲行动游戏分析师，分两部分输出：

**一、今日热点（3-5条）**
格式：**标题** — 一句话分析。
重点标注：版本更新/枪械调整/赛季变动/新活动。

**二、选题建议（2-3条）**
基于今日热点，给一个叫"烟火"的游戏博主（做三角洲性价比改枪教学视频，人设"管家→少爷"，账号风格参考饼干小警长）推荐今天的视频选题方向。
每条：**选题方向** + 一句话为什么今天做这个。

总字数<600字。末尾加「每日10:00自动推送 | 烟火专属」"""

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


titles = fetch_all_hotspots()
if not titles:
    titles = ["今日暂未抓取到热门资讯"]
analysis = ai_analyze(titles)
send_wechat(f"🎯 三角洲日报 | {today}", analysis)
