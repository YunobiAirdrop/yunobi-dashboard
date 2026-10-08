#!/bin/bash
set -euo pipefail
cd ~/workspace/dashboard
python3 dashboard.py
cp dashboard.html index.html
git add -A
if git diff --cached --quiet; then echo "tidak ada perubahan"; exit 0; fi
git -c user.name="yunobi-backup" -c user.email="backup@local" commit -qm "Update otomatis $(TZ=Asia/Jakarta date '+%Y-%m-%d %H:%M WIB')"
git -c credential.helper="$HOME/.hermes/gh-dash-helper.sh" push -q origin HEAD:main && echo "push OK $(TZ=Asia/Jakarta date '+%H:%M')"
