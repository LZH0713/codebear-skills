#!/usr/bin/env python3
"""Stage-0 Viral Video Deconstructor & Original Script Generator.

Pipeline:
  1) Accepts a viral video URL (YouTube/IG/FB/TikTok/direct MP4 via yt-dlp) OR a local .mp4 file
  2) Extracts 1-fps contact sheet (timeline_sheet.png) + audio track
  3) Optionally transcribes speech via whisper/faster-whisper if installed
  4) Calls muse-spark (via .muse.env) to:
     - Deconstruct the viral video (hook, pain points, beat-by-beat table, viral drivers, AI feasibility)
     - Inject our own SKU listing facts (listing.md) to generate an original FB script + shots.json draft
       directly compatible with run_muse.py + build_fb_15s.py!

Usage:
  python3 analyze_viral.py --input "https://www.youtube.com/watch?v=..." \
      --sku "./listing.md" \
      --out "./ref"
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(work_dir):
    if os.environ.get("MUSE_BASE") and os.environ.get("MUSE_KEY"):
        return {
            "MUSE_BASE": os.environ["MUSE_BASE"].rstrip("/"),
            "MUSE_KEY": os.environ["MUSE_KEY"],
        }
    candidates = [
        os.path.join(work_dir, ".muse.env"),
        os.path.join(os.getcwd(), ".muse.env"),
        os.path.join(os.path.dirname(os.getcwd()), ".muse.env"),
        os.path.join(HERE, ".muse.env"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        raise FileNotFoundError("Missing .muse.env (MUSE_BASE / MUSE_KEY)")
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def download_video(url, out_mp4):
    import site
    ytdlp = shutil.which("yt-dlp") or os.path.join(site.getuserbase(), "bin", "yt-dlp")
    if not os.path.exists(ytdlp):
        raise RuntimeError(
            "yt-dlp not found. Install via `python3 -m pip install --user yt-dlp` or pass a local .mp4 via --input"
        )
    cmd = [
        ytdlp, "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
        "--merge-output-format", "mp4",
        "-o", out_mp4, url,
    ]
    subprocess.run(cmd, check=True)
    return out_mp4


def probe_duration(mp4_path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4_path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def build_timeline_sheet(mp4_path, out_dir, interval=1.5, max_frames=20):
    dur = probe_duration(mp4_path)
    step = max(interval, dur / max_frames)
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    stamps = []
    t = 0.2
    while t < dur - 0.1 and len(stamps) < max_frames:
        stamps.append(round(t, 2))
        t += step

    imgs = []
    for idx, ts in enumerate(stamps):
        fp = os.path.join(frames_dir, f"f_{idx:02d}_{ts:.1f}s.png")
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-ss", str(ts), "-i", mp4_path,
             "-update", "1", "-frames:v", "1", fp],
            check=True,
        )
        imgs.append((ts, Image.open(fp)))

    if not imgs:
        return None, dur

    cols = 4
    rows = (len(imgs) + cols - 1) // cols
    tw = 270
    aspect = imgs[0][1].height / max(1, imgs[0][1].width)
    th = int(tw * aspect)
    sheet = Image.new("RGB", (tw * cols, th * rows), (18, 18, 18))
    dr = ImageDraw.Draw(sheet)
    for idx, (ts, im) in enumerate(imgs):
        r, c = divmod(idx, cols)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (c * tw, r * th))
        dr.rectangle([c * tw + 4, r * th + 4, c * tw + 88, r * th + 26], fill=(0, 0, 0))
        dr.text((c * tw + 10, r * th + 8), f"{ts:.1f}s", fill=(255, 220, 0))

    sheet_path = os.path.join(out_dir, "timeline_sheet.png")
    sheet.save(sheet_path)
    return sheet_path, dur


def transcribe_audio(mp4_path, out_dir):
    wav_path = os.path.join(out_dir, "audio.wav")
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", mp4_path, "-vn",
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path],
        check=False,
    )
    if not os.path.exists(wav_path):
        return ""
    whisper_cli = shutil.which("whisper")
    if whisper_cli:
        subprocess.run(
            [whisper_cli, wav_path, "--model", "base", "--output_format", "txt", "--output_dir", out_dir],
            check=False,
        )
        txt_path = os.path.join(out_dir, "audio.txt")
        if os.path.exists(txt_path):
            return open(txt_path).read().strip()
    return "(未检测到本地 whisper，已保留 audio.wav，可手动补充台词或由视觉抽帧拆解)"


def call_muse_spark(base, key, prompt):
    url = base.rstrip("/") + "/v1/chat/completions"
    payload = {
        "model": "muse-spark",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return data["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Video URL or local .mp4 path")
    ap.add_argument("--sku", required=True, help="Path to our SKU listing.md")
    ap.add_argument("--out", required=True, help="Output folder for breakdown & original script")
    ap.add_argument("--notes", default="", help="Optional manual observations / hook / visual notes")
    ap.add_argument("--skip-llm", action="store_true", help="Only download + extract timeline sheet & audio")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    if args.input.startswith(("http://", "https://")):
        mp4_path = os.path.join(args.out, "reference.mp4")
        print(f"[1/4] Downloading reference video -> {mp4_path}", flush=True)
        download_video(args.input, mp4_path)
    else:
        mp4_path = args.input

    print("[2/4] Extracting 1-fps timeline contact sheet...", flush=True)
    sheet_path, dur = build_timeline_sheet(mp4_path, args.out)
    print(f"      duration={dur:.2f}s sheet={sheet_path}", flush=True)

    print("[3/4] Extracting audio / transcript...", flush=True)
    transcript = transcribe_audio(mp4_path, args.out)
    with open(os.path.join(args.out, "transcript.txt"), "w") as f:
        f.write(transcript)

    if args.skip_llm:
        print("Done (--skip-llm). Inspect timeline_sheet.png and transcript.txt.")
        return

    sku_text = open(args.sku).read()
    env = load_env(args.out)
    print("[4/4] Calling muse-spark for viral deconstruction & original FB script...", flush=True)
    prompt = f"""你是一名专精欧美 DTC 独立站 Facebook Reels 投流的广告创意总监。
