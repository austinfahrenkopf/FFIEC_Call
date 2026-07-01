# FFIEC 031 Call Report Dashboard — Design Context for Future Editors

This document distills the standing design decisions, methodology constraints, and
non-obvious implementation choices for the FFIEC 031 Call Report dashboard. Read this
before making substantive changes to `make_site_call.py`, `build_hierarchy.py`, or any
curated input files.

---

## What this project is

A browser dashboard over FFIEC **Call Report** (FFIEC 031/041/051) filings for all U.S.
commercial banks. The Call Report is a detailed regulatory form (~1,400 line items across
~45 schedules) filed quarterly by ~7,500 FDIC-insured commercial banks.

This is one of three sibling projects (Y-9C, FFIEC 002, Call). The three `make_site_*.py`
scripts are **clones** — they share no module. Every engine/UI change must be ported to all
three. **Never copy an MDRM code from Y-9C or FFIEC 002 into Call without verifying the code
exists in Call's panel parquet** — this caused real bugs.

---

## MDRM prefix conventions for Call

Call uses the following prefixes (different from Y-9C which uses BH* prefixes):

| Prefix | Scope / filer type |
|---|---|
| RCFD | Consolidated (both domestic + foreign offices) |
| RCON | Domestic offices only |
| RIAD | Income / changes (Schedule RI) |
| RCFA | Foreign-branch consolidated (mutual-exclusive with RCFW for some codes) |
| RCFW | Wholesale bank consolidated (mutual-exclusive with RCFA) |
| RCOA | Domestic offices of foreign-branch banks |
| RCOW | Domestic offices of wholesale banks |
| RCFN | Other consolidated variant (used for specific items) |

**Coalesce order in the engine:** COMB -> RCFD -> RCON -> RIAD -> RCFA -> RCFW -> RCOA -> RCOW -> RCFN.
For any given bank only ONE prefix is non-null per base code (mutual exclusion) — the
`[...new Set(out)]` dedup in `descCodes` handles this correctly.

**Report regex:** `/^(RCON|RCFD|RCFN|RCFA|RCFW|RCOA|RCOW|RIAD)[A-Z0-9]{4}$/`

---

## COMB denominators — use COMB, not RCFD (§NORMDEN-LEAGUE-CALL, 2026-07-01)

Denominator codes must use COMB variants (not raw RCFD) to cover all charter types:

| Purpose | Denominator code | Why not RCFD? |
|---|---|---|
| Assets (÷ assets ratios) | `COMB2170` | 041/051 filers report RCON2170, not RCFD2170 |
| Loans | `COMB2122` | Same cross-form coverage issue |
| Deposits | `COMB2200` | RCFD2200 does not exist; see §IBF synthesis below |
| Equity | `COMB3210` | Same cross-form coverage issue |

These four are the available presets in the `#normden` dropdown (`NORM_DEN_LABELS`).

---

## Roll-up de-duplication layer (CRITICAL — added 2026-06-29)

Call schedules can double-count if header subtotals simply sum all children. The engine
has a three-layer de-dup system in `descCodes(nd)`:

### 1. ROLLUP_RULES — item-level overrides
For schedule/item combinations where the standard sum would double-count, `ROLLUP_RULES`
specifies either an explicit pre-aggregated total code or a suppression:

```
RC item 4  -> RCFD5369 / RCFDB529   (Loans & leases — avoids gross + net + HFS)
RI item 1  -> RIAD4107               (Total interest income)
RI item 2  -> RIAD4073               (Total interest expense)
RI item 5  -> RIAD4079               (Total noninterest income)
RI item 7  -> RIAD4093               (Total noninterest expense)
```

All codes were verified against the panel parquet before wiring.

### 2. colStrat — column selection for matrix schedules
Matrix schedules (multiple columns per row) must use the right column to avoid summing
partial subtotals:

| Schedule | colStrat | Behavior |
|---|---|---|
| RC-B | `'AD'` | Col A (HTM amortized cost) + Col D (AFS fair value) |
| RC-T | `'A'` | Col A only (total dollar amount, not count columns) |
| all others | `'pair'` | Drop RCON domestic when RCFD/COMB consolidated exists for same base |

### 3. FV_SCHED — fair value schedules
`FV_SCHED = {'RCQ'}` — for these schedules, `descCodes` takes only Col A (total fair value)
to avoid summing Level 1 + Level 2 + Level 3 sub-components that add up to the total.

---

