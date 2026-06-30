# FFIEC 031 Call Report Reproduce Kit — Verification Record

**Date verified:** 2026-06-29 (§CALL-EMP1 audit fixes + §EMP2 independent re-sweep)
**Environment:** Python 3.12 · Windows 11

---

## Validation state

Both QA gates pass on the current build (as of 2026-06-29):

```
============================================================
FFIEC 031 (Call) build validation
============================================================
  site parts: 1   tool codes: 7625
  NOTE  [HIERARCHY] 45 schedule sections
  NOTE  [GOLDEN] RCFD2170=4,016,571,000 at 2026-03-31 [OK]
  NOTE  [COMPLETE2] FFIEC 031 (Call): all must-add codes from manifest are now present
  NOTE  [MISSING] OK — every active-era code is in the hierarchy or documented (1381 active codes checked)
  NOTE  [SPURIOUS] OK — every hierarchy leaf code is reported in the panel or documented in spurious_allowed
  NOTE  [SEQUENCE] OK — no undocumented item-number gaps
  NOTE  [ERA_SEAM] OK — headline NPL/charge-off/past-due/assets series are continuous

  ALL CHECKS PASSED [OK]
```

```
  [OK] Call: prevQtr helper
  [OK] Call: yoyQtr helper
  [OK] Call: pctChg sign-flip
  [OK] Call: perFilerValues
  [OK] Call: HIGH-2 PCTC set
  [OK] Call: isRawPct (Call)
  [OK] Call: isAggScope (Call)
  [OK] Call: blocked label
  [OK] GOLDEN: JPM BHCK2170 @ 2026-03-31 = 4,900,475,000

ALL QA CHECKS PASSED
```

---

## Golden cells confirmed

| Check | Entity | Code | Quarter | Value | Source |
|---|---|---|---|---|---|
| Bank-level | JPMorgan Chase Bank NA (RSSD 852218) | RCFD2170 | 2026-03-31 | 4,016,571,000 | validate_build_call.py [GOLDEN] |
| BHC-level | JPMorgan Chase & Co (RSSD 1039502) | BHCK2170 | 2026-03-31 | 4,900,475,000 | _qa_final.py [GOLDEN] |

---

## Independent empirical re-sweep (§EMP2, 2026-06-29)

An independent roll-up re-sweep was performed on the corrected build before first push.
All header subtotals verified against individual bank data:

| Schedule / Item | Multiplier | Status |
|---|---|---|
| RC item 4 (Loans & leases) | 0.98× | PASS — 2% gap is data-coverage artifact (confirmed on JPM individually), not double-count |
| RI item 5 (Noninterest income) | 1.000× | PASS — exact match |
| RC-B (Securities) | corrected | PASS |
| RC-T (Fiduciary) | corrected | PASS |
| RC-Q (Fair value) | corrected | PASS |
| 5 RCFA/RCFW/RCFN header subtotals | resolve | PASS — extended coalesce fixed empty charts |
| RI M.11 (RIADA530) | renders | PASS — item restored |
| RC-D item 6.c (RCFDHT65) | .nodata | PASS — 0 rows ever filed, correct indicator |
| Accounting identity (RC assets = RC liabilities + equity) | holds | PASS |

---

## Panel stats

| Item | Value |
|---|---|
| Parquet file | `ffiec_call.parquet` (~62 MB) |
| Quarters | 201 (1993-Q1 through 2026-Q1) |
| Schedule sections | 45 |
| Active codes checked | 1,381 |
| Tool codes embedded | 7,625 |
| Build output | app/index.html = 181,071 bytes |

---

## What is NOT in this kit (regenerate from raw data)

- Raw CDR ZIPs (`cdr_zips/` — ~15 GB for full history): run `cdr_download_031.py`
- Source panel parquet (`ffiec_call_segments.parquet`): run steps 2-4 in RUNBOOK.md
- The panel parquet in `app/ffiec_call.parquet` was built from the full CDR history and IS
  committed to this repo (62 MB, under GitHub's 100 MB limit)

---

## Curated artifacts

`ffiec_call_hierarchy.json` in `reproduce/` is the canonical curated hierarchy — it cannot
be bit-for-bit reproduced by `build_hierarchy.py` alone. The script generates a base from
the PDF, but the final hierarchy includes patches from the §CALL-EMP1 audit session
(2026-06-29: RI M.11 + RC-D 6.c restored; sch-stamping for roll-up de-dup). Use the
shipped `ffiec_call_hierarchy.json` directly.
