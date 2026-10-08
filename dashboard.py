#!/usr/bin/env python3
"""Generator dashboard monitoring project otomasi konten Yunobi.

Membaca data LIVE dari mesin dan menghasilkan dashboard.html tunggal
(self-contained, mobile-first, Bahasa Indonesia).

Section (urut dari atas):
  1. Ringkasan (kartu angka)
  2. Jadwal Produksi (18 channel YouTube, data statis)
  3. Riwayat Upload (dari upload-history.json — bisa diupdate manual)
  4. Antrean Upload (dari retry-queue/*.json, kartu + tombol salin perintah)
  5. Blog Hari Ini
  6. Footer

Cara pakai:
    python3 dashboard.py
    # lalu buka dashboard.html di browser, atau push via update-dan-push.sh

Stdlib only — tanpa dependensi eksternal.
"""
import json
import glob
import os
import re
import subprocess
import html as htmlmod
from datetime import datetime, timedelta, timezone

# --- Konfigurasi ---
BASE = os.path.expanduser("~")
WIB = timezone(timedelta(hours=7))
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_FILE = os.path.join(OUT_DIR, "dashboard.html")
HISTORY_FILE = os.path.join(OUT_DIR, "upload-history.json")

RETRY_DIR = os.path.join(BASE, "workspace/youtube-otomatis/retry-queue")
MEMORY_DIR = os.path.join(BASE, "memory")
DATA_DIR = os.path.join(BASE, "workspace/blog-otomatis/data")

# 18 channel YouTube (dari backup-repo/docs/03-youtube.md).
# (nama, handle, niche, pola upload). Jam produksi semua: 16:11 WIB.
CHANNELS = [
    ("Kisah Horor", "@KisahPOV", "horor ID, voice Mudiwa", "long/shorts bergantian"),
    ("Cerita Rakyat (POV Sejarah)", "@ceritarakyat862", "sejarah ID, voice Mudiwa", "long/shorts bergantian"),
    ("Lima Misteri", "@LimaMisteri", "countdown misteri ID, voice Mudiwa", "long/shorts bergantian"),
    ("Kisah Dharma", "@KisahDharma", "Hindu, footage Pexels", "long/shorts bergantian"),
    ("Jejak Islami", "@JejakIslami-h3d", "Islam, footage Pexels", "long/shorts bergantian"),
    ("Kisah Alkitab", "@KisahAlkitab-k9j", "Kristen, footage Pexels", "long/shorts bergantian"),
    ("Jejak Buddha", "@JejakBuddha", "Buddha, footage Pexels", "long/shorts bergantian"),
    ("Tiny Builders", "@tinybuilders-d5z", "miniatur AI (satu-satunya full-AI)", "long/shorts bergantian"),
    ("InkTime", "@InkTime-d3t", "explainer whiteboard EN", "harian (mulai 9 Okt)"),
    ("Strange Tales", "@StrangeTales-g6n", "shorts EN, voice Miles, target USA", "3 shorts/hari (21:00/03:00/07:00)"),
    ("Ancient Empires", "@AncientEmpiresTV", "sejarah EN", "harian"),
    ("Echoes of the Past", "@EchoesOfThePast-e9n", "history EN", "harian"),
    ("Tales of Dread", "@TalesOfDreadTV", "horror EN", "harian"),
    ("The Dark Mind Files", "@TheDarkMindFiles-s6n", "psikologi/mind EN", "harian"),
    ("Mystery Shadows", "@MysteryShadowsTV", "misteri EN", "harian"),
    ("Cosmos Unknown", "@CosmosUnknownTV", "luar angkasa EN", "harian"),
    ("True Case Files", "@TrueCaseFilesTV", "true crime EN", "harian"),
    ("Bizarre World Daily", "@BizarreWorldDaily", "weird EN", "harian"),
]

