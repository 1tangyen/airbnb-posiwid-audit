"""
VoxelNoir POSIWID Analysis — Airbnb Platform Power Audit
=========================================================
Tests 4 signals of platform control over host autonomy:
  A. Price variance compression (Braverman deskilling)
  B. Price synchrony increase (Noble control path)
  C. Review text vs score gap (Brynjolfsson bargaining power)
  D. Listing description homogenization (Winner "political by arrangement")
"""

import pandas as pd
import numpy as np
import json
import re
import warnings
from collections import Counter
warnings.filterwarnings('ignore')

DATA_DIR = '.'
OUT_DIR = '.'

SNAPSHOTS = [
    ('2025-03', 'listings_2025_03.csv.gz'),
    ('2025-09', 'listings_2025_09.csv.gz'),
    ('2026-04', 'listings_2026_04.csv.gz'),
]

def clean_price(s):
    if pd.isna(s):
        return np.nan
    s = str(s).replace('$', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return np.nan

def load_listings(path, label):
    df = pd.read_csv(path, low_memory=False)
    df['price_clean'] = df['price'].apply(clean_price)
    df['snapshot'] = label
    return df


# ===================================================================
# SIGNAL A: Price Variance Compression (Braverman Deskilling)
# ===================================================================
def analyze_price_variance(snapshots_data):
    print("\n" + "="*70)
    print("SIGNAL A: PRICE VARIANCE COMPRESSION (Braverman Deskilling)")
    print("="*70)
    print("Hypothesis: Smart Pricing compresses price diversity over time.")
    print("If true → host pricing 'craft' is being systematically flattened.\n")

    results = []
    for label, df in snapshots_data:
        for rt in ['Entire home/apt', 'Private room']:
            subset = df[(df['room_type'] == rt) & (df['price_clean'] > 0) & (df['price_clean'] < 5000)]
            if len(subset) < 100:
                continue
            stats = {
                'snapshot': label,
                'room_type': rt,
                'count': len(subset),
                'median': subset['price_clean'].median(),
                'mean': round(subset['price_clean'].mean(), 2),
                'std': round(subset['price_clean'].std(), 2),
                'iqr': round(subset['price_clean'].quantile(0.75) - subset['price_clean'].quantile(0.25), 2),
                'cv': round(subset['price_clean'].std() / subset['price_clean'].mean(), 4),
            }
            results.append(stats)

    df_res = pd.DataFrame(results)
    print(df_res.to_string(index=False))

    print("\n--- Per-neighbourhood analysis (top 5 neighbourhoods) ---")
    latest = snapshots_data[-1][1]
    top_hoods = latest['neighbourhood_cleansed'].value_counts().head(5).index.tolist()

    hood_results = []
    for label, df in snapshots_data:
        for hood in top_hoods:
            subset = df[(df['neighbourhood_cleansed'] == hood) &
                        (df['room_type'] == 'Entire home/apt') &
                        (df['price_clean'] > 0) & (df['price_clean'] < 5000)]
            if len(subset) < 30:
                continue
            hood_results.append({
                'snapshot': label,
                'neighbourhood': hood[:25],
                'n': len(subset),
                'median': subset['price_clean'].median(),
                'std': round(subset['price_clean'].std(), 2),
                'cv': round(subset['price_clean'].std() / subset['price_clean'].mean(), 4),
            })

    df_hood = pd.DataFrame(hood_results)
    print(df_hood.to_string(index=False))
    return df_res


# ===================================================================
# SIGNAL B: Price Synchrony (Noble Control Path)
# ===================================================================
def analyze_price_synchrony(snapshots_data):
    print("\n" + "="*70)
    print("SIGNAL B: PRICE SYNCHRONY (Noble Control Path)")
    print("="*70)
    print("Hypothesis: Listings in the same area increasingly price in lockstep.")
    print("If true → individual judgment replaced by algorithmic consensus.\n")

    latest = snapshots_data[-1][1]
    earliest = snapshots_data[0][1]

    for label_tag, df in [('Earliest (2025-03)', earliest), ('Latest (2026-04)', latest)]:
        print(f"\n--- {label_tag} ---")
        top_hoods = df['neighbourhood_cleansed'].value_counts().head(5).index.tolist()
        for hood in top_hoods:
            subset = df[(df['neighbourhood_cleansed'] == hood) &
                        (df['room_type'] == 'Entire home/apt') &
                        (df['price_clean'] > 0) & (df['price_clean'] < 5000)]
            if len(subset) < 50:
                continue
            prices = subset['price_clean'].values
            p25, p50, p75 = np.percentile(prices, [25, 50, 75])
            within_band = np.sum((prices >= p50*0.8) & (prices <= p50*1.2)) / len(prices)
            print(f"  {hood[:30]:30s}  n={len(subset):5d}  median=${p50:7.0f}  "
                  f"IQR=${p75-p25:7.0f}  within_±20%_of_median={within_band:.1%}")


# ===================================================================
# SIGNAL C: Review Score vs Text Sentiment Gap (Brynjolfsson)
# ===================================================================
def analyze_review_gap(reviews_path, listings_df):
    print("\n" + "="*70)
    print("SIGNAL C: REVIEW TEXT vs SCORE GAP (Brynjolfsson Bargaining Power)")
    print("="*70)
    print("Hypothesis: Scores are inflated. Text reveals complaints scores hide.")
    print("POSIWID: Rating system claims to help guests. Actually maintains trust facade.\n")

    reviews = pd.read_csv(reviews_path, low_memory=False)
    reviews['date'] = pd.to_datetime(reviews['date'], errors='coerce')
    reviews = reviews.dropna(subset=['comments', 'date'])
    reviews['comments'] = reviews['comments'].astype(str)

    negative_patterns = [
        r'\bnot worth\b', r'\boverpriced\b', r'\btoo expensive\b',
        r'\bdirty\b', r'\bnoisy\b', r'\brude\b', r'\bunclean\b',
        r'\bdisappoint\w*\b', r'\bawful\b', r'\bterrible\b',
        r'\bworse?\b', r'\bhorrible\b', r'\bscam\b', r'\bmisleading\b',
        r'\bnot as described\b', r'\bnot as pictured\b',
        r'\bsmell\w*\b', r'\bbug\w?\b', r'\bcockroach\w*\b', r'\brat\b',
        r'\bwouldn.?t recommend\b', r'\bwouldn.?t stay\b',
        r'\bnot clean\b', r'\bnever again\b', r'\bregret\b',
    ]
    combined_pattern = '|'.join(negative_patterns)

    reviews['has_negative'] = reviews['comments'].str.lower().str.contains(
        combined_pattern, regex=True, na=False
    )

    value_patterns = [
        r'\bnot worth\b', r'\boverpriced\b', r'\btoo expensive\b',
        r'\bnot value\b', r'\bpricey\b', r'\bcost(?:ly)\b',
        r'\bexpensive\b', r'\brip.?off\b',
    ]
    value_pattern = '|'.join(value_patterns)
    reviews['has_value_complaint'] = reviews['comments'].str.lower().str.contains(
        value_pattern, regex=True, na=False
    )

    reviews['year'] = reviews['date'].dt.year
    yearly = reviews.groupby('year').agg(
        total=('has_negative', 'count'),
        negative_count=('has_negative', 'sum'),
        value_complaint_count=('has_value_complaint', 'sum'),
    ).reset_index()
    yearly['negative_rate'] = (yearly['negative_count'] / yearly['total'] * 100).round(2)
    yearly['value_rate'] = (yearly['value_complaint_count'] / yearly['total'] * 100).round(2)
    yearly = yearly[yearly['total'] > 1000]
    print("Negative signal rates by year:")
    print(yearly.to_string(index=False))

    print("\n--- Score distribution (latest listings) ---")
    rated = listings_df[listings_df['review_scores_rating'].notna()]
    print(f"  Mean rating: {rated['review_scores_rating'].mean():.2f}")
    print(f"  Median rating: {rated['review_scores_rating'].median():.2f}")
    print(f"  % rated >= 4.5: {(rated['review_scores_rating'] >= 4.5).mean():.1%}")
    print(f"  % rated >= 4.0: {(rated['review_scores_rating'] >= 4.0).mean():.1%}")

    value_rated = listings_df[listings_df['review_scores_value'].notna()]
    print(f"\n  Mean value score: {value_rated['review_scores_value'].mean():.2f}")
    print(f"  Median value score: {value_rated['review_scores_value'].median():.2f}")

    merged = reviews.merge(
        listings_df[['id', 'review_scores_rating', 'price_clean']].rename(columns={'id': 'listing_id'}),
        on='listing_id', how='inner'
    )
    high_rated_negative = merged[
        (merged['review_scores_rating'] >= 4.5) & (merged['has_negative'])
    ]
    total_high = merged[merged['review_scores_rating'] >= 4.5]
    if len(total_high) > 0:
        print(f"\n  High-rated (≥4.5) listings with negative text: "
              f"{len(high_rated_negative):,} / {len(total_high):,} = "
              f"{len(high_rated_negative)/len(total_high):.1%}")

    return reviews


# ===================================================================
# SIGNAL D: Description Homogenization (Winner "Political by Arrangement")
# ===================================================================
def analyze_description_homogenization(snapshots_data):
    print("\n" + "="*70)
    print("SIGNAL D: DESCRIPTION HOMOGENIZATION (Winner 'Political by Arrangement')")
    print("="*70)
    print("Hypothesis: Platform SEO/AI tools make listing descriptions converge.")
    print("POSIWID: Airbnb claims 'every home is unique'. Platform produces uniformity.\n")

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    for label, df in snapshots_data:
        print(f"\n--- {label} ---")
        descs = df['description'].dropna().astype(str)
        descs = descs[descs.str.len() > 50]

        if len(descs) > 5000:
            descs = descs.sample(5000, random_state=42)

        vectorizer = TfidfVectorizer(max_features=3000, stop_words='english', min_df=5)
        tfidf = vectorizer.fit_transform(descs)

        n_sample = min(2000, tfidf.shape[0])
        idx = np.random.RandomState(42).choice(tfidf.shape[0], n_sample, replace=False)
        sample_matrix = tfidf[idx]
        sim = cosine_similarity(sample_matrix)
        upper_tri = sim[np.triu_indices_from(sim, k=1)]

        print(f"  n_descriptions: {len(descs)}")
        print(f"  mean_pairwise_similarity: {upper_tri.mean():.4f}")
        print(f"  median_pairwise_similarity: {np.median(upper_tri):.4f}")
        print(f"  p90_similarity: {np.percentile(upper_tri, 90):.4f}")

        # top shared phrases
        features = vectorizer.get_feature_names_out()
        mean_tfidf = np.array(tfidf.mean(axis=0)).flatten()
        top_idx = mean_tfidf.argsort()[-20:][::-1]
        top_terms = [(features[i], round(mean_tfidf[i], 4)) for i in top_idx]
        print(f"  top_20_terms: {[t[0] for t in top_terms]}")

    # description length trend
    print("\n--- Description length trend ---")
    for label, df in snapshots_data:
        descs = df['description'].dropna().astype(str)
        descs = descs[descs.str.len() > 10]
        lengths = descs.str.len()
        print(f"  {label}: n={len(descs):,}  mean_len={lengths.mean():.0f}  "
              f"median_len={lengths.median():.0f}  std_len={lengths.std():.0f}")


# ===================================================================
# BONUS: Host listing count distribution (concentration)
# ===================================================================
def analyze_host_concentration(snapshots_data):
    print("\n" + "="*70)
    print("BONUS: HOST CONCENTRATION (Platform as Landlord)")
    print("="*70)

    for label, df in snapshots_data:
        total = df['host_id'].nunique()
        multi = df.groupby('host_id').size()
        single = (multi == 1).sum()
        multi_2_10 = ((multi >= 2) & (multi <= 10)).sum()
        multi_10plus = (multi > 10).sum()
        top10_hosts = multi.nlargest(10).sum()
        total_listings = len(df)
        print(f"\n  {label}: {total:,} hosts, {total_listings:,} listings")
        print(f"    Single listing: {single:,} ({single/total:.1%})")
        print(f"    2-10 listings:  {multi_2_10:,} ({multi_2_10/total:.1%})")
        print(f"    10+ listings:   {multi_10plus:,} ({multi_10plus/total:.1%})")
        print(f"    Top 10 hosts own: {top10_hosts:,} listings ({top10_hosts/total_listings:.1%})")


# ===================================================================
# MAIN
# ===================================================================
if __name__ == '__main__':
    print("Loading listings data...")
    snapshots_data = []
    for label, path in SNAPSHOTS:
        df = load_listings(path, label)
        print(f"  {label}: {len(df):,} listings, {df['price_clean'].notna().sum():,} with price")
        snapshots_data.append((label, df))

    # A: Price variance
    price_results = analyze_price_variance(snapshots_data)

    # B: Price synchrony
    analyze_price_synchrony(snapshots_data)

    # D: Description homogenization
    analyze_description_homogenization(snapshots_data)

    # Bonus: Host concentration
    analyze_host_concentration(snapshots_data)

    # C: Review gap (load separately - big file)
    print("\nLoading reviews data (this may take a moment)...")
    reviews = analyze_review_gap('reviews_2026_04.csv.gz', snapshots_data[-1][1])

    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
