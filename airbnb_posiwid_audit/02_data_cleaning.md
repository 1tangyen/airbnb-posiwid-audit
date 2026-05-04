# 02 — Data Cleaning

## Script

`scripts/02_clean.py` — deterministic pipeline, no randomness, no manual steps.

**Input**: `data/{city}/listings.csv.gz`, `data/{city}/reviews.csv.gz`
**Output**: `data/{city}/listings_clean.csv.gz`, `data/{city}/reviews_clean.csv.gz`
**Report**: `data/cleaning_report.json` (machine-readable full audit trail)

---

## Cleaning Steps — Listings

| Step | What | Why | NYC Dropped | Boston Dropped | Chicago Dropped |
|------|------|-----|-------------|----------------|-----------------|
| 1. Select columns | Keep 30 analysis-relevant columns from 79-90 | Reduce noise, standardize across cities | 0 rows | 0 rows | 0 rows |
| 2. Parse price | Convert `"$1,234.00"` → `1234.0` float | Numeric analysis requires numeric values | — | — | — |
| 3. Drop no price | Remove listings with null price | Can't analyze price signals without price | 14,343 | 913 | 835 |
| 4. Drop price outliers | Remove price < $10 or > $10,000/night | Likely data entry errors or test listings | 13 | 41 | 5 |
| 5. Drop hotel rooms | Remove `room_type == "Hotel room"` | Different business model (institutional, not peer hosting) | 330 | 5 | 94 |
| 6. Flag active | Mark listings with review since 2025-01-01 | Both active and inactive kept; flag for optional filtering | — | — | — |

### Listings Summary

| City | Raw | After Cleaning | Removed | % Removed | Active | Inactive |
|------|-----|---------------|---------|-----------|--------|----------|
| NYC | 35,036 | 20,350 | 14,686 | 41.9% | 10,115 | 10,235 |
| Boston | 4,419 | 3,460 | 959 | 21.7% | 1,828 | 1,632 |
| Chicago | 8,660 | 7,726 | 934 | 10.8% | 4,419 | 3,307 |

**NYC has the highest removal rate (41.9%)** — primarily because 14,343 listings (40.9%) had no price data in this snapshot. This is consistent with NYC's heavy regulation (Local Law 18) making many listings inactive.

---

## Cleaning Steps — Reviews

| Step | What | Why | NYC Dropped | Boston Dropped | Chicago Dropped |
|------|------|-----|-------------|----------------|-----------------|
| 1. Filter to clean listings | Keep only reviews for listings that survived listing cleaning | Orphaned reviews add noise | 179,589 | 24,122 | 31,379 |
| 2. Drop empty comments | Remove null or whitespace-only comments | Can't do text analysis on empty strings | 199 | 46 | 140 |
| 3. Parse date | Convert to datetime, drop unparseable | Need dates for time-series analysis | 0 | 0 | 0 |
| 4. Filter English only | Keep reviews where >50% of letters are ASCII | Sentiment patterns are language-specific; non-English reviews would introduce noise | 11,116 | 2,448 | 2,758 |

### Reviews Summary

| City | Raw | After Cleaning | Removed | % Removed | Date Range |
|------|-----|---------------|---------|-----------|------------|
| NYC | 1,003,299 | 812,395 | 190,904 | 19.0% | 2009-05-25 to 2026-04-15 |
| Boston | 233,094 | 206,478 | 26,616 | 11.4% | 2009-03-21 to 2025-09-23 |
| Chicago | 492,465 | 458,188 | 34,277 | 7.0% | 2009-07-03 to 2025-09-23 |

---

## Columns Retained (30 per listing)

| Column | Type | Signal |
|--------|------|--------|
| `id` | int | All — primary key |
| `host_id` | int | Host concentration |
| `host_name` | str | Reference |
| `neighbourhood_cleansed` | str | Price variance (A) |
| `neighbourhood_group_cleansed` | str | Borough/area grouping |
| `latitude`, `longitude` | float | Geo reference |
| `property_type` | str | Filtering |
| `room_type` | str | Filtering (hotel rooms excluded) |
| `accommodates` | int | Reference |
| `price` | float | Price signals (A, B) |
| `minimum_nights`, `maximum_nights` | int | Reference |
| `number_of_reviews`, `number_of_reviews_ltm` | int | Activity level |
| `first_review`, `last_review` | date | Active flag |
| `review_scores_rating` | float | Score inflation (B, C) |
| `review_scores_accuracy` through `_value` | float | Sub-score analysis |
| `instant_bookable` | bool | Platform control indicator |
| `calculated_host_listings_count*` | int | Host concentration |
| `description` | str | Homogenization (D) |

---

## Decisions & Rationale

1. **Price outlier threshold ($10–$10,000)**: Very few listings affected (13+41+5 = 59 total). The $10 floor removes test/error listings. The $10,000 ceiling removes novelty listings (castles, yachts) that aren't comparable.

