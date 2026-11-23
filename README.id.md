# GridVault

**Cadangkan seluruh isi profil Instagram (semua foto, video, carousel, dan reels, lengkap dengan caption dan metadata) memakai browser yang sudah Anda pakai login.**

[English](README.md)

GridVault menggulir profil di browser Anda sendiri, mencatat postingan yang
dimuat halaman, lalu menyimpannya sebagai manifest JSON kecil. Script Python
kemudian mengunduh semua file dalam resolusi penuh ke folder yang rapi. Karena
memakai sesi browsing biasa, bukan membombardir API Instagram, GridVault tetap
jalan saat tool seperti instaloader kena `429` atau `feedback_required`.

```
downloads/<username>/
  profile_pic.jpg
  manifest.json                              # likes, views, caption, lokasi, tanggal
  posts/2024-05-01_10-22-33_C6abcXYZ.jpg     # carousel: _1.jpg, _2.jpg, ...
  posts/2024-05-01_10-22-33_C6abcXYZ.mp4     # video & reels
  posts/2024-05-01_10-22-33_C6abcXYZ.txt     # caption
```

Diuji pada profil nyata berisi 433 postingan: 394 postingan yang tampil di grid
menjadi 613 gambar + 156 video (654 MB) dalam sekitar 5 menit, tanpa diblokir.

## Fitur

- Foto, carousel, video, dan reels dalam resolusi tertinggi yang tersedia
- Caption (`.txt`) dan `manifest.json` lengkap (likes, komentar, views, lokasi, waktu)
- Postingan kolaborasi yang tampil di grid; opsional postingan tempat akun di-tag
- Bisa dijalankan ulang: file yang sudah ada dilewati
- Hanya mengunduh dari CDN Instagram
- **Mode instaloader** opsional untuk stories dan highlights
- Bisa dipakai sebagai **skill [Claude Code](https://claude.com/claude-code)**: cukup bilang *"backup instagram.com/natgeo"*

## Kebutuhan

- Python 3.10+ (mode Chrome hanya memakai library bawaan)
- Google Chrome (atau browser Chromium lain) yang sudah login Instagram
- Opsional: `pip install -r requirements.txt` untuk mode instaloader

## Cara cepat (manual, tanpa AI)

1. **Kumpulkan.** Buka `https://www.instagram.com/<username>/` di Chrome,
   tekan **F12 → Console**, tempel isi
   [`scripts/chrome_collect.js`](scripts/chrome_collect.js), tekan Enter, lalu jalankan:
   ```js
   __ig.start({reels: true, autosave: true})
   ```
   Progres muncul setiap 15 detik. Jangan klik apa pun di tab itu sampai
   muncul tulisan *done*. Setelah itu `ig_<username>_manifest.json` tersimpan
   di folder Downloads.

   > Chrome mungkin meminta Anda mengetik `allow pasting` dulu, dan Instagram
   > menampilkan peringatan besar **"Stop!"**. Peringatan itu benar: jangan
   > pernah menempel kode yang tidak Anda pahami. Kolektor ini sekitar 250
   > baris, jadi baca dulu. Ia hanya membaca data yang memang diterima halaman
   > dan tidak mengirim apa pun ke mana pun.

2. **Unduh.**
   ```bash
   python -I scripts/download_manifest.py ~/Downloads/ig_<username>_manifest.json --out ./downloads
   ```
   Jalankan segera setelah mengumpulkan, karena link CDN Instagram kedaluwarsa dalam beberapa hari.

Opsi kolektor: `reels` (ikut memindai tab Reels), `tagged` (ikut memindai tab
Tagged), `autosave`. Perintah lain: `__ig.status()`, `__ig.stop()`, `__ig.save()`.

## Dipakai dengan Claude Code

Clone repo ini ke folder skills:

```bash
git clone https://github.com/aphriellart/GridVault ~/.claude/skills/gridvault
```

Lalu, dengan extension [Claude in Chrome](https://claude.com/chrome)
tersambung, minta Claude misalnya *"download semua postingan
instagram.com/natgeo"*. Claude akan membuka profil di tab baru, menjalankan
kolektor, menyimpan manifest, dan mengunduh semuanya. Lihat [SKILL.md](SKILL.md).

## Mode instaloader (stories & highlights)

Instagram sangat membatasi sesi otomatis, jadi pakai mode ini hanya untuk yang
tidak bisa dilakukan mode Chrome.

```bash
pip install -r requirements.txt
python scripts/ig_session_from_cookie.py <username_anda>   # sekali saja, tanpa password
python scripts/ig_download.py <target> --all --login <username_anda> --out ./downloads
```

`ig_session_from_cookie.py` meminta Anda menempel cookie `sessionid` (F12 →
Application → Cookies) ke kolom tersembunyi, lalu membaca cookie lainnya dari
clipboard setelah Anda menjalankan `copy(document.cookie)` di Console. File
session memberi akses ke akun Anda: simpan baik-baik, dan logout dari Instagram
untuk mematikannya. Sebaiknya pakai akun sekunder.

Jalankan `python scripts/ig_download.py --help` untuk semua opsi.

## Batasan

- Postingan yang diarsipkan, disembunyikan, atau dibatasi tidak tampil di grid
  sehingga tidak bisa diambil (jumlah postingan versi Instagram mungkin tetap menghitungnya).
- Mode Chrome tidak mengambil stories atau highlights.
- Akun privat hanya bisa jika akun Anda mengikutinya.
- Instagram sering mengubah aplikasi web-nya. Jika kolektor berhenti menemukan
  postingan, silakan buka issue.

## Penggunaan yang bertanggung jawab

GridVault untuk **arsip pribadi**: mencadangkan akun Anda sendiri, atau
menyimpan konten publik untuk referensi pribadi atau riset. Kontennya milik
pembuatnya. Jangan diunggah ulang, dijual, atau disebarkan tanpa izin, jangan
dipakai untuk melecehkan siapa pun, dan patuhi Ketentuan Penggunaan Instagram
serta hukum yang berlaku di tempat Anda. Pengumpulan otomatis bisa melanggar
ketentuan Instagram dan membuat akun dibatasi sementara; risiko penggunaan ada
pada Anda.

GridVault tidak berafiliasi dengan, didukung, atau disponsori oleh Instagram maupun Meta.

## Lisensi

[MIT](LICENSE)
