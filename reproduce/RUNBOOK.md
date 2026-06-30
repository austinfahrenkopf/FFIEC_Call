# FINAL RUNBOOK — All Three Dashboards

**Date:** 2026-06-19  
**State:** All three dashboards are done-done and deployable. No open engineering work.

Read this to understand how to rebuild, modify, or deploy any of the three dashboards.  
Read `HANDOFF_CONTINUE.md` for a full account of what was done.  
Read `ORCHESTRATION_STATE.md` for standing decisions and constraints.

---

## Quick-start: rebuild everything in one click

```powershell
# From the "External Bank Data\" folder:
.\FINALIZE.ps1
```

This runs: Y-9C hierarchy + validate + html-only rebuild → 002 html-only → Call html-only → 23-point QA check.  
Exit 0 = everything is clean. Takes ~3 minutes.

---

## Prerequisites (one-time setup on a new machine)

```powershell
pip install pandas pyarrow pypdf playwright requests
playwright install chrome
```

Python 3.10+ is required. DuckDB is NOT needed server-side — it runs as DuckDB-WASM in the browser.

---

## Per-project rebuild pipelines

### FR Y-9C (Bank Holding Companies)
Source: NIC Financial Data Download (free, from Fed website, Akamai-guarded → Playwright).  
Folder: `FR Y-9C\`

| Step | Command | When to run |
|---|---|---|
| Download quarterly data | `python download_fry9c_playwright.py` | New quarter available |
| Build panel | `python build_fry9c_panel.py` | After download |
| Build MDRM dictionary | `python build_fry9c_dictionary.py` | When Fed updates MDRM.zip |
| Download NIC lineage | `python download_fry9c_nic_playwright.py` | Rarely (RSSD changes) |
| Build lineage | `python build_fry9c_lineage.py` | After NIC download |
| Build topholder map | `python build_fry9c_topholder.py` | After NIC download |
| **Build hierarchy** | `python build_hierarchy_fry9c.py` | After any change to `fry9c_matrix.csv`, `fry9c_hierarchy_overrides.json`, or the PDF |
| **Validate** | `python validate_build.py` | After every hierarchy rebuild — must exit 0 |
| **Build site** | `python make_site_fry9c.py` | After panel rebuild |
| **JS-only rebuild** | `python make_site_fry9c.py --html-only` | After changes to `make_site_fry9c.py` only |
| Serve locally | `cd site_fry9c ; python -m http.server 8003` | Local testing |

**Golden cell:** JPMorgan RSSD 1039502, BHCK2170 @ 2026-03-31 = 4,900,475,000 (thousands).  
`validate_build.py` asserts this automatically.

**Curated files (edit with a text editor, NOT shell `>>`)**:
- `fry9c_matrix.csv` — matrix schedules the PDF parser can't read (HC-N, HC-C, HC-R, HC-V, …)
- `fry9c_hierarchy_overrides.json` — force_rows, captions, drop_codes applied after parsing

**Typical edit-rebuild loop** (curating a matrix row or override):  
`build_hierarchy_fry9c.py → validate_build.py → make_site_fry9c.py --html-only → reload browser`

---

### FFIEC 002 (US Branches of Foreign Banks)
Source: Chicago Fed "Complete" files (free, usually direct download).  
Folder: `FFIEC 002\`

| Step | Command | When to run |
|---|---|---|
| Download / update data | See `HANDOFF_002.md` | New data available |
| **Build site** | `python make_site_002.py` | After data update |
| **JS-only rebuild** | `python make_site_002.py --html-only` | After changes to `make_site_002.py` only |
| Serve locally | `cd site_002 ; python -m http.server 8002` | Local testing |

See `RUNBOOK.md` in the `FFIEC 002\` folder for the full pipeline.

---

### FFIEC 031/041/051 Call Reports (All US Commercial Banks)
Source: FFIEC CDR Bulk Data (free, from FFIEC website).  
Folder: `FFIEC 031\`

| Step | Command | When to run |
|---|---|---|
| Download / update data | See `HANDOFF_CALL.md` | New quarter available |
| **Build site** | `python make_site_call.py` | After data update |
| **JS-only rebuild** | `python make_site_call.py --html-only` | After changes to `make_site_call.py` only |
| Serve locally | `cd site_call ; python -m http.server 8001` | Local testing |

---

## What to include when moving to a new repo (GitHub Pages deployment)

Each dashboard is its own repo. Upload the contents of the `site_*/` folder:

| File | Include? |
|---|---|
| `site_*/index.html` | YES — the dashboard (self-contained HTML + embedded JS) |
| `site_*/*.parquet` | YES — the data (DuckDB-WASM reads these via fetch) |
| `site_*/ffiec*_hierarchy.json` / `fry9c_hierarchy.json` | YES — the form tree |
| `make_site_*.py` | YES — needed for future rebuilds (include in repo root or `scripts/`) |
| `build_*.py` | YES — pipeline scripts |
| `fry9c_matrix.csv` / `fry9c_hierarchy_overrides.json` | YES (Y-9C only) |
| `requirements.txt`, `RUNBOOK.md` | YES |
| `fry9c_zips/` (raw BHCF downloads, ~1.5 GB) | NO — regenerate from `download_fry9c_playwright.py` |
| `fry9c_panel_long.parquet` (~154 MB) | NO — too large; regenerate from raw data |
| `ffiec_call.parquet`, `ffiec002.parquet` (source panels) | NO — too large; regenerate |
| `.pw_profile/` (Playwright Chrome profile) | NO — machine-specific |
| `_archive/`, `_qa_scratch/`, `_check_*.py` | NO — build artifacts and temp files |

**GitHub file size limits:** web upload = 25 MB max; GitHub Desktop = 100 MB.  
Use GitHub Desktop for `site_*/` contents (parquet files may be 17–67 MB each).

### GitHub Pages setup
Settings → Pages → Source = Deploy from branch → main / root.  
Site is live at `https://austinfahrenkopf.github.io/<repo>/`.

