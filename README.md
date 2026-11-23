# GridVault

**Back up an entire Instagram profile — every photo, video, carousel and reel, with captions and metadata — using the browser you're already logged in to.**

[Bahasa Indonesia](README.id.md)

GridVault scrolls a profile in your own browser, records the posts the page
loads, and saves them as a small JSON manifest. A Python script then downloads
every file in full resolution into a tidy folder. Because it rides on your
normal browsing session instead of hammering Instagram's API, it keeps working
when tools like instaloader get `429` or `feedback_required`.

```
downloads/<username>/
  profile_pic.jpg
  manifest.json                              # likes, views, caption, location, dates
  posts/2024-05-01_10-22-33_C6abcXYZ.jpg     # carousels: _1.jpg, _2.jpg, ...
  posts/2024-05-01_10-22-33_C6abcXYZ.mp4     # videos & reels
  posts/2024-05-01_10-22-33_C6abcXYZ.txt     # caption
```

Tested on a real 433-post profile: 394 visible posts → 613 images + 156 videos
(654 MB) in about 5 minutes, with zero blocks.

## Features

- Photos, multi-photo carousels, videos and reels in the highest available resolution
- Captions (`.txt`) plus a full `manifest.json` (likes, comments, views, location, timestamps)
- Collab posts that appear in the profile grid; optionally posts the account is tagged in
- Re-runnable: existing files are skipped
- Downloads only from Instagram's CDN, nothing else
- Optional **instaloader mode** for stories and highlights
- Works as a **[Claude Code](https://claude.com/claude-code) skill**: just say *"back up instagram.com/natgeo"*

## Requirements

- Python 3.10+ (standard library only for Chrome mode)
- Google Chrome (or any Chromium browser) logged in to Instagram
- Optional: `pip install -r requirements.txt` for instaloader mode

## Quick start (manual, no AI needed)

1. **Collect.** Open `https://www.instagram.com/<username>/` in Chrome, press
   **F12 → Console**, paste the contents of
   [`scripts/chrome_collect.js`](scripts/chrome_collect.js) and press Enter,
   then run:
   ```js
   __ig.start({reels: true, autosave: true})
   ```
   Progress is printed every 15 seconds. Don't click in the tab until it says
   *done*; `ig_<username>_manifest.json` is then saved to your Downloads folder.

   > Chrome may ask you to type `allow pasting` first, and Instagram shows a
   > big **"Stop!"** warning. That warning is right: never paste code you
   > don't understand. The collector is ~250 lines; read it first. It only
   > reads what the page already receives and sends nothing anywhere.

2. **Download.**
   ```bash
   python -I scripts/download_manifest.py ~/Downloads/ig_<username>_manifest.json --out ./downloads
   ```
   Run it soon after collecting: Instagram's CDN links expire within a few days.

Collector options: `reels` (also scan the Reels tab), `tagged` (also scan the
Tagged tab), `autosave`. Other commands: `__ig.status()`, `__ig.stop()`,
`__ig.save()`.

## Use with Claude Code

Clone the repo into your skills folder:

```bash
git clone https://github.com/aphriellart/GridVault ~/.claude/skills/gridvault
```

Then, with the [Claude in Chrome](https://claude.com/chrome) extension
connected, ask Claude something like *"download all posts from
instagram.com/natgeo"*. Claude opens the profile in a new tab, runs the
collector, saves the manifest and downloads everything. See [SKILL.md](SKILL.md).

## instaloader mode (stories & highlights)

Instagram aggressively limits automated sessions, so use this only for what
Chrome mode can't do.

```bash
pip install -r requirements.txt
python scripts/ig_session_from_cookie.py <your_username>   # once, no password needed
python scripts/ig_download.py <target> --all --login <your_username> --out ./downloads
```

`ig_session_from_cookie.py` asks you to paste your `sessionid` cookie (F12 →
Application → Cookies) into a hidden prompt and reads the rest from the
clipboard after you run `copy(document.cookie)` in the Console. The session
file grants access to your account: keep it private, and log out of Instagram
to invalidate it. Prefer a secondary account.

Run `python scripts/ig_download.py --help` for all options.

## Limitations

- Archived, hidden or restricted posts are not in the grid, so they can't be
  collected (Instagram's post count may still include them).
- Chrome mode does not fetch stories or highlights.
- Private accounts work only if your account follows them.
- Instagram changes its web app often; if the collector stops finding posts,
  please open an issue.

## Responsible use

GridVault is for **personal archiving**: backing up your own account, or saving
public content for personal reference or research. The content belongs to its
creators. Don't re-upload, sell or redistribute it without permission, don't
use it to harass anyone, and respect Instagram's Terms of Use and the laws
where you live. Automated collection may violate Instagram's terms and can get
accounts temporarily restricted; you use this tool at your own risk.

GridVault is not affiliated with, endorsed by, or sponsored by Instagram or Meta.

## License

[MIT](LICENSE)
