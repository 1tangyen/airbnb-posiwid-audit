"""
07_description_impact.py — Description features → Price and Review impact analysis

Tests how listing description characteristics correlate with price and review outcomes.
Purpose: understand if description quality/style predicts pricing power or guest satisfaction.

Input:  data/{city}/listings_clean.csv.gz, data/{city}/reviews_clean.csv.gz
Output: output/description_impact.json
"""

import pandas as pd
import numpy as np
import json
import re
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

neg_regex = re.compile("|".join(NEGATIVE_PATTERNS), re.IGNORECASE)

# Description feature keywords (marketing language tiers)
LUXURY_KEYWORDS = re.compile(
    r"\bluxury\b|\bluxurious\b|\bupscale\b|\bpremium\b|\bhigh[- ]end\b|\belegant\b|\bsophisticated\b|\bexquisite\b",
    re.IGNORECASE,
)
MODERN_KEYWORDS = re.compile(
    r"\bmodern\b|\bcontemporary\b|\brenovated\b|\bupdated\b|\bnewly\b|\bstylish\b|\bdesigner\b",
    re.IGNORECASE,
)
COZY_KEYWORDS = re.compile(
    r"\bcozy\b|\bcosy\b|\bcharming\b|\bquaint\b|\bwarm\b|\bhomey\b|\bcomfortable\b|\bwelcoming\b",
    re.IGNORECASE,
)
LOCATION_KEYWORDS = re.compile(
    r"\bwalk\b|\bminutes?\s+(?:from|to|away)\b|\bsteps?\s+(?:from|to)\b|\bnear\b|\bclose\s+to\b|\bconvenient\b|\bdowntown\b|\bcentral\b",
    re.IGNORECASE,
)

MIN_DESCRIPTION_LENGTH = 50
TFIDF_MAX_FEATURES = 5000
SAMPLE_SIZE = 2000
RANDOM_STATE = 42


def load_city(city: str):
    listings = pd.read_csv(DATA_DIR / city / "listings_clean.csv.gz", compression="gzip", low_memory=False)
    reviews = pd.read_csv(DATA_DIR / city / "reviews_clean.csv.gz", compression="gzip", low_memory=False)
    listings["id"] = pd.to_numeric(listings["id"], errors="coerce").astype("Int64")
    reviews["listing_id"] = pd.to_numeric(reviews["listing_id"], errors="coerce").astype("Int64")
    return listings, reviews


def extract_description_features(listings: pd.DataFrame) -> pd.DataFrame:
    """Extract measurable features from listing descriptions."""
    df = listings[listings["description"].notna()].copy()
    df = df[df["description"].str.len() >= MIN_DESCRIPTION_LENGTH].copy()

    # Length features
    df["desc_length"] = df["description"].str.len()
    df["desc_word_count"] = df["description"].str.split().str.len()

    # Keyword density (count per 100 words)
    df["luxury_count"] = df["description"].str.count(LUXURY_KEYWORDS)
    df["modern_count"] = df["description"].str.count(MODERN_KEYWORDS)
    df["cozy_count"] = df["description"].str.count(COZY_KEYWORDS)
    df["location_count"] = df["description"].str.count(LOCATION_KEYWORDS)

    df["luxury_density"] = df["luxury_count"] / df["desc_word_count"] * 100
    df["modern_density"] = df["modern_count"] / df["desc_word_count"] * 100
    df["cozy_density"] = df["cozy_count"] / df["desc_word_count"] * 100
    df["location_density"] = df["location_count"] / df["desc_word_count"] * 100

    # Total marketing language density
    df["marketing_density"] = df["luxury_density"] + df["modern_density"] + df["cozy_density"]

    return df


def compute_centroid_distance(listings: pd.DataFrame) -> pd.Series:
    """Compute each listing's TF-IDF cosine distance from the corpus centroid."""
    valid = listings[
        (listings["description"].notna()) &
        (listings["description"].str.len() >= MIN_DESCRIPTION_LENGTH)
    ].copy()

    if len(valid) > SAMPLE_SIZE * 2:
        sample = valid.sample(n=SAMPLE_SIZE * 2, random_state=RANDOM_STATE)
    else:
        sample = valid

    vectorizer = TfidfVectorizer(
        max_features=TFIDF_MAX_FEATURES,
        stop_words="english",
        min_df=2,
    )
    tfidf_matrix = vectorizer.fit_transform(sample["description"].fillna(""))

    # Centroid = mean of all vectors
    centroid = tfidf_matrix.mean(axis=0)
    centroid = np.asarray(centroid).flatten()

    # Distance from centroid for each listing
    similarities = cosine_similarity(tfidf_matrix, centroid.reshape(1, -1)).flatten()
    distances = 1 - similarities

    result = pd.Series(distances, index=sample.index, name="centroid_distance")
    return result


