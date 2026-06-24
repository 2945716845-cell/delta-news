"""用阿里百炼 Qwen-VL 分析视频帧，输出文字描述。
用法: python analyze-frames.py <frames-dir> [问题，可选]
"""
import sys, os, json, base64
from pathlib import Path
import urllib.request

API_KEY = "sk-8c646774f9b04bdb83d665b7d38e67ef"
API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"


def encode_frame(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def analyze(frames_dir: str, question: str = "详细描述这个视频的画面内容，包括：操作手法、准星移动、击杀过程、画面是否自然流畅"):
    frames = sorted(Path(frames_dir).glob("frame_*.jpg"))
    if not frames:
        print("❌ 没找到帧文件")
        return

    # 挑关键帧（均匀采样 8 张，避免 token 爆炸）
    step = max(1, len(frames) // 8)
    sampled = frames[::step][:8]
    print(f"[分析] {len(frames)} 帧 → 采样 {len(sampled)} 张，调用 Qwen-VL...")

    content = [{"text": question}]
    for f in sampled:
        content.append({"image": f"data:image/jpeg;base64,{encode_frame(str(f))}"})

    body = json.dumps({
        "model": "qwen-vl-plus",
        "input": {"messages": [{"role": "user", "content": content}]}
    }).encode()

    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            text = result["output"]["choices"][0]["message"]["content"]
            # 可能返回 list 或 str
            if isinstance(text, list):
                text = "\n".join(t.get("text", "") for t in text if isinstance(t, dict))
            print("\n📹 画面分析结果：\n")
            print(text)
            print(f"\n[Token 用量] {result.get('usage', {})}")
    except Exception as e:
        print(f"❌ API 调用失败: {e}")


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else "D:/cheat-tools/video-frames"
    q = sys.argv[2] if len(sys.argv) > 2 else "详细描述视频画面：操作是否自然、有没有可疑的瞄准行为、画面节奏如何"
    analyze(d, q)
