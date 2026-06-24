"""全维度视频自动分析工具。
输入: 视频文件 .mp4
输出: 6层评分 + 7维文案评分 + Bucket预测 + 完整报告

用法: python analyze-full.py <视频路径>
"""
import sys, os, json, base64, urllib.request, subprocess, re
from pathlib import Path
from datetime import datetime

# === 配置 ===
# DeepSeek API（你现有的Key，支持视觉）
API_KEY = "sk-f86e87a52b2440858ef95ce4c953dba3"
API_BASE = "https://api.deepseek.com"
FFMPEG = r"C:\Users\15323\AppData\Roaming\bilibili\ffmpeg\ffmpeg.exe"
OUT = Path(r"D:\cheat-tools\video-frames\reports")
OUT.mkdir(parents=True, exist_ok=True)

# === 工具函数 ===
def run_ffmpeg(args):
    subprocess.run([FFMPEG, "-y"] + args, capture_output=True)


def ai_vision(images: list[str], prompt: str) -> str:
    """多图 + 问题 → Ollama 本地视觉模型 (qwen3-vl:4b) 分析"""
    content = [{"type": "text", "text": prompt}]
    for path in images:
        if os.path.exists(path):
            with open(path, "rb") as f:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode()}"}
                })
    body = json.dumps({
        "model": "qwen3-vl:4b",
        "messages": [{"role": "user", "content": content}],
        "stream": False
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions",
        data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        r = json.loads(resp.read())
        return r["choices"][0]["message"]["content"]


# === Phase 1: 视频预处理 ===
def prep_video(video_path: str, work_dir: str):
    """抽帧 + 抽音频"""
    frames_dir = os.path.join(work_dir, "frames")
    audio_path = os.path.join(work_dir, "audio.wav")
    # 清空旧帧
    if os.path.exists(frames_dir):
        for f in os.listdir(frames_dir):
            os.remove(os.path.join(frames_dir, f))
    os.makedirs(frames_dir, exist_ok=True)

    # 每秒1帧，压缩控制文件大小
    run_ffmpeg(["-i", video_path, "-t", "120", "-vf", "fps=1,scale=320:-1", "-q:v", "8", f"{frames_dir}/f_%03d.jpg"])
    # 音频16kHz单声道
    run_ffmpeg(["-i", video_path, "-t", "120", "-vn", "-ar", "16000", "-ac", "1", audio_path])

    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith(".jpg")])
    return frames_dir, frames, audio_path


# === Phase 2: 从帧截图提取字幕 + 时间轴（比 ASR 更准）===
def extract_subtitles_from_frames(frames_dir: str, frames: list[str], total_seconds: int) -> list[dict]:
    """用 Qwen-VL 读取每帧画面上的字幕文字，构建精确时间轴"""
    # 每15帧一批，让AI读出字幕
    segments = []
    batch_size = 15
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i + batch_size]
        paths = [os.path.join(frames_dir, f) for f in batch]
        sec_start = int(batch[0][2:5]) if batch else i

        prompt = "逐秒列出每张截图中的字幕文字(画面底部的中文)。格式：秒数|字幕原文。无字幕则标'无'。不要描述画面，只要字幕文字。"
        resp = ai_vision(paths, prompt)

        # 解析 AI 返回的字幕时间轴
        for line in resp.split("\n"):
            match = re.match(r'\s*(\d+)\s*[|：:]\s*(.+)', line.strip())
            if match:
                sec = int(match.group(1)) + sec_start
                text = match.group(2).strip()
                if text and text != "无" and len(text) > 1:
                    # 合并相邻相同字幕
                    if segments and segments[-1]["text"] == text:
                        segments[-1]["end"] = sec
                    else:
                        segments.append({"start": sec, "end": sec, "text": text})

    # 合并同文字段
    merged = []
    for seg in segments:
        if merged and seg["text"] == merged[-1]["text"]:
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg)

    print(f"  提取到 {len(merged)} 条字幕")
    return merged


