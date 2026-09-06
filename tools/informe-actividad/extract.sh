#!/usr/bin/env bash
# extract.sh <dir_datos> <repo1> [repo2 ...]
# Vuelca a <dir_datos>/commits.tsv todos los commits (todas las ramas) de los últimos 40 días de cada repo clonado en /workspace/<repo>.
# Columnas: repo, sha, fecha_autor_iso, email, nombre, en_main(0/1), es_merge(0/1), asunto
set -euo pipefail
OUT="$1"; shift
mkdir -p "$OUT"
SINCE=$(date -u -d "40 days ago" +%F)
: > "$OUT/commits.tsv"
for R in "$@"; do
  D="/workspace/$R"
  [ -d "$D/.git" ] || { echo "AVISO: $R no está clonado, se omite" >&2; continue; }
  git -C "$D" fetch -q --all --prune 2>/dev/null || true
  MAIN=$(git -C "$D" symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)
  git -C "$D" rev-list "$MAIN" --since="$SINCE" > "$OUT/main_$R.txt" 2>/dev/null || : > "$OUT/main_$R.txt"
  git -C "$D" log --all --since="$SINCE" --format='%H%x09%aI%x09%ae%x09%an%x09%P%x09%s' | sort -u | \
  while IFS=$'\t' read -r sha aiso email name parents subj; do
    onmain=0; grep -q "^$sha$" "$OUT/main_$R.txt" && onmain=1
    ismerge=0; [ "$(echo "$parents" | wc -w)" -gt 1 ] && ismerge=1
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$R" "$sha" "$aiso" "$email" "$name" "$onmain" "$ismerge" "$subj"
  done >> "$OUT/commits.tsv"
  echo "$R: $(grep -c "^$R	" "$OUT/commits.tsv") commits"
done
