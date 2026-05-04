# 08 — Outlier Detection & Description Impact

## Purpose

Three independent analyses that serve dual purposes:
1. **Data quality validation** — verify that `02_clean.py` parsing is correct by examining extreme values
2. **Discovery** — find anomalous cases that reveal system dynamics invisible at the aggregate level

Inspired by the InnoVa Outlier Detection Scan (Semantic Pulse) concept: compute a "standard profile" centroid and measure deviation from it. Applied here to reviews, prices, and descriptions.

---

## Analysis 1: Review Sentiment Outliers

### Script
`scripts/05_outlier_reviews.py` → `output/outlier_reviews.json`

### Question
Among listings rated ≥4.5 (the "excellent" tier where 86-91% cluster), which individual listings have anomalously high negative text rates? Are these data quality problems or genuine Hidden Transcript extremes?

### Method

1. **Per-listing negative rate**: For each listing, compute `negative_review_count / total_reviews`
2. **Eligibility filter**: Only listings with score ≥4.5 AND ≥10 reviews (avoid small-sample noise)
3. **IQR-based outlier detection**:
   - Q1, Q3, IQR of per-listing negative rates across all eligible listings
   - Mild outlier: neg_rate > Q3 + 1.5×IQR
   - Extreme outlier: neg_rate > Q3 + 3×IQR
4. **Z-score reference**: Also compute z-score thresholds (2σ, 3σ) for comparison
5. **Enrichment**: Each outlier tagged with neighbourhood, room_type, price, host_listing_count
6. **Quality check**: Sample actual negative reviews from top outliers for manual inspection (are these real complaints or regex false positives?)

### Parameters
```python
MIN_REVIEWS = 10
SCORE_THRESHOLD = 4.5
IQR_MULTIPLIER = 1.5       # mild
EXTREME_IQR_MULTIPLIER = 3.0  # extreme
```

### Validation Logic
- If top outliers are concentrated in specific neighbourhoods → possible neighbourhood-level data issue
- If top outliers all have very short reviews → possible regex matching on fragments
- If top outliers show high host_listing_count → reinforces V2 finding (commercial operators deliver worse experiences)
- If outlier negative reviews are mostly false positives → indicates regex needs refinement

### Expected Outcome
- ~5-10% of eligible listings should be mild outliers (IQR-based)
- ~1-3% extreme outliers
- Quality samples should show genuine negative experiences (confirming Signal C is not a regex artifact)

---

## Analysis 2: Price Outliers by Neighbourhood

### Script
`scripts/06_outlier_price.py` → `output/outlier_price.json`

### Question
Within each neighbourhood, which listings have prices that deviate extremely from their local context? Are these genuine luxury/budget listings or parsing errors from `02_clean.py`?

### Method

1. **Per-neighbourhood IQR**: For each neighbourhood (≥10 listings), compute Q1, Q3, IQR of prices
2. **Outlier thresholds**:
   - Mild: price > Q3 + 1.5×IQR or < Q1 - 1.5×IQR
   - Extreme: price > Q3 + 3×IQR or < Q1 - 3×IQR
3. **Enrichment**: Each outlier tagged with ratio-to-median, room_type, property_type, accommodates, host_listing_count, description snippet
4. **Quality check**: Extreme high-price outliers with no/short description flagged as suspicious (possible parsing artifact)

### Parameters
```python
MIN_NEIGHBOURHOOD_SIZE = 10
IQR_MULTIPLIER = 1.5
EXTREME_IQR_MULTIPLIER = 3.0
GLOBAL_FLOOR = 10       # already filtered in cleaning
GLOBAL_CEILING = 10000  # already filtered in cleaning
```

### Validation Logic
- If extreme outliers have descriptions mentioning "penthouse", "entire floor", "mansion" → genuine luxury listings, cleaning is correct
- If extreme outliers have empty/minimal descriptions → suspicious, may be data entry errors that survived cleaning
- If low-price outliers show "Shared room" or unusual property_type → genuine budget listings
- If price outliers cluster in certain neighbourhoods → possible neighbourhood-level pricing anomaly

### Data Quality Signals
| Pattern | Interpretation |
|---------|---------------|
| High price + valid luxury description | ✓ Cleaning correct, genuine luxury |
| High price + no description | ⚠ Possible parsing error or placeholder |
| High price + "Shared room" | ⚠ Likely data error |
| Low price + "Entire home" in expensive neighbourhood | ⚠ Possible error or promotional rate |

---

## Analysis 3: Description Impact on Price & Reviews

### Script
`scripts/07_description_impact.py` → `output/description_impact.json`

