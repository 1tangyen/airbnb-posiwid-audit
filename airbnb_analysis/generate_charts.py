"""
Generate static chart data for the Airbnb POSIWID HTML report.
Outputs a JSON file consumed by the HTML dashboard.
"""
import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings('ignore')

def clean_price(s):
    if pd.isna(s):
        return np.nan
    s = str(s).replace('$', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return np.nan

SNAPSHOTS = [
    ('2025-03', 'listings_2025_03.csv.gz'),
    ('2025-09', 'listings_2025_09.csv.gz'),
    ('2026-04', 'listings_2026_04.csv.gz'),
]

print("Loading listings...")
snapshots = []
for label, path in SNAPSHOTS:
    df = pd.read_csv(path, low_memory=False)
    df['price_clean'] = df['price'].apply(clean_price)
    df['snapshot'] = label
    snapshots.append((label, df))

print("Loading reviews...")
reviews = pd.read_csv('reviews_2026_04.csv.gz', low_memory=False)
reviews['date'] = pd.to_datetime(reviews['date'], errors='coerce')
reviews = reviews.dropna(subset=['comments', 'date'])
reviews['comments'] = reviews['comments'].astype(str)
reviews['year'] = reviews['date'].dt.year

negative_patterns = '|'.join([
    r'\bnot worth\b', r'\boverpriced\b', r'\btoo expensive\b',
    r'\bdirty\b', r'\bnoisy\b', r'\brude\b', r'\bunclean\b',
    r'\bdisappoint\w*\b', r'\bawful\b', r'\bterrible\b',
    r'\bworse?\b', r'\bhorrible\b', r'\bscam\b', r'\bmisleading\b',
    r'\bnot as described\b', r'\bnot as pictured\b',
    r'\bsmell\w*\b', r'\bbug\w?\b', r'\bcockroach\w*\b', r'\brat\b',
    r'\bwouldn.?t recommend\b', r'\bwouldn.?t stay\b',
    r'\bnot clean\b', r'\bnever again\b', r'\bregret\b',
])
value_patterns = '|'.join([
    r'\bnot worth\b', r'\boverpriced\b', r'\btoo expensive\b',
    r'\bnot value\b', r'\bpricey\b', r'\bcost(?:ly)\b',
    r'\bexpensive\b', r'\brip.?off\b',
])

reviews['has_negative'] = reviews['comments'].str.lower().str.contains(negative_patterns, regex=True, na=False)
reviews['has_value_complaint'] = reviews['comments'].str.lower().str.contains(value_patterns, regex=True, na=False)

charts = {}

# Chart 1: Review sentiment by year
yearly = reviews[reviews['year'] >= 2013].groupby('year').agg(
    total=('has_negative', 'count'),
    negative=('has_negative', 'sum'),
    value=('has_value_complaint', 'sum'),
).reset_index()
yearly['neg_rate'] = (yearly['negative'] / yearly['total'] * 100).round(2)
yearly['val_rate'] = (yearly['value'] / yearly['total'] * 100).round(2)
charts['sentiment_by_year'] = {
    'years': yearly['year'].tolist(),
    'negative_rate': yearly['neg_rate'].tolist(),
    'value_rate': yearly['val_rate'].tolist(),
    'total_reviews': yearly['total'].tolist(),
}

# Chart 2: Score distribution (latest)
latest = snapshots[-1][1]
rated = latest['review_scores_rating'].dropna()
bins = np.arange(1, 5.2, 0.1)
hist, edges = np.histogram(rated, bins=bins)
charts['score_distribution'] = {
    'bins': [round(e, 1) for e in edges[:-1]],
    'counts': hist.tolist(),
    'mean': round(rated.mean(), 2),
    'median': round(rated.median(), 2),
    'pct_above_4': round((rated >= 4.0).mean() * 100, 1),
    'pct_above_45': round((rated >= 4.5).mean() * 100, 1),
}

# Chart 3: Price CV by snapshot and neighbourhood
top_hoods = latest['neighbourhood_cleansed'].value_counts().head(5).index.tolist()
cv_data = []
for label, df in snapshots:
    for hood in top_hoods:
        sub = df[(df['neighbourhood_cleansed'] == hood) &
                 (df['room_type'] == 'Entire home/apt') &
                 (df['price_clean'] > 0) & (df['price_clean'] < 5000)]
        if len(sub) < 30:
            continue
        cv_data.append({
            'snapshot': label,
            'neighbourhood': hood,
            'cv': round(sub['price_clean'].std() / sub['price_clean'].mean(), 4),
            'median_price': round(sub['price_clean'].median(), 0),
            'n': len(sub),
        })
charts['price_cv'] = cv_data

# Chart 4: Host concentration
conc_data = []
for label, df in snapshots:
    multi = df.groupby('host_id').size()
    total_h = len(multi)
    total_l = len(df)
    top10 = multi.nlargest(10).sum()
    conc_data.append({
        'snapshot': label,
        'total_hosts': total_h,
        'total_listings': total_l,
        'single_pct': round((multi == 1).sum() / total_h * 100, 1),
        'multi10_pct': round((multi > 10).sum() / total_h * 100, 2),
        'top10_share': round(top10 / total_l * 100, 1),
    })
charts['host_concentration'] = conc_data

# Chart 5: Description similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sim_data = []
for label, df in snapshots:
    descs = df['description'].dropna().astype(str)
    descs = descs[descs.str.len() > 50]
    if len(descs) > 5000:
        descs = descs.sample(5000, random_state=42)
    vec = TfidfVectorizer(max_features=3000, stop_words='english', min_df=5)
    tfidf = vec.fit_transform(descs)
    n = min(2000, tfidf.shape[0])
    idx = np.random.RandomState(42).choice(tfidf.shape[0], n, replace=False)
    sm = tfidf[idx]
    sim = cosine_similarity(sm)
    upper = sim[np.triu_indices_from(sim, k=1)]
    sim_data.append({
        'snapshot': label,
        'mean_sim': round(float(upper.mean()), 4),
        'median_sim': round(float(np.median(upper)), 4),
        'p90_sim': round(float(np.percentile(upper, 90)), 4),
    })
charts['description_similarity'] = sim_data

with open('chart_data.json', 'w') as f:
    json.dump(charts, f, indent=2)

print("chart_data.json written.")
