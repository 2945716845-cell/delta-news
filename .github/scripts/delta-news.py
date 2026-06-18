"""三角洲行动日报 — GitHub Actions 每天10点推送微信"""
import os, json, urllib.request, datetime

SERVER_KEY = os.environ["SERVER_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def send_wechat(title, content):
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{SERVER_KEY}.send",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


send_wechat(f"🎯 三角洲日报 | {today}", """
📰 **今日更新速查**

1. 🔍 [抖音搜索最新攻略](https://www.douyin.com/search/三角洲行动)
2. 🔍 [B站搜最新改枪视频](https://search.bilibili.com/all?keyword=三角洲行动+改枪)
3. 🔍 [抖音搜最新版本更新](https://www.douyin.com/search/三角洲行动+更新)

---
> 每日10:00自动推送 | 烟火专用
""")
