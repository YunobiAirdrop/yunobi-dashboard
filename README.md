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

- **Kartu ringkasan:** video antre | artikel tayang hari ini | blog gagal
- **Antrean YouTube:** dari `retry-queue/*.json` — status SIAP (≥23 jam
  sejak gagal) atau MENUNGGU + countdown, urut dari yang paling siap
- **Blog Hari Ini:** dari `~/memory/2026-10-*.md` terbaru (fallback:
  file `artikel_terkirim-*.json` yang dimodifikasi hari ini)
- **Status Video Terakhir:** dari file `upload-terakhir.txt` di workspace
- **Jadwal:** ringkasan cron penting (hardcode dari `docs/06-cron.md`)

## Catatan

- Semua sumber data dibungkus try/except — file hilang = "data tidak
  tersedia", bukan crash.
- Timestamp memakai WIB (Asia/Jakarta).
- Stdlib only, tanpa dependensi.
