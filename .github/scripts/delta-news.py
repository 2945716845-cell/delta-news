"""三角洲行动日报 — GitHub Actions 每天10点推送微信"""
import os, json, urllib.request, datetime, re

SERVER_KEY = os.environ["SERVER_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def search_bing():
    """用 Bing 搜中文资讯（比 Google 容易通过）"""
    query = "三角洲行动+更新+版本+赛季"
    url = f"https://www.bing.com/search?q={urllib.request.quote(query)}&filters=ex1:\"ez1\"&hl=zh-CN"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GitHubActions/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    titles = []
    for m in re.finditer(r'<h2[^>]*?>.*?<a[^>]*?>(.*?)</a>', html, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if 5 < len(text) < 200 and "三角洲" not in text.lower():
            titles.append(text)
    return titles[:5]


def send_wechat(title, content):
    """通过 Server酱 推送到微信"""
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{SERVER_KEY}.send",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


# 主逻辑
try:
    news = search_bing()
except Exception:
    news = []

if news:
    lines = [f"## 🎯 三角洲日报 | {today}\n"]
    for i, t in enumerate(news, 1):
        lines.append(f"{i}. {t}")
    send_wechat(f"🎯 三角洲日报 | {today}", "\n".join(lines))
else:
    send_wechat(f"🎯 三角洲日报 | {today}",
        f"今日资讯请查看：\n\n"
        f"📱 [抖音搜索：三角洲行动](https://www.douyin.com/search/三角洲行动)\n"
        f"📺 [B站三角洲专区](https://search.bilibili.com/all?keyword=三角洲行动)\n"
        f"\n每日10点自动推送。")
