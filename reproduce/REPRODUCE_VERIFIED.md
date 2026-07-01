# FFIEC 031 Call Report Reproduce Kit — Verification Record

**Date verified:** 2026-07-01 (§NORMDEN-LEAGUE-CALL + §IBF-DEPOSIT-REBUILD clean-room re-verify)
**Commit verified:** c6e53a1 (feat(call): denominator dropdown + full league measure set)
**Environment:** Python 3.12 · Windows 11

---

## Validation state (clean-room result against c6e53a1)

Clean-room test setup: scratch directory containing only committed `reproduce/` files
plus `app/ffiec_call.parquet` copied to `site_call/ffiec_call.parquet`. No dev-workspace
files, no intermediate parquets beyond those committed.

### Step 1 — HTML-only rebuild

```
python make_site_call.py --html-only
```

**RESULT: PASS** ✓
Output: `site_call/index.html = 214,795 bytes`

> **Note on byte-for-byte identity:** The output is always 214,795 bytes but the SHA-256
> hash is non-deterministic between runs. The NODATA code set (codes in the hierarchy but
> absent from the panel) is serialized from a Python `set`, whose iteration order is
> hash-randomized per process. The dashboard content is functionally identical across runs.
> Use validate_build_call.py (not hash comparison) to confirm correctness.

### Step 2 — Validator with committed tool parquet

`ffiec_call_tool.parquet` is now committed to `reproduce/` (67.7 MB). Run from the
`reproduce/` directory (or any directory containing `ffiec_call_tool.parquet`,
`ffiec_call_hierarchy.json`, and `site_call/`):

```
python validate_build_call.py
```

**RESULT: PASS** ✓

```
============================================================
FFIEC 031 (Call) build validation
============================================================
  site parts: 1   tool codes: 7628
  NOTE  [HIERARCHY] 45 schedule sections
  NOTE  [GOLDEN] RCFD2170=4,016,571,000 at 2026-03-31 [OK]
  NOTE  [RIAD] ffiec_call_segments_long.parquet not found (skipped — not committed)
  NOTE  [COMPLETE2] no expected_items.json manifest found (skipped — not committed)
  NOTE  [HIERARCHY_LINT] hierarchy_linter not found (skipped — dev-only tool)
  NOTE  [MISSING] OK — every active-era code is in the hierarchy or documented (1384 active codes checked)
  NOTE  [SPURIOUS] OK — every hierarchy leaf code is reported in the panel or documented in spurious_allowed
  NOTE  [SEQUENCE] OK — no undocumented item-number gaps
  NOTE  [ERA_SEAM] OK — headline NPL/charge-off/past-due/assets series are continuous

  ALL CHECKS PASSED [OK]
```

### QA final (dev-workspace check, run from `External Bank Data\`)

```
python _qa_final.py
```
**RESULT: PASS** ✓ — 12 Call checks pass including NORM_DEN_LABELS, buildLGMEAS,
COMB2200 normden denominator, and LGMEAS count ≥ 353.

---

## Golden cells confirmed

| Check | Entity | Code | Quarter | Value | Source |
|---|---|---|---|---|---|
| Bank-level | JPMorgan Chase Bank NA (RSSD 852218) | RCFD2170 | 2026-03-31 | 4,016,571,000 | validate_build_call.py [GOLDEN] |
| BHC-level | JPMorgan Chase & Co (RSSD 1039502) | BHCK2170 | 2026-03-31 | 4,900,475,000 | _qa_final.py [GOLDEN] |

---

## Features verified at c6e53a1

All features from prior sessions through §NORMDEN-LEAGUE-CALL (2026-07-01) are present
in the committed engine (confirmed by REPO_READINESS.md audit):