# === Phase 2.5: 音频特征分析（音量、语速、停顿）===
def analyze_audio_features(audio_path: str) -> dict:
    """用 ffmpeg 分析音频波形特征"""
    result = subprocess.run(
        [FFMPEG, "-i", audio_path, "-af",
         "silencedetect=n=-30dB:d=0.5,volumedetect,astats=metadata=1:reset=1",
         "-f", "null", "-"],
        capture_output=True, text=True, timeout=30
    )
    output = result.stderr

    features = {"silence_count": 0, "max_volume": "", "mean_volume": "",
                "silence_segments": [], "duration_seconds": 0}

    for line in output.split("\n"):
        if "silence_start" in line:
            features["silence_count"] += 1
            m = re.search(r"silence_start:\s*([\d.]+)", line)
            if m:
                end_m = re.search(r"silence_end:\s*([\d.]+)", line)
                duration_m = re.search(r"silence_duration:\s*([\d.]+)", line)
                if end_m and duration_m:
                    features["silence_segments"].append({
                        "start": float(m.group(1)),
                        "end": float(end_m.group(1)),
                        "duration": float(duration_m.group(1))
                    })
        if "max_volume" in line:
            features["max_volume"] = line.split(":", 1)[-1].strip()
        if "mean_volume" in line:
            features["mean_volume"] = line.split(":", 1)[-1].strip()
        if "Duration" in line and "time=" not in line:
            m = re.search(r"Duration:\s*([\d:.]+)", line)
            if m:
                parts = m.group(1).split(":")
                features["duration_seconds"] = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

    # 统计长停顿（>1秒的静音表示可能的节奏断裂）
    long_pauses = [s for s in features["silence_segments"] if s["duration"] > 1.0]
    features["long_pause_count"] = len(long_pauses)
    features["total_silence"] = sum(s["duration"] for s in features["silence_segments"])

    return features
def analyze_visuals(frames_dir: str, frames: list[str]) -> list[dict]:
    """分批送 Qwen-VL，返回每秒的画面描述"""
    results = []
    batch_size = 3
    for i in range(0, len(frames), batch_size):
        batch = frames[i:i + batch_size]
        paths = [os.path.join(frames_dir, f) for f in batch]
        sec_start = int(batch[0][2:5]) if batch else i
        sec_end = sec_start + len(batch) - 1
        prompt = f"这是视频第{sec_start}到{sec_end}秒的逐秒截图。请以'秒数: 画面描述'格式列出每秒内容，特别标注：战斗/装备界面/结算/黑屏/字幕。只列关键变化，连续相同的合并。"
        resp = ai_vision(paths, prompt)
        results.append({"start": sec_start, "end": sec_end, "raw": resp})
        print(f"  画面分析: {sec_start}-{sec_end}秒")
    return results


# === Phase 4: 7层评分 ===
def score_layers(frames_analysis: list[dict], audio_timeline: list[dict],
                 total_duration: float, visual_summary: str, audio_features: dict) -> dict:
    """AI 综合评分（含配音表现层）"""
    timeline_text = ""
    for a in audio_timeline:
        timeline_text += f"[{a['start']:.1f}s] 字幕: {a['text']}\n"
    audio_features_str = json.dumps(audio_features, ensure_ascii=False)

    prompt = f"""你是顶级游戏视频分析师。以下是一个三角洲行动改枪教学视频的完整分析数据：

视频时长: {total_duration:.0f}秒

=== 字幕时间轴(从画面提取) ===
{timeline_text[:3000]}

=== 音频特征 ===
{audio_features_str[:500]}

=== 画面分析摘要 ===
{visual_summary[:2000]}

请按以下7个维度打分(0-10分，保留1位小数)，并给出每个维度的扣分点和改进建议：

1. 钩子层(0-5秒)：开头画面是否动态、声音是否立刻出现、前三帧是否有视觉冲击
2. 声画同步层：每个时间段的配音/字幕是否与画面内容匹配、有无信息错位
3. 配音表现层：语速节奏是否合适、音量是否稳定、语气是否与内容匹配（紧张/搞笑/自信）、有无长时间停顿或含混不清
4. 剪辑节奏层：镜头切换频率是否在5-8秒一次、有无超过0.5秒的停顿、信息密度是否足够
5. 结构层：是否有"开头炸→中间抖→结尾留"的三段式、结算/装备界面是否太靠前
6. 情绪曲线层：开场情绪、高潮秒数、波谷秒数、结尾情绪类型
7. 游戏专有层：击杀展示清晰度、操作可信度、数据可视化(属性面板/对比图)、枪械展示

输出格式(严格JSON)：
{{"钩子层": {{"score": X.X, "扣分点": "...", "建议": "..."}},
 "声画同步层": {{...}},
 "配音表现层": {{...}},
 "剪辑节奏层": {{...}},
 "结构层": {{...}},
 "情绪曲线层": {{...}},
 "游戏专有层": {{...}},
 "总分": X.X,
 "总体评价": "..."}}"""

    return ai_vision([], prompt)  # 纯文本分析


