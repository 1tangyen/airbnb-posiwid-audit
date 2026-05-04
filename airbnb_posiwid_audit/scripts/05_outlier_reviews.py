"""
05_outlier_reviews.py — Review sentiment outlier detection

Identifies listings with anomalously high negative text rates despite high scores (>=4.5).
Purpose: validate data cleaning quality + discover extreme Hidden Transcript cases.

Input:  data/{city}/listings_clean.csv.gz, data/{city}/reviews_clean.csv.gz
Output: output/outlier_reviews.json
"""

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CITIES = {
    "nyc": "New York City",
    "boston": "Boston",
    "chicago": "Chicago",
}

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

VALUE_PATTERNS = [
    r"\boverpriced\b", r"\bover\s*priced\b", r"\btoo\s+expensive\b",
    r"\bnot\s+worth\b", r"\brip\s*off\b", r"\brip-off\b",
    r"\bbetter\s+(?:off|deal|value)\s+(?:at|with)\s+(?:a\s+)?hotel",
    r"\bhidden\s+fee", r"\bcleaning\s+fee",
]

neg_regex = re.compile("|".join(NEGATIVE_PATTERNS), re.IGNORECASE)
val_regex = re.compile("|".join(VALUE_PATTERNS), re.IGNORECASE)

# Outlier detection parameters
MIN_REVIEWS = 10  # minimum reviews for a listing to be considered
SCORE_THRESHOLD = 4.5  # only look at "excellent" listings
OUTLIER_METHOD = "iqr"  # "iqr" or "zscore"
IQR_MULTIPLIER = 1.5  # Q3 + 1.5*IQR for mild outliers
EXTREME_IQR_MULTIPLIER = 3.0  # Q3 + 3*IQR for extreme outliers


def load_city(city: str):
    listings = pd.read_csv(DATA_DIR / city / "listings_clean.csv.gz", compression="gzip", low_memory=False)
    reviews = pd.read_csv(DATA_DIR / city / "reviews_clean.csv.gz", compression="gzip", low_memory=False)
    listings["id"] = pd.to_numeric(listings["id"], errors="coerce").astype("Int64")
    reviews["listing_id"] = pd.to_numeric(reviews["listing_id"], errors="coerce").astype("Int64")
    return listings, reviews