| Feature tag | What it adds |
|---|---|
| §CALL-EMP1 / §EMP2 | RI/RC-B/RC-T/RC-Q/RC-D hierarchy fixes; RIADA530 restored; sch-stamping for roll-up de-dup |
| §SUBTOTAL-CALL | `hybrid_sum` for COMBHK05 (brokered deposits ≤$250K, 24q gap) + RCFN2200 (IBF deposits) |
| §MISNEST-FIX-CALL | De-nested RCFDG482/RCFD1773 from RCQ; override mechanism in hierarchy_overrides.json |
| §EXPORT-FIX-CALL | Export Builder `ebRawCodes` → `runExport` calls `seriesFor()` (not per-row fetch) |
| §IBF-DEPOSIT-REBUILD | `build_segments_call.py` synthesizes RCFD2200/6631/6636 = RCON+RCFN for IBF filers; `quick_enrich.py` re-enriches without Fed download; `build_tool_dataset.py` mirrors synthesis for individual banks |
| §NORMDEN-LEAGUE-CALL | Denominator dropdown (`#normden`, 4 presets, COMB2170/2122/2200/3210); `buildLGMEAS()` walks full hierarchy → 353 league options; `NORM_DEN_LABELS`; `window._normDenCd` |

---

## Independent empirical re-sweep (§EMP2, 2026-06-29)

An independent roll-up re-sweep was performed on the corrected build before first push.
All header subtotals verified against individual bank data — see prior REPRODUCE_VERIFIED.md
entries. The §NORMDEN-LEAGUE-CALL and §IBF-DEPOSIT-REBUILD features are data-pipeline
and UI-only — they do not change any existing subtotal or roll-up result.

---

## Panel stats (c6e53a1)

| Item | Value |
|---|---|
| Parquet file | `ffiec_call.parquet` (~62.3 MB, committed to `app/`) |
| Quarters | 201 (1993-Q1 through 2026-Q1) |
| Schedule sections | 45 |
| Active codes checked | 1,384 |
| Tool codes in tool parquet | 7,628 |
| Build output | `site_call/index.html` = 214,795 bytes (non-bit-reproducible; see note above) |

---

## What IS committed to this kit

| Artifact | Location | Notes |
|---|---|---|
| Dashboard HTML | `app/index.html` | 214,795 bytes; also rebuilt by --html-only |
| Site parquet | `app/ffiec_call.parquet` | 62.3 MB; required for --html-only rebuild |
| Hierarchy JSON | `reproduce/ffiec_call_hierarchy.json` + `app/ffiec_call_hierarchy.json` | Curated artifact; see below |
| Tool parquet | `reproduce/ffiec_call_tool.parquet` | 67.7 MB; required for full validator run |
| All build scripts | `reproduce/*.py` | cdr_download → parse → build_segments → enrich → build_tool → make_site |
| Dictionary + roster | `reproduce/ffiec_call_dictionary.csv`, `reproduce/ffiec_call_roster.csv` | Needed by build_tool_dataset.py |

## What is NOT committed (regenerate from raw data)

- Raw CDR ZIPs (`cdr_zips/` — ~15 GB for full history): run `cdr_download_031.py`
- Intermediate CDR parquets (`cdr_parquet/*.parquet`): run `cdr_parse_call.py`
- Segments parquet (`ffiec_call_segments_long.parquet`): run `build_segments_call.py`
- Enriched segments (`ffiec_call_segments.parquet`): run `quick_enrich.py` (or `enrich_call.py`)

## Full data-stream regeneration (from scratch on a new machine)

```powershell
# 1. Download raw CDR ZIPs (Playwright required; ~15 GB; ~1–2 hours)
python cdr_download_031.py

# 2. Parse CDR ZIPs into columnar parquet
python cdr_parse_call.py

# 3. Build aggregate segments — synthesizes RCFD2200=RCON+RCFN for IBF filers
python build_segments_call.py

# 4a. Enrich without Fed download (uses committed dictionary CSV)
python quick_enrich.py
# 4b. OR full enrich with Fed MDRM.zip download
python enrich_call.py

# 5. Build tool parquet (aggregate + individual banks ≥$10B)
python build_tool_dataset.py

# 6. Build site
python make_site_call.py
# Or HTML-only (after copying app/ffiec_call.parquet → site_call/):
python make_site_call.py --html-only

# 7. Validate
python validate_build_call.py
```

---

## Curated artifacts

`ffiec_call_hierarchy.json` in `reproduce/` is the canonical curated hierarchy — it cannot
be bit-for-bit reproduced by `build_hierarchy.py` alone. The script generates a base from
the PDF, but the final hierarchy includes patches from the §CALL-EMP1 audit session
(2026-06-29: RI M.11 + RC-D 6.c restored; sch-stamping for roll-up de-dup). Use the
shipped `ffiec_call_hierarchy.json` directly.
