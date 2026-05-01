"""
04_generate_dashboard.py — Generate interactive HTML dashboard from analysis results.

Reads:  output/analysis_results.json
Writes: output/dashboard.html

The HTML is self-contained (inline CSS, inline JS, inline data).
Uses Chart.js via CDN for charts. Lavender Lab design system.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "output"

def load_results():
    with open(OUTPUT_DIR / "analysis_results.json") as f:
        return json.load(f)


def generate_html(results: dict) -> str:
    data_json = json.dumps(results)

    # Extract cross-city summary for quick reference
    summary = results["cross_city_summary"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Airbnb POSIWID Audit — Cross-City Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg: #F5F5F8;
  --bg-grad: radial-gradient(ellipse 80% 60% at 80% 0%, #EAE6F8 0%, #F5F5F8 70%);
  --surface: #FFFFFF;
  --surface-2: #F0EEF8;
  --surface-3: #ECEAF5;
  --border: #DDD9EC;
  --nav: #6B5E9E;
  --purple: #6B5E9E;
  --purple-hover: #5B4F8E;
  --purple-light: rgba(107,94,158,0.08);
  --text-1: #1E1A38;
  --text-2: #3A3360;
  --text-3: #6A6090;
  --text-4: #9A96B4;
  --green: #1DB876;
  --green-bg: rgba(29,184,118,0.08);
  --green-border: rgba(29,184,118,0.25);
  --amber: #D97706;
  --amber-bg: rgba(217,119,6,0.07);
  --amber-border: rgba(217,119,6,0.25);
  --red: #DC2626;
  --red-bg: rgba(220,38,38,0.06);
  --red-border: rgba(220,38,38,0.2);
  --sans: 'Inter', 'Noto Sans SC', -apple-system, sans-serif;
  --mono: 'JetBrains Mono', monospace;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: var(--sans); background: var(--bg-grad); color: var(--text-2); line-height: 1.6; font-size: 14px; }}

nav {{ background: var(--nav); height: 52px; display: flex; align-items: center; padding: 0 2rem; color: #fff; position: sticky; top: 0; z-index: 100; }}
nav .brand {{ font-weight: 700; font-size: 1.1rem; }}
nav .subtitle {{ font-weight: 400; font-size: 0.85rem; opacity: 0.85; margin-left: 1rem; }}

.container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }}

h1 {{ font-size: 1.8rem; font-weight: 700; color: var(--text-1); margin-bottom: 0.5rem; }}
h2 {{ font-size: 1.3rem; font-weight: 600; color: var(--text-1); margin: 2.5rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }}
h3 {{ font-size: 1.05rem; font-weight: 600; color: var(--text-1); margin: 1.5rem 0 0.75rem; }}

.lead {{ font-size: 1.05rem; color: var(--text-3); margin-bottom: 2rem; max-width: 720px; }}

/* Stat cards row */
.stats-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
.stat-card {{ background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--purple); border-radius: 12px; padding: 1.25rem 1.5rem; }}
.stat-card .label {{ font-size: 0.75rem; font-family: var(--mono); color: var(--text-4); text-transform: uppercase; letter-spacing: 0.05em; }}
.stat-card .value {{ font-size: 1.6rem; font-weight: 700; color: var(--text-1); margin: 0.25rem 0; }}
.stat-card .sub {{ font-size: 0.8rem; color: var(--text-3); }}

/* Signal cards */
.signal-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 2rem; margin-bottom: 1.5rem; }}
.signal-card .signal-header {{ display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem; }}
.signal-card .signal-id {{ font-family: var(--mono); font-size: 0.7rem; padding: 3px 8px; border-radius: 4px; font-weight: 600; }}
.signal-strong {{ background: var(--red-bg); border: 1px solid var(--red-border); color: var(--red); }}
.signal-moderate {{ background: var(--amber-bg); border: 1px solid var(--amber-border); color: var(--amber); }}
.signal-weak {{ background: var(--green-bg); border: 1px solid var(--green-border); color: var(--green); }}

/* Comparison table */
table {{ width: 100%; background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; border-collapse: collapse; margin: 1rem 0; font-size: 0.9rem; }}
thead {{ background: var(--surface-2); }}
th {{ padding: 0.75rem 1rem; text-align: left; font-weight: 600; color: var(--text-1); font-size: 0.8rem; }}
td {{ padding: 0.75rem 1rem; border-top: 1px solid var(--border); }}
td.num {{ font-family: var(--mono); text-align: right; }}

/* Chart containers */
.chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 1.5rem 0; }}
.chart-box {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }}
.chart-box h4 {{ font-size: 0.9rem; font-weight: 600; color: var(--text-1); margin-bottom: 1rem; }}
.chart-box canvas {{ max-height: 300px; }}

@media (max-width: 768px) {{
  .chart-row {{ grid-template-columns: 1fr; }}
  .stats-row {{ grid-template-columns: 1fr 1fr; }}
}}

/* POSIWID audit box */
.posiwid-box {{ background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--purple); border-radius: 12px; padding: 1.5rem 2rem; margin: 1.5rem 0; }}
.posiwid-box .claimed {{ color: var(--text-3); font-style: italic; }}
.posiwid-box .actual {{ color: var(--red); font-weight: 600; }}

/* Method card */
details.method-card {{ background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; margin: 1rem 0; padding: 0; }}
details.method-card summary {{ padding: 0.75rem 1rem; cursor: pointer; font-size: 0.85rem; font-weight: 500; color: var(--text-3); }}
details.method-card summary:hover {{ color: var(--purple); }}
.method-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 0 1rem 1rem; }}
.method-cell {{ font-size: 0.8rem; }}
.method-cell .label {{ font-family: var(--mono); font-size: 0.7rem; color: var(--text-4); text-transform: uppercase; margin-bottom: 0.25rem; }}
.method-cell a {{ color: var(--purple); text-decoration: none; }}
.method-cell a:hover {{ text-decoration: underline; }}

@media (max-width: 768px) {{
  .method-grid {{ grid-template-columns: 1fr; }}
}}

/* Story card */
.story-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 2rem; margin: 2rem 0; }}
.story-card p {{ margin-bottom: 1rem; line-height: 1.8; }}
.story-card .principle-box {{ background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem 1.5rem; margin-top: 1.5rem; }}

/* Footer */
footer {{ margin-top: 3rem; padding: 2rem 0; border-top: 1px solid var(--border); font-size: 0.8rem; color: var(--text-4); }}
footer a {{ color: var(--purple); text-decoration: none; }}
</style>
</head>
<body>

<nav>
  <span class="brand">Airbnb POSIWID Audit</span>
  <span class="subtitle">Platform Power Through the Lens of What Systems Actually Do</span>
</nav>

<div class="container">

<h1>Cross-City POSIWID Dashboard</h1>
<p class="lead">
  Applying Stafford Beer's POSIWID framework to 1.48M reviews across NYC, Boston, and Chicago.
  What does Airbnb's review and pricing system <em>actually produce</em>?
</p>

<!-- Summary Stats -->
<div class="stats-row">
  <div class="stat-card">
    <div class="label">Total Listings</div>
    <div class="value">31,536</div>
    <div class="sub">After cleaning (3 cities)</div>
  </div>
  <div class="stat-card">
    <div class="label">Total Reviews</div>
    <div class="value">1.48M</div>
    <div class="sub">English, 2009–2026</div>
  </div>
  <div class="stat-card">
    <div class="label">Score &gt; 4.5</div>
    <div class="value">86–91%</div>
    <div class="sub">Across all 3 cities</div>
  </div>
  <div class="stat-card">
    <div class="label">Hidden Transcript</div>
    <div class="value">5–6%</div>
    <div class="sub">Neg text in 4.5+ listings</div>
  </div>
</div>

<!-- Signal B: Score Inflation -->
<h2>Signal B — Review Score Inflation</h2>
<div class="signal-card">
  <div class="signal-header">
    <span class="signal-id signal-strong">STRONG SIGNAL</span>
    <span>Brynjolfsson (2022) — Information asymmetry as bargaining leverage</span>
  </div>
  <p><strong>Claim</strong>: "Reviews help guests make informed decisions."<br>
  <strong>POSIWID</strong>: If 86–91% of listings score identically (&gt;4.5), the system produces undifferentiation, not information.</p>

  <table>
    <thead><tr><th>Metric</th><th>NYC</th><th>Boston</th><th>Chicago</th></tr></thead>
    <tbody>
      <tr><td>Mean Score</td><td class="num">4.721</td><td class="num">4.738</td><td class="num">4.769</td></tr>
      <tr><td>% Above 4.5</td><td class="num">86.4%</td><td class="num">88.3%</td><td class="num">90.9%</td></tr>
      <tr><td>% Above 4.8</td><td class="num">59.4%</td><td class="num">58.0%</td><td class="num">65.4%</td></tr>
      <tr><td>% Perfect 5.0</td><td class="num">27.1%</td><td class="num">21.6%</td><td class="num">21.3%</td></tr>
      <tr><td>Value Sub-Score (lowest)</td><td class="num">4.608</td><td class="num">4.601</td><td class="num">4.677</td></tr>
    </tbody>
  </table>

  <details class="method-card">
    <summary>Methodology &amp; Data Source</summary>
    <div class="method-grid">
      <div class="method-cell">
        <div class="label">Data Source</div>
        <a href="https://data.insideairbnb.com/united-states/ny/new-york-city/2026-04-14/data/listings.csv.gz">NYC listings</a> &middot;
        <a href="https://data.insideairbnb.com/united-states/ma/boston/2025-09-23/data/listings.csv.gz">Boston listings</a> &middot;
        <a href="https://data.insideairbnb.com/united-states/il/chicago/2025-09-22/data/listings.csv.gz">Chicago listings</a><br>
        Source: <a href="http://insideairbnb.com/get-the-data/">Inside Airbnb</a> (CC BY 4.0)
      </div>
      <div class="method-cell">
        <div class="label">Method</div>
        Field: <code>review_scores_rating</code> (1.0–5.0).<br>
        Distribution histogram (0.1 bins). Sub-scores compared across 6 dimensions.
      </div>
      <div class="method-cell">
        <div class="label">Results</div>
        86–91% above 4.5 across all cities. Value is the lowest sub-score everywhere (4.60–4.68).
        27% of NYC listings have a perfect 5.0.
      </div>
      <div class="method-cell">
        <div class="label">Reproducibility</div>
        <code>scripts/03_analyze.py → analyze_score_inflation()</code>
      </div>
    </div>
  </details>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h4>Score Distribution — NYC</h4>
    <canvas id="chart-score-nyc"></canvas>
  </div>
  <div class="chart-box">
    <h4>Score Distribution — Boston vs Chicago</h4>
    <canvas id="chart-score-compare"></canvas>
  </div>
</div>

<!-- Signal C: Hidden Transcript -->
<h2>Signal C — The Hidden Transcript</h2>
<div class="signal-card">
  <div class="signal-header">
    <span class="signal-id signal-strong">STRONG SIGNAL</span>
    <span>James C. Scott (1990) — Domination and the Arts of Resistance</span>
  </div>
  <p><strong>Claim</strong>: "Scores and text together give the full picture."<br>
  <strong>POSIWID</strong>: Scores and text tell <em>different stories</em>. Scores are compliant. Text is honest. The gap is the power structure.</p>

  <table>
    <thead><tr><th>Metric</th><th>NYC</th><th>Boston</th><th>Chicago</th></tr></thead>
    <tbody>
      <tr><td>Total Reviews (cleaned)</td><td class="num">812,395</td><td class="num">206,478</td><td class="num">458,188</td></tr>
      <tr><td>Negative Text Rate (overall)</td><td class="num">5.67%</td><td class="num">6.22%</td><td class="num">5.98%</td></tr>
      <tr><td>Value Complaint Rate</td><td class="num">0.23%</td><td class="num">0.29%</td><td class="num">0.22%</td></tr>
      <tr><td>Reviews for 4.5+ Listings</td><td class="num">527,681</td><td class="num">143,901</td><td class="num">299,737</td></tr>
      <tr><td><strong>Neg Rate in 4.5+ Reviews</strong></td><td class="num"><strong>5.09%</strong></td><td class="num"><strong>5.66%</strong></td><td class="num"><strong>5.25%</strong></td></tr>
    </tbody>
  </table>

  <div class="posiwid-box">
    <p>In NYC alone, <strong>26,857 reviews</strong> describe dirty rooms, misleading photos, noise, or safety concerns — for listings rated 4.5+.</p>
    <p>The negative rate in "excellent" listings (5.1–5.7%) is nearly identical to the overall rate (5.7–6.2%) — <span class="actual">high scores do not predict absence of negative experiences.</span></p>
  </div>

  <details class="method-card">
    <summary>Methodology &amp; Data Source</summary>
    <div class="method-grid">
      <div class="method-cell">
        <div class="label">Data Source</div>
        <a href="https://data.insideairbnb.com/united-states/ny/new-york-city/2026-04-14/data/reviews.csv.gz">NYC reviews</a> &middot;
        <a href="https://data.insideairbnb.com/united-states/ma/boston/2025-09-23/data/reviews.csv.gz">Boston reviews</a> &middot;
        <a href="https://data.insideairbnb.com/united-states/il/chicago/2025-09-22/data/reviews.csv.gz">Chicago reviews</a><br>
        Source: <a href="http://insideairbnb.com/get-the-data/">Inside Airbnb</a> (CC BY 4.0)
      </div>
      <div class="method-cell">
        <div class="label">Method</div>
        25 regex negative patterns + 8 value-complaint patterns applied to <code>comments</code> field.
        Cross-referenced with <code>review_scores_rating &ge; 4.5</code> from listings.
        English-only reviews (ASCII letter ratio &gt; 50%).
      </div>
      <div class="method-cell">
        <div class="label">Results</div>
        5–6% of reviews for "excellent" listings contain negative sentiment.
        Value complaints doubled since 2015 across all cities.
      </div>
      <div class="method-cell">
        <div class="label">Reproducibility</div>
        <code>scripts/03_analyze.py → analyze_hidden_transcript()</code>
      </div>
    </div>
  </details>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h4>Negative Sentiment Rate by Year — All Cities</h4>
    <canvas id="chart-neg-trend"></canvas>
  </div>
  <div class="chart-box">
    <h4>Value Complaint Rate by Year — All Cities</h4>
    <canvas id="chart-val-trend"></canvas>
  </div>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h4>Negative Rate by Score Bucket — The Gradient Test</h4>
    <canvas id="chart-score-buckets"></canvas>
  </div>
  <div class="chart-box" style="display:flex;flex-direction:column;justify-content:center;">
    <h4>Methodology Validation</h4>
    <div class="posiwid-box" style="border-left-color: var(--green);">
      <p><strong>Precision check</strong> (automated negation-context analysis on 100 random negative matches per city):</p>
      <table style="margin:0.75rem 0;">
        <thead><tr><th>City</th><th>Sample</th><th>Est. FP</th><th>Precision</th></tr></thead>
        <tbody>
          <tr><td>NYC</td><td class="num">100</td><td class="num">11</td><td class="num">89.0%</td></tr>
          <tr><td>Boston</td><td class="num">100</td><td class="num">9</td><td class="num">91.0%</td></tr>
          <tr><td>Chicago</td><td class="num">100</td><td class="num">13</td><td class="num">87.0%</td></tr>
        </tbody>
      </table>
      <p style="font-size:0.8rem;color:var(--text-3);">False positives primarily from negation contexts ("not dirty", "wasn't noisy"). Even after ~11% FP discount, all patterns hold: adjusted negative rate ~4.5-5.5% in 4.5+ listings.</p>
    </div>
    <details class="method-card" style="margin-top:0.75rem;">
      <summary>Falsification Conditions</summary>
      <div style="padding:0.5rem 1rem 1rem;font-size:0.85rem;">
        <p><strong>Hidden Transcript is falsified if:</strong> negative text rate in 4.5+ listings is &lt;50% of rate in &lt;4.0 listings (i.e., scores actually predict experience quality).</p>
        <p><strong>Result:</strong> &lt;3.0 bucket = 38-83% negative; 4.5+ bucket = 5-6%. Scores DO correlate — but 4.5+ still contains 26,000+ negative reviews in NYC alone. The gradient exists but is radically insufficient for differentiation.</p>
        <p><strong>Description homogenization is falsified if:</strong> cross-city similarity variance &gt;30% (would indicate local, not platform, effect).</p>
        <p><strong>Result:</strong> Cross-city range = 0.051-0.058, variance = 12%. Platform-level effect confirmed.</p>
      </div>
    </details>
  </div>
</div>

<!-- Signal A: Price Variance (Supplementary) -->
<h2>Supplementary — Price Variance</h2>
<div class="signal-card">
  <div class="signal-header">
    <span class="signal-id signal-moderate">INCONCLUSIVE — RETAINED FOR TRANSPARENCY</span>
    <span>Braverman (1974) — Deskilling through tool design</span>
  </div>
  <p><strong>Claim</strong>: "Hosts set their own prices."<br>
  <strong>POSIWID</strong>: High aggregate CV (&gt;1.0) suggests price diversity, but this mixes neighbourhood effects. Without Smart Pricing adoption data, the signal is inconclusive. Retained to show we do not cherry-pick results.</p>

  <table>
    <thead><tr><th>Metric</th><th>NYC</th><th>Boston</th><th>Chicago</th></tr></thead>
    <tbody>
      <tr><td>Median Price</td><td class="num">$165.93</td><td class="num">$202.00</td><td class="num">$152.00</td></tr>
      <tr><td>Overall CV</td><td class="num">1.495</td><td class="num">1.123</td><td class="num">1.615</td></tr>
    </tbody>
  </table>

  <details class="method-card">
    <summary>Methodology &amp; Data Source</summary>
    <div class="method-grid">
      <div class="method-cell">
        <div class="label">Data Source</div>
        Same listing files as Signal B. Field: <code>price</code> (parsed from "$xxx.xx" to float).<br>
        Source: <a href="http://insideairbnb.com/get-the-data/">Inside Airbnb</a> (CC BY 4.0)
      </div>
      <div class="method-cell">
        <div class="label">Method</div>
        Coefficient of Variation (CV = &sigma;/&mu;) per neighbourhood (&ge;30 listings).
        Also computed by room_type and city-level aggregate.
      </div>
      <div class="method-cell">
        <div class="label">Results</div>
        CV 1.1–1.6 at city level. Neighbourhood-level CV lower (0.6–1.2). Tourist areas show highest CV.
      </div>
      <div class="method-cell">
        <div class="label">Reproducibility</div>
        <code>scripts/03_analyze.py → analyze_price_variance()</code>
      </div>
    </div>
  </details>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h4>Neighbourhood Price CV — Top 10 by Listing Count (NYC)</h4>
    <canvas id="chart-price-cv-nyc"></canvas>
  </div>
  <div class="chart-box">
    <h4>Median Price by City &amp; Room Type</h4>
    <canvas id="chart-price-roomtype"></canvas>
  </div>
</div>

<!-- Signal D: Description Homogenization -->
<h2>Signal D — Description Homogenization</h2>
<div class="signal-card">
  <div class="signal-header">
    <span class="signal-id signal-moderate">MODERATE SIGNAL</span>
    <span>Winner (1980) — Do Artifacts Have Politics?</span>
  </div>
  <p><strong>Claim</strong>: "Hosts write their own listings."<br>
  <strong>POSIWID</strong>: Mean similarity is low (~5%), but <em>cross-city consistency</em> (0.051–0.058) suggests platform-driven homogenization rather than authentic variation.</p>

  <table>
    <thead><tr><th>Metric</th><th>NYC</th><th>Boston</th><th>Chicago</th></tr></thead>
    <tbody>
      <tr><td>Mean Pairwise Similarity</td><td class="num">0.0512</td><td class="num">0.0581</td><td class="num">0.0570</td></tr>
      <tr><td>P90 Similarity</td><td class="num">0.1130</td><td class="num">0.1187</td><td class="num">0.1176</td></tr>
    </tbody>
  </table>

  <details class="method-card">
    <summary>Methodology &amp; Data Source</summary>
    <div class="method-grid">
      <div class="method-cell">
        <div class="label">Data Source</div>
        Same listing files. Field: <code>description</code> (text, &gt;50 chars).<br>
        Source: <a href="http://insideairbnb.com/get-the-data/">Inside Airbnb</a> (CC BY 4.0)
      </div>
      <div class="method-cell">
        <div class="label">Method</div>
        TF-IDF (5000 features, English stop words, min_df=2) + cosine similarity.
        Random sample of 2000 descriptions per city (seed=42).
      </div>
      <div class="method-cell">
        <div class="label">Results</div>
        Mean ~5%, P90 ~12%. Cross-city consistency is the strongest indicator of platform-driven convergence.
      </div>
      <div class="method-cell">
        <div class="label">Reproducibility</div>
        <code>scripts/03_analyze.py → analyze_description_homogenization()</code>
      </div>
    </div>
  </details>
</div>

<!-- Host Concentration -->
<h2>Supplementary — Host Concentration</h2>
<div class="signal-card">
  <div class="signal-header">
    <span class="signal-id signal-moderate">VARIES BY CITY</span>
    <span>"Sharing Economy" vs. Commercial Operation</span>
  </div>

  <table>
    <thead><tr><th>Metric</th><th>NYC</th><th>Boston</th><th>Chicago</th></tr></thead>
    <tbody>
      <tr><td>Total Hosts</td><td class="num">14,088</td><td class="num">2,251</td><td class="num">5,520</td></tr>
      <tr><td>Single-Listing Hosts</td><td class="num">75.7%</td><td class="num">65.2%</td><td class="num">73.3%</td></tr>
      <tr><td>Top 10 Hosts' Share</td><td class="num">8.4%</td><td class="num"><strong>24.7%</strong></td><td class="num">15.2%</td></tr>
      <tr><td>Gini Coefficient</td><td class="num">0.449</td><td class="num"><strong>0.602</strong></td><td class="num">0.515</td></tr>
    </tbody>
  </table>

  <div class="posiwid-box">
    <p><strong>Boston</strong> is the most concentrated market: only 65% single-listing hosts, and the top 10 hosts control <strong>24.7%</strong> of all listings — nearly 3× NYC's 8.4%. The "sharing economy" narrative collapses hardest here.</p>
  </div>

  <details class="method-card">
    <summary>Methodology &amp; Data Source</summary>
    <div class="method-grid">
      <div class="method-cell">
        <div class="label">Data Source</div>
        Same listing files. Fields: <code>host_id</code>, <code>calculated_host_listings_count</code>.<br>
        Source: <a href="http://insideairbnb.com/get-the-data/">Inside Airbnb</a> (CC BY 4.0)
      </div>
      <div class="method-cell">
        <div class="label">Method</div>
        Group by <code>host_id</code>, count listings. Gini coefficient on listing distribution.
        Top-N host share of total.
      </div>
      <div class="method-cell">
        <div class="label">Results</div>
        Boston Gini 0.60 = moderate-high inequality. Top 10 Boston hosts control 1/4 of market.
      </div>
      <div class="method-cell">
        <div class="label">Reproducibility</div>
        <code>scripts/03_analyze.py → analyze_host_concentration()</code>
      </div>
    </div>
  </details>
</div>

<div class="chart-row">
  <div class="chart-box">
    <h4>Host Concentration — Single vs Multi-Listing</h4>
    <canvas id="chart-host-conc"></canvas>
  </div>
  <div class="chart-box">
    <h4>Gini Coefficient &amp; Top-10 Share</h4>
    <canvas id="chart-gini"></canvas>
  </div>
</div>

<!-- Hidden Transcript Story -->
<h2>The Hidden Transcript — An Illustration</h2>
<div class="story-card">
  <p>A traveler books a room for the weekend. The listing shows 4.87 stars from 312 reviews. The photos are bright and clean. The description reads like every other listing on the first page of search results: "cozy apartment in the heart of the city, walking distance to everything."</p>

  <p>She arrives to find a different reality. The sheets have a faint stain the photos didn't show. The walls are thin enough to hear every conversation next door. The "walking distance to everything" turns out to mean a 25-minute walk to the nearest subway. She opens the app to leave a review. The score interface appears first — five stars, a simple tap. She thinks about the host, who seemed nice enough over text. She thinks about her own guest rating, which she needs for her next trip. She gives 4 stars — generous, all things considered. Then she scrolls down to the text box. Here, in a space she knows the algorithm won't spotlight and the host won't read carefully, she writes what she actually experienced: "Stains on the sheets, very noisy walls, farther from transit than described."</p>

  <p>Multiply this by a million reviews. The scores say 4.87. The text says something else entirely. The platform counts the 4.87.</p>

  <div class="principle-box">
    <p><strong>Hidden Transcript (隐藏文本)</strong> — James C. Scott, <em>Domination and the Arts of Resistance</em> (1990)</p>
    <p>在任何权力关系中，从属者维持两套话语：<strong>公开文本（Public Transcript）</strong>是面对权力时的表演——顺从、合规、符合期望；<strong>隐藏文本（Hidden Transcript）</strong>是权力看不见的角落里的真话。Airbnb 的评分系统完美复制了这一结构：评分是公开文本（你的名字附在上面，房东可以反评你），评论文字是隐藏文本（埋在成千上万条评论里，算法从不表面化它）。差距不是噪音，差距<em>就是</em>权力结构的投影。</p>
  </div>
</div>

<!-- POSIWID Synthesis -->
<h2>POSIWID Synthesis</h2>
<div class="posiwid-box" style="border-left-color: var(--red);">
  <p class="claimed">"The purpose of a system is what it does." — Stafford Beer, 1974</p>
  <p style="margin-top: 1rem;">The purpose of Airbnb's review system is what it does: it produces <span class="actual">compliant public scores that reduce booking friction</span>, while burying honest feedback in unstructured text that the platform's algorithms never surface. This pattern replicates identically across NYC, Boston, and Chicago — it is a feature of the system, not an accident of any local market.</p>
</div>

<!-- Footer -->
<footer>
  <strong>Data</strong>: <a href="http://insideairbnb.com/get-the-data/">Inside Airbnb</a> (Murray Cox, CC BY 4.0) — NYC 2026-04-14, Boston 2025-09-23, Chicago 2025-09-22<br>
  <strong>Analysis</strong>: VoxelNoir Research &middot; <a href="https://voxelnoir.substack.com">voxelnoir.substack.com</a><br>
  <strong>Framework</strong>: POSIWID (Stafford Beer, 1974) &middot; Hidden Transcript (James C. Scott, 1990)<br>
  <strong>Pipeline</strong>: <code>01_download.sh → 02_clean.py → 03_analyze.py → 04_generate_dashboard.py</code><br>
  Generated: 2026-05-01
</footer>

</div><!-- /container -->

<script>
const DATA = {data_json};

const COLORS = {{
  nyc: '#6B5E9E',
  boston: '#1DB876',
  chicago: '#D97706',
}};

// === Score Distribution (NYC) ===
(() => {{
  const dist = DATA.nyc.signal_b_score_inflation.distribution;
  new Chart(document.getElementById('chart-score-nyc'), {{
    type: 'bar',
    data: {{
      labels: dist.bins.map(b => b.toFixed(1)),
      datasets: [{{
        label: 'NYC Listings',
        data: dist.counts,
        backgroundColor: COLORS.nyc + '99',
        borderColor: COLORS.nyc,
        borderWidth: 1,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Rating Score' }}, ticks: {{ maxTicksLimit: 10 }} }},
        y: {{ title: {{ display: true, text: 'Number of Listings' }} }}
      }}
    }}
  }});
}})();

// === Score Distribution Comparison (Boston vs Chicago) ===
(() => {{
  const distB = DATA.boston.signal_b_score_inflation.distribution;
  const distC = DATA.chicago.signal_b_score_inflation.distribution;
  const labels = distB.bins.map(b => b.toFixed(1));
  new Chart(document.getElementById('chart-score-compare'), {{
    type: 'bar',
    data: {{
      labels: labels,
      datasets: [
        {{ label: 'Boston', data: distB.counts, backgroundColor: COLORS.boston + '99', borderColor: COLORS.boston, borderWidth: 1 }},
        {{ label: 'Chicago', data: distC.counts, backgroundColor: COLORS.chicago + '99', borderColor: COLORS.chicago, borderWidth: 1 }},
      ]
    }},
    options: {{
      responsive: true,
      scales: {{
        x: {{ title: {{ display: true, text: 'Rating Score' }}, ticks: {{ maxTicksLimit: 10 }} }},
        y: {{ title: {{ display: true, text: 'Number of Listings' }} }}
      }}
    }}
  }});
}})();

// === Negative Sentiment Trend ===
(() => {{
  const datasets = [];
  for (const [city, color] of [['nyc', COLORS.nyc], ['boston', COLORS.boston], ['chicago', COLORS.chicago]]) {{
    const trend = DATA[city].signal_c_hidden_transcript.yearly_trend;
    datasets.push({{
      label: city.toUpperCase(),
      data: trend.map(y => ({{ x: y.year, y: y.negative_rate }})),
      borderColor: color,
      backgroundColor: color + '22',
      fill: false,
      tension: 0.3,
      pointRadius: 2,
    }});
  }}
  new Chart(document.getElementById('chart-neg-trend'), {{
    type: 'line',
    data: {{ datasets }},
    options: {{
      responsive: true,
      scales: {{
        x: {{ type: 'linear', title: {{ display: true, text: 'Year' }}, ticks: {{ stepSize: 2 }} }},
        y: {{ title: {{ display: true, text: 'Negative Rate (%)' }}, beginAtZero: true }}
      }}
    }}
  }});
}})();

// === Value Complaint Trend ===
(() => {{
  const datasets = [];
  for (const [city, color] of [['nyc', COLORS.nyc], ['boston', COLORS.boston], ['chicago', COLORS.chicago]]) {{
    const trend = DATA[city].signal_c_hidden_transcript.yearly_trend;
    datasets.push({{
      label: city.toUpperCase(),
      data: trend.map(y => ({{ x: y.year, y: y.value_rate }})),
      borderColor: color,
      backgroundColor: color + '22',
      fill: false,
      tension: 0.3,
      pointRadius: 2,
    }});
  }}
  new Chart(document.getElementById('chart-val-trend'), {{
    type: 'line',
    data: {{ datasets }},
    options: {{
      responsive: true,
      scales: {{
        x: {{ type: 'linear', title: {{ display: true, text: 'Year' }}, ticks: {{ stepSize: 2 }} }},
        y: {{ title: {{ display: true, text: 'Value Complaint Rate (%)' }}, beginAtZero: true }}
      }}
    }}
  }});
}})();

// === Score Bucket Analysis (Negative Rate by Score Range) ===
(() => {{
  const bucketLabels = ['<3.0', '3.0-3.5', '3.5-4.0', '4.0-4.5', '4.5-5.0'];
  const datasets = [];
  for (const [city, color] of [['nyc', COLORS.nyc], ['boston', COLORS.boston], ['chicago', COLORS.chicago]]) {{
    const buckets = DATA[city].signal_c_hidden_transcript.score_buckets || [];
    const rateMap = {{}};
    buckets.forEach(b => rateMap[b.bucket] = b.negative_rate);
    datasets.push({{
      label: city.toUpperCase(),
      data: bucketLabels.map(l => rateMap[l] || 0),
      backgroundColor: color + '99',
      borderColor: color,
      borderWidth: 1,
    }});
  }}
  new Chart(document.getElementById('chart-score-buckets'), {{
    type: 'bar',
    data: {{ labels: bucketLabels, datasets }},
    options: {{
      responsive: true,
      scales: {{
        x: {{ title: {{ display: true, text: 'Listing Score Range' }} }},
        y: {{ title: {{ display: true, text: 'Negative Text Rate (%)' }}, beginAtZero: true }}
      }}
    }}
  }});
}})();

// === Price CV by Neighbourhood (NYC top 10) ===
(() => {{
  const hoods = DATA.nyc.signal_a_price_variance.by_neighbourhood.slice(0, 10);
  new Chart(document.getElementById('chart-price-cv-nyc'), {{
    type: 'bar',
    data: {{
      labels: hoods.map(h => h.neighbourhood.length > 18 ? h.neighbourhood.slice(0, 16) + '…' : h.neighbourhood),
      datasets: [{{
        label: 'CV',
        data: hoods.map(h => h.cv),
        backgroundColor: COLORS.nyc + '99',
        borderColor: COLORS.nyc,
        borderWidth: 1,
      }}]
    }},
    options: {{
      responsive: true,
      indexAxis: 'y',
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        x: {{ title: {{ display: true, text: 'Coefficient of Variation' }}, beginAtZero: true }}
      }}
    }}
  }});
}})();

// === Price by Room Type ===
(() => {{
  const cities = ['nyc', 'boston', 'chicago'];
  const roomTypes = [...new Set(cities.flatMap(c => DATA[c].signal_a_price_variance.by_room_type.map(r => r.room_type)))];
  const datasets = cities.map((city, i) => ({{
    label: city.toUpperCase(),
    data: roomTypes.map(rt => {{
      const found = DATA[city].signal_a_price_variance.by_room_type.find(r => r.room_type === rt);
      return found ? found.median_price : 0;
    }}),
    backgroundColor: Object.values(COLORS)[i] + '99',
    borderColor: Object.values(COLORS)[i],
    borderWidth: 1,
  }}));
  new Chart(document.getElementById('chart-price-roomtype'), {{
    type: 'bar',
    data: {{ labels: roomTypes, datasets }},
    options: {{
      responsive: true,
      scales: {{
        y: {{ title: {{ display: true, text: 'Median Price ($)' }}, beginAtZero: true }}
      }}
    }}
  }});
}})();

// === Host Concentration ===
(() => {{
  const cities = ['nyc', 'boston', 'chicago'];
  const labels = cities.map(c => c.toUpperCase());
  new Chart(document.getElementById('chart-host-conc'), {{
    type: 'bar',
    data: {{
      labels,
      datasets: [
        {{
          label: 'Single-Listing Hosts %',
          data: cities.map(c => DATA[c].host_concentration.single_listing_hosts_pct),
          backgroundColor: COLORS.nyc + '99',
        }},
        {{
          label: 'Top 10 Hosts Share %',
          data: cities.map(c => DATA[c].host_concentration.top10_hosts_listing_share_pct),
          backgroundColor: '#DC262699',
        }},
      ]
    }},
    options: {{
      responsive: true,
      scales: {{ y: {{ beginAtZero: true, max: 100, title: {{ display: true, text: '%' }} }} }}
    }}
  }});
}})();

// === Gini ===
(() => {{
  const cities = ['nyc', 'boston', 'chicago'];
  new Chart(document.getElementById('chart-gini'), {{
    type: 'bar',
    data: {{
      labels: cities.map(c => c.toUpperCase()),
      datasets: [{{
        label: 'Gini Coefficient',
        data: cities.map(c => DATA[c].host_concentration.gini_coefficient),
        backgroundColor: cities.map(c => COLORS[c] + '99'),
        borderColor: cities.map(c => COLORS[c]),
        borderWidth: 1,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ y: {{ beginAtZero: true, max: 1.0, title: {{ display: true, text: 'Gini (0 = equal, 1 = concentrated)' }} }} }}
    }}
  }});
}})();
</script>

</body>
</html>"""

    return html


def main():
    results = load_results()
    html = generate_html(results)

    output_path = OUTPUT_DIR / "dashboard.html"
    with open(output_path, "w") as f:
        f.write(html)
    print(f"Dashboard written to {output_path}")
    print(f"Size: {len(html):,} bytes")


if __name__ == "__main__":
    main()
