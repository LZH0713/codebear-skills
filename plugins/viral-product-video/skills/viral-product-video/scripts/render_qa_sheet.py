#!/usr/bin/env python3
"""Render a 5-frame-per-shot dense QA contact sheet for all MP4s in a render directory.

Usage:
  python3 render_qa_sheet.py --dir renders/v1
"""
import argparse
import glob
import json
import os
import subprocess
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Directory containing S1.mp4, S2.mp4, ...")
    ap.add_argument("--out", default="", help="Output PNG path (defaults to <dir>/qa_sheet_all.png)")
    args = ap.parse_args()

    mp4s = sorted(glob.glob(os.path.join(args.dir, "*.mp4")))
    if not mp4s:
        raise SystemExit(f"No .mp4 files found in {args.dir}")

    times = [0.2, 1.2, 2.2, 3.2, 4.4]
    qa_dir = os.path.join(args.dir, "qa_dense")
    os.makedirs(qa_dir, exist_ok=True)

    W, H = 270, 480
    sheet = Image.new("RGB", (W * len(times), H * len(mp4s)), (20, 20, 20))
    draw = ImageDraw.Draw(sheet)

    for r, mp4 in enumerate(mp4s):
        sid = os.path.splitext(os.path.basename(mp4))[0]
        info = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", mp4],
            capture_output=True, text=True, check=True,
        ).stdout)
        dur = float(info["format"]["duration"])
        st = [(x.get("codec_type"), x.get("width"), x.get("height"), x.get("r_frame_rate")) for x in info["streams"]]
        print(f"{sid}: dur={dur:.2f}s streams={st}")
        for c, t in enumerate(times):
            t_use = min(t, max(0.0, dur - 0.15))
            fp = os.path.join(qa_dir, f"{sid}_{t:.1f}.png")
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t_use), "-i", mp4,
                 "-update", "1", "-frames:v", "1", fp],
                check=True,
            )
            im = Image.open(fp).resize((W, H), Image.LANCZOS)
            sheet.paste(im, (c * W, r * H))
            draw.rectangle([c * W + 4, r * H + 4, c * W + 115, r * H + 28], fill=(0, 0, 0))
            draw.text((c * W + 10, r * H + 9), f"{sid} @ {t_use:.1f}s", fill=(255, 220, 0))

    out_png = args.out or os.path.join(args.dir, "qa_sheet_all.png")
    sheet.save(out_png)
    print("SAVED ->", out_png)


if __name__ == "__main__":
    main()