请根据以下参考爆款视频的真实信息，完成「第二步：爆款拆解」与「第三步：原创转写（15秒人货同框 FB 广告）」。

【参考视频信息】
- 来源：{args.input}
- 时长：{dur:.1f} 秒
- 音频转写台词：{transcript}
- 补充画面观察：{args.notes or "（请结合台词与常见结构拆解，如画面信息不足请标明待对照 timeline_sheet.png 核实）"}

【我方独立站商品真实资料（所有宣称必须严格出自这里，禁止编造任何未验证参数）】
{sku_text}

【输出要求（Markdown）】
1. **爆款拆解（6 维）**：
   - 开头 0–3s 双钩子（视觉钩子 + 文案钩子）
   - 核心情绪痛点与反转点
   - 逐拍框架结构表（时间 | 画面动作 | 文案/字幕 | 转场/音效）
   - 爆火/高转化底层归因
   - 呈现形式与 AI 人货同框复刻可行性（标注哪些动作易穿帮需拆分）
   - 去品牌化通用公式
2. **原创 15s FB 投流脚本（人货全程同框，适配 muse-image + muse-video）**：
   - 严守“只借结构与情绪曲线，不抄原台词和构图”
   - 拆成 5 个单一动作分镜（每镜 2–3.5s，总长 15s），给出美区英文黑底白字短字幕 + 中文对照 + 明确转场（开关硬切 / 闪白 / 推拉）+ 每条宣称的 `claims_basis`。
"""
    md = call_muse_spark(env["MUSE_BASE"], env["MUSE_KEY"], prompt)
    out_md = os.path.join(args.out, "viral_breakdown_and_script.md")
    with open(out_md, "w") as f:
        f.write(md)
    print(f"DONE -> {out_md}", flush=True)


if __name__ == "__main__":
    main()