def detect_review_outliers(listings: pd.DataFrame, reviews: pd.DataFrame, city: str) -> dict:
    reviews = reviews.copy()
    reviews["is_negative"] = reviews["comments"].str.contains(neg_regex, na=False)
    reviews["is_value_complaint"] = reviews["comments"].str.contains(val_regex, na=False)

    # Per-listing negative rate
    listing_stats = reviews.groupby("listing_id").agg(
        total_reviews=("is_negative", "count"),
        negative_count=("is_negative", "sum"),
        value_count=("is_value_complaint", "sum"),
    ).reset_index()

    listing_stats["neg_rate"] = listing_stats["negative_count"] / listing_stats["total_reviews"]
    listing_stats["val_rate"] = listing_stats["value_count"] / listing_stats["total_reviews"]

    # Filter: minimum reviews + high score
    high_score_ids = set(listings[listings["review_scores_rating"] >= SCORE_THRESHOLD]["id"])
    eligible = listing_stats[
        (listing_stats["listing_id"].isin(high_score_ids)) &
        (listing_stats["total_reviews"] >= MIN_REVIEWS)
    ].copy()

    if len(eligible) == 0:
        return {"error": "no eligible listings", "city": city}

    # IQR-based outlier detection on negative rate
    q1 = eligible["neg_rate"].quantile(0.25)
    q3 = eligible["neg_rate"].quantile(0.75)
    iqr = q3 - q1
    mild_threshold = q3 + IQR_MULTIPLIER * iqr
    extreme_threshold = q3 + EXTREME_IQR_MULTIPLIER * iqr

    # Z-score for reference
    mean_neg = eligible["neg_rate"].mean()
    std_neg = eligible["neg_rate"].std()
    zscore_threshold_2 = mean_neg + 2 * std_neg
    zscore_threshold_3 = mean_neg + 3 * std_neg

    # Flag outliers
    eligible["is_mild_outlier"] = eligible["neg_rate"] > mild_threshold
    eligible["is_extreme_outlier"] = eligible["neg_rate"] > extreme_threshold
    eligible["zscore"] = (eligible["neg_rate"] - mean_neg) / std_neg

    mild_outliers = eligible[eligible["is_mild_outlier"]].copy()
    extreme_outliers = eligible[eligible["is_extreme_outlier"]].copy()

    # Enrich outliers with listing metadata
    listing_cols = ["id", "neighbourhood_cleansed", "room_type", "price",
                    "review_scores_rating", "calculated_host_listings_count",
                    "host_id", "property_type"]
    available_cols = [c for c in listing_cols if c in listings.columns]
    listing_meta = listings[available_cols].copy()
    listing_meta = listing_meta.rename(columns={"id": "listing_id"})

    mild_enriched = mild_outliers.merge(listing_meta, on="listing_id", how="left")
    extreme_enriched = extreme_outliers.merge(listing_meta, on="listing_id", how="left")

    # Distribution summary
    distribution = {
        "eligible_listings": int(len(eligible)),
        "mean_neg_rate": round(float(mean_neg), 4),
        "std_neg_rate": round(float(std_neg), 4),
        "q1": round(float(q1), 4),
        "median": round(float(eligible["neg_rate"].median()), 4),
        "q3": round(float(q3), 4),
        "iqr": round(float(iqr), 4),
        "mild_threshold": round(float(mild_threshold), 4),
        "extreme_threshold": round(float(extreme_threshold), 4),
        "zscore_2_threshold": round(float(zscore_threshold_2), 4),
        "zscore_3_threshold": round(float(zscore_threshold_3), 4),
    }

    # Outlier summary
    outlier_summary = {
        "mild_outlier_count": int(len(mild_outliers)),
        "mild_outlier_pct": round(len(mild_outliers) / len(eligible) * 100, 2),
        "extreme_outlier_count": int(len(extreme_outliers)),
        "extreme_outlier_pct": round(len(extreme_outliers) / len(eligible) * 100, 2),
    }

    # Top 20 extreme outliers (for inspection)
    top_outliers = extreme_enriched.nlargest(20, "neg_rate")
    top_outlier_list = []
    for _, row in top_outliers.iterrows():
        entry = {
            "listing_id": int(row["listing_id"]) if pd.notna(row["listing_id"]) else None,
            "neg_rate": round(float(row["neg_rate"]), 4),
            "neg_count": int(row["negative_count"]),
            "total_reviews": int(row["total_reviews"]),
            "zscore": round(float(row["zscore"]), 2),
            "score": round(float(row.get("review_scores_rating", 0)), 2) if pd.notna(row.get("review_scores_rating")) else None,
            "price": round(float(row.get("price", 0)), 2) if pd.notna(row.get("price")) else None,
            "neighbourhood": row.get("neighbourhood_cleansed", ""),
            "room_type": row.get("room_type", ""),
            "host_listings": int(row.get("calculated_host_listings_count", 0)) if pd.notna(row.get("calculated_host_listings_count")) else None,
        }
        top_outlier_list.append(entry)

    # By room_type breakdown of outlier counts
    by_room_type = {}
    if "room_type" in mild_enriched.columns:
        for rt, group in mild_enriched.groupby("room_type"):
            by_room_type[rt] = {
                "mild_outlier_count": int(len(group)),
                "mean_neg_rate": round(float(group["neg_rate"].mean()), 4),
            }

    # By host scale breakdown
    by_host_scale = {}
    if "calculated_host_listings_count" in mild_enriched.columns:
        bins = [0, 1, 4, 9, float("inf")]
        labels = ["single", "small_2-4", "medium_5-9", "large_10+"]
        mild_enriched["host_scale"] = pd.cut(
            mild_enriched["calculated_host_listings_count"], bins=bins, labels=labels, right=True
        )
        for scale, group in mild_enriched.groupby("host_scale", observed=True):
            by_host_scale[scale] = {
                "mild_outlier_count": int(len(group)),
                "mean_neg_rate": round(float(group["neg_rate"].mean()), 4),
            }

    # Data quality check: sample negative reviews from top outliers for manual inspection
    quality_samples = []
    top_3_ids = top_outliers["listing_id"].head(3).tolist()
    for lid in top_3_ids:
        listing_reviews = reviews[
            (reviews["listing_id"] == lid) & (reviews["is_negative"])
        ]["comments"].head(5).tolist()
        quality_samples.append({
            "listing_id": int(lid) if pd.notna(lid) else None,
            "sample_negative_reviews": [str(r)[:200] for r in listing_reviews],
        })

    return {
        "city": city,
        "distribution": distribution,
        "outlier_summary": outlier_summary,
        "top_outliers": top_outlier_list,
        "by_room_type": by_room_type,
        "by_host_scale": by_host_scale,
        "quality_samples": quality_samples,
    }


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    all_results = {}

    for city, city_name in CITIES.items():
        print(f"\n{'='*60}")
        print(f"  Review Outlier Detection — {city_name}")
        print(f"{'='*60}")

        listings, reviews = load_city(city)
        print(f"  Loaded {len(listings):,} listings, {len(reviews):,} reviews")

        results = detect_review_outliers(listings, reviews, city)

        if "error" not in results:
            print(f"  Eligible listings (≥{MIN_REVIEWS} reviews, score ≥{SCORE_THRESHOLD}): {results['distribution']['eligible_listings']:,}")
            print(f"  Mean negative rate: {results['distribution']['mean_neg_rate']:.2%}")
            print(f"  IQR mild threshold: {results['distribution']['mild_threshold']:.2%}")
            print(f"  IQR extreme threshold: {results['distribution']['extreme_threshold']:.2%}")
            print(f"  Mild outliers: {results['outlier_summary']['mild_outlier_count']} ({results['outlier_summary']['mild_outlier_pct']:.1f}%)")
            print(f"  Extreme outliers: {results['outlier_summary']['extreme_outlier_count']} ({results['outlier_summary']['extreme_outlier_pct']:.1f}%)")
            if results["top_outliers"]:
                top = results["top_outliers"][0]
                print(f"  Worst outlier: listing {top['listing_id']} — {top['neg_rate']:.0%} neg rate ({top['neg_count']}/{top['total_reviews']} reviews), score {top['score']}")
        else:
            print(f"  ERROR: {results['error']}")

        all_results[city] = results

    # Save results
    output_path = OUTPUT_DIR / "outlier_reviews.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n✓ Results saved to {output_path}")


if __name__ == "__main__":
    main()
