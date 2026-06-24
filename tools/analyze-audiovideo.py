"""视频+音频一体化分析：DashScope Qwen-VL 直接处理带声音的视频片段。
用法: python analyze-audiovideo.py <video-file> [问题]
"""
import sys, json, base64, urllib.request, subprocess, tempfile, os
from pathlib import Path

API_KEY = "sk-8c646774f9b04bdb83d665b7d38e67ef"
FFMPEG = str(Path("D:/cheat-tools/npm-global/node_modules/@ffmpeg-installer/win32-x64/ffmpeg.exe"))
OUT = Path("D:/cheat-tools/video-frames")


def prepare_clip(video_path: str, start: float = 0, duration: float = 60) -> str:
    """用 ffmpeg 截取视频片段（保留音频，降低分辨率以控制文件大小）。"""
    clip_path = str(OUT / "analysis_clip.mp4")
    cmd = [
        FFMPEG, "-y",
        "-ss", str(start), "-t", str(duration),
        "-i", video_path,
        "-vf", "scale=480:-2,fps=8",  # 降分辨率+帧率控制大小
        "-c:v", "libx264", "-crf", "30",
        "-c:a", "aac", "-b:a", "64k",
        "-movflags", "+faststart",
        clip_path
    ]
    subprocess.run(cmd, capture_output=True)
    return clip_path if os.path.exists(clip_path) else ""


def analyze_clip(clip_path: str, question: str) -> str:
    """将视频片段送 DashScope Qwen-VL（完整视听理解）。"""
    with open(clip_path, "rb") as f:
        video_b64 = base64.b64encode(f.read()).decode()

    body = json.dumps({
        "model": "qwen-vl-max",
        "input": {"messages": [{"role": "user", "content": [
            {"video": f"data:video/mp4;base64,{video_b64}"},
            {"text": question}
        ]}]}
    }).encode()

    req = urllib.request.Request(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
        data=body,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        r = json.loads(resp.read())
        c = r["output"]["choices"][0]["message"]["content"]
        if isinstance(c, list):
            return "\n".join(t.get("text", "") for t in c if isinstance(t, dict))
        return c


def main():
    video = sys.argv[1] if len(sys.argv) > 1 else None
    if not video or not os.path.exists(video):
        print("用法: python analyze-audiovideo.py <视频文件> [分析问题]")
        return

    question = sys.argv[2] if len(sys.argv) > 2 else (
        "你是游戏视频分析师。请完整观看这个三角洲行动(Delta Force)游戏视频（包含画面和声音），"
        "从以下维度综合分析："
        "1.开头3秒的视听冲击力——画面是否连续、枪声/配音是否立刻出现"
        "2.画面节奏与音频配合——剪辑点是否跟枪声/音乐节拍对齐"
        "3.操作可信度——准星移动是否自然、有无可疑行为"
        "4.情绪节奏——配音语气、枪声音效和画面激烈程度是否匹配"
        "5.整体留存预测——哪些时间点观众最可能划走、哪些片段最有分享冲动"
        "用中文回答，每条给出具体时间点和建议。"
    )

    print(f"[1] 处理视频: {video}")
    OUT.mkdir(parents=True, exist_ok=True)

    # 截取前 60 秒（抖音视频的核心分析窗口）
    print("[2] 准备分析片段（带音频）...")
    clip = prepare_clip(video, start=0, duration=60)
    if not clip:
        print("❌ ffmpeg 处理失败")
        return

    size_mb = os.path.getsize(clip) / 1024 / 1024
    print(f"    片段大小: {size_mb:.1f}MB")

    print("[3] 送 Qwen-VL 一体化分析（画面+音频）...")
    result = analyze_clip(clip, question)

    print("\n📹🎵 视听一体化分析结果：\n")
    print(result)
    print(f"\n[Token用量] {r.get('usage', {})}" if 'r' in dir() else "")


if __name__ == "__main__":
    main()
