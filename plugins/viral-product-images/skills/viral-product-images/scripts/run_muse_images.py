#!/usr/bin/env python3
"""Muse2API batch clean-base image generator for viral-product-images.
Generates 100% text-free, multi-reference product & lifestyle base images at native ratios
(1:1, 4:5, 3:4, 9:16) with HTTP 202 async polling, retry, concurrency control, and QA sheet export.

Usage (from campaign directory containing images.json & .muse.env):
  python3 run_muse_images.py --doc images.json --ids P1,P2 --workers 2 --retries 2
  python3 run_muse_images.py --doc images.json --ids all   --workers 2 --retries 2
"""
import argparse
import base64
import concurrent.futures
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
DONE_STATES = {"completed", "succeeded", "done"}
FAIL_STATES = {"failed", "error", "cancelled"}


def load_env():
    if os.environ.get("MUSE_BASE") and os.environ.get("MUSE_KEY"):
        return {
            "MUSE_BASE": os.environ["MUSE_BASE"].rstrip("/"),
            "MUSE_KEY": os.environ["MUSE_KEY"],
        }
    candidates = [
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
        return e.code, {"_error_body": e.read().decode("utf-8", "replace")[:800]}
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
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode("ascii")


def poll_task(base, key, tid, label, timeout_s=360):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        time.sleep(6)
        st_code, resp = api_req("GET", f"{base}/v1/images/tasks/{tid}", key, timeout=60)
        st = (resp.get("status") or "").lower()
        if st in DONE_STATES:
            url = (
                (resp.get("result") or {}).get("url")
                or resp.get("url")
                or ((resp.get("data") or [{}])[0].get("url") if isinstance(resp.get("data"), list) else None)
            )
            if url:
                return True, resolve_url(url, base)
            return False, f"completed without url: {resp}"
        if st in FAIL_STATES:
            return False, resp.get("error") or resp.get("_error_body") or str(resp)
        print(f"[{label}] status={st or st_code} progress={resp.get('progress')}", flush=True)
    return False, "timeout"


def run_one(item, base, key, cwd, out_dir, retries=2):
    iid = item["id"]
    out_png = os.path.join(out_dir, f"{iid}.png")
    size = item.get("size", "1:1")
    prompt = item["prompt"].strip()
    if "no text" not in prompt.lower():
        prompt += " Strictly no text, no labels, no numbers, no watermark."

    payload = {
        "model": "muse-image",
        "prompt": prompt,
        "size": size,
        "aspect_ratio": size,
        "response_format": "url",
        "async": True,
    }
    refs = item.get("ref_images") or []
    if refs:
        uris = []
        for rp in refs:
            full = os.path.join(cwd, rp)
            if not os.path.exists(full):
                return {"id": iid, "status": "missing_ref", "error": f"Missing {full}"}
            uris.append(file_to_data_uri(full))
        if len(uris) == 1:
            payload["image"] = uris[0]
        else:
            payload["images"] = uris

    for attempt in range(1, retries + 2):
        print(f"[{iid}] submit attempt {attempt} ({size})...", flush=True)
        code, resp = api_req("POST", f"{base}/v1/images/generations", key, payload, timeout=240)
        url = None
        if code in (200, 201, 202) and isinstance(resp.get("data"), list) and resp["data"]:
            url = resolve_url(resp["data"][0].get("url", ""), base)
        elif code in (200, 201, 202) and (resp.get("id") or resp.get("task_id")):
            tid = resp.get("id") or resp.get("task_id")
            ok, res = poll_task(base, key, tid, iid)
            if ok:
                url = res
            else:
                print(f"[{iid}] attempt {attempt} failed: {res}", flush=True)
                continue
        else:
            print(f"[{iid}] attempt {attempt} http={code} err={resp}", flush=True)
            time.sleep(3)
            continue

        if url:
            raw_path = out_png + ".raw"
            download_file(url, raw_path, key)
            im = Image.open(raw_path)
            im.save(out_png, format="PNG")
            if os.path.exists(raw_path):
                os.remove(raw_path)
            print(f"[{iid}] DONE -> {out_png} ({im.size[0]}x{im.size[1]})", flush=True)
            return {"id": iid, "status": "done", "file": out_png, "size": list(im.size), "url": url}

    return {"id": iid, "status": "failed"}


def build_qa_sheet(out_dir, items):
    done_files = [(it["id"], os.path.join(out_dir, f"{it['id']}.png")) for it in items if os.path.exists(os.path.join(out_dir, f"{it['id']}.png"))]
    if not done_files:
        return
    cols = min(3, len(done_files))
    rows = (len(done_files) + cols - 1) // cols
    cell = 420
    sheet = Image.new("RGB", (cell * cols, cell * rows), (24, 24, 24))
    dr = ImageDraw.Draw(sheet)
    for idx, (iid, fp) in enumerate(done_files):
        im = Image.open(fp).convert("RGB")
        im.thumbnail((cell - 16, cell - 40), Image.LANCZOS)
        r, c = divmod(idx, cols)
        x0 = c * cell + (cell - im.width) // 2
        y0 = r * cell + 34 + ((cell - 40) - im.height) // 2
        sheet.paste(im, (x0, y0))
        dr.rectangle([c * cell + 6, r * cell + 6, c * cell + 200, r * cell + 30], fill=(0, 0, 0))
        dr.text((c * cell + 12, r * cell + 11), f"{iid} ({im.width}x{im.height})", fill=(255, 220, 0))
    sp = os.path.join(out_dir, "clean_base_sheet.png")
    sheet.save(sp)
    print(f"QA SHEET -> {sp}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default="images.json")
    ap.add_argument("--ids", default="all")
    ap.add_argument("--out", default="assets/clean_base")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--retries", type=int, default=2)
    args = ap.parse_args()

    cwd = os.getcwd()
    env = load_env()
    base, key = env["MUSE_BASE"].rstrip("/"), env["MUSE_KEY"]
    doc = json.load(open(os.path.join(cwd, args.doc)))
    all_items = doc["images"]
    want = None if args.ids == "all" else {x.strip() for x in args.ids.split(",")}
    items = [x for x in all_items if want is None or x["id"] in want]

    out_dir = os.path.join(cwd, args.out)
    os.makedirs(out_dir, exist_ok=True)

    results = []
    if args.workers > 1 and len(items) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = [pool.submit(run_one, it, base, key, cwd, out_dir, args.retries) for it in items]
            for f in concurrent.futures.as_completed(futs):
                results.append(f.result())
    else:
        for it in items:
            results.append(run_one(it, base, key, cwd, out_dir, args.retries))

    manifest = os.path.join(out_dir, "manifest.json")
    json.dump({"results": results}, open(manifest, "w"), ensure_ascii=False, indent=2)
    build_qa_sheet(out_dir, all_items)
    sys.exit(0 if all(r["status"] == "done" for r in results) else 1)


if __name__ == "__main__":
    main()
