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

请作为三角洲行动游戏分析师，分三步输出：

**第一步：热点判断**
从以上标题中筛选出真正有热度的话题。判断标准：
- "赛季更新""版本公告""枪械调整""削弱""加强" → 自动 🔥🔥🔥
- "新枪""新武器""新配件""新活动""新地图" → 🔥🔥 起步
- "性价比""粑粑枪""改枪码""穷鬼""廉价" → 🔥 起步
- 同一把枪/同一个配件被多人讨论 → 升一级
- 播放量 > 5000 的视频标题 → 升一级
排除：纯击杀集锦、搞笑剪辑、个人实况/排位日常、标题党
列出3-5条**真热点**，标注热度等级（🔥🔥🔥=全社区讨论 / 🔥🔥=多人在做 / 🔥=新出现）。

**二、热点总结**
每个热点一句话分析：为什么今天这个话题火？跟游戏更新/赛季变动/玩家痛点有什么关系？

**三、选题建议（2条）**
基于今日热点，给游戏博主"烟火"（三角洲性价比改枪教学，人设"管家→少爷"）推荐选题。
每条：**选题方向** + 今天做这个的原因。

总字数<600字。末尾加「每日8:00自动推送 | 烟火专属」"""

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
