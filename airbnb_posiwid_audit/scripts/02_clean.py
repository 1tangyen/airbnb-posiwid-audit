"""
02_clean.py — Data cleaning pipeline for Airbnb POSIWID Audit

Input:  data/{city}/listings.csv.gz, data/{city}/reviews.csv.gz
Output: data/{city}/listings_clean.csv.gz, data/{city}/reviews_clean.csv.gz
Report: data/cleaning_report.json

Each cleaning step is logged: what was removed, why, and how many rows.
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path

CITIES = {
    "nyc": {"snapshot": "2026-04-14", "name": "New York City"},
    "boston": {"snapshot": "2025-09-23", "name": "Boston"},
    "chicago": {"snapshot": "2025-09-22", "name": "Chicago"},
}

DATA_DIR = Path(__file__).parent.parent / "data"

LISTING_COLS_KEEP = [
    "id", "host_id", "host_name", "neighbourhood_cleansed",
    "neighbourhood_group_cleansed", "latitude", "longitude",
    "property_type", "room_type", "accommodates", "price",
    "minimum_nights", "maximum_nights", "number_of_reviews",
    "number_of_reviews_ltm", "first_review", "last_review",
    "review_scores_rating", "review_scores_accuracy",
    "review_scores_cleanliness", "review_scores_checkin",
    "review_scores_communication", "review_scores_location",
    "review_scores_value", "instant_bookable",
    "calculated_host_listings_count",
    "calculated_host_listings_count_entire_homes",
    "calculated_host_listings_count_private_rooms",
    "calculated_host_listings_count_shared_rooms",
    "description",
]

REVIEW_COLS_KEEP = [
    "listing_id", "id", "date", "reviewer_id", "comments",
]


def parse_price(price_str):
    if pd.isna(price_str):
        return np.nan
    s = str(price_str).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def clean_listings(city: str, log: dict) -> pd.DataFrame:
    path = DATA_DIR / city / "listings.csv.gz"
    df = pd.read_csv(path, compression="gzip", low_memory=False)
    steps = []
    initial = len(df)
    steps.append({"step": "load_raw", "rows": initial, "note": f"Loaded {initial:,} raw listings"})

    # Step 1: select columns (keep only what we need)
    available = [c for c in LISTING_COLS_KEEP if c in df.columns]
    missing = [c for c in LISTING_COLS_KEEP if c not in df.columns]
    df = df[available].copy()
    steps.append({"step": "select_columns", "kept": len(available), "missing": missing})

    # Step 2: parse price → numeric
    df["price_raw"] = df["price"]
    df["price"] = df["price"].apply(parse_price)
    price_null = df["price"].isna().sum()
    steps.append({"step": "parse_price", "null_after_parse": int(price_null),
                   "note": f"{price_null:,} listings have no price"})

    # Step 3: drop rows with no price (can't analyze price signals without it)
    before = len(df)
    df = df.dropna(subset=["price"])
    dropped = before - len(df)
    steps.append({"step": "drop_no_price", "dropped": dropped, "remaining": len(df),
                   "note": "Listings without price are excluded from all price-related analysis"})

    # Step 4: drop price outliers (< $10 or > $10,000/night — likely errors)
    before = len(df)
    df = df[(df["price"] >= 10) & (df["price"] <= 10000)]
    dropped = before - len(df)
    steps.append({"step": "drop_price_outliers", "dropped": dropped, "remaining": len(df),
                   "note": "Prices < $10 or > $10,000/night removed as likely data errors"})

    # Step 5: drop hotel rooms (different business model, not peer hosting)
    before = len(df)
    hotel_count = (df["room_type"] == "Hotel room").sum()
    df = df[df["room_type"] != "Hotel room"]
    dropped = before - len(df)
    steps.append({"step": "drop_hotel_rooms", "dropped": dropped, "remaining": len(df),
                   "note": "Hotel rooms excluded — they operate under a different business model"})

    # Step 6: flag active vs inactive (has review in last 12 months)
    df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce")
    cutoff = pd.Timestamp("2025-01-01")
    df["is_active"] = df["last_review"] >= cutoff
    active = df["is_active"].sum()
    steps.append({"step": "flag_active", "active": int(active), "inactive": int(len(df) - active),
                   "note": f"Active = reviewed since {cutoff.date()}. Both kept; flag for filtering."})

    final = len(df)
    steps.append({"step": "final", "rows": final,
                   "note": f"{initial:,} → {final:,} ({initial - final:,} removed, {(initial-final)/initial*100:.1f}%)"})

    log[city] = {"listings": steps}
    return df


def clean_reviews(city: str, listing_ids: set, log: dict) -> pd.DataFrame:
    path = DATA_DIR / city / "reviews.csv.gz"
    df = pd.read_csv(path, compression="gzip", low_memory=False)
    steps = []
    initial = len(df)
    steps.append({"step": "load_raw", "rows": initial})

    # Step 1: select columns
    available = [c for c in REVIEW_COLS_KEEP if c in df.columns]
    df = df[available].copy()

    # Step 1.5: coerce listing_id to numeric (CSV parsing issues with <br/> in comments
    # can cause row misalignment, producing non-numeric listing_ids)
    before = len(df)
    df["listing_id"] = pd.to_numeric(df["listing_id"], errors="coerce")
    bad_ids = df["listing_id"].isna().sum()
    df = df.dropna(subset=["listing_id"])
    df["listing_id"] = df["listing_id"].astype(int)
    steps.append({"step": "fix_listing_id_type", "dropped": int(bad_ids), "remaining": len(df),
                   "note": f"Dropped {bad_ids:,} rows with non-numeric listing_id (CSV parse errors from <br/> in comments)"})

    # Step 2: drop reviews for listings not in cleaned listing set
    before = len(df)
    df = df[df["listing_id"].isin(listing_ids)]
    dropped = before - len(df)
    steps.append({"step": "filter_to_clean_listings", "dropped": dropped, "remaining": len(df),
                   "note": "Keep only reviews for listings that survived cleaning"})

    # Step 3: drop null/empty comments
    before = len(df)
    df = df.dropna(subset=["comments"])
    df = df[df["comments"].str.strip().str.len() > 0]
    dropped = before - len(df)
    steps.append({"step": "drop_empty_comments", "dropped": dropped, "remaining": len(df)})

    # Step 4: parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    null_dates = df["date"].isna().sum()
    df = df.dropna(subset=["date"])
    steps.append({"step": "parse_date", "dropped_null_date": int(null_dates), "remaining": len(df),
                   "date_range": f"{df['date'].min().date()} to {df['date'].max().date()}"})

    # Step 5: detect language (keep only English for NLP)
    # Simple heuristic: if >50% of characters are ASCII letters, treat as English
    def is_likely_english(text):
        if not isinstance(text, str) or len(text) == 0:
            return False
        ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
        total_letters = sum(1 for c in text if c.isalpha())
        if total_letters == 0:
            return False
        return ascii_letters / total_letters > 0.5

    before = len(df)
    df["is_english"] = df["comments"].apply(is_likely_english)
    non_english = (~df["is_english"]).sum()
    df = df[df["is_english"]].drop(columns=["is_english"])
    dropped = before - len(df)
    steps.append({"step": "filter_english_only", "dropped": dropped, "remaining": len(df),
                   "note": "Non-English reviews excluded for sentiment analysis consistency"})

    final = len(df)
    steps.append({"step": "final", "rows": final,
                   "note": f"{initial:,} → {final:,} ({initial - final:,} removed, {(initial-final)/initial*100:.1f}%)"})

    log[city]["reviews"] = steps
    return df


def main():
    report = {}

    for city in CITIES:
        print(f"\n{'='*50}")
        print(f"Cleaning {CITIES[city]['name']} ({CITIES[city]['snapshot']})")
        print(f"{'='*50}")

        # Clean listings
        listings_df = clean_listings(city, report)
        listing_ids = set(listings_df["id"])

        # Clean reviews
        reviews_df = clean_reviews(city, listing_ids, report)

        # Save
        out_listings = DATA_DIR / city / "listings_clean.csv.gz"
        out_reviews = DATA_DIR / city / "reviews_clean.csv.gz"
        listings_df.to_csv(out_listings, index=False, compression="gzip")
        reviews_df.to_csv(out_reviews, index=False, compression="gzip")

        # Print summary
        for stage in ["listings", "reviews"]:
            print(f"\n  {stage}:")
            for step in report[city][stage]:
                print(f"    {step['step']}: {step.get('note', step)}")

    # Save full report
    report_path = DATA_DIR / "cleaning_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nCleaning report saved to {report_path}")


if __name__ == "__main__":
    main()
