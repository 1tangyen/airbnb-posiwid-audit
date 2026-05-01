# 05 — Dashboard

## Script

`scripts/04_generate_dashboard.py` — reads `output/analysis_results.json`, generates `output/dashboard.html`.

## What's in the Dashboard

A single self-contained HTML file with:

1. **Summary stat cards** — total listings, reviews, key findings
2. **Signal B (Score Inflation)** — cross-city table + score distribution histograms (NYC, Boston vs Chicago)
3. **Signal C (Hidden Transcript)** — cross-city table + negative/value complaint trend lines + POSIWID audit box
4. **Signal A (Price Variance)** — cross-city table + neighbourhood CV bar chart + room type median price
5. **Signal D (Description Homogenization)** — cross-city TF-IDF similarity table
6. **Host Concentration** — single vs multi-listing bar chart + Gini coefficient comparison
7. **Hidden Transcript story** — 3-paragraph illustration + Chinese principle explanation
8. **POSIWID Synthesis** — final verdict box
9. **Methodology cards** — every signal has an expandable `<details>` section with Data Source (direct download links), Method, Results, and Reproducibility

## Design System

Lavender Lab (defined in vault CLAUDE.md):
- Inter + Noto Sans SC + JetBrains Mono
- `#F5F5F8` gradient background, `#FFFFFF` cards, `#6B5E9E` accents
- Chart.js 4.4.4 via CDN
- Signal strength badges: red (strong), amber (moderate/inconclusive), green (weak)

## How to Regenerate

```bash
# Full pipeline from scratch:
bash scripts/01_download.sh          # download raw data
python3 scripts/02_clean.py          # clean → data/{city}/*_clean.csv.gz
python3 scripts/03_analyze.py        # analyze → output/analysis_results.json
python3 scripts/04_generate_dashboard.py  # dashboard → output/dashboard.html
```

## Data Inline

All chart data is embedded directly in the HTML as a JSON object (assigned to `const DATA`). No external file fetches needed — the dashboard works offline after loading Chart.js from CDN.
