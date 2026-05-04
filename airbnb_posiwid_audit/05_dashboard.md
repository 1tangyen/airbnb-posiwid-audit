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

---

## V2 — Stratified Views (Planned)

> **Status**: Pending V2 analysis results. Dashboard will be regenerated after `03_analyze.py` is updated to output stratified data.

### New Chart Panels

| Panel | Chart Type | Data Source |
|-------|-----------|-------------|
| **Score Inflation by Room Type** | Grouped bar (entire/private/shared × 3 cities) | Signal B stratified — % >4.5 per room type |
| **Score Inflation by Host Scale** | Grouped bar (single/small/medium/large × 3 cities) | Signal B stratified — % >4.5 per host listing count group |
| **Hidden Transcript by Room Type** | Grouped bar | Signal C stratified — negative rate in 4.5+ listings per room type |
| **Hidden Transcript by Host Scale** | Grouped bar | Signal C stratified — negative rate per host listing count group |
| **Same-Host vs Cross-Host Similarity** | Side-by-side bar (intra vs inter × 3 cities) | Signal D stratified — mean TF-IDF similarity |
| **Description Similarity by Host Scale** | Grouped bar | Signal D stratified — mean similarity per host listing count group |

### Dashboard Layout Update

V1 layout (7 sections) expands to include a new **"V2: Host Stratification"** tab or section after the existing signal sections. Each stratified chart should have a one-line interpretation note below it (auto-generated from analysis JSON).

### Implementation Notes

- `04_generate_dashboard.py` will need to read stratified keys from `analysis_results.json`
- Stratified data structure: `results.signal_b.stratified.room_type`, `.host_scale`, etc.
- Chart.js grouped bar config: one dataset per group, one category per city
- Lavender Lab design system applies — same color palette, card style, badges
