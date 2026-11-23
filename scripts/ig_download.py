"""GridVault - instaloader mode: download an Instagram account with instaloader.

Use this mode for stories/highlights. For posts and reels, the Chrome mode
(chrome_collect.js + download_manifest.py) is far less likely to be blocked.

Examples:
  python ig_download.py natgeo --info
  python ig_download.py natgeo --out ./downloads --login my_account
  python ig_download.py natgeo --all --login my_account --out ./downloads
  python ig_download.py natgeo --update --login my_account   # only new items
"""
import argparse
import sys
from pathlib import Path

try:
    import instaloader
    from instaloader.lateststamps import LatestStamps
except ImportError:
    sys.exit("instaloader is not installed. Run: pip install --upgrade instaloader")


def build_loader(args) -> "instaloader.Instaloader":
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    return instaloader.Instaloader(
        dirname_pattern=str(out / "{target}"),
        filename_pattern="{date_utc:%Y-%m-%d_%H-%M-%S}_{shortcode}",
        download_comments=args.comments,
        download_geotags=args.geotags,
        save_metadata=not args.no_metadata,
        compress_json=False,
        post_metadata_txt_pattern="{caption}",
        download_video_thumbnails=False,
        max_connection_attempts=5,
        quiet=False,
    )


def login(L, user: str | None) -> bool:
    if not user:
        return False
    try:
        L.load_session_from_file(user)
    except FileNotFoundError:
        sys.exit(
            f"No saved session for '{user}'. Create one yourself in your terminal, either:\n"
            f"  python \"{Path(__file__).with_name('ig_session_from_cookie.py')}\" {user}\n"
            "    (no password; paste the sessionid cookie from a logged-in browser)\n"
            f"  instaloader --login {user}\n"
            "then run this command again."
        )
    # Verify via the v1 API (the old GraphQL query used by test_login() often returns 401).
    L.context.fatal_status_codes = [401, 429]
    try:
        data = L.context.get_iphone_json("api/v1/accounts/current_user/?edit=true", {})
        who = data.get("user", {}).get("username")
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "login_required" in msg or "403" in msg:
            sys.exit(f"Session '{user}' has expired. Recreate it with ig_session_from_cookie.py.")
        print(f"[warning] could not verify the session ({msg[:120]}); trying anyway.")
        who = user
    finally:
        L.context.fatal_status_codes = []
    print(f"[login] as @{who}")
    return True


def safe(p, attr, default="?"):
    """Read a profile attribute; some need an extra query that Instagram may reject."""
    try:
        return getattr(p, attr)
    except Exception:  # noqa: BLE001
        return default


def show_info(p) -> None:
    print(f"Account    : @{p.username} ({safe(p, 'full_name')})")
    print(f"Private    : {'yes' if safe(p, 'is_private', False) else 'no'}")
    print(f"Posts      : {safe(p, 'mediacount')}")
    print(f"IGTV       : {safe(p, 'igtvcount')}")
    print(f"Followers  : {safe(p, 'followers')}")
    print(f"Bio        : {str(safe(p, 'biography', ''))[:200]}")


