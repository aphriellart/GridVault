// GridVault - Chrome collector (capture-while-scrolling).
// MIT License
//
// What it does: on an Instagram profile page in YOUR logged-in browser, it listens to the
// responses the page itself receives (XHR/fetch), scrolls the grid to the end, and records
// every post object (code + media URLs) that passes by. Posts loaded before the listener was
// installed are fetched by opening and closing their pop-up. It never calls Instagram APIs on
// its own and sends nothing anywhere: the result is saved as a JSON manifest to your
// Downloads folder. Then download_manifest.py downloads the media files.
//
// Manual use (no Claude needed):
//   1. Open https://www.instagram.com/<username>/ while logged in.
//   2. F12 -> Console. Chrome may ask you to type "allow pasting" first.
//      Instagram shows a "Stop!" self-XSS warning: it is right in general. Only paste code
//      you have read and trust - this file is short, read it first.
//   3. Paste this whole file, press Enter, then run:
//        __ig.start({reels: true, autosave: true})
//      Progress is printed every 15 s. Do not click in this tab until it says "done".
//   4. The manifest ig_<username>_manifest.json lands in Downloads (autosave), or run __ig.save().
//
// API:  __ig.start({reels, tagged, autosave}) · __ig.status() · __ig.stop() · __ig.save()
(() => {
  if (window.__ig && window.__ig.running) return "GridVault is already running; use __ig.status()";
  const TAG = "%c[GridVault]";
  const CSS = "color:#fff;background:#6c3ce1;padding:1px 6px;border-radius:3px";
  const log = (...a) => console.log(TAG, CSS, ...a);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const jitter = (a, b) => a + Math.random() * (b - a);

  // Kept on window so re-injecting this file (e.g. after a fix) keeps what was captured.
  const items = (window.__igItems = window.__igItems || new Map()); // code -> raw media object
  let responses = 0;

  function walk(o, depth = 0) {
    if (!o || typeof o !== "object" || depth > 40) return;
    if (Array.isArray(o)) { for (const x of o) walk(x, depth + 1); return; }
    if (typeof o.code === "string" && (o.image_versions2 || o.carousel_media || o.video_versions)) {
      const prev = items.get(o.code);
      // keep the richest version (with carousel/video data)
      if (!prev || JSON.stringify(o).length > JSON.stringify(prev).length) items.set(o.code, o);
    }
    for (const k in o) { const v = o[k]; if (v && typeof v === "object") walk(v, depth + 1); }
  }
  function eat(text) {
    if (!text || text.indexOf("image_versions2") < 0) return;
    responses++;
    for (const line of text.split("\n")) { try { walk(JSON.parse(line)); } catch { /* not JSON */ } }
  }
  window.__igEat = eat; // hooks always call the latest version
  if (!window.__igHooked) {
    const os = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function (...a) {
      this.addEventListener("load", () => {
        try { if (!this.responseType || this.responseType === "text") window.__igEat(this.responseText); } catch { /* ignore */ }
      });
      return os.apply(this, a);
    };
    const of = window.fetch;
    window.fetch = async function (...a) {
      const r = await of.apply(this, a);
      try { r.clone().text().then((t) => window.__igEat(t)).catch(() => {}); } catch { /* ignore */ }
      return r;
    };
    window.__igHooked = true;
  }
  for (const s of document.querySelectorAll('script[type="application/json"]')) {
    if (s.textContent.includes("image_versions2")) { try { walk(JSON.parse(s.textContent)); } catch { /* ignore */ } }
  }

  const best = (arr) => (arr || []).slice().sort((a, b) => (b.width || 0) - (a.width || 0))[0];
  function mediaOf(it) {
    const parts = it.carousel_media && it.carousel_media.length ? it.carousel_media : [it];
    return parts.map((m) => {
      const v = best(m.video_versions);
      const img = best(m.image_versions2 && m.image_versions2.candidates);
      return v
        ? { type: "video", url: v.url, width: v.width, height: v.height, thumb: img && img.url }
        : { type: "image", url: img && img.url, width: img && img.width, height: img && img.height };
    }).filter((m) => m.url);
  }
  function slim(it) {
    return {
      pk: String(it.pk || it.id || ""), code: it.code, taken_at: it.taken_at,
      product_type: it.product_type || null, owner: (it.user && it.user.username) || (it.owner && it.owner.username) || null,
      caption: (it.caption && it.caption.text) || "",
      like_count: it.like_count ?? null, comment_count: it.comment_count ?? null,
      view_count: it.play_count ?? it.view_count ?? null,
      location: it.location ? it.location.name : null, media: mediaOf(it),
    };
  }

  const username = location.pathname.split("/").filter(Boolean)[0];
  const S = { running: false, done: false, stopped: false, error: null, phase: "idle", started: null,
              grid: (window.__igGrid = window.__igGrid || new Set()),
              tagged: (window.__igTagged = window.__igTagged || new Set()), gapsFilled: 0, gapsLeft: 0 };
  // A profile's posts = everything shown in its grid (including collabs) or owned by the username.
  const isOwn = (code, owner) => S.grid.has(code) || (!!owner && owner.toLowerCase() === username.toLowerCase());

  function expectedPosts() {
    const d = (document.querySelector('meta[name="description"]') || {}).content || "";
    const m = d.match(/([\d.,]+)\s*([KkMm]|rb|jt)?\s+(Posts|postingan|Beiträge|publicaciones|publications|publicações)/i);
    if (!m) return null;
    let n = parseFloat(m[1].replace(/[.,](?=\d{3}\b)/g, "").replace(",", "."));
    const s = (m[2] || "").toLowerCase();
    if (s === "k" || s === "rb") n *= 1e3; else if (s === "m" || s === "jt") n *= 1e6;
    return Math.round(n);
  }
  const gridCodes = () => [...document.querySelectorAll('main a[href*="/p/"], main a[href*="/reel/"]')]
    .map((a) => ({ a, code: a.getAttribute("href").split("/").filter(Boolean).pop() }));

  async function scrollAll(label, into) {
    let idle = 0, round = 0;
    while (idle < 5 && !S.stopped) {
      round++;
      const before = items.size + into.size;
      for (const g of gridCodes()) into.add(g.code);
      window.scrollTo(0, document.documentElement.scrollHeight);
      S.phase = `${label}: scroll #${round}`;
      await sleep(jitter(2500, 4500));
      for (const g of gridCodes()) into.add(g.code);
      idle = items.size + into.size === before ? idle + 1 : 0;
      if (round % 25 === 0) await sleep(jitter(8000, 15000)); // periodic longer pause
    }
  }

  async function fillGaps(codes) {
    const missing = [...codes].filter((c) => !items.has(c));
    S.gapsLeft = missing.length;
    if (!missing.length) return;
    window.scrollTo(0, 0);
    await sleep(1500);
    for (const code of missing) {
      if (S.stopped) return;
      S.phase = `filling in post ${code}`;
      let link = gridCodes().find((g) => g.code === code);
      for (let i = 0; !link && i < 30; i++) { // scroll slowly to find links not rendered yet
        window.scrollBy(0, 600); await sleep(800);
        link = gridCodes().find((g) => g.code === code);
      }
      if (!link) continue;
      link.a.scrollIntoView({ block: "center" });
      await sleep(500);
      link.a.click();
      for (let i = 0; i < 10 && !items.has(code); i++) await sleep(500);
      if (location.pathname.includes(code)) { history.back(); await sleep(jitter(1500, 2500)); }
      if (items.has(code)) S.gapsFilled++;
      S.gapsLeft = [...codes].filter((c) => !items.has(c)).length;
      await sleep(jitter(1500, 3000));
    }
  }

  async function openTab(path) {
    const a = document.querySelector(`a[href="/${username}/${path}"]`);
    if (!a) return false;
    window.scrollTo(0, 0); await sleep(800);
    a.click(); await sleep(jitter(3000, 4500));
    return true;
  }

  async function run(opts) {
    if (!username || !document.querySelector("main")) throw new Error("Open a profile page first: https://www.instagram.com/<username>/");
    S.expected = expectedPosts();
    await scrollAll("posts", S.grid);
    await fillGaps(S.grid);
    if (opts.reels && !S.stopped && await openTab("reels/")) {
      const reelCodes = new Set();
      await scrollAll("reels", reelCodes);
      for (const c of reelCodes) S.grid.add(c);
      await openTab("");
    }
    if (opts.tagged && !S.stopped && await openTab("tagged/")) {
      await scrollAll("tagged", S.tagged);
      await fillGaps(S.tagged);
      await openTab("");
    }
    S.gapsLeft = [...S.grid].filter((c) => !items.has(c)).length;
  }

  function manifest() {
    const all = [...items.values()].map(slim);
    const own = all.filter((p) => isOwn(p.code, p.owner));
    const tagged = all.filter((p) => S.tagged.has(p.code) && !isOwn(p.code, p.owner));
    own.sort((a, b) => (b.taken_at || 0) - (a.taken_at || 0));
    const pic = document.querySelector("header img");
    return {
      tool: "gridvault/chrome_collect", version: 2, username,
      profile_pic: pic && pic.src, expected_posts: S.expected ?? null,
      collected_at: new Date().toISOString(), posts: own, tagged, stories: [], highlights: [],
      missing_codes: [...S.grid].filter((c) => !items.has(c)),
    };
  }

  const api = {
    get running() { return S.running; },
    start(opts = {}) {
      if (S.running) return "Already running; use __ig.status()";
      Object.assign(S, { running: true, done: false, stopped: false, error: null, started: Date.now() });
      log(`collecting @${username}... do not click in this tab until it says done.`);
      const ticker = setInterval(() => {
        const s = api.status();
        log(`${s.phase} · ${s.posts}/${s.expected_posts ?? "?"} posts · ${s.media_files} files · ${s.seconds}s`);
      }, 15000);
      run(opts).catch((e) => { S.error = String(e.message || e); })
        .finally(() => {
          clearInterval(ticker);
          S.running = false; S.done = true; S.phase = S.error ? "failed" : "done";
          const s = api.status();
          if (S.error) log(`failed: ${S.error}. You can still run __ig.save() for a partial manifest.`);
          else log(`done: ${s.posts}/${s.expected_posts ?? "?"} posts, ${s.media_files} files in ${s.seconds}s.`);
          if (opts.autosave) log(api.save());
          else log("Run __ig.save() to download the manifest.");
        });
      return `GridVault started for @${username}`;
    },
    status() {
      const own = [...items.values()].filter((o) => isOwn(o.code, o.user && o.user.username));
      return {
        done: S.done, phase: S.phase, error: S.error, username,
        posts: own.length, expected_posts: S.expected ?? null,
        grid_links: S.grid.size, gaps_filled: S.gapsFilled, gaps_left: S.gapsLeft,
        tagged: S.tagged.size, responses,
        media_files: own.reduce((n, o) => n + mediaOf(o).length, 0),
        seconds: S.started ? Math.round((Date.now() - S.started) / 1000) : 0,
      };
    },
    stop() { S.stopped = true; return "Stopping after the current step"; },
    save() {
      const M = manifest();
      M.partial = !!(S.error || S.stopped || !S.done || M.missing_codes.length);
      M.error = S.error;
      const blob = new Blob([JSON.stringify(M)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `ig_${username}_manifest.json`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 10000);
      return `Saved ${a.download} (${Math.round(blob.size / 1024)} KB, ${M.posts.length} posts) to your Downloads folder`;
    },
  };
  window.__ig = window.GridVault = api;
  log(`ready for @${username}. Run: __ig.start({reels: true, autosave: true})`);
  return `GridVault ready for @${username}`;
})();
