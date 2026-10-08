#!/usr/bin/env python3
"""Generator dashboard monitoring project otomasi konten Yunobi.

Membaca data LIVE dari mesin dan menghasilkan dashboard.html tunggal
(self-contained, mobile-friendly, Bahasa Indonesia).

Cara pakai:
    python3 dashboard.py
    # lalu buka dashboard.html di browser

Stdlib only — tanpa dependensi eksternal.
"""
import json
import glob
import os
import re
import html as htmlmod
from datetime import datetime, timedelta, timezone

# --- Konfigurasi ---
BASE = os.path.expanduser("~")
WIB = timezone(timedelta(hours=7))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(OUT_DIR, "dashboard.html")

RETRY_DIR = os.path.join(BASE, "workspace/youtube-otomatis/retry-queue")
MEMORY_DIR = os.path.join(BASE, "memory")
DATA_DIR = os.path.join(BASE, "workspace/blog-otomatis/data")
WORKSPACE = os.path.join(BASE, "workspace")

# Ringkasan jadwal penting (dari docs/06-cron.md, di-hardcode agar tidak
# bergantung pada format markdown yang bisa berubah).
JADWAL = [
    ("10:11", "TikTok FYP harian", "Konten hiburan @ngeweb.yuk via Taisly (otomatis)"),
    ("13:11", "Trend radar YouTube", "Riset demand per 10 niche (silent jika sukses)"),
    ("15:11", "Blog otomatis harian", "Pipeline 6 artikel/hari → posting via web UI"),
    ("16:11", "18 channel YouTube", "Produksi + upload video harian tiap channel"),
    ("17:11", "Promo afiliasi harian", "5 produk → 4 akun (butuh persetujuan)"),
    ("17:11", "Verifikasi pagi blog", "Cek artikel via feed publik + bounce Gmail"),
    ("19:11", "Paket video Shopee", "5 video + caption + link (upload manual)"),
    ("20:00", "Watchdog retry upload", "Eksekusi antrean umur ≥23 jam via browser"),
    ("20:11", "Share IG harian", "IG reel → FB → Threads (butuh persetujuan)"),
    ("21:11", "Balas komentar (malam)", "Cek 12 channel, balas + seed diskusi"),
    ("Senin 09:00", "Refresh SEO mingguan", "Update metadata via yt-growth"),
]

BLOG_NAMES = {
    "kabarviral": "KabarViral", "teknopedia": "TEKNO PEDIA",
    "infokesehatan": "Info Kesehatan", "ekonomibisnis": "Ekonomi Bisnis",
    "gayahidup": "Gaya Hidup", "olahraga": "Olahraga",
    "wisata": "WisataIndo", "kuliner": "KulinerNusantara",
    "otomotif": "OtomotifInfo", "pendidikan": "PendidikanCerdas",
}


def esc(s):
    return htmlmod.escape(str(s if s is not None else ""))


def now_wib():
    return datetime.now(WIB)


def parse_dt(s):
    """Parse ISO datetime; kembalikan aware-datetime WIB atau None."""
    if not s:
        return None
    s = str(s).strip()
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=WIB)
        return dt.astimezone(WIB)
    except Exception:
        return None


# --- 1. Antrean YouTube ---
def load_queue():
    items = []
    try:
        files = sorted(glob.glob(os.path.join(RETRY_DIR, "*.json")))
    except Exception:
        return items
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            gagal = parse_dt(d.get("gagal_pada"))
            if gagal is None:
                continue
            siap_pada = gagal + timedelta(hours=23)
            items.append({
                "channel": d.get("channel", "?"),
                "slot": d.get("slot_target", "-"),
                "gagal_pada": gagal,
                "siap_pada": siap_pada,
                "sebab": d.get("sebab", "-"),
                "file": os.path.basename(f),
            })
        except Exception:
            continue
    # Urut: yang paling siap duluan (siap_pada paling awal)
    items.sort(key=lambda x: x["siap_pada"])
    return items


