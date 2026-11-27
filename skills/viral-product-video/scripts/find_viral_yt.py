#!/usr/bin/env python3
"""Search YouTube & Shorts for high-view short-form viral videos matching a specific product,
verify real view counts/durations/descriptions, and render a 2x3 thumbnail QA sheet
so wrong-form-factor items can be visually filtered out before downloading.

Usage:
  python3 find_viral_yt.py --queries "wood nightstand #shorts" "bedside table #shorts" \
      --out 投流素材/nightstand-v1/viral_candidates --max-sec 90 --top 6
"""
import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from PIL import Image, ImageDraw

HDR = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_views(s):
    if not s:
        return 0
    s = str(s).upper().replace(",", "")
    m = re.search(r"([0-9.]+)\s*([KMB]?)", s)
    if not m:
        return 0
    return int(float(m.group(1)) * {"": 1, "K": 1000, "M": 1000000, "B": 1000000000}[m.group(2)])


def dur_secs(d):
    if not d:
        return 9999
    if d == "SHORT":
        return 30
    parts = d.split(":")
    if len(parts) == 2 and all(p.isdigit() for p in parts):
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 9999


def search_youtube(queries):
    seen = {}
    for q in queries:
        for sp in ("CAMSAhAB", "EgIYAQ%3D%3D"):  # sort by views, and under 4 min
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(q)}&sp={sp}"
            try:
                html = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=15).read().decode("utf-8", "replace")
                m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
                if not m:
                    continue
                data = json.loads(m.group(1))

                def walk(obj):
                    if isinstance(obj, dict):
                        if "videoRenderer" in obj:
                            v = obj["videoRenderer"]
                            vid = v.get("videoId")
                            if vid and vid not in seen:
                                title = "".join(r.get("text", "") for r in v.get("title", {}).get("runs", []))
                                views = (v.get("viewCountText") or {}).get("simpleText") or ""
                                dur = (v.get("lengthText") or {}).get("simpleText") or ""
                                chan = "".join(r.get("text", "") for r in v.get("ownerText", {}).get("runs", []))
                                nav = json.dumps(v.get("navigationEndpoint", {}))
                                is_short = "reelWatchEndpoint" in nav or "/shorts/" in nav
                                seen[vid] = {
                                    "id": vid, "title": title, "views": parse_views(views),
                                    "dur_str": "SHORT" if is_short else dur, "is_short": is_short,
                                    "channel": chan,
                                    "url": f"https://www.youtube.com/shorts/{vid}" if is_short else f"https://www.youtube.com/watch?v={vid}",
                                }
                        if "shortsLockupViewModel" in obj:
                            s = obj["shortsLockupViewModel"]
                            vid = s.get("onTap", {}).get("innertubeCommand", {}).get("reelWatchEndpoint", {}).get("videoId")
                            if vid and vid not in seen:
                                ov = s.get("overlayMetadata", {})
                                title = (ov.get("primaryText") or {}).get("content", "")
                                views = (ov.get("secondaryText") or {}).get("content", "")
                                seen[vid] = {
                                    "id": vid, "title": title, "views": parse_views(views),
                                    "dur_str": "SHORT", "is_short": True, "channel": "",
                                    "url": f"https://www.youtube.com/shorts/{vid}",
                                }
                        for val in obj.values():
                            walk(val)
                    elif isinstance(obj, list):
                        for item in obj:
                            walk(item)

                walk(data)
            except Exception as e:
                print(f"[warn] query={q} err={e}")
    return list(seen.values())


def verify_video(vid):
    dec = json.JSONDecoder()
    url = f"https://www.youtube.com/watch?v={vid}"
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=15).read().decode("utf-8", "replace")
    idx = html.find("var ytInitialPlayerResponse = ")
    if idx == -1:
        return {}
    obj, _ = dec.raw_decode(html[idx + len("var ytInitialPlayerResponse = "):])
    return obj.get("videoDetails", {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-sec", type=int, default=90)
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    raw = search_youtube(args.queries)
    shortlist = [x for x in raw if x["is_short"] or dur_secs(x["dur_str"]) <= args.max_sec]
    shortlist.sort(key=lambda x: x["views"], reverse=True)
    picks = shortlist[:args.top]

    verified = []
    thumbs = []
    for idx, item in enumerate(picks, 1):
        vid = item["id"]
        try:
            vd = verify_video(vid)
        except Exception:
            vd = {}
        views = int(vd.get("viewCount") or item["views"] or 0)
        secs = int(vd.get("lengthSeconds") or dur_secs(item["dur_str"]))
        title = vd.get("title") or item["title"]
        author = vd.get("author") or item["channel"]
        desc = (vd.get("shortDescription") or "").replace("\n", " ")[:220]
        rec = {
            "rank": idx, "id": vid, "views": views, "seconds": secs,
            "author": author, "title": title, "desc": desc, "url": item["url"],
        }
        verified.append(rec)
        print(f"[#{idx}] {views:>9,d} views | {secs:>3d}s | {author[:20]:20s} | {title[:65]} | {item['url']}")
        if desc:
            print(f"      desc: {desc[:140]}")
        tp = os.path.join(args.out, f"cand_{idx}_{vid}.jpg")
        try:
            open(tp, "wb").write(urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg", timeout=15).read())
            thumbs.append((f"#{idx} {views//1000}K ({secs}s)", tp))
        except Exception:
            pass

    json.dump(verified, open(os.path.join(args.out, "candidates.json"), "w"), ensure_ascii=False, indent=2)

    if thumbs:
        cols = 3
        rows = (len(thumbs) + cols - 1) // cols
        cw, ch = 400, 300
        sheet = Image.new("RGB", (cw * cols, ch * rows), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for i, (lbl, tp) in enumerate(thumbs):
            r, c = divmod(i, cols)
            sheet.paste(Image.open(tp).resize((cw, ch), Image.LANCZOS), (c * cw, r * ch))
            dr.rectangle([c * cw + 4, r * ch + 4, c * cw + 195, r * ch + 30], fill=(0, 0, 0))
            dr.text((c * cw + 10, r * ch + 9), lbl, fill=(255, 220, 0))
        sp = os.path.join(args.out, "candidates_sheet.png")
        sheet.save(sp)
        print("SHEET ->", sp)


if __name__ == "__main__":
    main()
