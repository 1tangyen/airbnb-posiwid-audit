# Airbnb POSIWID Audit — Platform Power Through the Lens of What Systems Actually Do

> **POSIWID** (The Purpose Of a System Is What It Does) — Stafford Beer, 1974

![Dashboard Overview](assets/dashboard_hero.png)

## Research Question

Airbnb claims its review and pricing systems exist to **build trust between hosts and guests**. POSIWID asks: what do these systems *actually produce*?

This project applies the POSIWID framework to publicly available Inside Airbnb data across three U.S. cities — **New York City**, **Boston**, and **Chicago** — to test whether platform mechanisms produce the outcomes they claim, or whether the observable outputs reveal a different systemic purpose.

## Key Findings at a Glance

| Metric | NYC | Boston | Chicago |
|--------|-----|--------|---------|
| Listings analyzed | 20,350 | 3,460 | 7,726 |
| Reviews analyzed | 812,395 | 206,478 | 458,188 |
| Scores above 4.5 | 86.4% | 88.3% | 90.9% |
| Negative text in "excellent" reviews | 5.09% | 5.66% | 5.25% |
| Top 10 hosts' market share | 8.4% | **24.7%** | 15.2% |

> **1.48 million reviews. Three cities. The same pattern everywhere.**

## Theoretical Signals

We test three core signals and one supplementary, each grounded in political economy theory:

| Signal | Claim vs. Reality | Theory | Status |
|--------|-------------------|--------|--------|
| **B — Review Score Inflation** | "Reviews reflect quality" vs. 86-91% above 4.5 | Brynjolfsson (2022) — information asymmetry | **Strong** |
| **C — Text vs. Score Gap** | "Scores match sentiment" vs. negative text + high scores | James C. Scott (1990) — Hidden Transcript | **Strong** |
| **D — Description Homogenization** | "Hosts write authentic descriptions" vs. template convergence | Winner (1980) — artifacts have politics | **Moderate** |
| A — Price Variance | "Hosts set their own prices" vs. algorithmic convergence | Braverman (1974) — deskilling | *Inconclusive* |

## The Hidden Transcript — The Core Insight

The most striking finding: **review scores and review text tell different stories**.

![Hidden Transcript Data](assets/charts_hidden_transcript.png)

In NYC alone, **26,857 reviews** describe dirty rooms, misleading photos, noise, or safety concerns — for listings officially rated 4.5+. The negative rate in "excellent" listings (5.1–5.7%) is nearly identical to the overall rate (5.7–6.2%). **High scores do not predict absence of negative experiences.**

This is not a data quality issue — it is the **Hidden Transcript** (James C. Scott, 1990):
- **Public Transcript (scores)**: Visible, identity-bound, subject to retaliation. Overwhelmingly positive.
- **Hidden Transcript (text)**: Buried in volume, rarely surfaced by the algorithm. Contains the honest signal.

## Sentiment Trends Across Cities

![Sentiment Trends](assets/charts_sentiment_trends.png)

Negative sentiment rate (left) and value complaint rate (right) over time across all three cities. Value complaints have roughly doubled since 2015.

## The Gradient Test & Precision Validation

![Score Buckets and Validation](assets/charts_score_buckets_validation.png)

Left: Negative text rate drops sharply from low-scoring to high-scoring listings — scores are not meaningless. But the 4.5-5.0 bucket (where 86-91% of listings cluster) still contains 5-6% negative text — tens of thousands of complaints invisible at the score level. Right: Regex-based detection validated at 87-91% precision.

## Host Concentration

![Host Concentration](assets/charts_host_concentration.png)

Boston stands out: only 65% single-listing hosts, and the top 10 hosts control **24.7%** of all listings — nearly 3x NYC's 8.4%. The "sharing economy" narrative collapses hardest where concentration is highest.

## Project Structure

