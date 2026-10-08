# Dashboard Monitor Project Yunobi

Generator dashboard HTML tunggal untuk memantau project otomasi konten.

## Cara pakai

```bash
cd ~/workspace/dashboard
python3 dashboard.py
# lalu buka dashboard.html di browser (bisa juga dibuka dari HP via file)
```

Halaman me-refresh otomatis tiap 30 menit (meta refresh). Untuk data
terbaru, jalankan ulang `python3 dashboard.py`.

## Isi dashboard

- **Ringkasan:** video antre | siap dicoba | tayang/terjadwal | artikel blog hari ini
- **Jadwal Produksi:** 18 channel YouTube (nama, handle, niche, pola upload, jam produksi 16:11)
- **Riwayat Upload:** dari `upload-history.json` — judul, channel, status TAYANG/TERJADWAL/ANTRE,
  tanggal, link video (klik). **Bisa diupdate manual** (lihat bawah).
- **Antrean YouTube:** dari `retry-queue/*.json` — kartu per video: channel, slot target,
  gagal kapan, bisa dicoba kapan + countdown, status SIAP/MENUNGGU, sebab singkat.
  Item SIAP punya tombol **📋 Salin perintah** → copy `upload ulang: <nama-file-json>` ke clipboard
  (tempel di chat WhatsApp).
- **Blog Hari Ini:** dari `~/memory/2026-10-*.md` terbaru (fallback:
  file `artikel_terkirim-*.json` yang dimodifikasi hari ini)

## Update Riwayat Upload (manual)

Edit `upload-history.json`, tambah objek baru di array:

```json
{
  "judul": "Judul video",
  "channel": "NamaChannel",
  "status": "TAYANG",
  "tanggal": "10 Okt 19:00",
  "url": "https://www.youtube.com/watch?v=..."
}
```

- `status` harus salah satu: `TAYANG`, `TERJADWAL`, atau `ANTRE`.
- `url` boleh string kosong (`""`) kalau belum ada link.
- `tipe` (opsional): `SHORT` atau `LONG`. Kalau dikosongkan, ditebak dari
  judul (mengandung kata "short"/"long"), kalau tidak ketemu tampil `-`.
- `durasi` (opsional): teks bebas, mis. `"45 dtk"` atau `"14 mnt"`.
  Untuk video di antrean, durasi dibaca otomatis via ffprobe dari `video_path`.
- Setelah edit, jalankan `python3 dashboard.py` (atau tunggu update otomatis 30 menit).

## Mobile

Layout mobile-first: di layar HP (<640px) semua section tampil sebagai kartu
vertikal — tidak ada tabel, tidak ada scroll horizontal. Tombol/link minimal
48px agar mudah diketuk. Di layar lebar (≥900px) kartu tersusun grid 2–3 kolom.

## Catatan

- Semua sumber data dibungkus try/except — file hilang = "data tidak
  tersedia", bukan crash.
- Timestamp memakai WIB (Asia/Jakarta).
- Stdlib only, tanpa dependensi.
