"""
04_fetch_by_class.py
---------------------
Query city-wide land/improvement sums and parcel-pattern counts broken out
by PropertyClass (top level) and by PropertyUse within the Residential class.

Outputs:
  outputs/tables/by_class_totals.csv    — aggregate sums for 2025 and 2026
  outputs/tables/by_class_patterns.csv  — pattern counts per class / use
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

# Only current (2026) and previous (2025) fields — Previous2 (2024) is
# less relevant for the class breakdown.
SUM_FIELDS = [
    "PreviousLand", "PreviousImpr", "PreviousTotal",
    "CurrentLand",  "CurrentImpr",  "CurrentTotal",
]

# Pattern WHERE clauses (current vs previous only)
IMPR_DOWN_LAND_UP = "(CurrentImpr < PreviousImpr) AND (CurrentLand > PreviousLand)"
EXACT_FLAT        = f"({IMPR_DOWN_LAND_UP}) AND (CurrentTotal = PreviousTotal)"

# Exempt and Manufacturing parcels have CurrentLand = 0 (fully tax-exempt
# in 2026), so YoY comparisons are meaningless for them. Exclude from totals.
MAJOR_CLASSES = ["Residential", "Commercial", "Agriculture"]

# Residential PropertyUse groups to report
RES_USES = [
    "Single family",
    "Condominium",
    "2 Unit",
    "3 Unit",
    "Vacant",
]


def build_stats_payload(fields: list[str]) -> list[dict]:
    return [
        {"statisticType": "sum", "onStatisticField": f, "outStatisticFieldName": f"sum_{f}"}
        for f in fields
    ]


def fetch_grouped_sums(group_field: str, where: str = "1=1") -> pd.DataFrame:
    resp = requests.get(
        f"{SERVICE_URL}/query",
        params={
            "where": where,
            "outStatistics": json.dumps(build_stats_payload(SUM_FIELDS)),
            "groupByFieldsForStatistics": group_field,
            "f": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    rows = []
    for feat in data["features"]:
        a = feat["attributes"]
        row = {group_field: a[group_field]}
        for f in SUM_FIELDS:
            row[f] = a[f"sum_{f}"]
        rows.append(row)
    return pd.DataFrame(rows)


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


def main() -> None:
    # -----------------------------------------------------------------------
    # 1. Aggregate sums by PropertyClass
    # -----------------------------------------------------------------------
    print("Fetching aggregate sums by PropertyClass...")
    df_class = fetch_grouped_sums("PropertyClass")

    # Lump all AG subclasses into "Agriculture"
    ag_mask = df_class["PropertyClass"].str.startswith("AG")
    if ag_mask.any():
        ag_row = df_class[ag_mask][SUM_FIELDS].sum()
        ag_row["PropertyClass"] = "Agriculture"
        df_class = pd.concat(
            [df_class[~ag_mask], pd.DataFrame([ag_row])],
            ignore_index=True,
        )

    # Keep only taxable classes with meaningful Current values
    keep = MAJOR_CLASSES
    df_class = df_class[df_class["PropertyClass"].isin(keep)].copy()
    df_class = df_class.set_index("PropertyClass").reindex(keep).reset_index()

    # Derived columns
    for prefix_curr, prefix_prev in [("Current", "Previous")]:
        for comp in ["Land", "Impr", "Total"]:
            curr_col = f"{prefix_curr}{comp}"
            prev_col = f"{prefix_prev}{comp}"
            df_class[f"yoy_{comp.lower()}"] = (
                (df_class[curr_col] - df_class[prev_col]) / df_class[prev_col] * 100
            )

    # -----------------------------------------------------------------------
    # 2. Aggregate sums by PropertyUse within Residential
    # -----------------------------------------------------------------------
    print("Fetching aggregate sums by PropertyUse (Residential only)...")
    df_use = fetch_grouped_sums(
        "PropertyUse", where="PropertyClass = 'Residential'"
    )
    df_use = df_use[df_use["PropertyUse"].isin(RES_USES)].copy()
    df_use = df_use.set_index("PropertyUse").reindex(RES_USES).reset_index()

    for comp in ["Land", "Impr", "Total"]:
        df_use[f"yoy_{comp.lower()}"] = (
            (df_use[f"Current{comp}"] - df_use[f"Previous{comp}"])
            / df_use[f"Previous{comp}"] * 100
        )

    # -----------------------------------------------------------------------
    # 3. Pattern counts by PropertyClass
    # -----------------------------------------------------------------------
    print("Fetching pattern counts by PropertyClass...")
    pattern_rows = []
    for cls in MAJOR_CLASSES:
        if cls == "Agriculture":
            cls_where = "PropertyClass LIKE 'AG%'"
        else:
            cls_where = f"PropertyClass = '{cls}'"
        n_both  = count_where(f"({cls_where}) AND ({IMPR_DOWN_LAND_UP})")
        n_exact = count_where(f"({cls_where}) AND ({EXACT_FLAT})")
        n_total = count_where(cls_where)
        print(f"  {cls}: both={n_both:,} exact={n_exact:,} total={n_total:,}")
        pattern_rows.append({
            "group_type": "PropertyClass",
            "group_value": cls,
            "total_parcels": n_total,
            "impr_down_land_up": n_both,
            "exact_flat": n_exact,
        })

    # -----------------------------------------------------------------------
    # 4. Pattern counts by PropertyUse within Residential
    # -----------------------------------------------------------------------
    print("Fetching pattern counts by PropertyUse (Residential only)...")
    for use in RES_USES:
        use_where = f"PropertyClass = 'Residential' AND PropertyUse = '{use}'"
        n_both  = count_where(f"({use_where}) AND ({IMPR_DOWN_LAND_UP})")
        n_exact = count_where(f"({use_where}) AND ({EXACT_FLAT})")
        n_total = count_where(use_where)
        print(f"  {use}: both={n_both:,} exact={n_exact:,} total={n_total:,}")
        pattern_rows.append({
            "group_type": "PropertyUse",
            "group_value": use,
            "total_parcels": n_total,
            "impr_down_land_up": n_both,
            "exact_flat": n_exact,
        })

    df_patterns = pd.DataFrame(pattern_rows)

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    # Combine class + use totals into one file with a group_type column
    df_class.insert(0, "group_type", "PropertyClass")
    df_class = df_class.rename(columns={"PropertyClass": "group_value"})
    df_use.insert(0, "group_type", "PropertyUse")
    df_use = df_use.rename(columns={"PropertyUse": "group_value"})
    df_totals = pd.concat([df_class, df_use], ignore_index=True)

    totals_path = OUT_DIR / "by_class_totals.csv"
    patterns_path = OUT_DIR / "by_class_patterns.csv"

    df_totals.to_csv(totals_path, index=False)
    df_patterns.to_csv(patterns_path, index=False)

    print(f"\nSaved {totals_path}")
    print(f"Saved {patterns_path}")

    # Quick summary
    print("\n=== Land YoY % by class (2025->2026) ===")
    for _, r in df_class.iterrows():
        print(f"  {r['group_value']}: land {r['yoy_land']:+.1f}%  impr {r['yoy_impr']:+.1f}%  total {r['yoy_total']:+.1f}%")

    print("\n=== Pattern counts (impr down AND land up) ===")
    for _, r in df_patterns[df_patterns["group_type"] == "PropertyClass"].iterrows():
        pct = r["impr_down_land_up"] / r["total_parcels"] * 100 if r["total_parcels"] else 0
        print(f"  {r['group_value']}: {r['impr_down_land_up']:,} ({pct:.1f}%)  exact: {r['exact_flat']:,}")


if __name__ == "__main__":
    main()