def analyze_description_price(df: pd.DataFrame) -> dict:
    """Correlate description features with price."""
    valid = df[df["price"].notna() & (df["price"] > 0)].copy()

    if len(valid) < 100:
        return {"error": "insufficient data"}

    # Log price for better correlation (price is right-skewed)
    valid["log_price"] = np.log1p(valid["price"])

    features = ["desc_length", "desc_word_count", "luxury_density",
                "modern_density", "cozy_density", "location_density", "marketing_density"]

    correlations = {}
    for feat in features:
        if feat in valid.columns and valid[feat].notna().sum() > 50:
            corr = valid[[feat, "log_price"]].corr().iloc[0, 1]
            correlations[feat] = round(float(corr), 4) if not np.isnan(corr) else None

    # Quartile analysis: price by description length quartiles
    valid["desc_length_q"] = pd.qcut(valid["desc_length"], 4, labels=["short", "medium", "long", "very_long"])
    price_by_length = valid.groupby("desc_length_q", observed=True)["price"].agg(["median", "mean", "count"]).reset_index()
    price_by_length_list = [
        {"quartile": row["desc_length_q"], "median_price": round(float(row["median"]), 2),
         "mean_price": round(float(row["mean"]), 2), "n": int(row["count"])}
        for _, row in price_by_length.iterrows()
    ]

    # Luxury keyword impact
    valid["has_luxury"] = valid["luxury_count"] > 0
    luxury_price = valid.groupby("has_luxury")["price"].median()
    luxury_premium = {
        "with_luxury_keywords_median": round(float(luxury_price.get(True, 0)), 2),
        "without_luxury_keywords_median": round(float(luxury_price.get(False, 0)), 2),
        "premium_pct": round(
            (luxury_price.get(True, 0) / luxury_price.get(False, 1) - 1) * 100, 1
        ) if luxury_price.get(False, 0) > 0 else None,
    }

    # Centroid distance vs price (if available)
    centroid_corr = None
    if "centroid_distance" in valid.columns and valid["centroid_distance"].notna().sum() > 50:
        centroid_corr = round(float(valid[["centroid_distance", "log_price"]].corr().iloc[0, 1]), 4)

    return {
        "correlations": correlations,
        "price_by_description_length": price_by_length_list,
        "luxury_premium": luxury_premium,
        "centroid_distance_vs_price_corr": centroid_corr,
        "n": int(len(valid)),
    }


