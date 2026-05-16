"""
02_fetch_parcels.py
-------------------
Query parcel-level pattern counts and example records from the City of Madison
ArcGIS feature service.

Pattern queries use returnCountOnly=true so no row-level data is downloaded.
Example records are fetched for the exact-shift pattern (impr down = land up,
total exactly flat).

Outputs:
  outputs/tables/parcel_counts.csv
  outputs/tables/example_parcels.csv
"""

import json
import pathlib
import requests
import pandas as pd

SERVICE_URL = (
    "https://maps.cityofmadison.com/arcgis/rest/services"
    "/Public/OPEN_DATA2/FeatureServer/0"
)

OUT_DIR = pathlib.Path(__file__).parent.parent / "outputs" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def count_where(where: str) -> int:
    resp = requests.get(
        f"{SERVICE_URL}/query",
        params={"where": where, "returnCountOnly": "true", "f": "json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    return data["count"]


_ADDRESS_CANDIDATES = [
    "situs_address", "SITUS_ADDRESS", "SiteAddress", "Address",
    "PROP_ADDR", "PropertyAddress", "FullAddress",
]


def _detect_address_field(sample_attr: dict) -> str:
    for f in _ADDRESS_CANDIDATES:
        if f in sample_attr:
            return f
    # fall back to any key with "addr" or "address" in its name
    for k in sample_attr:
        if "addr" in k.lower() or "address" in k.lower():
            return k
    return ""


def fetch_examples(where: str, n: int = 3) -> list[dict]:
    resp = requests.get(
        f"{SERVICE_URL}/query",
        params={
            "where": where,
            "outFields": "*",
            "resultRecordCount": n,
            "f": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    attrs_list = [feat["attributes"] for feat in data["features"]]
    addr_field = _detect_address_field(attrs_list[0]) if attrs_list else ""
    for a in attrs_list:
        a["_address"] = a.get(addr_field, "") if addr_field else ""
    return attrs_list


# ---------------------------------------------------------------------------
# WHERE clauses for each pattern condition
# Current vs Previous (2025→2026)
# ---------------------------------------------------------------------------

CURR_IMPR_DOWN = "CurrentImpr < PreviousImpr"
CURR_LAND_UP   = "CurrentLand > PreviousLand"
CURR_BOTH      = f"({CURR_IMPR_DOWN}) AND ({CURR_LAND_UP})"
CURR_NEAR_FLAT = (
    f"({CURR_BOTH}) AND "
    "(CurrentTotal >= PreviousTotal * 0.97) AND "
    "(CurrentTotal <= PreviousTotal * 1.03)"
)
CURR_EXACT_FLAT = (
    f"({CURR_BOTH}) AND "
    "(CurrentTotal = PreviousTotal)"
)

# Previous vs Previous2 (2024→2025)
PREV_IMPR_DOWN  = "PreviousImpr < PreviousImpr2"
PREV_LAND_UP    = "PreviousLand > PreviousLand2"
PREV_BOTH       = f"({PREV_IMPR_DOWN}) AND ({PREV_LAND_UP})"
PREV_EXACT_FLAT = (
    f"({PREV_BOTH}) AND "
    "(PreviousTotal = PreviousTotal2)"
)

TOTAL_PARCELS = 82249  # known total taxable parcels


def main() -> None:
    print("Querying parcel-level pattern counts from ArcGIS...")

    rows = []

    criteria = [
        ("impr_down_only",
         CURR_IMPR_DOWN, "2025-2026"),
        ("impr_down_and_land_up",
         CURR_BOTH, "2025-2026"),
        ("impr_down_land_up_near_flat",
         CURR_NEAR_FLAT, "2025-2026"),
        ("impr_down_land_up_exact_flat",
         CURR_EXACT_FLAT, "2025-2026"),
        ("impr_down_and_land_up",
         PREV_BOTH, "2024-2025"),
        ("impr_down_land_up_exact_flat",
         PREV_EXACT_FLAT, "2024-2025"),
    ]

    for criterion, where, period in criteria:
        n = count_where(where)
        print(f"  {period} | {criterion}: {n:,}")
        rows.append({"period": period, "criterion": criterion, "count": n})

    df_counts = pd.DataFrame(rows)
    counts_path = OUT_DIR / "parcel_counts.csv"
    df_counts.to_csv(counts_path, index=False)
    print(f"\nSaved {counts_path}")

    # -----------------------------------------------------------------------
    # Example parcels — exact-shift pattern in current year
    # -----------------------------------------------------------------------
    print("\nFetching example parcels (exact shift, current year)...")
    examples = fetch_examples(CURR_EXACT_FLAT, n=5)

    ex_rows = []
    for attr in examples:
        addr = attr.get("_address") or "Unknown"
        ex_rows.append({
            "address": addr,
            "land_2024":  attr["PreviousLand2"],
            "impr_2024":  attr["PreviousImpr2"],
            "total_2024": attr["PreviousTotal2"],
            "land_2025":  attr["PreviousLand"],
            "impr_2025":  attr["PreviousImpr"],
            "total_2025": attr["PreviousTotal"],
            "land_2026":  attr["CurrentLand"],
            "impr_2026":  attr["CurrentImpr"],
            "total_2026": attr["CurrentTotal"],
            "land_shift":  attr["CurrentLand"]  - attr["PreviousLand"],
            "impr_shift":  attr["CurrentImpr"]  - attr["PreviousImpr"],
            "total_shift": attr["CurrentTotal"] - attr["PreviousTotal"],
        })

    df_ex = pd.DataFrame(ex_rows)
    ex_path = OUT_DIR / "example_parcels.csv"
    df_ex.to_csv(ex_path, index=False)
    print(f"Saved {ex_path}")

    print("\nExample parcels:")
    for _, r in df_ex.iterrows():
        line = (
            f"  {r['address']}: "
            f"land ${r['land_2025']:,.0f}->${r['land_2026']:,.0f} "
            f"({r['land_shift']:+,.0f}), "
            f"impr ${r['impr_2025']:,.0f}->${r['impr_2026']:,.0f} "
            f"({r['impr_shift']:+,.0f}), "
            f"total ${r['total_2025']:,.0f}->${r['total_2026']:,.0f} "
            f"({r['total_shift']:+,.0f})"
        )
        print(line.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    main()
