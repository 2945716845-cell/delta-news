"""三角洲日报 — 搜资讯 → DeepSeek AI分析 → 微信推送"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def fetch_all_titles() -> list[str]:
    """从多个来源抓三角洲相关标题"""
    items = []

    # B站搜索API
    try:
        url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=三角洲行动+更新+赛季&order=pubdate"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for v in data.get("data", {}).get("result", [])[:8]:
                title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                play = v.get("play", 0)
                if play > 500 and len(title) > 8 and title not in items:
                    items.append(title)
    except Exception:
        pass

    # 抖音热搜关键词（用B站备选）
    try:
        url2 = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=三角洲行动+攻略+2026&order=pubdate"
        req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
        with urllib.request.urlopen(req2, timeout=10) as resp:
            data2 = json.loads(resp.read())
            for v in data2.get("data", {}).get("result", [])[:5]:
                title = re.sub(r'<[^>]+>', '', v.get("title", ""))
                if len(title) > 8 and title not in items:
                    items.append(title)
    except Exception:
        pass

    return items[:10]


def ai_analyze(titles: list[str]) -> str:
    """送 DeepSeek 分析总结"""
    prompt = f"""今天是{today}。以下是关于《三角洲行动》游戏的最新视频标题/资讯：

{chr(10).join(f'- {t}' for t in titles)}

请你作为三角洲行动游戏分析师，从这些标题中提炼出今天最重要的3-5条资讯，用简洁中文总结。
每条格式：**资讯标题** + 一句话分析。
如果标题显示有版本更新、枪械调整、赛季变动、新活动等内容，重点标注。
最后加一行：每日10:00自动推送。

总字数控制在500字以内。"""

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
    titles = fetch_all_titles()
    if titles:
        analysis = ai_analyze(titles)
        send_wechat(f"🎯 三角洲日报 | {today}", analysis)
    else:
        send_wechat(f"🎯 三角洲日报 | {today}",
            f"今日暂未抓取到资讯。\n\n> [抖音搜最新内容](https://www.douyin.com/search/三角洲行动)")
except Exception as e:
    send_wechat(f"🎯 三角洲日报 | {today}",
        f"日报生成失败：{str(e)[:100]}\n\n> [手动查看](https://www.douyin.com/search/三角洲行动)")