def main() -> None:
    ap = argparse.ArgumentParser(description="GridVault (instaloader mode): download an Instagram account")
    ap.add_argument("usernames", nargs="+", help="target username(s), without @ (profile URLs also work)")
    ap.add_argument("--out", default=".", help="output folder (default: current folder)")
    ap.add_argument("--login", metavar="USER", help="use the saved session of USER")
    ap.add_argument("--info", action="store_true", help="only show account info")
    ap.add_argument("--all", action="store_true",
                    help="posts + reels + igtv + tagged + stories + highlights (needs --login)")
    ap.add_argument("--reels", action="store_true")
    ap.add_argument("--igtv", action="store_true")
    ap.add_argument("--tagged", action="store_true")
    ap.add_argument("--stories", action="store_true", help="needs --login")
    ap.add_argument("--highlights", action="store_true", help="needs --login")
    ap.add_argument("--no-posts", action="store_true", help="skip feed posts")
    ap.add_argument("--comments", action="store_true", help="save comments (slow)")
    ap.add_argument("--geotags", action="store_true", help="save locations (needs --login)")
    ap.add_argument("--no-metadata", action="store_true", help="do not save JSON metadata")
    ap.add_argument("--max", type=int, help="limit the number of posts")
    ap.add_argument("--update", action="store_true",
                    help="only download items newer than the last run")
    args = ap.parse_args()

    if args.all:
        args.reels = args.igtv = args.tagged = args.stories = args.highlights = True

    L = build_loader(args)
    logged_in = login(L, args.login)
    if not logged_in:
        # Anonymous access is usually rate-limited at once; fail fast instead of waiting 30 minutes.
        L.context.fatal_status_codes = [429]

    if (args.stories or args.highlights or args.geotags) and not logged_in:
        print("[warning] stories/highlights/geotags need --login; skipped.")
        args.stories = args.highlights = args.geotags = False
        L.download_geotags = False

    stamps = None
    if args.update:
        stamps = LatestStamps(str(Path(args.out).resolve() / "latest-stamps.ini"))

    failed = []
    for name in args.usernames:
        name = name.lstrip("@").strip("/").split("/")[-1]
        try:
            p = instaloader.Profile.from_username(L.context, name)
        except instaloader.ProfileNotExistsException:
            print(f"[failed] @{name} not found")
            failed.append(name)
            continue
        except instaloader.LoginRequiredException:
            print(f"[failed] Instagram requires login to view @{name}. Use --login.")
            failed.append(name)
            continue
        except (instaloader.exceptions.ConnectionException,
                instaloader.exceptions.AbortDownloadException) as e:
            hint = ("Instagram blocks anonymous access (429). Log in and use --login."
                    if not logged_in else "Rate limited. Wait 15-60 minutes and try again.")
            print(f"[failed] @{name}: {e}\n{hint}")
            failed.append(name)
            continue

        show_info(p)
        if args.info:
            print()
            continue
        if safe(p, "is_private", False) and not safe(p, "followed_by_viewer", True):
            print(f"[failed] @{name} is private and you don't follow it; only the profile picture is available.")

        try:
            L.download_profiles(
                {p},
                profile_pic=True,
                posts=not args.no_posts,
                tagged=args.tagged,
                igtv=args.igtv,
                reels=args.reels,
                stories=args.stories,
                highlights=args.highlights,
                fast_update=args.update and stamps is None,
                latest_stamps=stamps,
                max_count=args.max,
            )
        except KeyboardInterrupt:
            print("\n[stopped] Run the same command again to resume.")
            sys.exit(130)
        except (instaloader.exceptions.ConnectionException,
                instaloader.exceptions.AbortDownloadException) as e:
            if "feedback_required" in str(e) or "checkpoint" in str(e):
                print(f"[failed] @{name}: Instagram flagged this activity as automated "
                      "(feedback_required/checkpoint). STOP for now: open Instagram in your browser, "
                      "resolve any warning, wait a few hours (ideally 24), then rerun with --update "
                      "- or use the Chrome mode instead.")
            else:
                print(f"[failed] @{name}: {e}\nProbably rate limited. Wait 15-60 minutes, then rerun with --update.")
            failed.append(name)

        target = Path(args.out).resolve() / name
        if target.exists():
            files = [f for f in target.rglob("*") if f.is_file()]
            n_img = sum(f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") for f in files)
            n_vid = sum(f.suffix.lower() == ".mp4" for f in files)
            size = sum(f.stat().st_size for f in files) / 1e6
            print(f"[done] @{name}: {n_img} images, {n_vid} videos, {size:.1f} MB -> {target}")

    if failed:
        sys.exit(f"Failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
