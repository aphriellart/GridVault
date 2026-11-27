"""GridVault - download every media file listed in a manifest from chrome_collect.js.

Example:
  python -I download_manifest.py ~/Downloads/ig_natgeo_manifest.json --out ./downloads

Output layout:
  <out>/<username>/posts/2024-05-01_10-22-33_C6abcXYZ_1.jpg   (+ .txt caption)
  <out>/<username>/tagged/...
  <out>/<username>/profile_pic.jpg, manifest.json
Existing files are skipped, so it is safe to run again.
Only Instagram CDN hosts (*.cdninstagram.com, *.fbcdn.net) are downloaded.
"""
import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_HOSTS = (".cdninstagram.com", ".fbcdn.net")
KNOWN_TOOLS = ("gridvault/chrome_collect", "instagram-downloader/chrome_collect")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"


def safe_name(s: str, limit: int = 60) -> str:
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(s)).strip(" .")
    return (s or "_")[:limit]


def ext_of(url: str, kind: str) -> str:
    path = urlparse(url).path.lower()
    for e in (".jpg", ".jpeg", ".png", ".webp", ".heic", ".mp4"):
        if path.endswith(e):
            return ".jpg" if e == ".jpeg" else e
    return ".mp4" if kind == "video" else ".jpg"


def allowed(url: str) -> bool:
    p = urlparse(url)
    return p.scheme == "https" and any((p.hostname or "").endswith(h) for h in ALLOWED_HOSTS)


def fetch(url: str, dest: Path) -> str:
    if dest.exists() and dest.stat().st_size > 0:
        return "skip"
    if not allowed(url):
        return "rejected (host is not an Instagram CDN)"
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.instagram.com/"})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
            tmp.replace(dest)
            return "ok"
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                tmp.unlink(missing_ok=True)
                code = getattr(e, "code", None)
                return f"failed ({code or e})"
            time.sleep(2 * attempt)
    return "failed"


def plan_item(item: dict, folder: Path, jobs: list, write_caption: bool) -> None:
    ts = dt.datetime.fromtimestamp(item.get("taken_at") or 0, dt.timezone.utc)
    ident = safe_name(item.get("code") or item.get("pk") or "x", 40)
    base = f"{ts:%Y-%m-%d_%H-%M-%S}_{ident}"
    media = item.get("media") or []
    for i, m in enumerate(media, 1):
        suffix = f"_{i}" if len(media) > 1 else ""
        jobs.append((m["url"], folder / f"{base}{suffix}{ext_of(m['url'], m.get('type'))}"))
    if write_caption and item.get("caption"):
        cap = folder / f"{base}.txt"
        if not cap.exists():
            folder.mkdir(parents=True, exist_ok=True)
            cap.write_text(item["caption"], encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="GridVault: download media from a chrome_collect.js manifest")
    ap.add_argument("manifest")
    ap.add_argument("--out", default=".")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    mf = Path(os.path.expandvars(args.manifest)).expanduser()
    if "<" in args.manifest or not mf.is_file():
        sys.exit(
            f"Manifest not found: {args.manifest}\n"
            "Use the real file path, e.g. C:\\Users\\<you>\\Downloads\\ig_natgeo_manifest.json "
            "(replace <username> with the account name). In cmd.exe use %USERPROFILE%, "
            "in PowerShell $env:USERPROFILE."
        )
    data = json.loads(mf.read_text(encoding="utf-8"))
    if data.get("tool") not in KNOWN_TOOLS:
        sys.exit("Not a GridVault manifest (from chrome_collect.js)")
    user = safe_name(data["username"])
    root = Path(args.out).expanduser().resolve() / user
    root.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(mf, root / "manifest.json")

    jobs: list = []
    if data.get("profile_pic"):
        jobs.append((data["profile_pic"], root / "profile_pic.jpg"))
    for it in data.get("posts", []):
        plan_item(it, root / "posts", jobs, True)
    for it in data.get("stories", []):
        plan_item(it, root / "stories", jobs, False)
    for h in data.get("highlights", []):
        for it in h.get("items", []):
            plan_item(it, root / "highlights" / safe_name(h.get("title") or h.get("id")), jobs, False)
    for it in data.get("tagged", []):
        plan_item(it, root / "tagged", jobs, True)

    for _, dest in jobs:
        dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"@{user}: {len(data.get('posts', []))} posts"
          f" (profile says {data.get('expected_posts')}), {len(jobs)} files -> {root}")
    if data.get("partial"):
        print(f"[warning] partial manifest: {data.get('error') or 'stopped early or some posts missing'}")

    stats: dict = {}
    failed = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = {ex.submit(fetch, u, d): d for u, d in jobs}
        for n, f in enumerate(as_completed(futs), 1):
            res = f.result()
            key = res.split(" ")[0]
            stats[key] = stats.get(key, 0) + 1
            if key not in ("ok", "skip"):
                failed.append(f"{futs[f].name}: {res}")
            if n % 25 == 0 or n == len(jobs):
                print(f"  {n}/{len(jobs)}  {stats}", flush=True)

    files = [p for p in root.rglob("*") if p.is_file()]
    n_img = sum(p.suffix in (".jpg", ".png", ".webp", ".heic") for p in files)
    n_vid = sum(p.suffix == ".mp4" for p in files)
    size = sum(p.stat().st_size for p in files) / 1e6
    print(f"[done] @{user}: {n_img} images, {n_vid} videos, {size:.1f} MB -> {root}")
    if failed:
        print(f"[failed] {len(failed)} files. Examples: {failed[:3]}")
        print("CDN links expire after a few days; collect a fresh manifest if you see many 403s.")
        sys.exit(1)


if __name__ == "__main__":
    main()
