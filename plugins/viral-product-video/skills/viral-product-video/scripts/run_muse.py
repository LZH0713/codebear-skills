#!/usr/bin/env python3
"""Muse2API pipeline runner: generates multi-reference keyframes (muse-image)
and image-to-video shots (muse-video) with concurrency control, retry, and QA frame extraction.

Usage (from a campaign directory containing shots.json & .muse.env):
  python3 run_muse.py --stage keyframes --ids all --workers 2
  python3 run_muse.py --stage videos    --ids S1,S2 --workers 2 --tag v1

.muse.env format (gitignored):
  MUSE_BASE=http://<your-muse2api-host>:18610
  MUSE_KEY=m2a_...
"""
import argparse
import base64
import concurrent.futures
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DONE_STATES = {"completed", "succeeded", "done"}
FAIL_STATES = {"failed", "error", "cancelled"}


def load_env():
    env = {}
    candidates = [
        os.path.join(os.getcwd(), ".muse.env"),
        os.path.join(HERE, ".muse.env"),
    ]
    path = next((p for p in candidates if os.path.exists(p)), None)
    if not path:
        raise FileNotFoundError("Missing .muse.env (need MUSE_BASE and MUSE_KEY)")
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def api_req(method, url, key, payload=None, timeout=180):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {key}")
    if data is not None:
        r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:800]
        return e.code, {"_error_body": body}
    except Exception as e:
        return 0, {"_error_body": str(e)}


def resolve_url(url, base):
    if not url:
        return ""
    if url.startswith("/"):
        return base.rstrip("/") + url
    if "://127.0.0.1" in url or "://localhost" in url:
        rest = url.split("://", 1)[1]
        return base.rstrip("/") + "/" + rest.split("/", 1)[1]
    return url


def download_file(url, dst, key=None, retries=3):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = urllib.request.Request(url)
            if key and "/v1/media/" not in url:
                r.add_header("Authorization", f"Bearer {key}")
            with urllib.request.urlopen(r, timeout=240) as resp, open(dst, "wb") as f:
                while True:
                    chunk = resp.read(1 << 16)
                    if not chunk:
                        break
                    f.write(chunk)
            return
        except Exception as e:
            last_err = e
            time.sleep(2 * attempt)
    raise last_err


def file_to_data_uri(path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def save_as_png(src_bytes_path, dst_png_path):
    from PIL import Image
    im = Image.open(src_bytes_path)
    im.save(dst_png_path, format="PNG")
    if src_bytes_path != dst_png_path and os.path.exists(src_bytes_path):
        os.remove(src_bytes_path)


def extract_qa_frames(mp4_path, qa_dir, shot_id):
    os.makedirs(qa_dir, exist_ok=True)
    for ts in ("0.5", "2.5", "4.5"):
        out_png = os.path.join(qa_dir, f"{shot_id}_{ts}s.png")
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-ss", ts, "-i", mp4_path,
             "-update", "1", "-frames:v", "1", out_png],
            check=False,
        )


def poll_task(base, key, poll_path, label, timeout_s=600):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(6)
        st_code, resp = api_req("GET", f"{base}{poll_path}", key, timeout=60)
        st = (resp.get("status") or "").lower()
        if st in DONE_STATES:
            url = (
                (resp.get("result") or {}).get("url")
                or (resp.get("video") or {}).get("url")
                or resp.get("url")
                or ((resp.get("data") or [{}])[0].get("url") if isinstance(resp.get("data"), list) else None)
            )
            if url:
                return True, resolve_url(url, base), resp
            return False, f"completed without url: {resp}", resp
        if st in FAIL_STATES:
            return False, resp.get("error") or resp.get("_error_body") or str(resp), resp
        print(f"[{label}] status={st or st_code} progress={resp.get('progress')}", flush=True)
    return False, "timeout", {}


def run_keyframe(kf, base, key, cwd, retries=2):
    kid = kf["id"]
    out_png = os.path.join(cwd, "assets", "keyframes", f"{kid}.png")
    payload = {
        "model": "muse-image",
        "prompt": kf["prompt"],
        "size": kf.get("size", "9:16"),
        "aspect_ratio": kf.get("size", "9:16"),
        "response_format": "url",
        "async": True,
    }
    refs = kf.get("ref_images") or []
    if refs:
        uris = []
        for rp in refs:
            full = os.path.join(cwd, rp)
            if not os.path.exists(full):
                return {"id": kid, "status": "missing_ref", "error": f"Missing {full}"}
            uris.append(file_to_data_uri(full))
        if len(uris) == 1:
            payload["image"] = uris[0]
        else:
            payload["images"] = uris

    for attempt in range(1, retries + 2):
        print(f"[{kid}] keyframe submit attempt {attempt}...", flush=True)
        code, resp = api_req("POST", f"{base}/v1/images/generations", key, payload, timeout=240)
        # Handle synchronous return or async task id (200/201/202)
        url = None
        if code in (200, 201, 202) and isinstance(resp.get("data"), list) and resp["data"]:
            url = resolve_url(resp["data"][0].get("url", ""), base)
        elif code in (200, 201, 202) and (resp.get("id") or resp.get("task_id")):
            tid = resp.get("id") or resp.get("task_id")
            ok, res, _ = poll_task(base, key, f"/v1/images/tasks/{tid}", kid, timeout_s=360)
            if ok:
                url = res
            else:
                print(f"[{kid}] attempt {attempt} failed: {res}", flush=True)
                continue
        else:
            print(f"[{kid}] attempt {attempt} http={code} err={resp}", flush=True)
            continue

        if url:
            tmp_raw = out_png + ".raw"
            download_file(url, tmp_raw, key)
            save_as_png(tmp_raw, out_png)
            print(f"[{kid}] DONE -> {out_png}", flush=True)
            return {"id": kid, "status": "done", "file": out_png, "url": url}

    return {"id": kid, "status": "failed"}