BLOG_NAMES = {
    "kabarviral": "KabarViral", "teknopedia": "TEKNO PEDIA",
    "infokesehatan": "Info Kesehatan", "ekonomibisnis": "Ekonomi Bisnis",
    "gayahidup": "Gaya Hidup", "olahraga": "Olahraga",
    "wisata": "WisataIndo", "kuliner": "KulinerNusantara",
    "otomotif": "OtomotifInfo", "pendidikan": "PendidikanCerdas",
}

STATUS_BADGE = {
    "TAYANG": "st-tayang",
    "TERJADWAL": "st-terjadwal",
    "ANTRE": "st-antre",
}


def esc(s):
    return htmlmod.escape(str(s if s is not None else ""))


def now_wib():
    return datetime.now(WIB)


def parse_dt(s):
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
def probe_video(path):
    """Probe durasi via ffprobe. Kembalikan (tipe, durasi_str) atau (None, None)."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10)
        secs = float(r.stdout.strip())
        tipe = "SHORT" if secs <= 61 else "LONG"
        dur = f"{int(round(secs))} dtk" if secs < 60 else f"{int(round(secs / 60))} mnt"
        return tipe, dur
    except Exception:
        return None, None


def tebak_tipe_dari_nama(nama):
    n = (nama or "").lower()
    if "short" in n:
        return "SHORT"
    if "long" in n:
        return "LONG"
    return None


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
            # Tipe + durasi: ffprobe dulu, fallback tebak dari nama file
            vp = d.get("video_path", "") or ""
            tipe, dur = (None, None)
            if vp and os.path.isfile(vp):
                tipe, dur = probe_video(vp)
            if not tipe:
                tipe = tebak_tipe_dari_nama(os.path.basename(vp))
            items.append({
                "channel": d.get("channel", "?"),
                "slot": d.get("slot_target", "-"),
                "gagal_pada": gagal,
                "siap_pada": siap_pada,
                "sebab": d.get("sebab", "-"),
                "file": os.path.basename(f),
                "tipe": tipe or "-",
                "durasi": dur or "-",
            })
        except Exception:
            continue
    items.sort(key=lambda x: x["siap_pada"])
    return items


# --- 2. Riwayat upload (file JSON, bisa diupdate manual) ---
def load_history():
    try:
        with open(HISTORY_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            out = []
            for e in data:
                if isinstance(e, dict):
                    judul = e.get("judul", "-")
                    out.append({
                        "judul": judul,
                        "channel": e.get("channel", "-"),
                        "status": str(e.get("status", "ANTRE")).upper(),
                        "tanggal": e.get("tanggal", "-"),
                        "url": e.get("url", "") or "",
                        "tipe": e.get("tipe") or tebak_tipe_dari_nama(judul) or "-",
                        "durasi": e.get("durasi") or "-",
                    })
            return out
    except Exception:
        pass
    return []


# --- 3. Blog hari ini ---
def _parse_blog_text(text):
    """Parse satu isi memory file menjadi (posted, gagal)."""
    posted, gagal = {}, []
    for m in re.finditer(r"TERPOSTING[^\n]*?:(.+?)(?:\.\s*Total|\n)", text):
        seg = m.group(1)
        for pm in re.finditer(r"([a-z]+)\s+(\d+)\s*\(([^)]*)\)", seg):
            blog, n, titles = pm.group(1), int(pm.group(2)), pm.group(3)
            if blog in BLOG_NAMES:
                judul = [t.strip().strip('"').strip("'")
                         for t in re.split(r'"\s*,\s*"|,\s*"(?=[A-Z])', titles) if t.strip()]
                posted[blog] = (n, judul)
    for m in re.finditer(r"[Gg]agal posting (\d+) blog[^\n]*:?\s*([^\n]*)", text):
        gagal.append(("rotasi", m.group(0).strip()[:120]))
    for m in re.finditer(
            r"-\s*(infokesehatan|ekonomibisnis|kabarviral|teknopedia|otomotif|pendidikan|"
            r"gayahidup|olahraga|wisata|kuliner)\s*:\s*GAGAL\s*[—–-]\s*([^\n]{5,120})", text):
        gagal.append((m.group(1), m.group(2).strip()))
    # Pola alternatif: "GAGAL tulis: infokesehatan & ekonomibisnis (sebab...)"
    for m in re.finditer(r"GAGAL tulis:\s*([^\n]+)", text):
        seg = m.group(1)
        sm = re.search(r"\(([^)]{5,150})\)", seg)
        sebab = sm.group(1).strip() if sm else "gagal tulis artikel"
        for b in re.findall(r"(infokesehatan|ekonomibisnis|kabarviral|teknopedia|otomotif|"
                            r"pendidikan|gayahidup|olahraga|wisata|kuliner)", seg):
            if b not in [x[0] for x in gagal] and b not in posted:
                gagal.append((b, sebab))
    # Pola alternatif: "infokesehatan GAGAL; ekonomibisnis GAGAL"
    for m in re.finditer(r"\b(infokesehatan|ekonomibisnis|kabarviral|teknopedia|otomotif|"
                         r"pendidikan|gayahidup|olahraga|wisata|kuliner)\s+GAGAL\b", text):
        b = m.group(1)
        if b not in [x[0] for x in gagal] and b not in posted:
            gagal.append((b, "gagal tulis artikel"))
    return posted, gagal


def load_blog():
    """Kembalikan (posted, gagal, sumber). Cari mundur maks 4 file terakhir
    yang punya data posting (run blog 15:11, jadi dini hari data = kemarin)."""
    posted, gagal, sumber = {}, [], "data tidak tersedia"
    try:
        files = sorted(glob.glob(os.path.join(MEMORY_DIR, "2026-10-*.md")))
        for path in reversed(files[-4:]):
            try:
                with open(path, encoding="utf-8") as fh:
                    text = fh.read()
            except Exception:
                continue
            p, g = _parse_blog_text(text)
            if p:
                posted, gagal = p, g
                sumber = "memory/" + os.path.basename(path)
                break
    except Exception:
        pass

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


def badge_tipe(tipe, durasi):
    """Badge SHORT/LONG + durasi. Kembalikan string kosong bila tak diketahui."""
    if tipe == "SHORT":
        cls = "tipe-short"
    elif tipe == "LONG":
        cls = "tipe-long"
    else:
        return ""
    label = f"{tipe} • {durasi}" if durasi and durasi != "-" else tipe
    return f'<span class="badge {cls}">{esc(label)}</span>'


def fmt_countdown(delta):
    if delta.total_seconds() <= 0:
        return "sekarang"
    h = int(delta.total_seconds() // 3600)
    m = int((delta.total_seconds() % 3600) // 60)
    if h >= 24:
        return f"~{h // 24} hari {h % 24} jam"
    if h > 0:
        return f"~{h} jam {m} mnt"
    return f"~{m} mnt"


# --- Render ---
def card_ringkasan(n_antre, n_siap, n_tayang_hist, n_artikel):
    return f"""