## sch-stamping (required for roll-up rules)

`emitSchedule(sch, rows)` stamps `sch:sch` on every emitted node (header, placeholder,
COMB pair, showRaw, RCFN, or plain node). This lets `descCodes(nd)` read `nd.sch||''` to
look up the schedule-specific ROLLUP_RULES and colStrat. **Without sch-stamping, all
roll-up rules are silently bypassed.** Do not remove or omit the `sch:sch` fields.

---

## Mis-nest fix and override mechanism (§MISNEST-FIX-CALL, 2026-06-29)

RCFDG482 (Trading liabilities) and RCFD1773 were mis-nested under RCQ (fair-value
schedule) in the PDF-derived hierarchy. Moved to their correct parents using the
`ffiec_call_hierarchy_overrides.json` mechanism.

The override file supports:
- `force_rows`: place a node at an explicit schedule/parent
- `captions`: override display text
- `drop_codes`: remove a code from the hierarchy entirely

This is the canonical way to fix PDF-parse errors without touching the PDF parser.
**Do not fix mis-nests by editing `ffiec_call_hierarchy.json` directly** — the JSON is
rebuilt by `build_hierarchy.py`; all fixes must live in the overrides file.

---

## Export Builder fix — ebRawCodes → seriesFor (§EXPORT-FIX-CALL, 2026-06-29)

Prior to this fix, the Export Builder modal fetched data via a per-row loop that called
`runExport()` with a code-level query. This was changed to use `seriesFor(id, m)` (the
same function used by the main chart), which correctly handles DERIV/DYN codes and
applies the `isRawPct`/`isAggScope` guards.

The fix affects `ebRawCodes` (the array of codes to export). If you change how
`seriesFor()` works, re-test the Export Builder with a DERIV ratio code and an aggregate
scope — these were the failure modes before the fix.

---

## IBF deposit synthesis — RCFD2200 = RCON2200 + RCFN2200 (§IBF-DEPOSIT-REBUILD, 2026-07-01)

RCFD2200 (consolidated total deposits) does NOT exist as a reported code on the Call form.
031 filers (banks with foreign offices / IBFs) report deposits across two codes:
- RCON2200 = domestic-office deposits
- RCFN2200 = IBF (International Banking Facility) deposits

Without synthesis, COMB2200 = RCON2200 = domestic-only, understating system deposits
by ~$1.72T (9.1%). The synthesis is applied at two layers:

**1. Segment aggregates (`build_segments_call.py`):**
```sql
CREATE TEMP TABLE t_synth AS
SELECT quarter_end, id_rssd, 'RCFD'||substr(mdrm,5,4) AS mdrm,
       sum(value) AS value
FROM t0
WHERE substr(mdrm,5,4) IN ('2200','6631','6636')
  AND substr(mdrm,1,4) IN ('RCON','RCFN')
GROUP BY quarter_end, id_rssd, substr(mdrm,5,4)
HAVING max(CASE WHEN substr(mdrm,1,4)='RCFN' THEN value END) > 0
```
Synthesized codes: RCFD2200 (total deposits), RCFD6631 (non-IB deposits),
RCFD6636 (interest-bearing deposits). Codes 2625/2650/2898/2133 have RCFN but no RCON
counterpart — NOT synthesized.

**2. Individual banks (`build_tool_dataset.py`):**
Mirrors the same synthesis for large individual banks in the tool parquet, so per-bank
deposit KPIs (JPM, Citi, etc.) are correct.

**Re-enrichment without Fed download (`quick_enrich.py`):**
Adds schedule/title metadata for the synthetic RCFD codes using the committed
`ffiec_call_dictionary.csv`, without requiring a live Fed MDRM.zip download. Use
`quick_enrich.py` when the Fed endpoint is unavailable.

---

## Denominator dropdown — normden UI (§NORMDEN-LEAGUE-CALL, 2026-07-01)

The `#normden` select element lets users normalize any measure by a common denominator
(e.g., show metrics as % of assets). Implementation details:

- `NORM_DEN_LABELS`: JS constant mapping denominator code → display label
  (four presets for Call: COMB2170/2122/2200/3210)
- `window._normDenCd`: set by the `#normden` change handler; read by `recompute()` and
  `_getLinkTfm()`/`_applyLinkedTfm()` to sync normalization across linked charts
- localStorage key preserves the selection between sessions
- The normden value flows through to both the main chart and the linked "compare" panel
  via the link-transform chain