---

## Engine internals for a future editor

All three `make_site_*.py` are **clones of one explorer**. Every engine/UI change must be ported to
all three — there is no shared module. Key JS functions in the engine:

| Function | Purpose |
|---|---|
| `seriesFor(id, m)` | Fetches time series for one entity + measure from DuckDB-WASM. DERIV ratios sum numerators then divide. `isRawPct` guard blocks PCTC codes for aggregate scopes. |
| `perFilerValues(measCode, quarters)` | Per-entity league-table values for DERIV/DYN/raw codes. Used by sort and the 🏆 league modal. |
| `prevQtr(q)` / `yoyQtr(q)` | Date-arithmetic quarter helpers (YYYY-MM-DD strings). Used for date-based QoQ/YoY KPI deltas. |
| `pctChg(a, b)` | % change with sign-flip guard — returns null when prev and current have different signs. |
| `descCodes(nd)` | Collects non-PCTC leaf codes from a Y-9C tree node for dynamic subtotals (Y-9C only). |
| `isRawPct(m)` | True if `m` is in the PCTC set (raw non-additive percentage code) and not a DERIV/DYN. |
| `isAggScope(id)` | True if `id` is a multi-entity aggregate (ALL, type group, size bucket, or multi-member peer). |
| `allCond()` | Y-9C only: builds SQL WHERE clause for ALL scope with optional top-tier filter. |

**PCTC codes (non-additive percentages, blocked for aggregates):**
- Y-9C: ~33 HC-R capital ratio codes (BHCA/BHCW prefix + 7204/7205/7206/P793/H036/etc.)
- Call: 28 RC-R capital ratio codes (RCFA/RCFD/RCFW/RCOA/RCON/RCOW prefix + same suffixes)
- 002: none (foreign-branch form has no capital ratio codes)

**DYN subtotals (Y-9C only):** clicking a grouping header creates a `DYN['SUB:code']` measure that
sums non-PCTC leaf descendants. The `hasPctDesc` check shows a tooltip when a section has non-additive
cells. DYN does not exist in 002/Call (flat hierarchies).

**DERIV ratios:** sum-then-divide, not average-of-ratios. `type:'ratio'` → `100*sum(num)/sum(den)`.
`type:'sum'` → `sum(components)`. Optional `annualize:true` multiplies by `4/qn`.
