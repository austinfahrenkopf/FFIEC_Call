# RUNBOOK — All Three Dashboards (updated 2026-07-01)

**Date:** 2026-07-01
**Build state:** All three dashboards built, validated, and deployed. Eight major sessions
landed since 2026-06-19 — see "Recent feature history" below.

Read this to understand how to rebuild, modify, or deploy any of the three dashboards.
Read `HANDOFF_CONTINUE.md` for a full account of what was done.
Read `ORCHESTRATION_STATE.md` for standing decisions and constraints.
Read `CONTEXT.md` for Call-specific design decisions.

---

## Quick-start: rebuild everything in one click

> **WORKSPACE NOTE:** `FINALIZE.ps1` is designed for the `External Bank Data\` dev workspace,
> not for a fresh clone. From a fresh clone, use the per-project steps below (see
> "Clone → rebuild → serve" section). Running `.\FINALIZE.ps1` from a fresh clone
> will fail immediately because it references `FR Y-9C\`, `FFIEC 002\`, and `FFIEC 031\`
> subdirectories that only exist in the dev workspace.

From the dev workspace (`External Bank Data\` folder):

```powershell
.\FINALIZE.ps1
```

This runs: Y-9C hierarchy + validate + html-only → 002 html-only → Call html-only → QA check.
Exit 0 = all green. Takes ~3 minutes.

---

## Clone → rebuild → serve (from a fresh clone of this repo)

```powershell
# 1. Set up (one-time)
pip install pandas pyarrow pypdf playwright requests duckdb
playwright install chrome

# 2. Copy the site parquet into the expected location
cd reproduce
md site_call
copy ..\app\ffiec_call.parquet site_call\

# 3. HTML-only rebuild (fast — uses committed parquet)
python make_site_call.py --html-only

# 4. Validate (uses committed ffiec_call_tool.parquet in reproduce/)
python validate_build_call.py

# 5. Serve locally
cd site_call
python -m http.server 8001
# Open: http://localhost:8001
```

For a full data rebuild from raw CDR files, see `REPRODUCE_VERIFIED.md` → "Full data-stream
regeneration" section.

---

## Prerequisites (one-time setup on a new machine)

```powershell
pip install pandas pyarrow pypdf playwright requests duckdb
playwright install chrome
```

Python 3.10+ is required. DuckDB is NOT needed server-side — it runs as DuckDB-WASM in the
browser. DuckDB pip package is needed only for `build_segments_call.py` and
`build_tool_dataset.py`.

---

## Recent feature history (sessions since 2026-06-19)

Sessions are listed newest-first. All features are in the committed engine (c6e53a1 / 2026-07-01).

| Tag | Date | What changed |
|---|---|---|
| §NORMDEN-LEAGUE-CALL | 2026-07-01 | Denominator dropdown (`#normden`, 4 presets: COMB2170/2122/2200/3210); `buildLGMEAS()` → 353 league options; `NORM_DEN_LABELS`; `window._normDenCd` localStorage-backed |
| §IBF-DEPOSIT-REBUILD | 2026-07-01 | `build_segments_call.py` synthesizes RCFD2200=RCON+RCFN for IBF filers; `quick_enrich.py` re-enriches without Fed download; `build_tool_dataset.py` mirrors synthesis for individual large banks |
| §NORMBYASSETS | 2026-06-30 | `÷assets` preset uses COMB2170 (all-charter) not RCFD2170; fixes null denominator for 041/051 filers |
| §SUBTOTAL-CALL | 2026-06-30 | `hybrid_sum` subtotals for COMBHK05 (brokered deposits ≤$250K, 24q gap) + RCFN2200 (IBF deposits, 3q interior nulls) |
| §EXPORT-FIX-CALL | 2026-06-29 | Export Builder `ebRawCodes` → `runExport` → `seriesFor()` for fidelity with DERIV/DYN codes |
| §MISNEST-FIX-CALL | 2026-06-29 | RCFDG482/RCFD1773 de-nested from RCQ; override mechanism documented |
| §CALL-EMP1 / §EMP2 | 2026-06-29 | RI/RC-B/RC-T/RC-Q/RC-D hierarchy fixes; RIADA530 restored; sch-stamping for roll-up de-dup; independent re-sweep of all 45 schedules |

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
| Download / update data | `python cdr_download_031.py` | New quarter available |
| Parse CDR ZIPs | `python cdr_parse_call.py` | After download |
| Build segments | `python build_segments_call.py` | After parse (synthesizes RCFD2200/6631/6636) |
| Enrich (no download) | `python quick_enrich.py` | After segments (uses committed dictionary CSV) |
| Enrich (full) | `python enrich_call.py` | After segments (downloads Fed MDRM.zip) |
| Build tool parquet | `python build_tool_dataset.py` | After enrich |
| **Build site** | `python make_site_call.py` | After tool parquet |
| **JS-only rebuild** | `python make_site_call.py --html-only` | After changes to `make_site_call.py` only |
| **Validate** | `python validate_build_call.py` | After rebuild — must exit 0 |
| Serve locally | `cd site_call ; python -m http.server 8001` | Local testing |

**Golden cell:** JPMorgan Chase Bank NA RSSD 852218, RCFD2170 @ 2026-03-31 = 4,016,571,000.

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
| `seriesFor(id, m)` | Fetches time series for one entity + measure from DuckDB-WASM. DERIV ratios sum numerators then divide. `isRawPct` guard blocks PCTC codes for aggregate scopes. Applies `_normDenCd` normalization when set. |
| `perFilerValues(measCode, quarters)` | Per-entity league-table values for DERIV/DYN/raw codes. Used by sort and the 🏆 league modal. |
| `buildLGMEAS()` | Walks full hierarchy to build league measure list (353 options for Call). Creates `DYN['SUB:nd.code]` entries for header nodes. Run once at startup. |
| `prevQtr(q)` / `yoyQtr(q)` | Date-arithmetic quarter helpers (YYYY-MM-DD strings). Used for date-based QoQ/YoY KPI deltas. |
| `pctChg(a, b)` | % change with sign-flip guard — returns null when prev and current have different signs. |
| `descCodes(nd)` | Collects non-PCTC leaf codes from a node for dynamic subtotals and roll-up. Applies ROLLUP_RULES / colStrat / FV_SCHED. |
| `isRawPct(m)` | True if `m` is in the PCTC set (raw non-additive percentage code) and not a DERIV/DYN. |
| `isAggScope(id)` | True if `id` is a multi-entity aggregate (ALL, type group, size bucket, or multi-member peer). |

**PCTC codes (non-additive percentages, blocked for aggregates):**
- Y-9C: ~33 HC-R capital ratio codes (BHCA/BHCW prefix + 7204/7205/7206/P793/H036/etc.)
- Call: 28 RC-R capital ratio codes (RCFA/RCFD/RCFW/RCOA/RCON/RCOW prefix + same suffixes)
- 002: none (foreign-branch form has no capital ratio codes)

**DYN subtotals:** Tree-click DYN (on-demand header subtotals from `descCodes`) remains
Y-9C-only. However, `buildLGMEAS()` creates `DYN['SUB:...']` entries in all three forms
for the league table — this is intentional.

**DERIV ratios:** sum-then-divide, not average-of-ratios. `type:'ratio'` → `100*sum(num)/sum(den)`.
`type:'sum'` → `sum(components)`. Optional `annualize:true` multiplies by `4/qn`.
