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

### V2 Stratified Analysis (Supplementary Signal — No Stratification Planned)

Signal A remains supplementary. Without Smart Pricing adoption data, stratification cannot distinguish host choice from algorithmic convergence. If future data becomes available, stratify by `host_listing_count` to test whether professional operators show tighter price convergence than individual hosts.

---

## Signal B — Review Score Inflation (Winner + Scott: Captured Compliance)

### Claim
"Reviews help guests make informed decisions" — the rating system exists to surface quality differences.

### POSIWID Question
If ratings differentiate quality, scores should distribute across the 1-5 range. If 86-91% of listings score above 4.5, the system's actual output is undifferentiation — a participation trophy, not a quality signal.

### Theory

**Primary: Langdon Winner, "Do Artifacts Have Politics?" (1980) — vanishing latitude of choice.** Once a host enters the Airbnb ecosystem, the rating system's incentive structure (retaliatory reviews, algorithmic ranking tied to score) eliminates the "latitude of choice" that existed at the moment of joining. Individual hosts — dependent on a single income stream from the platform — comply most fully. The rating artifact does not merely display quality; it enforces a behavioral regime.

**Secondary: James C. Scott, *Domination and the Arts of Resistance* (1990) — learned compliance.** Hosts are not passively "manipulated" by information asymmetry; they actively learn that low scores → ranking demotion → income loss. Inflation is not the platform hiding information (the V1 Brynjolfsson reading); it is hosts rationally performing compliance within a power structure they cannot exit without economic cost.

**V1 theory (Brynjolfsson) revised**: Brynjolfsson's information asymmetry framework explains the *platform-level* design choice (prominently display scores, bury text). But V2 stratified data showed individual hosts inflate MORE than professional operators (93-98% vs 74-87% above 4.5) — the opposite of what "platform manipulates information" would predict. The stronger explanation is Winner's structural capture: the artifact's incentive design, not information control, drives inflation. Brynjolfsson is retained at the POSIWID summary level but demoted from the signal-level explanation.

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

### V2 Stratified Analysis

Run score distribution (mean, % >4.5, % =5.0, value sub-score mean) separately for each stratification layer:

| Stratification | Groups | Test Question |
|---------------|--------|---------------|
| `room_type` | entire / private / shared | Do commercial listings (entire home) inflate more than shared-living listings? |
| `host_listing_count` | 1 / 2-4 / 5-9 / 10+ | Do professional operators maintain higher scores? |
| Neighbourhood density | high / medium / low tercile | Does competition intensity drive inflation? |
| `property_type` | apartment / house / condo / room / other | Does property category affect score distribution? |

**Key test**: If inflation is uniform across all host types → platform-level effect (strengthens POSIWID). If inflation concentrates in entire-home + multi-listing hosts → host-type effect (weakens platform-level claim, shifts to "certain hosts game the system").

---

## Signal C — Text vs Score Gap / Hidden Transcript (Scott + Brynjolfsson)

### Claim
"Our review system is transparent and honest" — scores and text together give the full picture.

### POSIWID Question
If scores and text align, we should see negative text concentrated in low-score listings. If negative text appears frequently in reviews for 4.5+ rated listings, the system produces a split: a **Public Transcript** (scores — visible, identity-bound, retaliatory) and a **Hidden Transcript** (text — buried in volume, semi-anonymous, honest).

### Theory

**Primary: James C. Scott, *Domination and the Arts of Resistance* (1990) — Hidden Transcripts.** In any power relationship, subordinates maintain two registers — what they say in front of power (compliant) and what they say among themselves (resistant). The review system creates exactly this structure: scores are the Public Transcript (your name is attached, hosts can retaliate with bad guest reviews), text is the Hidden Transcript (buried among thousands of reviews, rarely surfaced by the algorithm). Scott explains the existence of the gap across ALL host types — it is a platform-level structural effect.

**V2 addition: Erik Brynjolfsson, "The Turing Trap" (2022) — scale as bargaining buffer.** V2 stratified data revealed the Hidden Transcript gap is 2-3x wider for large multi-listing operators (7-11% negative rate) vs individual hosts (4-5%). Scott's framework treats subordinates as homogeneous; this gradient requires an additional explanation. Brynjolfsson's bargaining power logic, repurposed: professional operators with 10+ listings have portfolio diversification — they can absorb occasional negative scores without existential threat. Individual hosts cannot. This asymmetric bargaining position means commercial operators invest in score maintenance (the Public Transcript) while under-investing in quality (amplifying the Hidden Transcript). Scale is not just an economic advantage; it is a bargaining buffer against the platform's own incentive structure.

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

### V2 Stratified Analysis

Run negative text rate and value complaint rate for 4.5+ listings, segmented by each stratification layer:

| Stratification | Test Question |
|---------------|---------------|
| `room_type` | Do entire-home 4.5+ listings have higher negative text rate than private rooms? (Commercial hosts maintain scores but not experience?) |
| `host_listing_count` | Do professional operators' listings show higher Hidden Transcript gap? (Score maintenance + lower quality?) |
| Neighbourhood density | Is the score-text gap wider in high-competition areas? |

**Critical test**: If entire-home + multi-listing hosts show BOTH higher scores AND higher negative text rate → evidence of score manipulation by commercial operators. This would be the strongest V2 finding: the Hidden Transcript is not just a platform artifact — it's amplified by professionalized hosting.

---

## Signal D — Description Homogenization (Winner + Meta Pattern 3: Enabling Structure + New Dependency)

### Claim
"Hosts write their own listings" — descriptions are authentic expressions of what makes each space unique.

### POSIWID Question
If descriptions are genuinely authored, similarity between descriptions should be low (each host describes their own space in their own words). If similarity is elevated, the system's actual output is template convergence — the platform's UI, guidelines, and optimization tips function as a mold.

### Theory

**Primary: Langdon Winner, "Do Artifacts Have Politics?" (1980) — enabling structure, not imposing force.** The platform's listing editor (suggested sections, character limits, SEO tips, auto-generated templates) is an artifact with embedded politics — but V2 data revealed its effect is baseline-setting (~5% cross-host similarity), not primary. Winner's framework applies as the **enabling structure**: the artifact creates conditions under which homogenization becomes rational, not conditions that mechanically impose it. The platform does not force template language; it rewards template-compatible language through search ranking and "Superhost" guidelines.

**V2 revision — the dominant mechanism is host replication, not platform templates.** Same-host descriptions are 7-9x more similar than cross-host descriptions (0.35-0.46 vs 0.05). Multi-listing operators copy-paste or template their own descriptions across properties. This is not Winner's "inherently political" artifact (which would produce high cross-host convergence regardless of host type); it is Winner's "political by arrangement" — the platform creates an environment where copy-paste is the rational strategy for operators managing 10+ listings.

**Secondary: Meta Pattern 3 — "New dependency forms before old one dissolves" (from automation wave analysis).** Once a host has invested in optimizing one listing's description for the platform's algorithm (learning the right keywords, structure, length), they face a sunk-cost incentive to replicate that template across all subsequent listings. The dependency is not on the platform's template but on the host's own accumulated optimization knowledge. This explains why the same-host effect (7-9x) dwarfs the cross-host platform effect (~5%): hosts become dependent on their own proven formula, not on the platform's suggested format.

**V1 theory revised**: V1 attributed homogenization primarily to the platform artifact ("the listing editor produces political outcomes — homogenized descriptions"). V2 same-host vs cross-host data shows this was overattributed. The platform contributes a modest baseline (~5%), but the primary homogenization engine is operator-level copy-paste amplified by portfolio scale. Winner remains valid as the structural explanation for WHY copy-paste is rational (the platform rewards it), but the mechanism is host behavior, not platform imposition.

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

### V2 Stratified Analysis

| Stratification | Test Question |
|---------------|---------------|
| `room_type` | Are entire-home descriptions more template-like than private rooms? |
| `host_listing_count` | Do professional operators' descriptions converge more than individual hosts? |
| **Same-host vs cross-host** | Is intra-host similarity (same operator's multiple listings) >> inter-host similarity? |

**Same-host vs cross-host method**:
1. Select multi-listing hosts (≥3 listings with valid descriptions)
2. Compute mean pairwise TF-IDF similarity within each host's listings (intra-host)
3. Compute mean pairwise similarity across random pairs from different hosts (inter-host)
4. Compare: if intra-host >> inter-host → homogenization partly driven by host copy-paste, not platform templates alone

This test directly challenges the Winner interpretation. If same-host similarity is not significantly higher than cross-host, the platform template force is confirmed. If it is much higher, the homogenization source shifts to host behavior.

---

## Supplementary: Host Concentration

### Question
Is Airbnb a peer-to-peer platform (individual hosts sharing their homes) or a disguised commercial market (multi-property operators)?

### Method
- Count listings per `host_id`
- Compute: % single-listing hosts, % multi-2+, multi-5+, multi-10+
- Top 10 hosts' share of total listings
- Gini coefficient of host listing distribution

### V2 Enhanced Analysis

| New Analysis | Method |
|-------------|--------|
| Professional host entire-home ratio | `calculated_host_listings_count_entire_homes` / `calculated_host_listings_count` per host |
| Price comparison by host scale | Median price by `host_listing_count` group (1 / 2-4 / 5-9 / 10+) |
| Geographic concentration of professional hosts | % of multi-listing hosts in high-density vs low-density neighbourhoods |

---

## Reproducibility

All analysis is deterministic. To reproduce:

```bash
# From project root
python3 scripts/02_clean.py    # produces data/{city}/*_clean.csv.gz
python3 scripts/03_analyze.py  # produces output/analysis_results.json
```

Random seed (42) is fixed for description sampling. All other operations are deterministic.
