"""
03_analyze.py — POSIWID signal analysis across NYC, Boston, Chicago

Reads cleaned data from data/{city}/listings_clean.csv.gz and reviews_clean.csv.gz.
Outputs results to output/analysis_results.json.

Four signals:
  A — Price Variance (Braverman deskilling)
  B — Review Score Inflation (Brynjolfsson bargaining power)
  C — Text vs Score Gap / Hidden Transcript (James C. Scott)
  D — Description Homogenization (Winner — artifacts have politics)
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

# --- Sentiment patterns (English) ---

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
    r"\bwouldn['’]?t\s+recommend\b",
]

VALUE_PATTERNS = [
    r"\boverpriced\b", r"\bover\s*priced\b", r"\btoo\s+expensive\b",
    r"\bnot\s+worth\b", r"\brip\s*off\b", r"\brip-off\b",
    r"\bbetter\s+(?:off|deal|value)\s+(?:at|with)\s+(?:a\s+)?hotel",
    r"\bhidden\s+fee", r"\bcleaning\s+fee",
]

neg_regex = re.compile("|".join(NEGATIVE_PATTERNS), re.IGNORECASE)
val_regex = re.compile("|".join(VALUE_PATTERNS), re.IGNORECASE)

# V2 stratification constants
HOST_SCALE_BINS = [0, 1, 4, 9, float("inf")]
HOST_SCALE_LABELS = ["single", "small_multi_2_4", "medium_multi_5_9", "large_multi_10+"]

STRAT_DIMENSIONS = [
    ("room_type", "room_type"),
    ("host_scale", "host_scale"),
    ("hood_density", "neighbourhood_density"),
]


def load_city(city: str):
    listings = pd.read_csv(DATA_DIR / city / "listings_clean.csv.gz", compression="gzip", low_memory=False)
    reviews = pd.read_csv(DATA_DIR / city / "reviews_clean.csv.gz", compression="gzip", low_memory=False)
    reviews["date"] = pd.to_datetime(reviews["date"], errors="coerce")
    listings["id"] = pd.to_numeric(listings["id"], errors="coerce").astype("Int64")
    reviews["listing_id"] = pd.to_numeric(reviews["listing_id"], errors="coerce").astype("Int64")
    return listings, reviews


def add_stratification_columns(listings: pd.DataFrame) -> pd.DataFrame:
    """Add V2 stratification columns to listings dataframe."""
    df = listings.copy()

    # host_scale: single / small_multi / medium_multi / large_multi
    df["host_scale"] = pd.cut(
        df["calculated_host_listings_count"],
        bins=HOST_SCALE_BINS,
        labels=HOST_SCALE_LABELS,
        right=True,
    )

    # neighbourhood_density: high / medium / low tercile by listing count per neighbourhood
    hood_counts = df.groupby("neighbourhood_cleansed").size().rename("hood_listing_count")
    df = df.merge(hood_counts, left_on="neighbourhood_cleansed", right_index=True, how="left")
    terciles = df["hood_listing_count"].quantile([1/3, 2/3])
    df["neighbourhood_density"] = pd.cut(
        df["hood_listing_count"],
        bins=[0, terciles.iloc[0], terciles.iloc[1], float("inf")],
        labels=["low", "medium", "high"],
        right=True,
    )

    return df


# === Signal A: Price Variance ===

def analyze_price_variance(listings: pd.DataFrame, city: str) -> dict:
    results = {}

    # Overall stats
    prices = listings["price"]
    results["overall"] = {
        "mean": round(prices.mean(), 2),
        "median": round(prices.median(), 2),
        "std": round(prices.std(), 2),
        "cv": round(prices.std() / prices.mean(), 4),
        "n": int(len(prices)),
    }

    # Per-neighbourhood CV (top 10 by listing count)
    hood_stats = []
    for hood, group in listings.groupby("neighbourhood_cleansed"):
        if len(group) >= 30:
            p = group["price"]
            hood_stats.append({
                "neighbourhood": hood,
                "n": int(len(group)),
                "median_price": round(p.median(), 2),
                "mean_price": round(p.mean(), 2),
                "cv": round(p.std() / p.mean(), 4),
            })
    hood_stats.sort(key=lambda x: x["n"], reverse=True)
    results["by_neighbourhood"] = hood_stats[:15]

    # Per room_type
    room_stats = []
    for rt, group in listings.groupby("room_type"):
        p = group["price"]
        room_stats.append({
            "room_type": rt,
            "n": int(len(group)),
            "median_price": round(p.median(), 2),
            "cv": round(p.std() / p.mean(), 4),
        })
    results["by_room_type"] = room_stats

    return results


# === Signal B: Review Score Inflation ===

def analyze_score_inflation(listings: pd.DataFrame, city: str) -> dict:
    scores = listings["review_scores_rating"].dropna()
    if len(scores) == 0:
        return {"error": "no scores"}

    results = {
        "n": int(len(scores)),
        "mean": round(scores.mean(), 3),
        "median": round(scores.median(), 3),
        "std": round(scores.std(), 3),
        "pct_above_4": round((scores >= 4.0).mean() * 100, 1),
        "pct_above_45": round((scores >= 4.5).mean() * 100, 1),
        "pct_above_48": round((scores >= 4.8).mean() * 100, 1),
        "pct_5_0": round((scores == 5.0).mean() * 100, 1),
    }

    # Distribution bins
    bins = np.arange(1.0, 5.1, 0.1)
    hist, edges = np.histogram(scores, bins=bins)
    results["distribution"] = {
        "bins": [round(b, 1) for b in edges[:-1].tolist()],
        "counts": hist.tolist(),
    }

    # Sub-scores comparison
    sub_scores = {}
    for col in ["review_scores_accuracy", "review_scores_cleanliness",
                "review_scores_checkin", "review_scores_communication",
                "review_scores_location", "review_scores_value"]:
        if col in listings.columns:
            s = listings[col].dropna()
            if len(s) > 0:
                sub_scores[col.replace("review_scores_", "")] = {
                    "mean": round(s.mean(), 3),
                    "n": int(len(s)),
                }
    results["sub_scores"] = sub_scores

    return results


# === Signal C: Text vs Score Gap (Hidden Transcript) ===

def analyze_hidden_transcript(reviews: pd.DataFrame, listings: pd.DataFrame, city: str) -> dict:
    # Add year column
    reviews = reviews.copy()
    reviews["year"] = reviews["date"].dt.year

    # Detect negative sentiment and value complaints
    reviews["is_negative"] = reviews["comments"].str.contains(neg_regex, na=False)
    reviews["is_value_complaint"] = reviews["comments"].str.contains(val_regex, na=False)

    # Year-by-year trend
    yearly = []
    for year, group in reviews.groupby("year"):
        if len(group) < 100:
            continue
        yearly.append({
            "year": int(year),
            "total_reviews": int(len(group)),
            "negative_count": int(group["is_negative"].sum()),
            "negative_rate": round(group["is_negative"].mean() * 100, 2),
            "value_complaint_count": int(group["is_value_complaint"].sum()),
            "value_rate": round(group["is_value_complaint"].mean() * 100, 2),
        })
    yearly.sort(key=lambda x: x["year"])

    # Overall rates
    total = len(reviews)
    neg_total = reviews["is_negative"].sum()
    val_total = reviews["is_value_complaint"].sum()

    # Score-text cross-tab: reviews for listings with high scores (>=4.5) that contain negative text
    high_score_ids = set(listings[listings["review_scores_rating"] >= 4.5]["id"])
    high_score_reviews = reviews[reviews["listing_id"].isin(high_score_ids)]
    neg_in_high = high_score_reviews["is_negative"].sum()
    val_in_high = high_score_reviews["is_value_complaint"].sum()

    # Score-bucket analysis: negative rate by listing score range
    score_map = listings.set_index("id")["review_scores_rating"].to_dict()
    reviews["listing_score"] = reviews["listing_id"].map(score_map)
    scored_reviews = reviews.dropna(subset=["listing_score"])

    bucket_bins = [0, 3.0, 3.5, 4.0, 4.5, 5.01]
    bucket_labels = ["<3.0", "3.0-3.5", "3.5-4.0", "4.0-4.5", "4.5-5.0"]
    scored_reviews["score_bucket"] = pd.cut(
        scored_reviews["listing_score"], bins=bucket_bins, labels=bucket_labels, right=False
    )

    score_buckets = []
    for bucket in bucket_labels:
        group = scored_reviews[scored_reviews["score_bucket"] == bucket]
        if len(group) > 0:
            score_buckets.append({
                "bucket": bucket,
                "reviews": int(len(group)),
                "negative_count": int(group["is_negative"].sum()),
                "negative_rate": round(group["is_negative"].mean() * 100, 2),
            })

    # Precision validation: automated negation-context check on 100 random negatives
    negation_re = re.compile(
        r"(?:not|no|n't|never|without|wasn't|weren't|isn't|aren't|don't|didn't|doesn't|hardly|barely)"
        r"\s+(?:\w+\s+){0,3}"
        r"(?:dirty|filthy|stain|smell|stink|noisy|loud|unsafe|dangerous|scary|rude|disappoint|terrible|horrible|awful)",
        re.IGNORECASE,
    )
    neg_sample = reviews[reviews["is_negative"]].sample(n=min(100, reviews["is_negative"].sum()), random_state=42)
    fp_count = 0
    for _, row in neg_sample.iterrows():
        text = str(row["comments"])
        if len(list(neg_regex.finditer(text))) == 1 and len(list(negation_re.finditer(text))) >= 1:
            fp_count += 1
    precision_est = round((len(neg_sample) - fp_count) / len(neg_sample) * 100, 1)

    return {
        "total_reviews": int(total),
        "negative_total": int(neg_total),
        "negative_rate_pct": round(neg_total / total * 100, 2),
        "value_complaint_total": int(val_total),
        "value_rate_pct": round(val_total / total * 100, 2),
        "yearly_trend": yearly,
        "hidden_transcript": {
            "high_score_listings_count": int(len(high_score_ids)),
            "reviews_for_high_score_listings": int(len(high_score_reviews)),
            "negative_in_high_score": int(neg_in_high),
            "negative_rate_in_high_score_pct": round(neg_in_high / len(high_score_reviews) * 100, 2) if len(high_score_reviews) > 0 else 0,
            "value_complaints_in_high_score": int(val_in_high),
        },
        "score_buckets": score_buckets,
        "precision_validation": {
            "sample_size": int(len(neg_sample)),
            "estimated_fp_from_negation": int(fp_count),
            "estimated_precision_pct": precision_est,
        },
    }


# === Signal D: Description Homogenization ===

def analyze_description_homogenization(listings: pd.DataFrame, city: str) -> dict:
    descs = listings["description"].dropna()
    descs = descs[descs.str.strip().str.len() > 50]

    if len(descs) < 100:
        return {"error": "too few descriptions", "n": int(len(descs))}

    sample_size = min(2000, len(descs))
    sample = descs.sample(n=sample_size, random_state=42)

    tfidf = TfidfVectorizer(max_features=5000, stop_words="english", min_df=2)
    matrix = tfidf.fit_transform(sample)
    sim_matrix = cosine_similarity(matrix)

    # Extract upper triangle (exclude diagonal)
    upper = sim_matrix[np.triu_indices_from(sim_matrix, k=1)]

    return {
        "n_descriptions": int(len(descs)),
        "n_sampled": int(sample_size),
        "mean_similarity": round(float(upper.mean()), 4),
        "median_similarity": round(float(np.median(upper)), 4),
        "p90_similarity": round(float(np.percentile(upper, 90)), 4),
        "p95_similarity": round(float(np.percentile(upper, 95)), 4),
        "std_similarity": round(float(upper.std()), 4),
        "note": "TF-IDF (5000 features, English stop words) + cosine similarity on random 2000 sample",
    }


# === V2 Stratified Signal B: Score Inflation by Host Segment ===

def analyze_score_inflation_stratified(listings: pd.DataFrame) -> dict:
    results = {}
    for dim_name, col in STRAT_DIMENSIONS:
        dim_results = {}
        for group_val, group_df in listings.groupby(col, observed=True):
            scores = group_df["review_scores_rating"].dropna()
            if len(scores) < 10:
                dim_results[str(group_val)] = {"n": int(len(scores)), "note": "insufficient sample"}
                continue
            value_scores = group_df["review_scores_value"].dropna()
            dim_results[str(group_val)] = {
                "n": int(len(scores)),
                "mean": round(scores.mean(), 3),
                "pct_above_45": round((scores >= 4.5).mean() * 100, 1),
                "pct_5_0": round((scores == 5.0).mean() * 100, 1),
                "value_sub_mean": round(value_scores.mean(), 3) if len(value_scores) > 0 else None,
            }
        results[dim_name] = dim_results
    return results


# === V2 Stratified Signal C: Hidden Transcript by Host Segment ===

def analyze_hidden_transcript_stratified(reviews: pd.DataFrame, listings: pd.DataFrame) -> dict:
    reviews = reviews.copy()
    reviews["is_negative"] = reviews["comments"].str.contains(neg_regex, na=False)
    reviews["is_value_complaint"] = reviews["comments"].str.contains(val_regex, na=False)

    listing_cols = ["id", "review_scores_rating", "room_type", "host_scale", "neighbourhood_density"]
    available = [c for c in listing_cols if c in listings.columns]
    review_merged = reviews.merge(listings[available], left_on="listing_id", right_on="id", how="left")

    high_score_mask = review_merged["review_scores_rating"] >= 4.5

    results = {}
    for dim_name, col in STRAT_DIMENSIONS:
        if col not in review_merged.columns:
            continue
        dim_results = {}
        for group_val, group_df in review_merged[high_score_mask].groupby(col, observed=True):
            n = len(group_df)
            if n < 50:
                dim_results[str(group_val)] = {"n": n, "note": "insufficient sample"}
                continue
            neg_count = int(group_df["is_negative"].sum())
            val_count = int(group_df["is_value_complaint"].sum())
            dim_results[str(group_val)] = {
                "n": n,
                "negative_rate_pct": round(neg_count / n * 100, 2),
                "value_complaint_rate_pct": round(val_count / n * 100, 2),
                "negative_count": neg_count,
            }
        results[dim_name] = dim_results
    return results


# === V2 Stratified Signal D: Description Homogenization by Host Segment ===

def analyze_description_stratified(listings: pd.DataFrame) -> dict:
    results = {}

    for dim_name, col in [("room_type", "room_type"), ("host_scale", "host_scale")]:
        dim_results = {}
        for group_val, group_df in listings.groupby(col, observed=True):
            descs = group_df["description"].dropna()
            descs = descs[descs.str.strip().str.len() > 50]
            if len(descs) < 100:
                dim_results[str(group_val)] = {"n": int(len(descs)), "note": "insufficient sample"}
                continue
            sample_size = min(1000, len(descs))
            sample = descs.sample(n=sample_size, random_state=42)
            tfidf = TfidfVectorizer(max_features=5000, stop_words="english", min_df=2)
            matrix = tfidf.fit_transform(sample)
            sim = cosine_similarity(matrix)
            upper = sim[np.triu_indices_from(sim, k=1)]
            dim_results[str(group_val)] = {
                "n_sampled": int(sample_size),
                "mean_similarity": round(float(upper.mean()), 4),
                "p90_similarity": round(float(np.percentile(upper, 90)), 4),
            }
        results[dim_name] = dim_results

    # Same-host vs cross-host comparison
    multi_hosts = listings.groupby("host_id").filter(lambda x: len(x) >= 3)
    descs_multi = multi_hosts[multi_hosts["description"].str.strip().str.len() > 50].copy()
    if len(descs_multi) >= 50:
        tfidf = TfidfVectorizer(max_features=5000, stop_words="english", min_df=2)
        all_descs = descs_multi["description"]
        matrix = tfidf.fit_transform(all_descs)
        host_ids = descs_multi["host_id"].values
        indices = np.arange(len(host_ids))

        intra_sims = []
        inter_sims = []
        unique_hosts = descs_multi["host_id"].unique()
        rng = np.random.RandomState(42)

        for h in unique_hosts:
            h_idx = indices[host_ids == h]
            if len(h_idx) < 2:
                continue
            for i in range(len(h_idx)):
                for j in range(i + 1, len(h_idx)):
                    sim_val = cosine_similarity(matrix[h_idx[i]], matrix[h_idx[j]])[0, 0]
                    intra_sims.append(sim_val)

        n_inter = min(len(intra_sims) * 3, 5000)
        for _ in range(n_inter):
            h1, h2 = rng.choice(unique_hosts, size=2, replace=False)
            idx1 = rng.choice(indices[host_ids == h1])
            idx2 = rng.choice(indices[host_ids == h2])
            sim_val = cosine_similarity(matrix[idx1], matrix[idx2])[0, 0]
            inter_sims.append(sim_val)

        results["same_host_vs_cross_host"] = {
            "intra_host_mean": round(float(np.mean(intra_sims)), 4) if intra_sims else None,
            "intra_host_n_pairs": len(intra_sims),
            "inter_host_mean": round(float(np.mean(inter_sims)), 4) if inter_sims else None,
            "inter_host_n_pairs": len(inter_sims),
            "multi_listing_hosts_used": int(len(unique_hosts)),
        }
    else:
        results["same_host_vs_cross_host"] = {"note": "insufficient multi-listing hosts with descriptions"}

    return results


# === V2 Enhanced Host Concentration ===

def analyze_host_concentration_enhanced(listings: pd.DataFrame) -> dict:
    results = {}

    # Professional host ratio: entire_homes / total per host scale group
    for scale, group_df in listings.groupby("host_scale", observed=True):
        entire_count = group_df["calculated_host_listings_count_entire_homes"]
        total_count = group_df["calculated_host_listings_count"]
        valid = total_count > 0
        if valid.sum() > 0:
            ratio = (entire_count[valid] / total_count[valid]).mean()
            results[f"{scale}_entire_home_ratio"] = round(float(ratio), 3)

    # Price by host scale
    price_by_scale = {}
    for scale, group_df in listings.groupby("host_scale", observed=True):
        prices = group_df["price"].dropna()
        if len(prices) >= 10:
            price_by_scale[str(scale)] = {
                "median_price": round(prices.median(), 2),
                "n": int(len(prices)),
            }
    results["price_by_host_scale"] = price_by_scale

    # Multi-listing host share in high vs low density neighbourhoods
    density_host = {}
    for density, group_df in listings.groupby("neighbourhood_density", observed=True):
        multi_pct = (group_df["calculated_host_listings_count"] >= 2).mean() * 100
        density_host[str(density)] = {
            "multi_listing_host_pct": round(multi_pct, 1),
            "n": int(len(group_df)),
        }
    results["multi_host_by_density"] = density_host

    return results


# === Host Concentration (supplementary) ===

def analyze_host_concentration(listings: pd.DataFrame, city: str) -> dict:
    host_counts = listings.groupby("host_id").size()
    total_hosts = len(host_counts)
    total_listings = len(listings)

    single = (host_counts == 1).sum()
    multi2 = (host_counts >= 2).sum()
    multi5 = (host_counts >= 5).sum()
    multi10 = (host_counts >= 10).sum()

    # Top 10 hosts share
    top10 = host_counts.nlargest(10).sum()

    # Gini coefficient
    sorted_counts = np.sort(host_counts.values)
    n = len(sorted_counts)
    index = np.arange(1, n + 1)
    gini = (2 * np.sum(index * sorted_counts) / (n * np.sum(sorted_counts))) - (n + 1) / n

    return {
        "total_hosts": int(total_hosts),
        "total_listings": int(total_listings),
        "listings_per_host_mean": round(total_listings / total_hosts, 2),
        "single_listing_hosts_pct": round(single / total_hosts * 100, 1),
        "multi2_plus_pct": round(multi2 / total_hosts * 100, 1),
        "multi5_plus_pct": round(multi5 / total_hosts * 100, 1),
        "multi10_plus_pct": round(multi10 / total_hosts * 100, 1),
        "top10_hosts_listing_share_pct": round(top10 / total_listings * 100, 1),
        "gini_coefficient": round(float(gini), 4),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    for city, name in CITIES.items():
        print(f"\n{'='*60}")
        print(f"Analyzing {name}")
        print(f"{'='*60}")

        listings, reviews = load_city(city)
        listings = add_stratification_columns(listings)
        city_results = {"name": name}

        print("  Signal A: Price Variance...")
        city_results["signal_a_price_variance"] = analyze_price_variance(listings, city)

        print("  Signal B: Score Inflation...")
        city_results["signal_b_score_inflation"] = analyze_score_inflation(listings, city)

        print("  Signal C: Hidden Transcript...")
        city_results["signal_c_hidden_transcript"] = analyze_hidden_transcript(reviews, listings, city)

        print("  Signal D: Description Homogenization...")
        city_results["signal_d_description_homogenization"] = analyze_description_homogenization(listings, city)

        print("  Host Concentration...")
        city_results["host_concentration"] = analyze_host_concentration(listings, city)

        # V2 Stratified Analysis
        print("  V2 Signal B: Stratified Score Inflation...")
        city_results["v2_signal_b_stratified"] = analyze_score_inflation_stratified(listings)

        print("  V2 Signal C: Stratified Hidden Transcript...")
        city_results["v2_signal_c_stratified"] = analyze_hidden_transcript_stratified(reviews, listings)

        print("  V2 Signal D: Stratified Description Homogenization...")
        city_results["v2_signal_d_stratified"] = analyze_description_stratified(listings)

        print("  V2 Enhanced Host Concentration...")
        city_results["v2_host_concentration_enhanced"] = analyze_host_concentration_enhanced(listings)

        results[city] = city_results

    # Cross-city comparison summary
    print("\n\n=== CROSS-CITY SUMMARY ===\n")
    summary = {}
    for signal in ["signal_a_price_variance", "signal_b_score_inflation",
                    "signal_c_hidden_transcript", "signal_d_description_homogenization",
                    "host_concentration"]:
        summary[signal] = {}
        for city in CITIES:
            r = results[city][signal]
            if signal == "signal_a_price_variance":
                summary[signal][city] = {"overall_cv": r["overall"]["cv"], "median_price": r["overall"]["median"]}
            elif signal == "signal_b_score_inflation":
                summary[signal][city] = {"mean": r.get("mean"), "pct_above_45": r.get("pct_above_45")}
            elif signal == "signal_c_hidden_transcript":
                summary[signal][city] = {
                    "negative_rate": r["negative_rate_pct"],
                    "value_rate": r["value_rate_pct"],
                    "hidden_transcript_neg_rate": r["hidden_transcript"]["negative_rate_in_high_score_pct"],
                }
            elif signal == "signal_d_description_homogenization":
                summary[signal][city] = {"mean_sim": r.get("mean_similarity"), "p90_sim": r.get("p90_similarity")}
            elif signal == "host_concentration":
                summary[signal][city] = {
                    "single_host_pct": r["single_listing_hosts_pct"],
                    "top10_share": r["top10_hosts_listing_share_pct"],
                    "gini": r["gini_coefficient"],
                }

    results["cross_city_summary"] = summary

    for signal, data in summary.items():
        print(f"  {signal}:")
        for city, vals in data.items():
            print(f"    {city}: {vals}")

    # Save
    output_path = OUTPUT_DIR / "analysis_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
