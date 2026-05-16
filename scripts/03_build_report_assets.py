"""
03_build_report_assets.py
--------------------------
Read the CSVs produced by scripts 01, 02, and 04, then write
outputs/tables/headlines.tex — a file of \newcommand macros consumed by
paper/Report.tex so numbers in the report are always in sync with the data.

Macro naming: all letters only (LaTeX command names cannot contain digits).
  Years: TwentyFour / TwentyFive / TwentySix
  YoY periods: Prev (2024->2025) / Curr (2025->2026)
  Examples: ordinals One / Two / Three, years Prev / Curr
  Classes: Res / Comm / Ag (PropertyClass); SF / Condo / TwoUnit / ThreeUnit / Vac (PropertyUse)
"""

import pathlib
import pandas as pd

IN_DIR  = pathlib.Path(__file__).parent.parent / "outputs" / "tables"
OUT_DIR = IN_DIR

HEADLINES_PATH = OUT_DIR / "headlines.tex"


def fmt_billions(v: float) -> str:
    return f"\\${v/1e9:.2f}\\,B"


def fmt_pct(v: float) -> str:
    if pd.isna(v):
        return "---"
    prefix = "+" if v > 0 else ""
    return f"{prefix}{v:.1f}\\%"


def fmt_dollars(v: float) -> str:
    return f"\\${v:,.0f}"


def fmt_count(v: int) -> str:
    return f"{v:,}"


ORDINALS = ["One", "Two", "Three"]


