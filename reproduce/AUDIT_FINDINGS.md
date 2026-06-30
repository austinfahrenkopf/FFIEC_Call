# AUDIT FINDINGS — FR Y-9C Dashboard

**Auditor:** Cowork QA agent · **Date:** 2026-06-19
**Scope:** FR Y-9C dashboard only (`FR Y-9C\` — `make_site_fry9c.py`, `site_fry9c\`, and the
underlying panel/roster/lineage/hierarchy). The Call (031) and FFIEC 002 dashboards are explicitly
**out of scope** (handled in a separate session) and are not assessed here.
**Status:** AUDIT ONLY. No build scripts or site output were modified. Fixes are described, not
implemented.

---

## How this audit was performed (and its limits)

- **Data integrity** was checked against the **raw published source** — the NIC BHCF caret-delimited
  bulk files in `fry9c_zips\` — plus the roster, lineage, and hierarchy JSON shipped in `site_fry9c\`.
- **Engine logic** was audited by reading `make_site_fry9c.py` in full (the embedded HTML/JS is the
  dashboard runtime).
- **Limitation — no live render.** The sandbox has no parquet reader (no pyarrow/duckdb, no network to
  install one) and a sandbox web server is not reachable from the user's real browser, so the page was
  **not** rendered live with DuckDB-WASM. Chart/table findings are from reading the JS, not
  screenshots. A short live-render pass on the user's machine is recommended to confirm the UX items.
  The data and code findings below do not depend on a live render.

---

## What is CORRECT (verified — safe to trust)

- **Source value confirmed.** JPMorgan `RSSD 1039502 · BHCK2170` (total assets) = **4,900,475,000**
  (thousands) at **2026-03-31** in the raw BHCF file. Units and magnitude are consistent with the
  "$ thousands" label, and `fmtUnit` renders it correctly ($4.9T → "4,900 B").
- **Derived ratios aggregate correctly.** For `DERIV` ratios the engine sums each component **across
  the entity set first, then divides** (`sum(num)/sum(den)`), which is the correct treatment for
  non-additive ratios at the peer/aggregate level. Division-by-zero is guarded (`den>0`).
- **YTD-flow ratios are annualized.** `D_ROA`/`D_ROE` carry `annualize:true`; the engine multiplies
  by `4/qn` (Q1×4, Q2×2, Q3×4/3, Q4×1), so the earnings ratios are annualized rather than a YTD
  sawtooth. (This is correct — but see LOW-3 for a label mismatch.)
- **Merger-lineage linking is sound.** `fry9c_lineage.json` has **118** lineages whose members carry
  **non-overlapping** `first`/`last` spans (e.g. WBSB Bancorp 2012Q1–2013Q1 → Westbury Bancorp
  2013Q2–2014Q4), and **no RSSD appears in more than one lineage group**. So stitching a predecessor
  RSSD into its successor does **not** double-count within any quarter, and the seam is marked with a
  dashed splice line. Roster names are populated (3,142 entities), so the dashboard shows names, not
  bare RSSDs.

---

## Prioritized issues (FR Y-9C)

Severity: **HIGH** = wrong/misleading numbers a user would likely hit · **MEDIUM** = wrong in
specific reachable cases · **LOW** = cosmetic / edge-case / docs.

### HIGH-1 · "ALL" (and any multi-filer aggregate) double-counts nested holding companies
**What's wrong:** `scopeCond('ALL')` returns `1=1`, so "ALL" sums **every** Y-9C filer in the
quarter. FR Y-9C is filed by holding companies that can be **nested** — a top-tier BHC and its
intermediate holding company (and U.S. IHCs of foreign banks) can each file a Y-9C. Summing all
filers therefore double-counts assets, deposits, loans, equity, etc. The same applies to any peer
group a user builds that happens to include both a parent and a sub-holding company.
**Evidence:** Σ`BHCK2170` over all **387** filers at 2026-03-31 = **$30.6 trillion**. Total U.S.
commercial-bank assets are ≈ $24–25T; even allowing for non-bank BHC assets, $30.6T across only 387
filers is implausibly high and consistent with parent/child overlap. The top entries are the known
top-tier megabanks (JPM $4.90T, then $3.50T, $2.78T, $2.21T, $2.06T, $1.58T…), so the long tail of
smaller/intermediate filers is inflating the total. There is **no top-tier filter** anywhere in
`build_fry9c_panel.py` or `make_site_fry9c.py` — it only drops Y-9SP/parent-only `BHSP/BHCP` rows.
**Why it matters:** the default landing view (entity = ALL, measure = Total assets) shows an inflated,
untrustworthy number, and every peer aggregate spanning a nested pair is similarly overstated.
**Recommended fix:** add a **top-tier ("highest holder") flag** to the panel — derive it from the NIC
relationships file already downloaded at `fry9c_nic\CSV_RELATIONSHIPS.ZIP` (parent/child RSSD links)
or the attributes file — and make "ALL" default to top-tier holders only, with an optional "include
all filers" toggle. At minimum, surface the caveat in the header and handoff. **Confirm the
double-count magnitude against the relationships file before shipping a fix** — this is currently
evidenced by the implausible total, not yet by a resolved parent/child map.

### HIGH-2 · Raw HC-R percentage / rate cells are summed across entities in aggregates
**What's wrong:** the curated `DERIV` ratios are correct, but the tree also exposes **raw** HC-R
cells, some of which are **percentages/rates, not $ thousands** (capital ratios, etc.). The engine's
`PCTC` set correctly routes these to the **% axis** for display — but for an aggregate entity (ALL,
or a peer) the raw cell is still **summed across all holding companies** (`SELECT … SUM(value) …
GROUP BY quarter_end`). Summing a percentage across hundreds of filers is meaningless (e.g. an "ALL"
CET1 ratio that is the arithmetic sum of every filer's CET1%).
**Evidence:** `PCTC` (lines 285–288) lists ~33 HC-R ratio MDRMs and is used only for **axis
selection** (`isPct`/the `%` pane), not to suppress cross-entity summation. The raw-measure branch of
`seriesFor` (line 334) sums `value` for every charted scope including ALL/peers.
**Why it matters:** a user charting a raw capital-ratio line for ALL or for a multi-member peer gets a
number that looks like a percentage (right axis) but is actually a sum of percentages — wrong by a
factor of N.
**Recommended fix:** for `PCTC`/percentage codes, never `SUM` across entities — for an aggregate show
blank, or an asset-weighted average if a sensible denominator exists; keep the single-entity case as
is. (The axis routing via `PCTC` is already correct and should stay.)

### MEDIUM-1 · Dynamic subtotals (DYN) can sum non-additive or nested-subtotal codes
**What's wrong:** clicking a grouping/header row creates a subtotal measure
`DYN['SUB:'+code]={type:'sum',plus:descCodes(nd)}` that sums **all descendant codes** (line 436). Two
hazards: (a) if the descendants include **percentage/rate cells** (e.g. anything under HC-R), the
subtotal sums percentages — a non-additivity trap; (b) if the hierarchy nests a **subtotal/total line
together with its own components** under the same parent, `descCodes` may include both, **double-
counting** within a single entity.
**Evidence:** `descCodes(nd)` is collected unconditionally from the node's descendants (line 434) with
no filter for percentage codes or for intermediate subtotal lines; `DYN` entries are always
`type:'sum'`.
**Why it matters:** the feature invites a user to "total" a section and silently returns a wrong
figure for sections that contain ratios or already-subtotaled items.
**Recommended fix:** in `descCodes`, restrict to **leaf data codes only** (exclude header/subtotal
nodes) and **exclude `PCTC`/percentage codes**; if a section is non-summable, disable the click with a
tooltip rather than producing a number. Spot-check a couple of generated subtotals against the form
PDF before trusting them.

### MEDIUM-2 · QoQ / YoY / Total-Δ are positional, not date-based
**What's wrong:** the KPI cards compute `prev=v[v.length-2]` and `yr=v[v.length-5]`, i.e. "1 data
point back" and "4 data points back." This assumes a dense, gap-free quarterly series. A holding
company with a missing quarter, a line item not reported every quarter, or a lineage hand-off with a
reporting gap will have `v.length-5` point to the **wrong period**, so YoY/QoQ silently compare the
wrong quarters and mislabel the % change.
**Evidence:** `make_site_fry9c.py:583`.
**Recommended fix:** compute QoQ/YoY by locating the value at the date exactly 1 / 4 quarters prior
(date arithmetic on `quarter_end`) and render "n/a" when that period is absent, instead of
substituting the nearest available data point.

### LOW-1 · "Sort entities by current measure" fails silently for derived ratios
**What's wrong:** when the active measure is a derived code (e.g. `D_NPL`, or a `SUB:` dynamic
subtotal), `computeSortVals` builds `WHERE mdrm='D_NPL'`, but no such MDRM exists in the data (it is
computed), so every entity gets no value and the sort quietly collapses to default order.
**Recommended fix:** detect derived/`SUB:` codes and either compute the value per entity for the
latest quarter, or grey out the "current measure" sort option with a tooltip when the measure is
derived.

### LOW-2 · % deltas on signed quantities, and ratios with negative denominators
**What's wrong:** (a) `100*(last/prev-1)` on a measure that can be negative (net income, equity) can
flip sign or read oddly. (b) Ratio quarters where the summed denominator is ≤ 0 (e.g. negative equity
→ ROE) are dropped by the `den>0` guard, so distressed-company quarters silently disappear from ratio
series.
**Recommended fix:** for KPI deltas on potentially-signed measures show absolute change or annotate;
for non-positive denominators render the point as "n/m" so the gap is visible rather than hidden.

### LOW-3 · Internal label inconsistency: "annualized" vs "YTD"
**What's wrong:** the `D_ROA`/`D_ROE` `DERIV` labels say "annualized" (and the value IS annualized),
but the **default measure chips** (lines 640–641) label them "ROA % YTD" / "ROE % YTD." Same measure,
two contradictory labels.
**Recommended fix:** change the chip labels to "annualized" to match the computed value.

### LOW-4 · Codify the validation cell in the build's self-test
**What's wrong (gap, not an error):** the JPM `BHCK2170` golden cell validates by hand, but
`validate_build.py` should assert it automatically so a future rebuild can't silently drift.
**Note:** `PROJECT_OVERVIEW.md` lists RSSD **450810** as a validation cell — that RSSD is an FFIEC 002
filer, not a Y-9C entity, so it is not a valid Y-9C check (out of scope here, flagged only so it isn't
mistaken for a Y-9C golden cell).
**Recommended fix:** add an assertion to `validate_build.py` that JPM (1039502) `BHCK2170` at the
latest quarter equals the raw BHCF value within rounding, plus a sanity assert that `ALL` total assets
do **not** exceed total U.S. banking assets (a cheap tripwire for HIGH-1).

---

## Appearance / UX notes (FR Y-9C)

- Dark mode default, ☀/🌙 toggle, resizable + pop-out rail, KPI cards, aligned $/% panes, range
  slider, peer builder, SQL box, call-report view, and the "Built by Austin Fahrenkopf" footer are all
  present. The lineage **splice markers** (dashed verticals at merger seams) and the "Link predecessor
  RSSDs" toggle are nice touches and are correctly wired.
- `index.html` is **204 KB** because the **roster and lineage are inlined** (the hierarchy is fetched
  separately). This is a reasonable design choice for the entity model; just note it loads everything
  up front.
- The **KPI cards reflect only the first series** (first entity × first measure). With several
  overlaid series this is easy to misread — consider labeling the KPI block with the primary series
  name (it partly does) or letting the user choose which series drives the KPIs.
- Suggested live-render checks (couldn't be done statically): chart a raw HC-R ratio for ALL (should
  expose HIGH-2), build a DYN subtotal over HC-R (should expose MEDIUM-1), toggle the RSSD link on a
  merged entity and confirm the seam, and open the call-report view for a single holding company.

---

## Suggested fix order (when fixes are authorized)

1. **HIGH-1** — top-tier filter for ALL/aggregates (confirm with `CSV_RELATIONSHIPS.ZIP` first).
2. **HIGH-2** — stop summing `PCTC`/percentage codes across entities (keep the axis routing).
3. **MEDIUM-1** — make `descCodes` leaf-only and percentage-aware for dynamic subtotals.
4. **MEDIUM-2** — date-based QoQ/YoY/Total-Δ.
5. **LOW-1…4** — sort-by-derived, signed-quantity deltas, label fix, and a codified validation assert.
