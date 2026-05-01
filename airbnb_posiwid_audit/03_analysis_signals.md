# 03 — Analysis Signals

## Script

`scripts/03_analyze.py` — reads cleaned data, outputs `output/analysis_results.json`.

---

## Signal A — Price Variance (Braverman Deskilling)

### Claim
"Hosts set their own prices" — Airbnb presents pricing as an expression of host autonomy.

### POSIWID Question
If hosts truly set prices independently, we should see high price diversity within neighborhoods (same location, different judgment). If prices converge, the system's actual output is standardization — regardless of the stated purpose.

### Theory
**Harry Braverman, *Labor and Monopoly Capital* (1974)**: Deskilling through tool design. When the platform provides "Smart Pricing" tools and algorithmic suggestions, it replaces host judgment with algorithmic output. The tool appears to assist; in practice it homogenizes.

### Method
- **Metric**: Coefficient of Variation (CV = σ/μ) per neighbourhood
- **Scope**: All cleaned listings with valid price, grouped by `neighbourhood_cleansed`
- **Filter**: Neighbourhoods with ≥30 listings (statistical minimum for meaningful CV)
- **Also computed**: CV by `room_type`, overall city-level CV

### Parameters
```python
min_neighbourhood_size = 30
top_neighbourhoods_reported = 15  # by listing count
price_column = "price"  # parsed from "$xxx.xx" to float
```

---

## Signal B — Review Score Inflation (Brynjolfsson Bargaining Power)

### Claim
"Reviews help guests make informed decisions" — the rating system exists to surface quality differences.

### POSIWID Question
If ratings differentiate quality, scores should distribute across the 1-5 range. If 86-91% of listings score above 4.5, the system's actual output is undifferentiation — a participation trophy, not a quality signal.

### Theory
**Erik Brynjolfsson, "The Turing Trap" (2022)**: Information asymmetry as bargaining leverage. When the platform controls what information surfaces (prominently displayed scores) and what stays buried (review text), it shapes the power dynamic between hosts and guests. Inflated scores serve the platform by reducing booking friction, not by informing guests.

### Method
- **Metric**: Distribution of `review_scores_rating` (1.0-5.0 scale)
- **Stats**: mean, median, % above 4.0, % above 4.5, % above 4.8, % at 5.0
- **Sub-scores**: accuracy, cleanliness, checkin, communication, location, value — compared to see which dimensions show most inflation
- **Distribution**: histogram with 0.1-wide bins from 1.0 to 5.0

### Parameters
```python
score_column = "review_scores_rating"
sub_score_columns = ["review_scores_accuracy", "review_scores_cleanliness",
                     "review_scores_checkin", "review_scores_communication",
                     "review_scores_location", "review_scores_value"]
histogram_bin_width = 0.1
```

---

## Signal C — Text vs Score Gap / Hidden Transcript (James C. Scott)

### Claim
"Our review system is transparent and honest" — scores and text together give the full picture.

### POSIWID Question
If scores and text align, we should see negative text concentrated in low-score listings. If negative text appears frequently in reviews for 4.5+ rated listings, the system produces a split: a **Public Transcript** (scores — visible, identity-bound, retaliatory) and a **Hidden Transcript** (text — buried in volume, semi-anonymous, honest).

### Theory
**James C. Scott, *Domination and the Arts of Resistance* (1990)**: Hidden Transcripts. In any power relationship, subordinates maintain two registers — what they say in front of power (compliant) and what they say among themselves (resistant). The review system creates exactly this structure: scores are the Public Transcript (your name is attached, hosts can retaliate with bad guest reviews), text is the Hidden Transcript (buried among thousands of reviews, rarely surfaced by the algorithm).

### Method
1. **Negative sentiment detection**: 25 regex patterns covering cleanliness, safety, honesty, disappointment, refusal to return
2. **Value complaint detection**: 8 regex patterns specifically about pricing/value
3. **Year-by-year trend**: negative rate and value complaint rate per year
4. **Hidden Transcript test**: among reviews for listings rated ≥4.5, what % contain negative text?

### Parameters
```python
# 25 negative patterns (see script for full list)
NEGATIVE_PATTERNS = [
    r"\bdirty\b", r"\bfilthy\b", r"\bstain", r"\bsmell", r"\bstink",
    r"\bbug\s*s?\b", r"\broach", r"\bcockroach", r"\bbed\s*bug",
    r"\bnois[ey]", r"\bloud\b", r"\bconstruction\b",
    r"\bunsafe\b", r"\bdangerous\b", r"\bscary\b",
    r"\brude\b", r"\bunresponsive\b", r"\bignor",
    r"\bmislead", r"\blie[sd]?\b", r"\bfraud", r"\bscam",
    r"\bnot\s+(?:as\s+)?(?:pictured|described|shown|advertised)",
    r"\bdisappoint", r"\bterrible\b", r"\bhorrible\b", r"\bawful\b",
    r"\bnever\s+(?:again|stay|come\s+back|return)",
    r"\bwouldn['']?t\s+recommend\b",
]

# 8 value-specific patterns
VALUE_PATTERNS = [
    r"\boverpriced\b", r"\bover\s*priced\b", r"\btoo\s+expensive\b",
    r"\bnot\s+worth\b", r"\brip\s*off\b", r"\brip-off\b",
    r"\bbetter\s+(?:off|deal|value)\s+(?:at|with)\s+(?:a\s+)?hotel",
    r"\bhidden\s+fee", r"\bcleaning\s+fee",
]

high_score_threshold = 4.5
```

---

## Signal D — Description Homogenization (Winner — Artifacts Have Politics)

### Claim
"Hosts write their own listings" — descriptions are authentic expressions of what makes each space unique.

### POSIWID Question
If descriptions are genuinely authored, similarity between descriptions should be low (each host describes their own space in their own words). If similarity is elevated, the system's actual output is template convergence — the platform's UI, guidelines, and optimization tips function as a mold.

### Theory
**Langdon Winner, "Do Artifacts Have Politics?" (1980)**: Technologies embed power arrangements that persist regardless of user intent. Airbnb's listing editor, with its suggested sections, character limits, and SEO tips, is an artifact that produces political outcomes — homogenized descriptions that favor the platform's search algorithm over the host's authentic voice.

### Method
1. **TF-IDF vectorization**: Convert descriptions to term-frequency vectors (5000 max features, English stop words removed)
2. **Cosine similarity**: Compute pairwise similarity on a random sample of 2000 descriptions
3. **Stats**: mean, median, P90, P95 of pairwise similarity scores

### Parameters
```python
tfidf_max_features = 5000
tfidf_stop_words = "english"
tfidf_min_df = 2
sample_size = 2000
random_state = 42  # reproducible sampling
min_description_length = 50  # characters
```

---

## Supplementary: Host Concentration

### Question
Is Airbnb a peer-to-peer platform (individual hosts sharing their homes) or a disguised commercial market (multi-property operators)?

### Method
- Count listings per `host_id`
- Compute: % single-listing hosts, % multi-2+, multi-5+, multi-10+
- Top 10 hosts' share of total listings
- Gini coefficient of host listing distribution

---

## Reproducibility

All analysis is deterministic. To reproduce:

```bash
# From project root
python3 scripts/02_clean.py    # produces data/{city}/*_clean.csv.gz
python3 scripts/03_analyze.py  # produces output/analysis_results.json
```

Random seed (42) is fixed for description sampling. All other operations are deterministic.