### Question
Do description characteristics predict price premium or guest satisfaction? Does the "template-like" homogenization found in Signal D have economic consequences?

### Method

#### Feature Extraction
| Feature | Method | Hypothesis |
|---------|--------|-----------|
| `desc_length` | Character count | Longer = more effort = better experience? |
| `desc_word_count` | Word count | Same as above |
| `luxury_density` | Luxury keyword count per 100 words | Marketing language → price premium? |
| `modern_density` | Modern/renovated keyword count per 100 words | Renovation signal → price premium? |
| `cozy_density` | Cozy/charming keyword count per 100 words | Comfort signal → better reviews? |
| `location_density` | Location/proximity keyword count per 100 words | Location emphasis → higher value? |
| `marketing_density` | Sum of luxury + modern + cozy densities | Total marketing effort |
| `centroid_distance` | TF-IDF cosine distance from corpus centroid | Uniqueness/deviation from template |

#### Keyword Patterns
```python
LUXURY = luxury, luxurious, upscale, premium, high-end, elegant, sophisticated, exquisite
MODERN = modern, contemporary, renovated, updated, newly, stylish, designer
COZY   = cozy, cosy, charming, quaint, warm, homey, comfortable, welcoming
LOCATION = walk, minutes from/to, steps from/to, near, close to, convenient, downtown, central
```

#### Description → Price Analysis
1. Pearson correlations: each feature vs log(price) (log-transformed because price is right-skewed)
2. Quartile analysis: median price by description length quartile
3. Luxury keyword premium: median price with vs without luxury keywords
4. Centroid distance vs price: does uniqueness correlate with pricing power?

#### Description → Review Analysis
1. Pearson correlations: each feature vs review_scores_rating AND per-listing negative rate
2. Marketing density quartile analysis: negative rate by marketing language quartile
3. Centroid distance vs negative rate: do "unique" descriptions predict better/worse experiences?
4. Description length vs review score: does effort in writing correlate with quality?

### Parameters
```python
MIN_DESCRIPTION_LENGTH = 50  # characters
TFIDF_MAX_FEATURES = 5000
SAMPLE_SIZE = 2000  # for centroid computation
RANDOM_STATE = 42
MIN_REVIEWS_FOR_NEG_RATE = 10
```

### Key Test Questions

| Question | Positive Finding | Negative Finding |
|----------|-----------------|-----------------|
| Does luxury language predict higher price? | ✓ Expected — marketing language justifies premium | Unexpected — suggests pricing is not language-driven |
| Does marketing density predict MORE negative reviews? | ⭐ Strong POSIWID finding: inflated descriptions create expectation gap → complaints | Null result — descriptions don't affect experience |
| Does centroid distance (uniqueness) predict better reviews? | ✓ Authentic voice → better guest experience | Null or negative — template compliance rewarded |
| Does description length predict price? | Moderate — effort signals quality | Null — length is noise |

### POSIWID Connection

If marketing-heavy descriptions show **both** higher prices **and** higher negative rates, this is a POSIWID signal: the description system's purpose is to optimize for booking conversion (high price, attractive language) rather than to accurately represent the listing (which would reduce negative experiences). The system rewards description inflation the same way it rewards score inflation.

---

## Reproducibility

```bash
# From project root — run each independently
python3 scripts/05_outlier_reviews.py    # → output/outlier_reviews.json
python3 scripts/06_outlier_price.py      # → output/outlier_price.json
python3 scripts/07_description_impact.py # → output/description_impact.json
```

Requirements: Same as main analysis (Python 3.9+, pandas, numpy, scikit-learn).

---

## Relationship to Existing Signals

| Outlier Analysis | Validates | Extends |
|-----------------|-----------|---------|
| Review outliers | Signal C regex detection quality | Identifies extreme Hidden Transcript cases |
| Price outliers | `02_clean.py` price parsing | Reveals neighbourhood pricing dynamics |
| Description impact | Signal D homogenization finding | Tests economic consequences of template convergence |

---

## Connection to InnoVa Outlier Detection (Semantic Pulse)

This analysis applies the same conceptual pattern as the InnoVa Outlier Detection Scan proposal:

| InnoVa Concept | Airbnb Application |
|---------------|-------------------|
| Corpus centroid (standard profile) | TF-IDF centroid of all descriptions |
| Cosine deviation from centroid | `centroid_distance` feature |
| "Contextual noise" flagging | Extreme price/review outliers |
| Reducing review surface to anomalies | Top 20 outliers for manual inspection |

The key insight transfers: **measuring deviation from the corpus norm** reveals both data quality issues (things that shouldn't be there) and genuine anomalies (things that challenge the aggregate pattern).
