# 01 — Data Acquisition

## Download Method

All data downloaded via `scripts/01_download.sh` using `curl -kL` (skip SSL verification due to Zscaler corporate proxy; `-L` follows redirects).

## Download Results

| City | File | Size | Snapshot |
|------|------|------|----------|
| NYC | listings.csv.gz | 16 MB | 2026-04-14 |
| NYC | reviews.csv.gz | 128 MB | 2026-04-14 |
| Boston | listings.csv.gz | 2.2 MB | 2025-09-23 |
| Boston | reviews.csv.gz | 24 MB | 2025-09-23 |
| Chicago | listings.csv.gz | 4.8 MB | 2025-09-22 |
| Chicago | reviews.csv.gz | 51 MB | 2025-09-22 |
| **Total** | | **~227 MB** | |

## Verification

Files are gzipped CSVs. To verify integrity:

```bash
# check each file decompresses without error
for f in data/*/*.csv.gz; do
  gzip -t "$f" && echo "OK: $f" || echo "FAIL: $f"
done
```

## Directory Layout After Download

```
data/
├── nyc/
│   ├── listings.csv.gz
│   └── reviews.csv.gz
├── boston/
│   ├── listings.csv.gz
│   └── reviews.csv.gz
└── chicago/
    ├── listings.csv.gz
    └── reviews.csv.gz
```

## Next Step

→ `02_data_cleaning.md` — inspect raw data, define cleaning rules, document what gets removed and why.
