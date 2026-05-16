# Madison Assessment Reform — Fact-Check

Data verification of a May 2026 *Capital Times* letter to the editor claiming Madison's
City Assessor restructured property assessments by raising land values and lowering
improvement (building) values by equal amounts — a partial land value tax effect.

## Key Finding

**The mechanism the letter describes is real and documented in the public data.**

In the 2026 assessment cycle (assessed as of January 1, 2026):

- **3,336 parcels** had their improvement value reduced and land value raised by exactly equal
  and opposite amounts, leaving the total assessment unchanged to the dollar.
- **32,696 parcels** (39.8% of all taxable parcels) had improvements decrease while land increased.
- The prior year (2024→2025) showed just **43** such parcels — a 760× increase.

City-wide, land assessments jumped **+21.7%** while improvements rose only **+2.1%**,
reversing the prior year's pattern (land +1.7%, improvements +10.2%).

The letter's specific claim that the city-wide *total* was "kept the same" is incorrect
(overall assessments rose 6%), but accurately describes what happened to thousands of
individual parcels.

## Data Source

City of Madison ArcGIS feature service (public, no authentication):

```
https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA2/FeatureServer/0
```

Also cross-referenced against City Assessor annual Property Tax Base Reports (2024, 2025).

## Repository Structure

```
scripts/
    01_fetch_aggregate.py       Fetch city-wide land/impr sums across three years
    02_fetch_parcels.py         Fetch parcel-level pattern counts + example records
    03_build_report_assets.py   Generate outputs/tables/headlines.tex from CSVs
outputs/
    tables/
        city_wide_totals.csv    Raw aggregate sums from API
        parcel_counts.csv       Pattern match counts (current vs. prior year)
        example_parcels.csv     Sample parcels showing the exact shift
        headlines.tex           LaTeX macros consumed by paper/Report.tex
paper/
    Report.tex                  LaTeX source (compile twice with pdflatex)
    Report.pdf                  Compiled output
CLAUDE.md                       Developer/Claude context
requirements.txt                Python dependencies (requests, pandas)
```

## Reproducing the Analysis

```bash
# Install dependencies
C:/Users/druss/miniconda3/python.exe -m pip install -r requirements.txt

# Fetch data and build report assets (requires internet access)
C:/Users/druss/miniconda3/python.exe scripts/01_fetch_aggregate.py
C:/Users/druss/miniconda3/python.exe scripts/02_fetch_parcels.py
C:/Users/druss/miniconda3/python.exe scripts/03_build_report_assets.py

# Compile PDF
cd paper
pdflatex Report.tex && pdflatex Report.tex
```

## Sources

- [Capital Times LTE](https://captimes.com/opinion/letters-to-the-editor/letter-assessemnts-designed-to-build-at-any-cost/article_157aeab1-ac98-4eb2-948c-df694eb9630c.html) — Ginny White, May 2026
- [City of Madison Open Data — Tax Parcels](https://data-cityofmadison.opendata.arcgis.com/datasets/0338b0638e4749c395f8d38b39a5c466_0/explore)
- [2025 Property Tax Base Report (PDF)](https://www.cityofmadison.com/assessor/documents/PropTaxBaseReport2025.pdf)
- [2024 Property Tax Base Report (PDF)](https://www.cityofmadison.com/assessor/documents/PropTaxBaseReport2024.pdf)