# --- 2. Blog hari ini ---
def load_blog():
    """Kembalikan (posted: {blog: (n, [judul])}, gagal: [(blog, sebab)], sumber)."""
    posted, gagal, sumber = {}, [], "data tidak tersedia"
    try:
        files = sorted(glob.glob(os.path.join(MEMORY_DIR, "2026-10-*.md")))
        if not files:
            return posted, gagal, sumber
        latest = files[-1]
        with open(latest, encoding="utf-8") as fh:
            text = fh.read()
        sumber = "memory/" + os.path.basename(latest)

        # Cari baris "TERPOSTING (verifikasi feed publik): kabarviral 3 (...), ..."
        for m in re.finditer(r"TERPOSTING[^\n]*?:(.+?)(?:\.\s*Total|\n)", text):
            seg = m.group(1)
            for pm in re.finditer(r"([a-z]+)\s+(\d+)\s*\(([^)]*)\)", seg):
                blog, n, titles = pm.group(1), int(pm.group(2)), pm.group(3)
                if blog in BLOG_NAMES:
                    judul = [t.strip().strip('"').strip("'") for t in re.split(r'"\s*,\s*"|,\s*"(?=[A-Z])', titles) if t.strip()]
                    posted[blog] = (n, judul)
        # Cari "Total N artikel" sebagai validasi
        # Cari kegagalan: pola "Gagal posting N blog" / "blog: GAGAL — sebab"
        for m in re.finditer(r"[Gg]agal posting (\d+) blog[^\n]*:?\s*([^\n]*)", text):
            gagal.append(("rotasi", m.group(0).strip()[:120]))
        for m in re.finditer(r"-\s*(infokesehatan|ekonomibisnis|kabarviral|teknopedia|otomotif|pendidikan|gayahidup|olahraga|wisata|kuliner)\s*:\s*GAGAL\s*[—–-]\s*([^\n]{5,120})", text):
            gagal.append((m.group(1), m.group(2).strip()))
    except Exception:
        pass

    # Fallback: file artikel_terkirim-*.json yang dimodifikasi hari ini
    if not posted:
        try:
            today = now_wib().date()
            for f in glob.glob(os.path.join(DATA_DIR, "artikel_terkirim-*.json")):
                mtime = datetime.fromtimestamp(os.path.getmtime(f), tz=WIB).date()
                if mtime == today:
                    blog = os.path.basename(f).replace("artikel_terkirim-", "").replace(".json", "")
                    posted.setdefault(blog, (0, []))
            if posted:
                sumber = "artikel_terkirim-*.json (mtime hari ini)"
        except Exception:
            pass
    return posted, gagal, sumber


# --- 3. Status video terakhir per channel besar ---
def load_upload_status():
    rows = []
    try:
        for f in glob.glob(os.path.join(WORKSPACE, "*", "upload-terakhir.txt")):
            try:
                with open(f, encoding="utf-8") as fh:
                    isi = fh.read().strip().splitlines()
                channel = os.path.basename(os.path.dirname(f))
                rows.append((channel, "; ".join(isi)[:80] or "-"))
            except Exception:
                continue
    except Exception:
        pass
    return rows


