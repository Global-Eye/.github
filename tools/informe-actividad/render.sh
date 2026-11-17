#!/usr/bin/env bash
# render.sh <daily|weekly> <YYYY-MM-DD> [png]
set -euo pipefail
SC="$(cd "$(dirname "$0")" && pwd)"; MODE="$1"; D="$2"
CH=$(ls -d /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | head -1)
[ -x "$CH" ] || { echo "No se encuentra Chromium en /opt/pw-browsers" >&2; exit 1; }
mkdir -p "$SC/fonts" "$SC/out"
if [ ! -s "$SC/fonts/InterTight.ttf" ]; then
  U=$(curl -sS -m 30 -A "Mozilla/5.0" "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600;700&display=swap" | grep -oE "https://[^)]+\.(ttf|woff2)" | head -1 || true)
  [ -n "$U" ] && curl -sS -m 60 "$U" -o "$SC/fonts/InterTight.ttf" || echo "AVISO: sin Inter Tight, se usará la sans del sistema" >&2
fi
HTML=$(python3 "$SC/build.py" "$MODE" "$D"); PDF="${HTML%.html}.pdf"
timeout 120 "$CH" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --no-pdf-header-footer --print-to-pdf="$PDF" "file://$HTML" 2>/dev/null
python3 -c "import sys,re;b=open(sys.argv[1],'rb').read();print(sys.argv[1].split('/')[-1], f'{len(b)/1024:.0f} KB', 'páginas:', len(re.findall(rb'/Type\s*/Page[^s]', b)))" "$PDF"
if [ "${3:-}" = "png" ]; then
  for P in 1 2 3; do
    python3 -c "
import sys;f,p=sys.argv[1],sys.argv[2];h=open(f,encoding='utf-8').read()
css=f'<style>html,body{{background:#ddd}}.page{{display:none!important}}#p{p}{{display:flex!important;outline:2px solid #e00;outline-offset:-1px}}</style></head>'
open(f.replace('.html',f'-only{p}.html'),'w',encoding='utf-8').write(h.replace('</head>',css,1))" "$HTML" "$P"
    timeout 120 "$CH" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=794,1260 --screenshot="${HTML%.html}-p$P.png" "file://${HTML%.html}-only$P.html" 2>/dev/null
  done
fi