```
00_data_sources.md          — Data provenance: cities, snapshots, URLs, licensing
01_data_acquisition.md      — Download instructions and verification
02_data_cleaning.md         — Cleaning rules, what was removed, row counts before/after
03_analysis_signals.md      — Methods, parameters, theoretical grounding per signal
04_results.md               — Cross-city comparison results
05_dashboard.md             — Final HTML dashboard build notes
scripts/
  01_download.sh            — Automated data download
  02_clean.py               — Data cleaning pipeline
  03_analyze.py             — Signal analysis
  04_generate_dashboard.py  — Dashboard HTML generation
data/                       — Raw data (gitignored, ~226MB)
output/
  dashboard.html            — Interactive results dashboard
  analysis_results.json     — Full analysis output (JSON)
assets/                     — Screenshots for README
```

## Reproducibility

Every step from raw data to final dashboard is documented and scripted:

```bash
bash scripts/01_download.sh          # Download raw data (~226MB)
python3 scripts/02_clean.py          # Clean → data/{city}/*_clean.csv.gz
python3 scripts/03_analyze.py        # Analyze → output/analysis_results.json
python3 scripts/04_generate_dashboard.py  # Generate → output/dashboard.html
```

Requirements: Python 3.9+, pandas, numpy, scikit-learn. No API keys needed.

## Data Source

All data from [Inside Airbnb](http://insideairbnb.com/) — an independent, non-commercial project providing publicly available data about Airbnb listings worldwide.

- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Attribution**: Inside Airbnb, Murray Cox
- **Snapshots used**: NYC 2026-04-14, Boston 2025-09-23, Chicago 2025-09-22

## POSIWID Verdict

> *The purpose of Airbnb's review system is what it does*: it produces compliant public scores that reduce booking friction, while burying honest feedback in unstructured text that the platform's algorithms never surface. This pattern replicates identically across NYC, Boston, and Chicago — it is a feature of the system, not an accident of any local market.

## Author

VoxelNoir Research — [voxelnoir.substack.com](https://voxelnoir.substack.com)

---

## Methodology Validation

This project was stress-tested against five adversarial critiques. Each was addressed with data:

### 1. "5% negative rate is just normal dissatisfaction, not a power structure."

We ran a **gradient test** — negative rate by listing score bucket:

| Score Bucket | NYC | Boston | Chicago |
|-------------|-----|--------|---------|
| <3.0 | 37.9% | 83.3% | 44.4% |
| 3.5-4.0 | 21.9% | 22.7% | 22.9% |
| 4.0-4.5 | 10.4% | 12.3% | 9.1% |
| **4.5-5.0** | **5.1%** | **5.6%** | **5.2%** |

Scores do weakly correlate with negative experiences. But the 4.5+ bucket — where 86-91% of listings cluster — still contains **26,752 negative reviews in NYC alone**. The gradient exists but is radically insufficient for differentiation within the range that matters.

### 2. "Regex NLP has false positives. 'Not dirty' would match."

Precision validated at **87-91%** via automated negation-context analysis (100 samples per city). Even after ~11% FP discount, adjusted negative rate is ~4.5-5.0% in 4.5+ listings. All patterns hold.

### 3. "Price variance is inconclusive. Why include it?"

Signal A has been **demoted to supplementary** — listed alongside host concentration, not as a core signal. Retaining inconclusive results demonstrates we don't cherry-pick.

### 4. "Cross-sectional data can't support trend narratives."

Acknowledged. Listing data (Signals A, B, D) are single snapshots — we observe states, not processes. The only true longitudinal evidence is Signal C's review text trend (2009-2026), which shows value complaints doubling since 2015. This limitation is documented in `04_results.md`.

### 5. "POSIWID is unfalsifiable."

We added **falsification conditions** for each signal — defined data conditions under which we would abandon each hypothesis. POSIWID itself is used as a framing heuristic, not a testable claim. The testable claims are the individual signals. See `04_results.md § Falsification Conditions`.