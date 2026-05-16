# CLAUDE.md — Madison Assessment Reform Fact-Check

## Project Overview

Fact-check of a *Capital Times* letter to the editor (Ginny White, May 2026) claiming
Madison's City Assessor quietly restructured property assessments — raising land values
and lowering improvement values by equal amounts while holding each parcel's total flat.
Analysis uses the City of Madison's public ArcGIS feature service (no auth required).

## Running

```bash
# Always use miniconda python, never system python
C:/Users/druss/miniconda3/python.exe scripts/01_fetch_aggregate.py
C:/Users/druss/miniconda3/python.exe scripts/02_fetch_parcels.py
C:/Users/druss/miniconda3/python.exe scripts/03_build_report_assets.py

# Compile the report (from paper/ directory)
cd paper
pdflatex Report.tex && pdflatex Report.tex
```

## Data Source

Live ArcGIS feature service — no download or authentication needed:

```
https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA2/FeatureServer/0
```

Key fields per parcel:
- `CurrentLand` / `CurrentImpr` / `CurrentTotal`   — 2026 assessment
- `PreviousLand` / `PreviousImpr` / `PreviousTotal` — 2025 assessment
- `PreviousLand2` / `PreviousImpr2` / `PreviousTotal2` — 2024 assessment

"Current" confirmed as 2026 via AssessmentChangeDate timestamp (~April 2026).
"Previous" matches the May 2025 Property Tax Base Report total of ~$48.99B.

## Pipeline

| Script | Input | Output |
|--------|-------|--------|
| `01_fetch_aggregate.py` | ArcGIS REST API | `outputs/tables/city_wide_totals.csv` |
| `02_fetch_parcels.py` | ArcGIS REST API | `outputs/tables/parcel_counts.csv`, `outputs/tables/example_parcels.csv` |
| `03_build_report_assets.py` | outputs CSVs | `outputs/tables/headlines.tex` |
| `paper/Report.tex` | `outputs/tables/headlines.tex` | `paper/Report.pdf` |

## Key Findings (do not change without re-running pipeline)

- 3,336 parcels had improvements reduced and land raised by exactly equal amounts, total unchanged
- 32,696 parcels had improvements drop and land rise (any total change)
- Prior year (2024→2025): only 43/20 parcels showed these patterns
- City-wide land jumped +21.7% (2025→2026) vs +1.7% the prior year
- City-wide improvements rose just +2.1% (2025→2026) vs +10.2% the prior year

## Pitfalls

- **API pagination:** The feature service returns max 2,000 records per query when fetching
  features. Use `returnCountOnly=true` or `outStatistics` for aggregates — these have no
  row limit and return instantly.
- **Field name spaces:** Field names are camelCase with no spaces. A space in the URL
  (e.g., `Current Impr`) causes a 400 error. Always URL-encode the full query string.
- **Where clause encoding:** Operators `<`, `>`, `=` must be URL-encoded when passed as
  query parameters (`%3C`, `%3E`, `%3D`), or use `params=` in requests so it handles encoding.
- **outFields with specific names causes 400:** Passing a comma-separated list of field names
  in `outFields` fails with a 400 if any name is wrong. Use `outFields=*` when exploring,
  then auto-detect the address field name rather than hardcoding it.
- **LaTeX macro names must be all letters:** `\newcommand{\Land24}` silently treats `\Land`
  as the command and `24` as following text. Use spelled-out names: `\LandTwentyFour`,
  `\ExLandPrevOne`, etc. All macros in `headlines.tex` follow this convention.
- **pandas `applymap` removed in 2.1+:** Use `.map()` instead of `.applymap()` on DataFrames.
- **CSV index dtype:** `pd.read_csv(..., index_col="assessment_year")` reads year values as
  integers. Pass `dtype={"assessment_year": str}` to keep them as strings for `.loc["2026"]`
  lookups.
- **Windows console encoding:** Printing Unicode (arrows, ±) to a cp1252 terminal raises
  `UnicodeEncodeError`. Encode with `errors="replace"` for terminal output; CSVs are fine
  since they're written with explicit `encoding="utf-8"`.