# --- Render HTML ---
def fmt_countdown(delta):
    if delta.total_seconds() <= 0:
        return "sekarang"
    h = int(delta.total_seconds() // 3600)
    m = int((delta.total_seconds() % 3600) // 60)
    if h >= 24:
        d = h // 24
        return f"~{d} hari {h % 24} jam"
    if h > 0:
        return f"~{h} jam {m} mnt"
    return f"~{m} mnt"


def build_html(queue, posted, gagal_blog, sumber_blog, uploads):
    now = now_wib()
    ts = now.strftime("%d %b %Y %H:%M WIB")

    n_antre = len(queue)
    n_siap = sum(1 for q in queue if now >= q["siap_pada"])
    n_artikel = sum(n for n, _ in posted.values())
    n_gagal_blog = len(gagal_blog)

    # --- Tabel antrean ---
    if queue:
        rows = []
        for q in queue:
            siap = now >= q["siap_pada"]
            if siap:
                status = '<span class="badge ok">SIAP</span>'
            else:
                status = f'<span class="badge wait">MENUNGGU<br><small>{esc(fmt_countdown(q["siap_pada"] - now))}</small></span>'
            rows.append(
                "<tr>"
                f"<td><b>{esc(q['channel'])}</b></td>"
                f"<td>{esc(q['slot'])}</td>"
                f"<td>{q['gagal_pada'].strftime('%d %b %H:%M')}</td>"
                f"<td>{q['siap_pada'].strftime('%d %b %H:%M')}</td>"
                f"<td>{status}</td>"
                f"<td class='sebab'>{esc(q['sebab'][:140])}</td>"
                "</tr>"
            )
        tabel_antre = (
            '<div class="tblwrap"><table><thead><tr>'
            "<th>Channel</th><th>Slot target</th><th>Gagal</th>"
            "<th>Bisa dicoba</th><th>Status</th><th>Sebab</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        )
    else:
        tabel_antre = '<p class="empty">Antrean kosong — semua upload lancar. 🎉</p>'

    # --- Blog hari ini ---
    if posted or gagal_blog:
        blog_rows = []
        for blog, (n, judul) in sorted(posted.items(), key=lambda x: -x[1][0]):
            nama = BLOG_NAMES.get(blog, blog)
            j = "".join(f"<li>{esc(t)}</li>" for t in judul[:6]) if judul else ""
            blog_rows.append(
                f"<tr><td><b>{esc(nama)}</b></td>"
                f"<td class='num ok-t'>{n}</td>"
                f"<td><ul class='titles'>{j}</ul></td></tr>"
            )
        for blog, sebab in gagal_blog:
            nama = BLOG_NAMES.get(blog, blog)
            blog_rows.append(
                f"<tr class='failrow'><td><b>{esc(nama)}</b></td>"
                f"<td class='num bad-t'>0</td>"
                f"<td class='sebab'>Gagal: {esc(sebab)}</td></tr>"
            )
        tabel_blog = (
            f'<p class="src">Sumber: {esc(sumber_blog)}</p>'
            '<div class="tblwrap"><table><thead><tr>'
            "<th>Blog</th><th>Tayang</th><th>Judul / Keterangan</th>"
            "</tr></thead><tbody>" + "".join(blog_rows) + "</tbody></table></div>"
        )
    else:
        tabel_blog = '<p class="empty">Data blog hari ini tidak tersedia.</p>'

    # --- Upload terakhir ---
    if uploads:
        up_rows = "".join(
            f"<tr><td><b>{esc(c)}</b></td><td>{esc(i)}</td></tr>" for c, i in uploads
        )
        tabel_upload = (
            '<div class="tblwrap"><table><thead><tr><th>Channel</th><th>Status terakhir</th>'
            "</tr></thead><tbody>" + up_rows + "</tbody></table></div>"
        )
    else:
        tabel_upload = '<p class="empty">Data tidak tersedia.</p>'

    # --- Jadwal ---
    jadwal_rows = "".join(
        f"<tr><td class='jam'><b>{esc(j)}</b></td><td><b>{esc(nm)}</b></td><td>{esc(ds)}</td></tr>"
        for j, nm, ds in JADWAL
    )
    tabel_jadwal = (
        '<div class="tblwrap"><table><thead><tr><th>Jam</th><th>Agenda</th><th>Keterangan</th>'
        "</tr></thead><tbody>" + jadwal_rows + "</tbody></table></div>"
    )

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="1800">
<title>Monitor Project Yunobi</title>
<style>
:root {{ color-scheme: dark light; }}
* {{ box-sizing: border-box; }}
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
  padding: 12px; background: #0f1419; color: #e6edf3; }}
@media (prefers-color-scheme: light) {{
  body {{ background: #f6f8fa; color: #1f2328; }}
  .card {{ background: #fff; border-color: #d0d7de; }}
  table {{ background: #fff; }}
  th {{ background: #f0f3f6 !important; color: #1f2328 !important; }}
  td {{ border-color: #e5e9ec !important; color: #1f2328; }}
  .sebab {{ color: #57606a !important; }}
  .src, footer {{ color: #57606a !important; }}
  .titles li {{ color: #1f2328; }}
}}
header {{ text-align: center; margin-bottom: 14px; }}
header h1 {{ margin: 6px 0; font-size: 1.4rem; }}
header .ts {{ color: #8b949e; font-size: .85rem; }}
.cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px;
  padding: 12px; text-align: center; }}
.card .num {{ font-size: 1.8rem; font-weight: 700; }}
.card .lbl {{ font-size: .78rem; color: #8b949e; margin-top: 4px; }}
.card .num.warn {{ color: #f0a832; }} .card .num.bad {{ color: #f47067; }} .card .num.good {{ color: #3fb950; }}
section {{ margin-bottom: 20px; }}
section h2 {{ font-size: 1.05rem; border-bottom: 2px solid #30363d; padding-bottom: 6px; }}
.tblwrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: .82rem; background: #161b22; }}
th, td {{ padding: 8px 6px; border-bottom: 1px solid #30363d; text-align: left; vertical-align: top; }}
th {{ background: #1c2330; white-space: nowrap; }}
.num {{ text-align: center; font-weight: 700; font-size: 1.1rem; }}
.ok-t {{ color: #3fb950; }} .bad-t {{ color: #f47067; }}
.sebab {{ color: #9aa4b2; font-size: .76rem; max-width: 260px; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: .72rem; font-weight: 700; }}
.badge.ok {{ background: #1a4d2e; color: #3fb950; }}
.badge.wait {{ background: #4d3a1a; color: #f0a832; line-height: 1.3; }}
.badge small {{ font-weight: 400; }}
.titles {{ margin: 0; padding-left: 16px; font-size: .78rem; }}
.titles li {{ margin-bottom: 2px; }}
.failrow td {{ background: rgba(244,112,103,.06); }}
.empty {{ color: #8b949e; font-style: italic; }}
.src {{ color: #8b949e; font-size: .75rem; margin: 0 0 6px; }}
.jam {{ white-space: nowrap; }}
footer {{ text-align: center; color: #8b949e; font-size: .75rem; margin-top: 18px;
  border-top: 1px solid #30363d; padding-top: 10px; }}
@media (max-width: 560px) {{ .cards {{ grid-template-columns: 1fr 1fr 1fr; gap: 6px; }} .card .num {{ font-size: 1.4rem; }} }}
</style>
</head>
<body>
<header>
<h1>📊 Monitor Project Yunobi</h1>
<div class="ts">Update terakhir: {esc(ts)} &nbsp;•&nbsp; refresh otomatis 30 mnt</div>
</header>

<div class="cards">
  <div class="card"><div class="num warn">{n_antre}</div><div class="lbl">video antre<br>({n_siap} siap dicoba)</div></div>
  <div class="card"><div class="num good">{n_artikel}</div><div class="lbl">artikel tayang<br>hari ini</div></div>
  <div class="card"><div class="num bad">{n_gagal_blog}</div><div class="lbl">blog gagal<br>hari ini</div></div>
</div>

<section>
<h2>🎬 Antrean YouTube</h2>
{tabel_antre}
</section>

<section>
<h2>📰 Blog Hari Ini</h2>
{tabel_blog}
</section>

<section>
<h2>📤 Status Video Terakhir</h2>
{tabel_upload}
</section>

<section>
<h2>🗓️ Jadwal</h2>
{tabel_jadwal}
</section>

<footer>Data dari mesin otomasi — bukan live YouTube.<br>
Jalankan <code>python3 dashboard.py</code> untuk memperbarui.</footer>
</body>
</html>
"""


def main():
    try:
        queue = load_queue()
    except Exception:
        queue = []
    try:
        posted, gagal_blog, sumber_blog = load_blog()
    except Exception:
        posted, gagal_blog, sumber_blog = {}, [], "data tidak tersedia"
    try:
        uploads = load_upload_status()
    except Exception:
        uploads = []

    html_out = build_html(queue, posted, gagal_blog, sumber_blog, uploads)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    n_artikel = sum(n for n, _ in posted.values())
    print(f"OK: {OUT_FILE}")
    print(f"Video antre terdeteksi: {len(queue)}")
    print(f"Artikel blog terdeteksi: {n_artikel} ({len(posted)} blog)")
    print(f"Blog gagal: {len(gagal_blog)}")


if __name__ == "__main__":
    main()
