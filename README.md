# FFIEC 031 Call Report Dashboard

Interactive browser dashboard over the FFIEC **Call Report** (FFIEC 031/041/051) filings
for all U.S. commercial banks. Covers ~7,500 banks quarterly from 1993 through the most
recent reporting period (201 quarters through 2026-Q1).

**Live site:** https://austinfahrenkopf.github.io/FFIEC_Call/

Data source: free public filings from the FFIEC Central Data Repository (CDR).
No subscription required to rebuild.

---

## What it is

A single-page application that runs entirely in the browser. Data is stored as a Parquet
file served from this repo; all SQL queries execute client-side via **DuckDB-WASM** (no
server). The dashboard lets you:

- Browse all ~1,400 Call Report line items organized by schedule (RC, RI, RC-B, RC-C, RC-R, ...)
- Chart any measure for any bank or aggregate (ALL, size buckets, bank type)
- Compare entities side-by-side, build custom peer groups, export to CSV/Excel
- View KPI tiles (QoQ %, YoY %, total-period delta) and a quarterly data table
- Build custom ratio formulas from any two Call Report codes

---

## Repo layout

```
/                                   GitHub Pages root
├── index.html                      Redirect to app/index.html
├── .nojekyll                       Tells GitHub Pages not to run Jekyll
├── README.md                       This file
├── README_DEPLOY.md                Local deployment guide (SharePoint/OneDrive)
├── Open Dashboard.bat              One-click local launcher (double-click to open)
└── app/                            Dashboard application (served as the live site)
    ├── index.html                  Dashboard (self-contained HTML + embedded JS + CSS)
    ├── ffiec_call.parquet          Call Report panel — all banks, all quarters (~62 MB)
    ├── ffiec_call_hierarchy.json   Schedule/line-item tree (curated from the form PDF)
    ├── serve.ps1                   Local PowerShell server (supports HTTP Range requests)
    └── .nojekyll
└── reproduce/                      Full reproduction kit — everything to rebuild from scratch
    ├── cdr_download_031.py         Step 1: download quarterly CDR bulk ZIPs from FFIEC
    ├── cdr_parse_call.py           Step 2: parse ZIPs -> raw CSV files
    ├── build_segments_call.py      Step 3: build per-schedule segment parquets
    ├── enrich_call.py              Step 4: enrich with RSSD metadata -> ffiec_call_segments.parquet
    ├── build_hierarchy.py          Step 5: parse PDF + overrides -> ffiec_call_hierarchy.json
    ├── make_site_call.py           Step 6: build dashboard app/ from panel + hierarchy
    ├── validate_build_call.py      Step 7: gate check (golden cell + completeness validation)
    ├── _completeness_gate.py       Step 7b: bidirectional completeness gate (shared with Y-9C/002)
    ├── _qa_final.py                Step 8: 23-point QA smoke test across all three dashboards
    ├── FINALIZE.ps1                One-shot rebuild + QA for all three dashboards
    ├── ffiec_call_hierarchy.json   Canonical curated hierarchy (hand-patched; do not overwrite)
    ├── ffiec_call_hierarchy_overrides.json  Force-rows and caption fixes applied post-parse
    ├── ffiec_call_completeness_exclusions.json  Known-absent codes excluded from the gate
    ├── ffiec_call_dictionary.csv   MDRM data dictionary
    ├── requirements.txt            Python dependencies
    ├── RUNBOOK.md                  Step-by-step rebuild instructions
    ├── CONTEXT.md                  Design decisions and methodology for future editors
    └── REPRODUCE_VERIFIED.md       Clean-room rebuild verification record
```

---

## Dependencies (one-time setup)

```powershell
pip install -r reproduce/requirements.txt
playwright install chrome
```

Requires **Python 3.10+**. DuckDB is NOT needed server-side — it runs as DuckDB-WASM in
the browser. Playwright is needed only for the CDR download step (FFIEC endpoints require
a real browser).

---

## Full pipeline: rebuild from scratch

Raw data is NOT committed to this repo (the full CDR source is ~15 GB of ZIPs).
To rebuild completely:

### Step 1 — Download raw data  *(skip if you already have the CDR ZIPs)*

```powershell
cd "FFIEC 031"
python cdr_download_031.py
```

