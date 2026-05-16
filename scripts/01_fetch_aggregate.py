"""
01_fetch_aggregate.py
---------------------
Fetch city-wide sums of land and improvement values across three assessment
years from the City of Madison ArcGIS feature service.

Outputs: outputs/tables/city_wide_totals.csv
"""

import json
import pathlib
import requests
import pandas as pd

SERVICE_URL = (
    "https://maps.cityofmadison.com/arcgis/rest/services"
    "/Public/OPEN_DATA2/FeatureServer/0"
)

FIELDS = [
    "CurrentLand", "CurrentImpr", "CurrentTotal",
    "PreviousLand", "PreviousImpr", "PreviousTotal",
    "PreviousLand2", "PreviousImpr2", "PreviousTotal2",
]

OUT_DIR = pathlib.Path(__file__).parent.parent / "outputs" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_stats_payload(fields: list[str]) -> list[dict]:
    return [
        {
            "statisticType": "sum",
            "onStatisticField": f,
            "outStatisticFieldName": f"sum_{f}",
        }
        for f in fields
    ]


def fetch_sums() -> dict[str, float]:
    resp = requests.get(
        f"{SERVICE_URL}/query",
        params={
            "where": "1=1",
            "outStatistics": json.dumps(build_stats_payload(FIELDS)),
            "f": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    attrs = data["features"][0]["attributes"]
    return {f: attrs[f"sum_{f}"] for f in FIELDS}


def main() -> None:
    print("Fetching city-wide assessment sums from ArcGIS...")
    sums = fetch_sums()

    rows = []
    for year_label, land_key, impr_key, total_key in [
        ("2024", "PreviousLand2", "PreviousImpr2", "PreviousTotal2"),
        ("2025", "PreviousLand",  "PreviousImpr",  "PreviousTotal"),
        ("2026", "CurrentLand",   "CurrentImpr",   "CurrentTotal"),
    ]:
        rows.append({
            "assessment_year": year_label,
            "land":            sums[land_key],
            "improvements":    sums[impr_key],
            "total":           sums[total_key],
        })

    df = pd.DataFrame(rows).set_index("assessment_year")

    # Derived columns
    df["land_pct_of_total"] = df["land"] / df["total"] * 100
    df["land_yoy_pct"]      = df["land"].pct_change() * 100
    df["impr_yoy_pct"]      = df["improvements"].pct_change() * 100
    df["total_yoy_pct"]     = df["total"].pct_change() * 100

    out_path = OUT_DIR / "city_wide_totals.csv"
    df.to_csv(out_path)
    print(f"Saved {out_path}")

    # Print summary
    print("\nCity-wide totals ($ billions):")
    print(df[["land", "improvements", "total"]].map(lambda x: f"${x/1e9:.2f}B"))
    print("\nYear-over-year changes:")
    print(df[["land_yoy_pct", "impr_yoy_pct", "total_yoy_pct"]].map(
        lambda x: f"{x:+.1f}%" if pd.notna(x) else "—"
    ))


if __name__ == "__main__":
    main()
