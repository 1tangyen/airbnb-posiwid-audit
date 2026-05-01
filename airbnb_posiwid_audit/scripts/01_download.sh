#!/usr/bin/env bash
# Download Inside Airbnb data for NYC, Boston, Chicago
# Usage: bash scripts/01_download.sh
# Data is saved to data/{city}/ directories

set -euo pipefail

DATA_DIR="$(cd "$(dirname "$0")/.." && pwd)/data"
BASE_URL="https://data.insideairbnb.com"

download_city() {
  local city="$1"
  local path="$2"
  local dest="${DATA_DIR}/${city}"
  mkdir -p "$dest"

  for file in listings.csv.gz reviews.csv.gz; do
    local url="${BASE_URL}/${path}/data/${file}"
    local out="${dest}/${file}"

    if [ -f "$out" ]; then
      echo "[skip] ${city}/${file} already exists"
    else
      echo "[download] ${city}/${file} ..."
      curl -kL -o "$out" "$url"
      echo "[done] $(du -h "$out" | cut -f1) downloaded"
    fi
  done
}

download_city "nyc"     "united-states/ny/new-york-city/2026-04-14"
download_city "boston"   "united-states/ma/boston/2025-09-23"
download_city "chicago" "united-states/il/chicago/2025-09-22"

echo ""
echo "=== Download Summary ==="
for city in nyc boston chicago; do
  echo "${city}:"
  du -h "${DATA_DIR}/${city}"/*.csv.gz 2>/dev/null || echo "  (no files)"
done
