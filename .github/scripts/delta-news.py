"""三角洲日报 — 最简版测试"""
import os, json, urllib.request, datetime

SERVER_KEY = os.environ["SERVER_KEY"]
DEEPSEEK_KEY = os.environ["DEEPSEEK_KEY"]
today = datetime.date.today().strftime("%m月%d日")


def send_wechat(title, content):
    data = json.dumps({"title": title, "desp": content}).encode()
    req = urllib.request.Request(
        f"https://sctapi.ftqq.com/{SERVER_KEY}.send",
        data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode()


# 先测 Server酱
resp = send_wechat(f"🎯 三角洲日报 | {today} (测试)",
    "这是测试消息。如果收到说明 Server酱 通道正常。\n\n> 每日10:00自动推送")
print("Server酱:", resp)

# 再测 B站
try:
    url = "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=三角洲行动&order=pubdate"
    req = urllib.request.Request(url,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        titles = [v.get("title","") for v in data.get("data",{}).get("result",[])[:3]]
        print("B站:", titles)
except Exception as e:
    print(f"B站失败: {e}")

# 测 DeepSeek
try:
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "回复: OK"}],
        "max_tokens": 10
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("DeepSeek:", json.loads(resp.read())["choices"][0]["message"]["content"])
except Exception as e:
    print(f"DeepSeek失败: {e}")
