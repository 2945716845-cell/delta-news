"""三角洲日报 — newsnow多源聚合 + B站 → DeepSeek分析 → 微信"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")
UA = {"User-Agent": "Mozilla/5.0 (compatible; GitHubActions)"}

source_status = {}


def safe_fetch(url, headers=None, timeout=8, decode="utf-8"):
    try:
        req = urllib.request.Request(url, headers=headers or UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(decode, errors="ignore")
    except:
        return ""


def fetch_all_hotspots() -> list[str]:
    global source_status
    items = []

    # === 主源：newsnow API（多平台聚合，TrendRadar同款）===
    sources = {"douyin": "抖音", "kuaishou": "快手", "bilibili-hot-search": "B站热搜",
               "toutiao": "今日头条", "baidu": "百度", "zhihu": "知乎", "weibo": "微博"}
    for sid, sname in sources.items():
        before = len(items)
        html = safe_fetch(f"https://newsnow.busiyi.world/api/s?id={sid}&latest=10&limit=5")
        if html:
            try:
                data = json.loads(html)
                news_list = data.get("items", data.get("data", {}).get("items", []))
                for v in news_list[:3]:
                    t = v.get("title", "") or v.get("name", "")
                    t = re.sub(r'<[^>]+>', '', t).strip()
                    if len(t) > 4 and t not in items and any(kw in t for kw in ["三角洲", "枪", "改枪", "大坝", "行政", "赛季"]):
                        items.append(f"[{sname}] {t}")
            except:
                pass
        source_status[sname] = f"✅ {len(items) - before}条" if len(items) > before else "❌"

    # === 备选：B站 API 直搜 ===
    before = len(items)
    for kw in ["三角洲行动+更新", "三角洲行动+新赛季", "三角洲行动+新枪", "三角洲行动+改枪",
               "三角洲行动+活动", "三角洲行动+攻略", "三角洲行动+点位", "三角洲行动+大坝"]:
        html = safe_fetch(
            f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate",
            {**UA, "Referer": "https://www.bilibili.com"})
        if html:
            try:
                for v in json.loads(html).get("data", {}).get("result", [])[:3]:
                    t = re.sub(r'<[^>]+>', '', v.get("title", ""))
                    if v.get("play", 0) > 300 and len(t) > 8 and t not in items:
                        items.append(f"[B站] {t}")
            except:
                pass
    source_status["B站直搜"] = f"✅ {len(items) - before}条" if len(items) > before else "❌"

    return items[:15]


def ai_analyze(titles: list[str]) -> str:
    prompt = f"""今天是{today}。以下是《三角洲行动》全网络最新热点（来源：newsnow多平台+B站）：

{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(titles))}

请作为三角洲行动游戏分析师，分三步输出：

**第一步：热点判断** 筛选真热点。标准：
- "赛季更新""版本公告""枪械调整""削弱""加强" → 🔥🔥🔥
- "新枪""新武器""新配件""新活动""新地图" → 🔥🔥 起步
- "性价比""粑粑枪""改枪码""穷鬼""廉价" → 🔥 起步
- 同一话题多源出现 → 升一级
排除纯击杀/搞笑/日常/标题党。
列出3-5条真热点，标注🔥等级。

**二、热点总结** 每条一句话：为什么今天火？

**三、选题建议（2条）** 给博主"烟火"（三角洲性价比改枪，管家→少爷人设）推荐今日选题。

总字数<600字。末尾加「每日8:00自动推送 | 烟火专属」"""

    body = json.dumps({"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 800}).encode()
    req = urllib.request.Request("https://api.deepseek.com/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def send_wechat(title, content):
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(f"https://sctapi.ftqq.com/{SERVER_KEY}.send", data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


titles = fetch_all_hotspots()
if not titles: titles = ["今日暂未抓取到热门资讯"]
analysis = ai_analyze(titles)
src_report = "\n\n---\n📡 **数据来源**：" + " | ".join(f"{k} {v}" for k, v in source_status.items())
send_wechat(f"🎯 三角洲日报 | {today}", analysis + src_report)