def analyze_description_reviews(df: pd.DataFrame, reviews: pd.DataFrame) -> dict:
    """Correlate description features with review outcomes."""
    # Compute per-listing negative rate
    reviews_copy = reviews.copy()
    reviews_copy["is_negative"] = reviews_copy["comments"].str.contains(neg_regex, na=False)

    listing_neg = reviews_copy.groupby("listing_id").agg(
        total_reviews=("is_negative", "count"),
        negative_count=("is_negative", "sum"),
    ).reset_index()
    listing_neg["neg_rate"] = listing_neg["negative_count"] / listing_neg["total_reviews"]

    # Filter to listings with enough reviews
    listing_neg = listing_neg[listing_neg["total_reviews"] >= 10]

    # Merge with description features
    merged = df.merge(listing_neg, left_on="id", right_on="listing_id", how="inner")

    if len(merged) < 100:
        return {"error": "insufficient merged data"}

    # Correlations: description features vs review score and negative rate
    features = ["desc_length", "desc_word_count", "luxury_density",
                "modern_density", "cozy_density", "location_density", "marketing_density"]

    score_correlations = {}
    neg_rate_correlations = {}

    for feat in features:
        if feat in merged.columns and merged[feat].notna().sum() > 50:
            if merged["review_scores_rating"].notna().sum() > 50:
                corr_score = merged[[feat, "review_scores_rating"]].corr().iloc[0, 1]
                score_correlations[feat] = round(float(corr_score), 4) if not np.isnan(corr_score) else None

            corr_neg = merged[[feat, "neg_rate"]].corr().iloc[0, 1]
            neg_rate_correlations[feat] = round(float(corr_neg), 4) if not np.isnan(corr_neg) else None

    # Marketing language vs negative rate quartiles
    try:
        merged["marketing_q"] = pd.qcut(
            merged["marketing_density"].clip(lower=0),
            4, labels=False, duplicates="drop",
        )
        q_labels = {0: "low", 1: "medium", 2: "high", 3: "very_high"}
        merged["marketing_q"] = merged["marketing_q"].map(q_labels)
    except (ValueError, TypeError):
        merged["marketing_q"] = pd.cut(
            merged["marketing_density"].clip(lower=0),
            bins=4, labels=["low", "medium", "high", "very_high"],
        )
    neg_by_marketing = merged.groupby("marketing_q", observed=True)["neg_rate"].agg(["mean", "median", "count"]).reset_index()
    neg_by_marketing_list = [
        {"quartile": row["marketing_q"], "mean_neg_rate": round(float(row["mean"]), 4),
         "median_neg_rate": round(float(row["median"]), 4), "n": int(row["count"])}
        for _, row in neg_by_marketing.iterrows()
    ]

    # Centroid distance vs negative rate
    centroid_neg_corr = None
    if "centroid_distance" in merged.columns and merged["centroid_distance"].notna().sum() > 50:
        centroid_neg_corr = round(float(merged[["centroid_distance", "neg_rate"]].corr().iloc[0, 1]), 4)

    # Score by description length
    merged["desc_length_q"] = pd.qcut(merged["desc_length"], 4, labels=["short", "medium", "long", "very_long"])
    score_by_length = merged.groupby("desc_length_q", observed=True)["review_scores_rating"].agg(["mean", "count"]).reset_index()
    score_by_length_list = [
        {"quartile": row["desc_length_q"], "mean_score": round(float(row["mean"]), 3), "n": int(row["count"])}
        for _, row in score_by_length.iterrows()
    ]

    return {
        "score_correlations": score_correlations,
        "neg_rate_correlations": neg_rate_correlations,
        "neg_rate_by_marketing_density": neg_by_marketing_list,
        "score_by_description_length": score_by_length_list,
        "centroid_distance_vs_neg_rate_corr": centroid_neg_corr,
        "n": int(len(merged)),
    }


def analyze_city(city: str, city_name: str) -> dict:
    print(f"\n{'='*60}")
    print(f"  Description Impact Analysis — {city_name}")
    print(f"{'='*60}")

    listings, reviews = load_city(city)
    print(f"  Loaded {len(listings):,} listings, {len(reviews):,} reviews")

    # Extract description features
    df = extract_description_features(listings)
    print(f"  Listings with valid descriptions (≥{MIN_DESCRIPTION_LENGTH} chars): {len(df):,}")

    # Compute centroid distance
    print("  Computing TF-IDF centroid distances...")
    centroid_dist = compute_centroid_distance(listings)
    df = df.join(centroid_dist, how="left")
    print(f"  Centroid distances computed for {centroid_dist.notna().sum():,} listings")

    # Description → Price
    print("  Analyzing description → price relationship...")
    price_results = analyze_description_price(df)

    # Description → Reviews
    print("  Analyzing description → review relationship...")
    review_results = analyze_description_reviews(df, reviews)

    # Summary stats
    desc_stats = {
        "mean_length": round(float(df["desc_length"].mean()), 0),
        "median_length": round(float(df["desc_length"].median()), 0),
        "mean_word_count": round(float(df["desc_word_count"].mean()), 0),
        "pct_with_luxury_keywords": round(float((df["luxury_count"] > 0).mean() * 100), 1),
        "pct_with_modern_keywords": round(float((df["modern_count"] > 0).mean() * 100), 1),
        "pct_with_cozy_keywords": round(float((df["cozy_count"] > 0).mean() * 100), 1),
        "pct_with_location_keywords": round(float((df["location_count"] > 0).mean() * 100), 1),
        "mean_centroid_distance": round(float(df["centroid_distance"].mean()), 4) if "centroid_distance" in df.columns and df["centroid_distance"].notna().any() else None,
    }

    if "error" not in price_results:
        print(f"  Price correlations computed (n={price_results['n']:,})")
        if price_results["luxury_premium"]["premium_pct"]:
            print(f"  Luxury keyword premium: +{price_results['luxury_premium']['premium_pct']:.0f}% median price")
    if "error" not in review_results:
        print(f"  Review correlations computed (n={review_results['n']:,})")

    return {
        "city": city,
        "description_stats": desc_stats,
        "description_vs_price": price_results,
        "description_vs_reviews": review_results,
    }


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    all_results = {}

    for city, city_name in CITIES.items():
        all_results[city] = analyze_city(city, city_name)

    output_path = OUTPUT_DIR / "description_impact.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n✓ Results saved to {output_path}")


if __name__ == "__main__":
    main()
