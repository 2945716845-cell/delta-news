"""三角洲日报 — 七源搜索 → DeepSeek AI分析 → 微信"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")
UA = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions)"}


def safe_fetch(url, headers=None, timeout=8, decode="utf-8"):
    try:
        req = urllib.request.Request(url, headers=headers or UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(decode, errors="ignore")
    except Exception:
        return ""


source_status = {}  # 记录每个源是否抓到数据

def fetch_all_hotspots() -> list[str]:
    global source_status
    items = []

    before = len(items)

    # 1. B站搜索
    for kw in ["三角洲行动+更新+赛季","三角洲行动+新枪","三角洲行动+活动","三角洲行动+攻略"]:
        html = safe_fetch(
            f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate",
            {**UA, "Referer": "https://www.bilibili.com"})
        if html:
            try:
                for v in json.loads(html).get("data",{}).get("result",[])[:3]:
                    t = re.sub(r'<[^>]+>','',v.get("title",""))
                    if v.get("play",0)>300 and len(t)>8 and t not in items:
                        items.append(f"[B站] {t}")
            except: pass
    source_status["B站"] = f"✅ {len([x for x in items if '[B站]' in x])}条"

    # 2. 17173
    before = len(items)
    html = safe_fetch("https://news.17173.com/z/deltaforce/")
    for m in re.finditer(r'<a[^>]*?title="([^"]*)"[^>]*?>', html):
        t = m.group(1).strip()
        if len(t)>8 and "三角洲" in t and t not in items:
            items.append(f"[17173] {t}")
    source_status["17173"] = f"✅ {len(items)-before}条" if len(items)>before else "❌ 未抓到"

    # 3. 三角洲官网
    before = len(items)
    html = safe_fetch("https://df.qq.com/web202206/news.shtml")
    for m in re.finditer(r'<a[^>]*?title="([^"]*)"[^>]*?>', html):
        t = m.group(1).strip()
        if len(t)>4 and t not in items:
            items.append(f"[官网] {t}")
    html2 = safe_fetch("https://df.qq.com/web202206/newslist.html?type=notice")
    for m in re.finditer(r'<a[^>]*?title="([^"]*)"[^>]*?>', html2):
        t = m.group(1).strip()
        if len(t)>4 and t not in items:
            items.append(f"[官网公告] {t}")
    source_status["官网"] = f"✅ {len(items)-before}条" if len(items)>before else "❌ 未抓到"

    # 4. 小红书
    before = len(items)
    html = safe_fetch("https://www.xiaohongshu.com/search_result?keyword=三角洲行动&type=51")
    for m in re.finditer(r'"title":"([^"]*三角洲[^"]*)"', html):
        t = m.group(1).strip()
        if len(t)>8 and t not in items:
            items.append(f"[小红书] {t}")
    source_status["小红书"] = f"✅ {len(items)-before}条" if len(items)>before else "❌ 未抓到"

    # 5. 小黑盒
    before = len(items)
    html = safe_fetch("https://api.xiaoheihe.cn/v3/bbs/app/community/feeds?community_id=deltaforce&limit=10")
    if html:
        try:
            for v in json.loads(html).get("result",{}).get("feeds",[])[:5]:
                t = v.get("title","") or v.get("content","")[:50]
                t = re.sub(r'<[^>]+>','',t).strip()
                if len(t)>8 and t not in items:
                    items.append(f"[小黑盒] {t}")
        except: pass
    html2 = safe_fetch("https://www.xiaoheihe.cn/community/board/deltaforce")
    for m in re.finditer(r'<a[^>]*?title="([^"]*)"[^>]*?>', html2):
        t = m.group(1).strip()
        if len(t)>6 and t not in items:
            items.append(f"[小黑盒] {t}")
    source_status["小黑盒"] = f"✅ {len(items)-before}条" if len(items)>before else "❌ 未抓到"

    # 6. 快手
    before = len(items)
    html = safe_fetch("https://www.kuaishou.com/search/video?searchKey=三角洲行动")
    for m in re.finditer(r'"caption":"([^"]*三角洲[^"]*)"', html):
        t = m.group(1).strip()
        if len(t)>8 and t not in items:
            items.append(f"[快手] {t}")
    source_status["快手"] = f"✅ {len(items)-before}条" if len(items)>before else "❌ 未抓到"

    # 7. 抖音
    before = len(items)
    html = safe_fetch("https://www.douyin.com/search/三角洲行动?type=video")
    for m in re.finditer(r'"desc":"([^"]*)"', html):
        t = m.group(1).strip()
        if len(t)>8 and "三角洲" in t and t not in items:
            items.append(f"[抖音] {t}")
    source_status["抖音"] = f"✅ {len(items)-before}条" if len(items)>before else "❌ 未抓到"

    return items[:15]


def ai_analyze(titles: list[str]) -> str:
    prompt = f"""今天是{today}。以下是《三角洲行动》全网络最新热点（来源：B站/17173/官网/小红书/小黑盒/快手/抖音）：

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(titles))}

请作为三角洲行动游戏分析师，分三步输出：

**第一步：热点判断**
筛选真热点。标准：
- "赛季更新""版本公告""枪械调整""削弱""加强" → 自动 🔥🔥🔥
- "新枪""新武器""新配件""新活动""新地图" → 🔥🔥 起步
- "性价比""粑粑枪""改枪码""穷鬼""廉价" → 🔥 起步
- 同一话题被多人讨论 → 升一级
- 播放量 > 5000 → 升一级
排除：纯击杀/搞笑/日常排位/标题党
列出3-5条真热点，标注🔥等级。

**二、热点总结**
每条一句话：为什么今天火？

**三、选题建议（2条）**
给博主"烟火"（三角洲性价比改枪，管家→少爷人设）推荐今日选题。

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

# 追加来源状态
src_report = "\n\n---\n📡 **数据来源**：" + " | ".join(f"{k} {v}" for k, v in source_status.items())
send_wechat(f"🎯 三角洲日报 | {today}", analysis + src_report)
