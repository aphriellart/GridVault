---
name: gridvault
description: GridVault - download everything from an Instagram account (photos, videos, carousels, reels, captions, metadata, profile picture; stories/highlights via instaloader) using the user's own logged-in Chrome (default) or instaloader. Use whenever the user asks to download, back up, archive or save an Instagram account, IG posts, reels, stories or highlights, or shares an instagram.com/<username> link.
---

# GridVault

Two modes. **Chrome mode is the default**: it runs in the user's real browser
and keeps working when instaloader is blocked by Instagram.

| | Chrome mode (default) | instaloader mode |
|---|---|---|
| Needs | Claude in Chrome + user logged in to Instagram in Chrome | an instaloader session |
| Posts, carousels, reels, captions | yes | yes |
| Collabs shown in the grid | yes | not always |
| Tagged | yes (`tagged: true`) | yes |
| Stories / highlights | **no** | yes |
| Risk of being blocked | low (behaves like a user scrolling) | high (`feedback_required`, 429) |

`<skill>` below = the folder containing this SKILL.md; scripts are in
`<skill>/scripts`. Ask for an output folder if the user gives none; default
`<skill>/downloads` (git-ignored). Each account goes to `<output>/<username>/`.

## Chrome mode (default)

Follow the `chrome-browser` skill to load the tools (`tabs_context_mcp`,
`navigate`, `javascript_tool`, `tabs_close_mcp`).

1. **Open the profile** in a new Claude-owned tab:
   `navigate` to `https://www.instagram.com/<username>/` (also for links to
   `/reels/` or `/tagged/`). On a login page, ask the user to log in in their
   own Chrome; never type passwords.
2. **Inject the collector.** Read `scripts/chrome_collect.js` and send its
   **entire contents** to `javascript_tool`, followed by a final line:
   ```js
   __ig.start({reels: true})          // add tagged: true if asked
   ```
   It listens to responses the page receives, scrolls the grid to the end,
   then opens the pop-ups of top posts that loaded before the listener was
   installed. It makes no API calls of its own.
3. **Monitor** with `await new Promise(r => setTimeout(r, 30000)); __ig.status()`.
   Never wait more than ~35 s per call (CDP times out at 45 s). Do not
   navigate or click in that tab while it runs. Speed is roughly 400 posts
   in 4-5 minutes.
   - Finished when `done: true`. Compare `posts` with `expected_posts` and
     check `gaps_left` is 0. If posts < expected, scroll to the bottom a few
     more times with 6 s waits; if nothing new loads, the rest are hidden or
     archived posts (not downloadable).
   - Stop early with `__ig.stop()`.
4. **Save the manifest:** `__ig.save()` → `ig_<username>_manifest.json` in the
   user's Downloads folder. If one with the same name exists, Chrome names the
   new one `... (1).json`; use the newest (`ls -t`). Re-injecting the collector
   keeps what was captured (`window.__igItems`, `__igGrid`).
5. **Download the media** (in the background if there are many files):
   ```
   python -I "<skill>/scripts/download_manifest.py" "<Downloads>/ig_<username>_manifest.json" --out "<output>"
   ```
   Existing files are skipped, so it is safe to rerun. Only Instagram CDN hosts
   are downloaded. **CDN links expire within days** (verified: a 10-day-old
   manifest gave 403 for every file), so download right after collecting.
6. **Close the tab**, then report the `[done]` line (images, videos, size,
   folder) and any posts that could not be collected.

Output:
```
<output>/<username>/
  profile_pic.jpg
  manifest.json                              # all metadata (likes, views, caption, location, ...)
  posts/2024-05-01_10-22-33_C6abcXYZ.jpg     # carousels: _1.jpg, _2.jpg, ...
  posts/2024-05-01_10-22-33_C6abcXYZ.mp4     # videos / reels
  posts/2024-05-01_10-22-33_C6abcXYZ.txt     # caption
  tagged/...
```

## instaloader mode (stories/highlights, or no Chrome)

```
python "<skill>/scripts/ig_download.py" <username> [options]
```
Needs `pip install --upgrade instaloader` (tested with 4.16).

| Option | Effect |
|---|---|
| `--info` | show account info only |
| `--out DIR` | output folder |
| `--all` | posts + reels + igtv + tagged + stories + highlights |
| `--reels` `--igtv` `--tagged` `--stories` `--highlights` | content types |
| `--no-posts` | skip feed posts (e.g. stories only) |
| `--comments` `--geotags` | extra data (slow) |
| `--max N` | limit to the N newest posts |
| `--update` | only items newer than the last run |
| `--login USER` | use USER's saved session (practically required) |

**Password-free session**: ask the user to run this **themselves** in their terminal:
```
python "<skill>/scripts/ig_session_from_cookie.py" <their_username>
```
Steps for the user: Chrome → F12 → Application → Cookies →
`https://www.instagram.com` → copy `sessionid` → paste (hidden input). Then in
Console run `copy(document.cookie)` (`undefined` is normal) and press Enter in
the terminal; the script reads the clipboard. "Cookies captured" should list
`csrftoken` and `mid`. Password alternative: `instaloader --login <username>`
(typed by the user). `--load-cookies` cannot be combined with `--login`, and
importing cookies from Chrome on Windows usually fails.

Tested notes (Nov 2026): without login you get 429 at once. Even with a valid
session the post list may be refused (`feedback_required`) or the v1 feed may
return 0 items. If so, **stop** (do not retry repeatedly) and use Chrome mode.

## Rules

- **Claude never types, asks for or reads Instagram passwords or login
  cookies**, including through the Chrome extension. Cookies are handled only
  by the user via `ig_session_from_cookie.py`. Remind users never to paste
  cookies into chats or websites; logging out of Instagram kills all sessions.
- Saving the manifest to Downloads and media to the output folder is part of
  the user's request; mention both locations in the report.
- Suggest a secondary account for very large downloads.
- Personal archiving only: the user's own account, or public content for
  personal use/research. Copyright stays with the creator; do not help
  re-publish without permission. Do not help access private accounts the user
  doesn't follow or work around account blocks.

## Troubleshooting

- **Chrome mode: `posts` < `expected_posts`** → archived, hidden or restricted
  posts are not in the grid, but Instagram's count may include them. See
  `missing_codes` in the manifest.
- **Chrome mode: `javascript_tool` timeout** → use shorter waits per call; the
  collector keeps running in the page.
- **Chrome mode: login page / "Try again later"** → ask the user to open
  Instagram in Chrome and resolve it, then restart from step 1.
- **instaloader `401`/`429`/`feedback_required`** → stop, use Chrome mode.
- **Interrupted** → `download_manifest.py` and `ig_download.py --update` both
  skip existing files.