Downloads quarterly bulk ZIPs from the FFIEC CDR into `cdr_zips/`. Requires Playwright
(real Chrome) because FFIEC endpoints are Akamai-guarded.

### Step 2 — Build the panel

```powershell
python cdr_parse_call.py
python build_segments_call.py
python enrich_call.py
```

Outputs `ffiec_call_segments.parquet` (the enriched source panel). Not committed to this
repo due to size; regenerate from the CDR ZIPs.

### Step 3 — Build the hierarchy  *(run when overrides change)*

```powershell
python build_hierarchy.py
```

Reads the FFIEC 031 blank form PDF, extracts the schedule/line-item structure, and applies
`ffiec_call_hierarchy_overrides.json` (force-rows, caption fixes). Outputs
`ffiec_call_hierarchy.json`.

**Note:** `ffiec_call_hierarchy.json` in `reproduce/` is the canonical curated artifact.
Do not overwrite it from a bare `build_hierarchy.py` run unless you intend to re-apply
all patches.

### Step 4 — Build and validate the dashboard

```powershell
python make_site_call.py               # full build -> app/ (parquet + index.html)
python validate_build_call.py          # must exit 0 and print "ALL CHECKS PASSED"
```

For a quick HTML-only rebuild (parquet unchanged):
```powershell
python make_site_call.py --html-only
```

### Step 5 — One-shot rebuild (after initial setup)

```powershell
# From the "External Bank Data\" project root:
.\FINALIZE.ps1
```

Runs Y-9C + 002 + Call hierarchy → validate → html-only rebuild → 23-point QA.
Prints `FINALIZE COMPLETE - ALL PASSED` on success. Takes ~3 minutes.

### Step 6 — Serve locally

```powershell
cd app
powershell -NoProfile -ExecutionPolicy Bypass -File serve.ps1 -Port 8001
# or: cd site_call ; python -m http.server 8001
```

---

## Typical edit-rebuild loop

For curating a line item or override:
```
edit ffiec_call_hierarchy_overrides.json
  -> python build_hierarchy.py
  -> python validate_build_call.py
  -> python make_site_call.py --html-only
  -> reload http://localhost:8001
```

For a code fix in `make_site_call.py`:
```
edit make_site_call.py
  -> python make_site_call.py --html-only
  -> reload browser
```

---

## GitHub Pages deployment

Settings -> Pages -> Source = Deploy from branch -> `main` / `(root)`.

The root `index.html` redirects to `app/index.html`. The live site is at:
`https://austinfahrenkopf.github.io/FFIEC_Call/`

**Size note:** `ffiec_call.parquet` (~62 MB) is above GitHub's 50 MB advisory threshold
but below the 100 MB hard limit. The push succeeds with a warning.

---

## Golden validation cell

`validate_build_call.py` asserts a known value:

> **JPMorgan Chase (RSSD 852218), RCFD2170 @ 2026-03-31 = 4,016,571,000 (thousands)**

`_qa_final.py` also asserts the BHC-level golden cell:

> **JPMorgan Chase (RSSD 1039502), BHCK2170 @ 2026-03-31 = 4,900,475,000 (thousands)**

Both must pass before any push.

---

## Data source

Free public data — no subscription required:

- **FFIEC Call Report filings:** [FFIEC CDR Bulk Data](https://cdr.ffiec.gov/public/PWS/DownloadBulkData.aspx)
  (requires Playwright to navigate the Akamai-guarded download page)
- **MDRM dictionary:** Fed's MDRM bulk download

No data is bought or licensed. Everything comes from government public disclosure requirements.

---

## Sibling dashboards

| Dashboard | Scope | Repo |
|---|---|---|
| FR Y-9C | Bank Holding Companies (BHCs) | [austinfahrenkopf/FRY9C](https://github.com/austinfahrenkopf/FRY9C) |
| FFIEC 002 | US Branches of Foreign Banks | [austinfahrenkopf/FFIEC_002](https://github.com/austinfahrenkopf/FFIEC_002) |
| FFIEC 031 (this repo) | All US Commercial Banks | [austinfahrenkopf/FFIEC_Call](https://github.com/austinfahrenkopf/FFIEC_Call) |

The three dashboard engines (`make_site_*.py`) are clones of one explorer — no shared module.
Every engine/UI change must be ported to all three files.