def run_video_shot(shot, base, key, cwd, outdir, retries=2):
    sid = shot["id"]
    kf_path = os.path.join(cwd, shot["keyframe"])
    if not os.path.exists(kf_path):
        return {"id": sid, "status": "missing_keyframe", "error": f"Missing {kf_path}"}

    payload = {
        "model": "muse-video",
        "prompt": shot["prompt"],
        "duration": shot.get("duration", 5),
        "size": shot.get("size", "9:16"),
        "aspect_ratio": shot.get("aspect_ratio", "9:16"),
        "image": file_to_data_uri(kf_path),
    }
    if shot.get("extra_images"):
        payload["images"] = [file_to_data_uri(kf_path)] + [
            file_to_data_uri(os.path.join(cwd, p)) for p in shot["extra_images"]
        ]
        payload.pop("image", None)
    if shot.get("audio"):
        payload["audios"] = [file_to_data_uri(os.path.join(cwd, shot["audio"]))]

    for attempt in range(1, retries + 2):
        print(f"[{sid}] video submit attempt {attempt}...", flush=True)
        code, resp = api_req("POST", f"{base}/v1/videos", key, payload, timeout=120)
        tid = resp.get("id") or resp.get("task_id") or resp.get("request_id")
        if code not in (200, 201, 202) or not tid:
            print(f"[{sid}] attempt {attempt} submit http={code} err={resp}", flush=True)
            time.sleep(5)
            continue

        ok, res, meta = poll_task(base, key, f"/v1/videos/{tid}", sid, timeout_s=600)
        if ok:
            mp4_path = os.path.join(outdir, f"{sid}.mp4")
            download_file(res, mp4_path, key)
            extract_qa_frames(mp4_path, os.path.join(outdir, "qa"), sid)
            print(f"[{sid}] DONE -> {mp4_path}", flush=True)
            return {"id": sid, "status": "done", "task_id": tid, "file": mp4_path, "url": res}
        print(f"[{sid}] attempt {attempt} failed: {res}", flush=True)

    return {"id": sid, "status": "failed"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["keyframes", "videos"], required=True)
    ap.add_argument("--ids", default="all", help="Comma-separated IDs or 'all'")
    ap.add_argument("--doc", default="shots.json")
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--retries", type=int, default=2)
    args = ap.parse_args()

    cwd = os.getcwd()
    env = load_env()
    base, key = env["MUSE_BASE"].rstrip("/"), env["MUSE_KEY"]
    doc = json.load(open(os.path.join(cwd, args.doc)))

    want = None if args.ids == "all" else {x.strip() for x in args.ids.split(",")}

    if args.stage == "keyframes":
        items = [k for k in doc["keyframes"] if want is None or k["id"] in want]
        results = []
        if args.workers > 1 and len(items) > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                futs = [pool.submit(run_keyframe, kf, base, key, cwd, args.retries) for kf in items]
                for f in concurrent.futures.as_completed(futs):
                    results.append(f.result())
        else:
            for kf in items:
                results.append(run_keyframe(kf, base, key, cwd, retries=args.retries))
        manifest = os.path.join(cwd, "assets", "keyframes", "manifest.json")
        os.makedirs(os.path.dirname(manifest), exist_ok=True)
        json.dump({"results": results}, open(manifest, "w"), ensure_ascii=False, indent=2)
        print(f"manifest -> {manifest}")
        sys.exit(0 if all(r["status"] == "done" for r in results) else 1)

    shots = [s for s in doc["shots"] if want is None or s["id"] in want]
    outdir = os.path.join(cwd, "renders", args.tag)
    os.makedirs(outdir, exist_ok=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(run_video_shot, s, base, key, cwd, outdir, args.retries) for s in shots]
        for f in concurrent.futures.as_completed(futs):
            results.append(f.result())
    manifest = os.path.join(outdir, "manifest.json")
    json.dump({"tag": args.tag, "results": results}, open(manifest, "w"), ensure_ascii=False, indent=2)
    print(f"manifest -> {manifest}")
    sys.exit(0 if all(r["status"] == "done" for r in results) else 1)


if __name__ == "__main__":
    main()