2. **Hotel rooms excluded**: Hotels operate under hospitality regulation, professional management, and institutional pricing. Including them would dilute platform-power signals that are specifically about the host-platform relationship.

3. **Active flag, not filter**: We keep inactive listings because description homogenization analysis benefits from larger N. Price and review analyses can filter to active-only as needed.

4. **English-only reviews**: Our sentiment regex patterns are English-language. Including non-English text would create false negatives (complaints we can't detect). NYC loses the most (11K, 1.4%) due to tourism diversity — this is documented, not hidden.

5. **NYC's 41.9% listing removal**: This is NOT data quality failure — it's a real signal. NYC's Local Law 18 (2023) banned most short-term rentals in unregistered buildings. Many listings remain on Airbnb's website but are effectively inactive (no price, no availability). The cleaning step surfaces this regulatory impact.

---

## V2 — Stratification Variables (Host Segmentation)

V1 treated all hosts as a homogeneous group. V2 introduces host stratification to control for the strongest alternative explanation: that score inflation and Hidden Transcript effects are driven by **host type**, not platform design.

### New Fields for Stratification

All fields below already exist in the retained 30-column listing dataset. No re-download needed.

| Field | Type | Stratification Role | Already in V1 Clean? |
|-------|------|---------------------|---------------------|
| `room_type` | str | Operating model proxy (entire home = commercial, private = shared living) | ✓ Used for filtering only |
| `property_type` | str | Property category (apartment, house, condo, etc.) | ✓ Not used in analysis |
| `calculated_host_listings_count` | int | Host scale — total listings | ✓ Used for concentration only |
| `calculated_host_listings_count_entire_homes` | int | Professional host proxy — entire home count | ✓ Not used in analysis |
| `calculated_host_listings_count_private_rooms` | int | Room rental scale | ✓ Not used in analysis |
| `calculated_host_listings_count_shared_rooms` | int | Shared room scale | ✓ Not used in analysis |
| `neighbourhood_cleansed` | str | Competition intensity (via listing density) | ✓ Used for price CV only |
| `host_id` | int | Same-host cross-listing comparison | ✓ Used for concentration only |

### Field to Verify

| Field | Status | Action |
|-------|--------|--------|
| `host_since` | May exist in detailed listings (79-90 cols) but not in V1's 30-column selection | Check raw CSVs; if present, add to retained columns |

### Category Consolidation Rules

#### `room_type` (3 groups)

| Group | Values | Notes |
|-------|--------|-------|
| Entire home | `Entire home/apt` | Commercial/investment proxy |
| Private room | `Private room` | Shared living proxy |
| Shared room | `Shared room` | If N < 100 per city, merge into Private room or flag as insufficient |

#### `property_type` (5-8 groups from potentially 30+ raw values)

| Group | Typical Values |
|-------|---------------|
| Apartment | Entire rental unit, Rental unit, Entire condo |
| House | Entire home, Entire townhouse, Entire bungalow |
| Condo | Entire condo, Condominium (if distinct from apartment) |
| Room in dwelling | Private room in rental unit, Private room in home |
| Other | Loft, Guest suite, Boat, Tiny home, etc. |

Exact mapping TBD after inspecting raw `property_type` value counts per city.

#### `calculated_host_listings_count` (4 groups)

| Group | Range | Label |
|-------|-------|-------|
| Single | 1 | Individual host |
| Small multi | 2–4 | Side business |
| Medium multi | 5–9 | Semi-professional |
| Large multi | 10+ | Professional operator |

#### Neighbourhood Competition Intensity (3 tiers)

Computed per city: count listings per `neighbourhood_cleansed`, then tercile split.

| Tier | Definition | Hypothesis |
|------|-----------|-----------|
| High density | Top tercile by listing count | More commercial, more inflation |
| Medium density | Middle tercile | — |
| Low density | Bottom tercile | More personal, more natural distribution |

### Data Quality Checks Before V2 Analysis

| Check | Why | Action if Failed |
|-------|-----|-----------------|
| Boston `<3.0` and `3.0-3.5` score buckets sample size | V1 gradient test: Boston 3.0-3.5 had only 6 reviews | Merge into single `<3.5` bucket or flag as insufficient |
| Shared room count per city | If < 100, stratified analysis is unreliable | Merge into private room group or exclude from stratified analysis |
| `calculated_host_listings_count_entire_homes` null rate | Must be populated for professional host proxy | If >20% null, fall back to `calculated_host_listings_count` only |
| `property_type` cardinality | May have 30+ unique values | Consolidate to 5-8 groups before analysis |
| `host_since` existence in raw data | Not confirmed in V1 column selection | If missing, drop from stratification plan |

---

## Next Step

→ `03_analysis_signals.md` — apply the four POSIWID signals to cleaned data across all three cities, now with host stratification layers.