<div class="cards">
  <div class="card"><div class="num warn">{n_antre}</div><div class="lbl">video antre</div></div>
  <div class="card"><div class="num good">{n_siap}</div><div class="lbl">siap dicoba</div></div>
  <div class="card"><div class="num good">{n_tayang_hist}</div><div class="lbl">tayang/<br>terjadwal</div></div>
  <div class="card"><div class="num good">{n_artikel}</div><div class="lbl">artikel blog<br>hari ini</div></div>
</div>"""


def section_jadwal():
    cards = []
    for nama, handle, niche, pola in CHANNELS:
        cards.append(
            f'<div class="item compact">'
            f'<div class="item-head"><b>{esc(nama)}</b>'
            f'<span class="handle">{esc(handle)}</span></div>'
            f'<div class="meta">{esc(niche)}</div>'
            f'<div class="meta">🎬 Produksi 16:11 WIB &nbsp;•&nbsp; {esc(pola)}</div>'
            f'</div>'
        )
    return ('<section><h2>🗓️ Jadwal Produksi (18 Channel)</h2>'
            '<div class="grid">' + "".join(cards) + '</div></section>')


def section_history(history):
    if not history:
        body = '<p class="empty">Riwayat kosong — tambah entri di upload-history.json.</p>'
    else:
        cards = []
        for e in history:
            cls = STATUS_BADGE.get(e["status"], "st-antre")
            link = (f'<a class="linkbtn" href="{esc(e["url"])}" target="_blank" '
                    f'rel="noopener">▶ Buka video</a>' if e["url"] else "")
            cards.append(
                f'<div class="item">'
                f'<div class="item-head"><b>{esc(e["judul"])}</b>'
                f'<span class="badges">{badge_tipe(e["tipe"], e["durasi"])}'
                f'<span class="badge {cls}">{esc(e["status"])}</span></span></div>'
                f'<div class="meta">{esc(e["channel"])} &nbsp;•&nbsp; {esc(e["tanggal"])}</div>'
                f'{link}</div>'
            )
        body = '<div class="grid">' + "".join(cards) + '</div>'
    return f'<section><h2>📤 Riwayat Upload</h2>{body}</section>'


def section_queue(queue, now):
    if not queue:
        body = '<p class="empty">Antrean kosong — semua upload lancar. 🎉</p>'
    else:
        cards = []
        for q in queue:
            siap = now >= q["siap_pada"]
            if siap:
                badge = '<span class="badge ok">SIAP</span>'
                cmd = f"upload ulang: {q['file']}"
                aksi = (
                    f'<button class="copybtn" data-cmd="{esc(cmd)}" '
                    f'onclick="salinPerintah(this)">📋 Salin perintah</button>'
                    f'<div class="hint">tempel di chat WhatsApp</div>'
                )
            else:
                sisa = fmt_countdown(q["siap_pada"] - now)
                badge = f'<span class="badge wait">MENUNGGU<br><small>{esc(sisa)} lagi</small></span>'
                aksi = ""
            cards.append(
                f'<div class="item">'
                f'<div class="item-head"><b>{esc(q["channel"])}</b>'
                f'<span class="badges">{badge_tipe(q["tipe"], q["durasi"])}{badge}</span></div>'
                f'<dl class="kv">'
                f'<div><dt>Slot target</dt><dd>{esc(q["slot"])}</dd></div>'
                f'<div><dt>Gagal</dt><dd>{q["gagal_pada"].strftime("%d %b %H:%M")}</dd></div>'
                f'<div><dt>Bisa dicoba</dt><dd>{q["siap_pada"].strftime("%d %b %H:%M")}</dd></div>'
                f'<div><dt>Sebab</dt><dd class="sebab">{esc(q["sebab"][:160])}</dd></div>'
                f'</dl>{aksi}</div>'
            )
        body = '<div class="grid">' + "".join(cards) + '</div>'
    return f'<section><h2>🎬 Antrean Upload</h2>{body}</section>'


def section_blog(posted, gagal_blog, sumber_blog):
    if not posted and not gagal_blog:
        body = '<p class="empty">Data blog hari ini tidak tersedia.</p>'
    else:
        cards = []
        for blog, (n, judul) in sorted(posted.items(), key=lambda x: -x[1][0]):
            nama = BLOG_NAMES.get(blog, blog)
            j = "".join(f"<li>{esc(t)}</li>" for t in judul[:6]) if judul else ""
            cards.append(
                f'<div class="item"><div class="item-head"><b>{esc(nama)}</b>'
                f'<span class="badge ok">{n} tayang</span></div>'
                f'<ul class="titles">{j}</ul></div>'
            )
        for blog, sebab in gagal_blog:
            nama = BLOG_NAMES.get(blog, blog)
            cards.append(
                f'<div class="item fail"><div class="item-head"><b>{esc(nama)}</b>'
                f'<span class="badge bad">GAGAL</span></div>'
                f'<div class="sebab">{esc(sebab)}</div></div>'
            )
        body = (f'<p class="src">Sumber: {esc(sumber_blog)}</p>'
                '<div class="grid">' + "".join(cards) + '</div>')
    return f'<section><h2>📰 Blog Hari Ini</h2>{body}</section>'


def build_html(queue, history, posted, gagal_blog, sumber_blog):
    now = now_wib()
    ts = now.strftime("%d %b %Y %H:%M WIB")

    n_antre = len(queue)
    n_siap = sum(1 for q in queue if now >= q["siap_pada"])
    n_tayang_hist = sum(1 for e in history if e["status"] in ("TAYANG", "TERJADWAL"))
    n_artikel = sum(n for n, _ in posted.values())

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
html {{ -webkit-text-size-adjust: 100%; }}
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
  padding: 12px; background: #0f1419; color: #e6edf3; font-size: 16px; line-height: 1.45; }}
@media (prefers-color-scheme: light) {{
  body {{ background: #f6f8fa; color: #1f2328; }}
  .card, .item {{ background: #fff !important; border-color: #d0d7de !important; }}
  .sebab, .src, .meta, footer, header .ts, .hint {{ color: #57606a !important; }}
  .titles li, .kv dd {{ color: #1f2328; }}
  .kv dt {{ color: #57606a; }}
  .linkbtn {{ background: #1f6feb; }}
}}
header {{ text-align: center; margin-bottom: 14px; }}
header h1 {{ margin: 6px 0; font-size: 1.35rem; }}
header .ts {{ color: #8b949e; font-size: .85rem; }}
.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px;
  padding: 12px 6px; text-align: center; }}
.card .num {{ font-size: 1.7rem; font-weight: 700; }}
.card .lbl {{ font-size: .75rem; color: #8b949e; margin-top: 4px; }}
.num.warn {{ color: #f0a832; }} .num.bad {{ color: #f47067; }} .num.good {{ color: #3fb950; }}
section {{ margin-bottom: 22px; }}
section h2 {{ font-size: 1.05rem; border-bottom: 2px solid #30363d; padding-bottom: 6px; margin-bottom: 10px; }}
.grid {{ display: grid; gap: 10px; grid-template-columns: 1fr; }}
.item {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px;
  padding: 12px; overflow-wrap: anywhere; }}
.item.fail {{ border-color: #7a2e2e; }}
.item-head {{ display: flex; justify-content: space-between; align-items: flex-start;
  gap: 8px; margin-bottom: 6px; font-size: .95rem; }}
.item-head b {{ flex: 1; }}
.handle {{ color: #8b949e; font-size: .8rem; white-space: nowrap; }}
.meta {{ color: #9aa4b2; font-size: .82rem; margin-bottom: 2px; }}
.kv {{ margin: 8px 0 0; display: grid; gap: 6px; }}
.kv > div {{ display: grid; grid-template-columns: 96px 1fr; gap: 8px; }}
.kv dt {{ color: #8b949e; font-size: .78rem; }}
.kv dd {{ margin: 0; font-size: .85rem; }}
.sebab {{ color: #9aa4b2; font-size: .8rem; }}
.src {{ color: #8b949e; font-size: .75rem; margin: 0 0 8px; }}
.titles {{ margin: 6px 0 0; padding-left: 18px; font-size: .85rem; }}
.titles li {{ margin-bottom: 3px; }}
.badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px;
  font-size: .72rem; font-weight: 700; white-space: nowrap; text-align: center; }}
.badge.ok {{ background: #1a4d2e; color: #3fb950; }}
.badge.wait {{ background: #4d3a1a; color: #f0a832; line-height: 1.35; }}
.badge.bad {{ background: #4d1a1a; color: #f47067; }}
.badge.st-tayang {{ background: #1a4d2e; color: #3fb950; }}
.badge.st-terjadwal {{ background: #1a3a4d; color: #58a6ff; }}
.badge.st-antre {{ background: #4d3a1a; color: #f0a832; }}
.badge.tipe-short {{ background: #1a3a4d; color: #58a6ff; }}
.badge.tipe-long {{ background: #3a1a4d; color: #d2a8ff; }}
.badges {{ display: inline-flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end; }}
.badge small {{ font-weight: 400; }}
.copybtn {{ display: block; width: 100%; margin-top: 10px; padding: 13px;
  font-size: 1rem; font-weight: 700; border: none; border-radius: 10px;
  background: #1f6feb; color: #fff; cursor: pointer; min-height: 48px; }}
.copybtn:active {{ background: #388bfd; }}
.hint {{ text-align: center; color: #8b949e; font-size: .75rem; margin-top: 5px; }}
.linkbtn {{ display: inline-block; margin-top: 8px; padding: 10px 18px; min-height: 44px;
  background: #238636; color: #fff !important; border-radius: 10px;
  text-decoration: none; font-weight: 700; font-size: .9rem; }}
.empty {{ color: #8b949e; font-style: italic; }}
footer {{ text-align: center; color: #8b949e; font-size: .78rem; margin-top: 18px;
  border-top: 1px solid #30363d; padding-top: 10px; }}
/* Layar lebar: kartu jadi grid multi-kolom (TIDAK ada tabel di mana pun) */
@media (min-width: 900px) {{
  body {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
  section .grid {{ grid-template-columns: repeat(2, 1fr); }}
  section:nth-of-type(2) .grid {{ grid-template-columns: repeat(3, 1fr); }}
}}
</style>
</head>
<body>
<header>
<h1>📊 Monitor Project Yunobi</h1>
<div class="ts">Update terakhir: {esc(ts)} &nbsp;•&nbsp; refresh otomatis 30 mnt</div>
</header>

{card_ringkasan(n_antre, n_siap, n_tayang_hist, n_artikel)}
{section_jadwal()}
{section_history(history)}
{section_queue(queue, now)}
{section_blog(posted, gagal_blog, sumber_blog)}

<footer>Waktu update: {esc(ts)}<br>Data dari mesin otomasi — bukan live YouTube.</footer>

<script>
function salinPerintah(btn) {{
  var t = btn.getAttribute('data-cmd');
  var label = btn.innerHTML;
  function ok() {{
    btn.innerHTML = '✅ Tersalin!';
    setTimeout(function() {{ btn.innerHTML = label; }}, 2000);
  }}
  function fallback() {{
    var ta = document.createElement('textarea');
    ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try {{ document.execCommand('copy'); ok(); }}
    catch (e) {{ btn.innerHTML = '❌ Gagal menyalin'; }}
    document.body.removeChild(ta);
  }}
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(t).then(ok, fallback);
  }} else {{
    fallback();
  }}
}}
</script>
</body>
</html>
"""


def main():
    try:
        queue = load_queue()
    except Exception:
        queue = []
    try:
        history = load_history()
    except Exception:
        history = []
    try:
        posted, gagal_blog, sumber_blog = load_blog()
    except Exception:
        posted, gagal_blog, sumber_blog = {}, [], "data tidak tersedia"

    html_out = build_html(queue, history, posted, gagal_blog, sumber_blog)
    with open(OUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    n_artikel = sum(n for n, _ in posted.values())
    n_siap = sum(1 for q in queue if now_wib() >= q["siap_pada"])
    print(f"OK: {OUT_FILE}")
    print(f"Video antre: {len(queue)} ({n_siap} siap)")
    print(f"Riwayat upload: {len(history)} entri")
    print(f"Artikel blog: {n_artikel} ({len(posted)} blog), gagal: {len(gagal_blog)}")


if __name__ == "__main__":
    main()