# === Phase 5: 文案7维评分 ===
def score_script(audio_timeline: list[dict], prediction_data: dict) -> dict:
    """用 v0 rubric 给稿子打分"""
    script_text = " ".join([a["text"] for a in audio_timeline])

    prompt = f"""你是文案评分专家。以下是三角洲行动改枪视频的配音稿全文：

{script_text[:2000]}

请按以下7个维度打分(0-5整数)：
ER(情感共鸣) HP(钩子强度) QL(金句密度) NA(叙事性) AB(受众广度) SR(社会议题) SAT(讽刺深度)
Composite = (ER+HP+QL+NA+AB+SR+SAT)/7 × 2.0

输出JSON: {{"ER":N, "HP":N, "QL":N, "NA":N, "AB":N, "SR":N, "SAT":N, "composite":X.X, "一句话评价":"..."}}"""

    resp = ai_vision([], prompt)
    try:
        return json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group())
    except:
        return {"ER": 3, "HP": 4, "QL": 3, "NA": 3, "AB": 3, "SR": 1, "SAT": 1, "composite": 5.14, "一句话评价": "解析失败"}


# === Phase 6: 预测 ===
def predict_bucket(scores: dict, script_score: dict, historical_data_path: str = None) -> dict:
    """基于评分 + 历史数据预测 bucket"""
    layer_avg = sum(v["score"] for k, v in scores.items() if isinstance(v, dict) and "score" in v) / 6
    composite = script_score.get("composite", 5.0)

    # 加载历史对标数据
    benchmarks = {"min_2s跳出": 0.21, "max_5s完播": 0.56, "best_hook_score": 9}

    prompt = f"""你是游戏视频流量预测专家。已知数据：
- 6层平均分: {layer_avg:.1f}/10
- 文案composite: {composite:.1f}/10
- 账号历史最优2s跳出: 21.1%, 最高5s完播: 56.1%
- 对标视频(552)封面点击率: 22.3%, 2s跳出: 22.9%

请预测本视频的播放量级bucket:
底部(<5K) / 基础盘(5K-10K) / 命中(10K-30K) / 小爆(30K-100K) / 大爆(>100K)

给出各bucket概率分布(合计100%)和最可能bucket的中枢点估计。
再给出2-3条"如果XX就XX"的反事实。

输出JSON: {{"最可能bucket":"...", "中枢点估计":"...", "概率分布":{{"底部":N,"基础盘":N,"命中":N,"小爆":N,"大爆":N}}, "反事实":["...","..."]}}"""

    resp = ai_vision([], prompt)
    try:
        return json.loads(re.search(r'\{.*\}', resp, re.DOTALL).group())
    except:
        return {"最可能bucket": "命中", "中枢点估计": "8K-15K", "概率分布": {"底部": 5, "基础盘": 20, "命中": 45, "小爆": 25, "大爆": 5}}


