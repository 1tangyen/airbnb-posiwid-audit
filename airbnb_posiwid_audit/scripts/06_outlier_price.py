"""
06_outlier_price.py — Price outlier detection per neighbourhood

Identifies listings with anomalous prices within their neighbourhood context.
Purpose: validate price parsing in 02_clean.py + discover pricing anomalies.

Input:  data/{city}/listings_clean.csv.gz
Output: output/outlier_price.json
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "output"

CITIES = {
    "nyc": "New York City",
    "boston": "Boston",
    "chicago": "Chicago",
}

# Outlier detection parameters
MIN_NEIGHBOURHOOD_SIZE = 10  # minimum listings per neighbourhood for IQR to be meaningful
IQR_MULTIPLIER = 1.5  # mild outlier
EXTREME_IQR_MULTIPLIER = 3.0  # extreme outlier
GLOBAL_FLOOR = 10  # absolute minimum (already filtered in cleaning, but double-check)
GLOBAL_CEILING = 10000  # absolute maximum (already filtered in cleaning)


def load_listings(city: str) -> pd.DataFrame:
    listings = pd.read_csv(DATA_DIR / city / "listings_clean.csv.gz", compression="gzip", low_memory=False)
    listings["id"] = pd.to_numeric(listings["id"], errors="coerce").astype("Int64")
    return listings


def detect_price_outliers(listings: pd.DataFrame, city: str) -> dict:
    valid = listings[listings["price"].notna()].copy()

    # Global distribution
    global_stats = {
        "total_listings": int(len(valid)),
        "mean": round(float(valid["price"].mean()), 2),
        "median": round(float(valid["price"].median()), 2),
        "std": round(float(valid["price"].std()), 2),
        "min": round(float(valid["price"].min()), 2),
        "max": round(float(valid["price"].max()), 2),
        "q1": round(float(valid["price"].quantile(0.25)), 2),
        "q3": round(float(valid["price"].quantile(0.75)), 2),
        "p95": round(float(valid["price"].quantile(0.95)), 2),
        "p99": round(float(valid["price"].quantile(0.99)), 2),
    }

    # Per-neighbourhood outlier detection
    neighbourhood_results = []
    all_outliers = []

    for hood, group in valid.groupby("neighbourhood_cleansed"):
        if len(group) < MIN_NEIGHBOURHOOD_SIZE:
            continue

        prices = group["price"]
        q1 = prices.quantile(0.25)
        q3 = prices.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            # All prices identical — skip IQR method, use global z-score instead
            continue

        mild_upper = q3 + IQR_MULTIPLIER * iqr
        mild_lower = q1 - IQR_MULTIPLIER * iqr
        extreme_upper = q3 + EXTREME_IQR_MULTIPLIER * iqr
        extreme_lower = q1 - EXTREME_IQR_MULTIPLIER * iqr

        mild_high = group[prices > mild_upper]
        mild_low = group[prices < mild_lower]
        extreme_high = group[prices > extreme_upper]
        extreme_low = group[prices < extreme_lower]

        hood_result = {
            "neighbourhood": hood,
            "n": int(len(group)),
            "median_price": round(float(prices.median()), 2),
            "q1": round(float(q1), 2),
            "q3": round(float(q3), 2),
            "iqr": round(float(iqr), 2),
            "mild_upper_threshold": round(float(mild_upper), 2),
            "extreme_upper_threshold": round(float(extreme_upper), 2),
            "mild_outliers_high": int(len(mild_high)),
            "mild_outliers_low": int(len(mild_low)),
            "extreme_outliers_high": int(len(extreme_high)),
            "extreme_outliers_low": int(len(extreme_low)),
        }
        neighbourhood_results.append(hood_result)

        # Collect extreme outliers for inspection
        for _, row in extreme_high.iterrows():
            all_outliers.append({
                "listing_id": int(row["id"]) if pd.notna(row["id"]) else None,
                "price": round(float(row["price"]), 2),
                "neighbourhood": hood,
                "hood_median": round(float(prices.median()), 2),
                "ratio_to_median": round(float(row["price"] / prices.median()), 1),
                "room_type": row.get("room_type", ""),
                "property_type": row.get("property_type", ""),
                "accommodates": int(row.get("accommodates", 0)) if pd.notna(row.get("accommodates")) else None,
                "host_listings": int(row.get("calculated_host_listings_count", 0)) if pd.notna(row.get("calculated_host_listings_count")) else None,
                "description_snippet": str(row.get("description", ""))[:150] if pd.notna(row.get("description")) else "",
                "direction": "high",
            })
        for _, row in extreme_low.iterrows():
            all_outliers.append({
                "listing_id": int(row["id"]) if pd.notna(row["id"]) else None,
                "price": round(float(row["price"]), 2),
                "neighbourhood": hood,
                "hood_median": round(float(prices.median()), 2),
                "ratio_to_median": round(float(row["price"] / prices.median()), 2) if prices.median() > 0 else None,
                "room_type": row.get("room_type", ""),
                "property_type": row.get("property_type", ""),
                "accommodates": int(row.get("accommodates", 0)) if pd.notna(row.get("accommodates")) else None,
                "host_listings": int(row.get("calculated_host_listings_count", 0)) if pd.notna(row.get("calculated_host_listings_count")) else None,
                "description_snippet": str(row.get("description", ""))[:150] if pd.notna(row.get("description")) else "",
                "direction": "low",
            })

    # Sort neighbourhood results by outlier count
    neighbourhood_results.sort(key=lambda x: x["extreme_outliers_high"], reverse=True)

    # Sort all outliers by deviation from median
    all_outliers.sort(key=lambda x: x.get("ratio_to_median") or 0, reverse=True)

    # Summary statistics
    total_extreme = sum(h["extreme_outliers_high"] + h["extreme_outliers_low"] for h in neighbourhood_results)
    total_mild = sum(h["mild_outliers_high"] + h["mild_outliers_low"] for h in neighbourhood_results)

    summary = {
        "total_mild_outliers": total_mild,
        "total_mild_pct": round(total_mild / len(valid) * 100, 2) if len(valid) > 0 else 0,
        "total_extreme_outliers": total_extreme,
        "total_extreme_pct": round(total_extreme / len(valid) * 100, 2) if len(valid) > 0 else 0,
        "neighbourhoods_analyzed": len(neighbourhood_results),
    }

    # Room type breakdown of extreme outliers
    outlier_df = pd.DataFrame(all_outliers) if all_outliers else pd.DataFrame()
    by_room_type = {}
    if len(outlier_df) > 0 and "room_type" in outlier_df.columns:
        for rt, group in outlier_df.groupby("room_type"):
            by_room_type[rt] = {
                "count": int(len(group)),
                "mean_ratio_to_median": round(float(group["ratio_to_median"].mean()), 1) if group["ratio_to_median"].notna().any() else None,
            }

    # Data quality validation: check if extreme outliers have reasonable descriptions
    quality_check = {
        "high_price_with_short_description": 0,
        "high_price_with_no_description": 0,
        "suspicious_count": 0,
    }
    for o in all_outliers[:50]:
        if o["direction"] == "high":
            desc = o.get("description_snippet", "")
            if not desc or len(desc) < 10:
                quality_check["high_price_with_no_description"] += 1
                quality_check["suspicious_count"] += 1
            elif len(desc) < 50:
                quality_check["high_price_with_short_description"] += 1

    return {
        "city": city,
        "global_stats": global_stats,
        "summary": summary,
        "top_outliers": all_outliers[:30],
        "by_neighbourhood": neighbourhood_results[:20],
        "by_room_type": by_room_type,
        "quality_check": quality_check,
    }


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    all_results = {}

    for city, city_name in CITIES.items():
        print(f"\n{'='*60}")
        print(f"  Price Outlier Detection — {city_name}")
        print(f"{'='*60}")

        listings = load_listings(city)
        print(f"  Loaded {len(listings):,} listings")

        results = detect_price_outliers(listings, city)

        print(f"  Global: median ${results['global_stats']['median']}, P99 ${results['global_stats']['p99']}")
        print(f"  Neighbourhoods analyzed: {results['summary']['neighbourhoods_analyzed']}")
        print(f"  Mild outliers: {results['summary']['total_mild_outliers']} ({results['summary']['total_mild_pct']:.1f}%)")
        print(f"  Extreme outliers: {results['summary']['total_extreme_outliers']} ({results['summary']['total_extreme_pct']:.1f}%)")
        if results["top_outliers"]:
            top = results["top_outliers"][0]
            print(f"  Most extreme: listing {top['listing_id']} — ${top['price']} in {top['neighbourhood']} (median ${top['hood_median']}, {top['ratio_to_median']}x)")
        print(f"  Quality check — suspicious (no/short desc): {results['quality_check']['suspicious_count']}")

        all_results[city] = results

    output_path = OUTPUT_DIR / "outlier_price.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n✓ Results saved to {output_path}")


if __name__ == "__main__":
    main()
