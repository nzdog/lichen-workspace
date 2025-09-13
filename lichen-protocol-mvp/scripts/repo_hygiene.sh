#!/usr/bin/env bash
set -euo pipefail

THRESHOLD_BYTES=$((5 * 1024 * 1024))   # 5 MB
declare -a large_files=()
declare -a binary_files=()

# --- helpers
is_text_ext() {
  case "$1" in
    *.md|*.txt|*.json|*.jsonl|*.yml|*.yaml|*.toml|*.ini|*.csv|*.tsv|*.py|*.pyi|*.sh|*.bash|*.zsh|*.js|*.ts|*.tsx|*.jsx|*.css|*.scss|*.html|*.xml|*.svg)
      return 0;;
    *) return 1;;
  esac
}

# --- large (tracked only)
while IFS= read -r -d '' f; do
  sz=$(wc -c <"$f")
  if [ "$sz" -gt "$THRESHOLD_BYTES" ]; then
    large_files+=("$f ($sz bytes)")
  fi
done < <(git ls-files -z)

# --- binary (tracked only) — only flag true binary, skip common text/code
# On macOS/Linux, file -I outputs "...; charset=binary" for true binaries
while IFS= read -r -d '' f; do
  if is_text_ext "$f"; then continue; fi
  # file -I can exit 0 even if it prints nothing; grep -q returns 0/1; avoid set -e kill with || true
  if file -I "$f" | grep -q 'charset=binary'; then
    binary_files+=("$f")
  fi
done < <(git ls-files -z)

# --- report & exit
(( ${#large_files[@]} )) && {
  echo "❌ Large files over $THRESHOLD_BYTES bytes:"
  printf '  - %s\n' "${large_files[@]}"
}

(( ${#binary_files[@]} )) && {
  echo "❌ Binary files detected:"
  printf '  - %s\n' "${binary_files[@]}"
}

if (( ${#large_files[@]} + ${#binary_files[@]} )); then
  exit 1
fi

echo "✅ Hygiene checks passed."