When `_normDenCd` is set, `seriesFor(id, m)` fetches BOTH the measure series and the
denominator series, then divides element-wise. Result unit is a fraction (multiply by 100
for percentage). Quarters where the denominator is null or zero are excluded.

**Do not revert to raw `RCFD2170` for assets:** 041/051-form filers only report RCON2170,
so a raw RCFD denominator would produce null for ~50% of the bank universe.

---

## League table — buildLGMEAS (§NORMDEN-LEAGUE-CALL, 2026-07-01)

`buildLGMEAS()` dynamically constructs the full league measure list (353 options for Call)
from the loaded hierarchy at page startup. It:

1. Walks every schedule via `emitSchedule(sch)` → `nest()` → `descCodes(nd)`
2. For each header node, creates a `DYN['SUB:'+nd.code]` entry so headers are selectable
   in the league table
3. Uses `d.type === 'ratio'` to set the `pct` flag (not `!== 'sum'`, which would also flag
   hybrids incorrectly)

**Note on DYN:** tree-click DYN (on-demand header subtotals) remains Y-9C-only. But
`buildLGMEAS()` creates `DYN['SUB:...']` entries in all three forms for the league table
specifically — this is intentional and not a port error.

The league modal is opened by the 🏆 button. `perFilerValues(measCode, quarters)` drives
the per-entity values, using the same DERIV/DYN dispatch as `seriesFor()`.

---

## Completeness gate

`_completeness_gate.py` runs a bidirectional check:
1. Forward: every code in the expected manifest must appear in the built hierarchy.
2. Backward: every hierarchy leaf code must either be in the panel or documented in
   `ffiec_call_completeness_exclusions.json -> spurious_allowed`.

**CRITICAL:** `spurious_allowed` is a dict. If you need to add a code, add it to the
**existing** `spurious_allowed` key in the JSON file. Do NOT create a second
`spurious_allowed` key — Python's `json.load` uses the LAST occurrence of a duplicate
key, so a second key at an earlier position is silently ignored.

Currently documented in `spurious_allowed`:
- RCFDHT65 (RC-D item 6.c): valid PDF form line, 0 rows ever filed in CDR
- Many RCON*/RCFD*/RCON*/RIAD* codes with no panel data (valid form lines, never filed)
- TEXT*/RSSD* codes (free-text / admin fields, not charted)

---

## Atomic writes (mandatory)

Both `make_site_call.py` (the HTML) and `ffiec_call_hierarchy.json` have suffered
non-atomic-write truncation (NUL-truncation corruption). All future edits to these files
must use the atomic write pattern:

```python
with open(tmp_path, 'w', encoding='utf-8') as f:
    json.dump(obj, f, ...)
with open(tmp_path, 'r', encoding='utf-8') as f:
    verify = json.load(f)   # re-read + json.load verify
os.replace(tmp_path, target_path)
```

The Python build tail of `make_site_call.py` also has a completeness assert:
```python
assert _chk.rstrip().endswith("</html>") and len(_chk) == len(HTML)
```
This fails loudly if the HTML is truncated during write.

---

## DO NOT touch RC-N / RC-E / RC-L sums

These three schedules have been independently verified as correctly additive. Their column
structures are intentionally not subject to colStrat or ROLLUP_RULES. Do not add rules for
them.

---

## PCTC codes (non-additive percentages)

Call has 28 RC-R capital ratio codes (RCFA/RCFD/RCFW/RCOA/RCON/RCOW prefix + 7204/7205/
7206/P793/H036/etc.). These are blocked from aggregate scopes (`isRawPct` check). They are
stored in the PCTC set and excluded from `descCodes` via `_pctB`.

---

## Golden cell

`validate_build_call.py` asserts: **JPMorgan Chase (RSSD 852218) RCFD2170 @ 2026-03-31 =
4,016,571,000** (bank-level entity). `_qa_final.py` additionally asserts the BHC-level
**BHCK2170 @ 2026-03-31 = 4,900,475,000**. Both must pass before any push.

---

## Three-dashboard clone rule

Before porting any engine change from Y-9C or 002 to Call (or vice versa):
1. Verify the MDRM codes exist in Call's panel parquet.
2. Adapt prefixes (RCFD/RCON/RIAD for Call, BHCK/BHCA for Y-9C).
3. Run `validate_build_call.py` until green.
4. Update ORCHESTRATION_STATE.md and HANDOFF_CONTINUE.md.
