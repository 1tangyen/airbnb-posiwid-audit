# 00 — Data Sources

## Source: Inside Airbnb

- **Website**: [insideairbnb.com](http://insideairbnb.com/)
- **Get the Data**: [insideairbnb.com/get-the-data](http://insideairbnb.com/get-the-data/)
- **Maintainer**: Murray Cox
- **License**: CC BY 4.0
- **How data is collected**: Scraped from publicly visible Airbnb listing pages. Not from Airbnb's API or internal data.

## Cities & Snapshots

We use the **most recent snapshot with complete price data** for each city as of 2026-05-01.

> **Note**: The Dec 2025 snapshots for NYC and Boston dropped the `price` column (100% null). We use the most recent snapshot that includes price data for each city.

### New York City

| File | Snapshot Date | URL |
|------|--------------|-----|
| Detailed Listings | 2026-04-14 | [listings.csv.gz](https://data.insideairbnb.com/united-states/ny/new-york-city/2026-04-14/data/listings.csv.gz) |
| Reviews | 2026-04-14 | [reviews.csv.gz](https://data.insideairbnb.com/united-states/ny/new-york-city/2026-04-14/data/reviews.csv.gz) |

### Boston

| File | Snapshot Date | URL |
|------|--------------|-----|
| Detailed Listings | 2025-09-23 | [listings.csv.gz](https://data.insideairbnb.com/united-states/ma/boston/2025-09-23/data/listings.csv.gz) |
| Reviews | 2025-09-23 | [reviews.csv.gz](https://data.insideairbnb.com/united-states/ma/boston/2025-09-23/data/reviews.csv.gz) |

### Chicago

| File | Snapshot Date | URL |
|------|--------------|-----|
| Detailed Listings | 2025-09-22 | [listings.csv.gz](https://data.insideairbnb.com/united-states/il/chicago/2025-09-22/data/listings.csv.gz) |
| Reviews | 2025-09-22 | [reviews.csv.gz](https://data.insideairbnb.com/united-states/il/chicago/2025-09-22/data/reviews.csv.gz) |

## Why These Cities

- **New York City**: Largest Airbnb market in the US, heavy regulation (Local Law 18), most data history
- **Boston**: Mid-size market, university-heavy demand pattern, short-term rental regulations since 2019
- **Chicago**: Large market, different regulatory environment, Midwest pricing dynamics
- **Cross-city comparison**: If platform-level patterns (score inflation, price convergence, description homogenization) appear across markets with different regulations and demographics, it strengthens the POSIWID argument that these are **systemic** features, not local artifacts

## Data Files — What's Inside

### listings.csv.gz (Detailed Listings)

~75-90 columns per row. Key fields used in our analysis:

| Column | Type | Used In Signal |
|--------|------|---------------|
| `id` | int | All |
| `host_id` | int | Host concentration |
| `neighbourhood_cleansed` | str | Price variance (A) |
| `price` | str ("$1,234.00") | Price variance (A), Price synchrony (B) |
| `review_scores_rating` | float (1-5) | Score inflation (B) |
| `description` | str | Description homogenization (D) |
| `room_type` | str | Filtering |
| `last_review` | date | Filtering active listings |

### reviews.csv.gz (Reviews)

6 columns per row:

| Column | Type | Used In Signal |
|--------|------|---------------|
| `listing_id` | int | Join to listings |
| `id` | int | Unique review ID |
| `date` | date | Time series (C) |
| `reviewer_id` | int | Not used |
| `reviewer_name` | str | Not used |
| `comments` | str | Text analysis (C) |

## Data Size Estimates

| City | Listings (rows) | Reviews (rows) | Download Size |
|------|----------------|----------------|--------------|
| NYC | 35,036 | 1,003,299 | 144 MB |
| Boston | 4,419 | 233,094 | 26 MB |
| Chicago | 8,660 | 492,465 | 56 MB |
| **Total** | **48,115** | **1,728,858** | **~226 MB** |

*Cleaned counts in `02_data_cleaning.md`.*

## Snapshot Date Alignment

The snapshots span 2025-09 to 2026-04 (a ~7 month window). For cross-city comparison this is acceptable because:
1. We analyze **structural patterns** (score distributions, price CV), not point-in-time prices
2. Review text analysis covers the full historical corpus, not just the snapshot date
3. Platform mechanics (algorithmic pricing, review incentives) don't change quarter-to-quarter