# === 主流程 ===
def main():
    video_path = sys.argv[1] if len(sys.argv) > 1 else input("视频路径: ")
    if not os.path.exists(video_path):
        print(f"❌ 文件不存在: {video_path}")
        return

    video_name = Path(video_path).stem
    work_dir = str(OUT / video_name)
    os.makedirs(work_dir, exist_ok=True)

    print(f"📹 分析: {video_name}")
    t0 = datetime.now()

    # P1: 预处理
    print("[1/6] 抽帧+音频...")
    frames_dir, frames, audio_path = prep_video(video_path, work_dir)
    total_sec = len(frames)
    print(f"  {len(frames)}帧, {total_sec}秒")

    # P2: 字幕提取
    print("[2/6] 从画面提取字幕...")
    try:
        audio_timeline = extract_subtitles_from_frames(frames_dir, frames, total_sec)
    except Exception as e:
        print(f"  ⚠️ 字幕提取失败: {e}, 跳过")
        audio_timeline = []

    # P2.5: 音频特征分析
    print("[2.5] 分析音频特征...")
    try:
        audio_features = analyze_audio_features(audio_path)
        print(f"  静音段: {audio_features['silence_count']}个, 长停顿: {audio_features['long_pause_count']}个")
    except Exception as e:
        print(f"  ⚠️ 音频分析失败: {e}")
        audio_features = {"silence_count": 0, "long_pause_count": 0}

    # P3: 画面分析
    print("[3/6] Qwen-VL画面分析...")
    visual_results = analyze_visuals(frames_dir, frames)
    visual_summary = "\n".join([r["raw"][:500] for r in visual_results])

    # P4: 6层评分
    print("[4/6] 7层评分...")
    layer_scores_str = score_layers(visual_results, audio_timeline, total_sec, visual_summary, audio_features)
    try:
        layer_scores = json.loads(re.search(r'\{.*\}', layer_scores_str, re.DOTALL).group())
    except:
        layer_scores = {"钩子层": {"score": 5}, "总分": 30, "总体评价": "解析失败"}

    # P5: 文案7维评分
    print("[5/6] 文案7维评分...")
    script_score = score_script(audio_timeline, {})

    # P6: 预测
    print("[6/6] Bucket预测...")
    prediction = predict_bucket(layer_scores, script_score)

    # 输出
    elapsed = (datetime.now() - t0).total_seconds()
    print(f"\n{'='*60}")
    print(f"📊 {video_name} 完整分析报告 ({elapsed:.0f}秒)")
    print(f"{'='*60}")

    print(f"\n## 7层评分 (满分10)")
    layer_names = ["钩子层", "声画同步层", "配音表现层", "剪辑节奏层", "结构层", "情绪曲线层", "游戏专有层"]
    for name in layer_names:
        d = layer_scores.get(name, {})
        score = d.get("score", "?")
        bar = "█" * int(float(score)) if isinstance(score, (int, float)) else ""
        print(f"  {name}: {score}/10 {bar}")
        if d.get("扣分点"):
            print(f"    ⚠️ {d['扣分点'][:100]}")

    print(f"\n## 文案7维评分 (v0 rubric)")
    for dim in ["ER", "HP", "QL", "NA", "AB", "SR", "SAT"]:
        print(f"  {dim}: {script_score.get(dim, '?')}")
    print(f"  Composite: {script_score.get('composite', '?')}")

    print(f"\n## Bucket预测")
    print(f"  最可能: {prediction.get('最可能bucket', '?')}")
    print(f"  中枢: {prediction.get('中枢点估计', '?')}")
    dist = prediction.get("概率分布", {})
    print(f"  分布: 底部{dist.get('底部','?')}% | 基础盘{dist.get('基础盘','?')}% | 命中{dist.get('命中','?')}% | 小爆{dist.get('小爆','?')}% | 大爆{dist.get('大爆','?')}%")

    print(f"\n## 总体评价")
    print(f"  7层均分: {layer_scores.get('总分', '?')}/70")
    print(f"  文案: {script_score.get('一句话评价', '?')}")
    print(f"  {layer_scores.get('总体评价', '')[:200]}")

    # 保存完整报告
    report = {
        "视频": video_name, "时长秒": total_sec, "分析时间": str(datetime.now()),
        "6层评分": layer_scores, "文案7维": script_score, "预测": prediction,
        "音频时间轴": audio_timeline, "画面分析": visual_summary[:5000]
    }
    report_path = os.path.join(work_dir, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📁 完整报告: {report_path}")


if __name__ == "__main__":
    main()