def main() -> None:
    # -----------------------------------------------------------------------
    # City-wide totals
    # -----------------------------------------------------------------------
    totals = pd.read_csv(IN_DIR / "city_wide_totals.csv", index_col="assessment_year", dtype={"assessment_year": str})

    macros: list[tuple[str, str]] = []

    year_map = {
        "2024": "TwentyFour",
        "2025": "TwentyFive",
        "2026": "TwentySix",
    }
    for year, suffix in year_map.items():
        row = totals.loc[year]
        macros += [
            (f"Land{suffix}",    fmt_billions(row["land"])),
            (f"Impr{suffix}",    fmt_billions(row["improvements"])),
            (f"Total{suffix}",   fmt_billions(row["total"])),
            (f"LandPct{suffix}", f"{row['land_pct_of_total']:.1f}\\%"),
        ]

    macros += [
        ("LandYoYCurr",  fmt_pct(totals.loc["2026"]["land_yoy_pct"])),
        ("ImprYoYCurr",  fmt_pct(totals.loc["2026"]["impr_yoy_pct"])),
        ("TotalYoYCurr", fmt_pct(totals.loc["2026"]["total_yoy_pct"])),
        ("LandYoYPrev",  fmt_pct(totals.loc["2025"]["land_yoy_pct"])),
        ("ImprYoYPrev",  fmt_pct(totals.loc["2025"]["impr_yoy_pct"])),
        ("TotalYoYPrev", fmt_pct(totals.loc["2025"]["total_yoy_pct"])),
    ]

    # -----------------------------------------------------------------------
    # Parcel counts
    # -----------------------------------------------------------------------
    counts = pd.read_csv(IN_DIR / "parcel_counts.csv")

    def get_count(period: str, criterion: str) -> int:
        mask = (counts["period"] == period) & (counts["criterion"] == criterion)
        rows = counts[mask]
        if rows.empty:
            raise KeyError(f"No row for period={period!r}, criterion={criterion!r}")
        return int(rows.iloc[0]["count"])

    curr_both      = get_count("2025-2026", "impr_down_and_land_up")
    curr_near_flat = get_count("2025-2026", "impr_down_land_up_near_flat")
    curr_exact     = get_count("2025-2026", "impr_down_land_up_exact_flat")
    prev_both      = get_count("2024-2025", "impr_down_and_land_up")
    prev_exact     = get_count("2024-2025", "impr_down_land_up_exact_flat")

    multiplier = round(curr_both / prev_both) if prev_both else 0

    macros += [
        ("CurrBoth",      fmt_count(curr_both)),
        ("CurrNearFlat",  fmt_count(curr_near_flat)),
        ("CurrExact",     fmt_count(curr_exact)),
        ("PrevBoth",      fmt_count(prev_both)),
        ("PrevExact",     fmt_count(prev_exact)),
        ("BothMultiplier", f"{multiplier:,}\\times"),
        ("CurrBothPct",    f"{curr_both / 82249 * 100:.1f}\\%"),
    ]

    # -----------------------------------------------------------------------
    # Example parcels — first three rows
    # -----------------------------------------------------------------------
    ex = pd.read_csv(IN_DIR / "example_parcels.csv")
    for i, (_, row) in enumerate(ex.head(3).iterrows()):
        ord_name = ORDINALS[i]
        macros += [
            (f"ExAddr{ord_name}",       row["address"].replace("&", "\\&")),
            (f"ExLandPrev{ord_name}",   fmt_dollars(row["land_2025"])),
            (f"ExImprPrev{ord_name}",   fmt_dollars(row["impr_2025"])),
            (f"ExTotalPrev{ord_name}",  fmt_dollars(row["total_2025"])),
            (f"ExLandCurr{ord_name}",   fmt_dollars(row["land_2026"])),
            (f"ExImprCurr{ord_name}",   fmt_dollars(row["impr_2026"])),
            (f"ExTotalCurr{ord_name}",  fmt_dollars(row["total_2026"])),
            (f"ExShift{ord_name}",      fmt_dollars(abs(row["land_shift"]))),
        ]

    # -----------------------------------------------------------------------
    # By-class totals and patterns (script 04 outputs)
    # -----------------------------------------------------------------------
    cls_totals   = pd.read_csv(IN_DIR / "by_class_totals.csv")
    cls_patterns = pd.read_csv(IN_DIR / "by_class_patterns.csv")

    def get_cls(df: pd.DataFrame, gtype: str, gval: str) -> pd.Series:
        mask = (df["group_type"] == gtype) & (df["group_value"] == gval)
        return df[mask].iloc[0]

    def get_pat(gtype: str, gval: str) -> pd.Series:
        return get_cls(cls_patterns, gtype, gval)

    # PropertyClass macros
    class_map = {
        "Residential": "Res",
        "Commercial":  "Comm",
        "Agriculture": "Ag",
    }
    for cls_name, abbr in class_map.items():
        row = get_cls(cls_totals, "PropertyClass", cls_name)
        pat = get_pat("PropertyClass", cls_name)
        macros += [
            (f"Land{abbr}Prev",    fmt_billions(row["PreviousLand"])),
            (f"Impr{abbr}Prev",    fmt_billions(row["PreviousImpr"])),
            (f"Total{abbr}Prev",   fmt_billions(row["PreviousTotal"])),
            (f"Land{abbr}Curr",    fmt_billions(row["CurrentLand"])),
            (f"Impr{abbr}Curr",    fmt_billions(row["CurrentImpr"])),
            (f"Total{abbr}Curr",   fmt_billions(row["CurrentTotal"])),
            (f"LandYoY{abbr}",     fmt_pct(row["yoy_land"])),
            (f"ImprYoY{abbr}",     fmt_pct(row["yoy_impr"])),
            (f"TotalYoY{abbr}",    fmt_pct(row["yoy_total"])),
            (f"Both{abbr}",        fmt_count(int(pat["impr_down_land_up"]))),
            (f"Exact{abbr}",       fmt_count(int(pat["exact_flat"]))),
            (f"Parcels{abbr}",     fmt_count(int(pat["total_parcels"]))),
            (f"BothPct{abbr}",     f"{pat['impr_down_land_up'] / pat['total_parcels'] * 100:.1f}\\%"),
        ]

    # PropertyUse macros (Residential sub-types)
    use_map = {
        "Single family": "SF",
        "Condominium":   "Condo",
        "2 Unit":        "TwoUnit",
        "3 Unit":        "ThreeUnit",
        "Vacant":        "Vac",
    }
    for use_name, abbr in use_map.items():
        row = get_cls(cls_totals, "PropertyUse", use_name)
        pat = get_pat("PropertyUse", use_name)
        macros += [
            (f"LandYoY{abbr}",   fmt_pct(row["yoy_land"])),
            (f"ImprYoY{abbr}",   fmt_pct(row["yoy_impr"])),
            (f"TotalYoY{abbr}",  fmt_pct(row["yoy_total"])),
            (f"Both{abbr}",      fmt_count(int(pat["impr_down_land_up"]))),
            (f"Exact{abbr}",     fmt_count(int(pat["exact_flat"]))),
            (f"Parcels{abbr}",   fmt_count(int(pat["total_parcels"]))),
            (f"BothPct{abbr}",   f"{pat['impr_down_land_up'] / pat['total_parcels'] * 100:.1f}\\%"),
        ]

    # -----------------------------------------------------------------------
    # Write headlines.tex
    # -----------------------------------------------------------------------
    lines = [
        "% headlines.tex -- auto-generated by scripts/03_build_report_assets.py",
        "% Do not edit by hand.",
        "",
    ]
    for name, value in macros:
        lines.append(f"\\newcommand{{\\{name}}}{{{value}}}")

    HEADLINES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(macros)} macros to {HEADLINES_PATH}")


if __name__ == "__main__":
    main()
