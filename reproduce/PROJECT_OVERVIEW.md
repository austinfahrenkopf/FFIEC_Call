# PROJECT OVERVIEW — Bank Regulatory Data Explorers (master context)

Top-level context for the whole `External Bank Data\` workspace. Read this first, then the
per-project handoff in each folder.

## The vision
Three free, reproducible, browser-based dashboards over U.S. bank regulatory filings, built entirely
from **public Fed/FFIEC data** (no paid sources), for liquidity / ILST-style analysis and peer
comparison — usable at work (commercial use) and deployable to free GitHub Pages.

| Project | Folder | Who files it | Status | Handoff doc |
|---|---|---|---|---|
| Call Reports (031/041/051) | `FFIEC 031\` | every U.S. commercial bank | **done & deployable** | `HANDOFF_CALL.md` |
| FFIEC 002 | `FFIEC 002\` | U.S. branches/agencies of foreign banks | **done & deployable** | `HANDOFF_002.md` |
| FR Y-9C | `FR Y-9C\` | bank holding companies | explorer ready; **needs data scraper** | `HANDOFF_FRY9C_SCRAPER.md` |

`view.bat` (this folder) = one-click local launcher (menu → builds + serves each on 8001/8002/8003).

## Hard constraints / principles (these shaped every decision)
- **Free public data only.** WRDS / academic licenses are OFF-LIMITS (this is commercial bank use).
  Sources: FFIEC CDR Bulk Data (Call), Chicago Fed Complete files + NIC (002), NIC Financial Data
  Download (Y-9C), Fed MDRM dictionary.
- **Scraping rule:** some Fed/NIC endpoints are **Akamai-guarded** → drive a **real Chrome via
  Playwright** (headed, persistent profile, channel="chrome", hide webdriver, warm-up, in-page fetch).
  Do **NOT** bypass blocks with curl/wget/python-requests or archive.org mirrors. Real browser only.
- **Reproducible:** every dataset is rebuildable from scripts in its folder; upload CODE to GitHub,
  not giant data (data is regenerated or attached as parquet to the Pages site).

## The shared "v3 engine" — IMPORTANT
`make_site_call.py`, `make_site_002.py`, and `make_site_fry9c.py` are **three copies of the same
explorer**, differing only in data config (prefixes, schedules, derived ratios, entity model).
**There is no shared module** — so a fix or feature in one must be **hand-ported to the other two.**

Canonical feature set (keep all three at parity):
- Dark mode (default) + ☀/🌙 toggle.
- Left rail with **Items** and **Entities** tabs; rail is **resizable** (drag the divider) and
  **pop-out** (draggable, click-through).
- **Collapsible item-number hierarchy** that nests by item number (matrix-safe for RC-N/HC-N/etc.).
- **Single-level drill** (▾/▴ level) + Expand/Collapse all.
- One **consolidated row per item** (COMB) with a "show RCFD/RCON variants" toggle (N/A for Y-9C).
- **Multiple measures** → aligned **$ pane + % pane**; **index-to-100** growth pane; **range slider**.
- KPI cards: **Latest / QoQ / YoY / Total Δ (over range)**.
- **Peer-group builder** (saved in browser localStorage).
- **Call-report view**: form-replica, drill-down, From/To quarter columns, pop-out, CSV export.
- CSV export, SQL box (table `t`), footer "Built by Austin Fahrenkopf".

Engine internals worth knowing:
- **COMB = coalesce(RCFD, RCON[, RCFN]) per filer** = the consolidated total (≈ "the bigger one"),
  never a sum. Ratios sum components first, then divide → correct at bank, segment, or peer level.
- Hierarchy = `*_hierarchy.json` built from each form's blank PDF (structure) + the MDRM dictionary
  (full captions; CDR/bulk headers are truncated). `nest()` parents by item number, not sequence.

## Deployment playbook (GitHub Pages, free)
1. Repo must be **public** (private Pages needs a paid plan). Data here is public filings, so public
   is fine. Public = anyone can view/fork; only you can edit. To gate access, use Cloudflare Access
   (free) in front, or keep the repo private and share files directly.
2. Upload the contents of the `site_*\` folder (index.html + the parquet(s) + the hierarchy json).
3. **Files >25 MB:** use **GitHub Desktop** (100 MB limit); the web uploader caps at 25 MB.
4. Settings → Pages → Source = Deploy from a branch → main / root. Live at
   `https://austinfahrenkopf.github.io/<repo>/`. Each dashboard = its own repo/URL.
5. GitHub username is **austinfahrenkopf** (was austintfahrenkopf-prog; renamed → old Pages URLs
   don't redirect, so reshare new links).

## Environment / dependencies (Windows)
Python 3 with: `pandas`, `pyarrow`, `duckdb`, `playwright` (+ `playwright install chrome` / real
Chrome). PowerShell: chain commands with `;` not `&&`. Stop a local server with **Ctrl+C** (keeps the
terminal). DuckDB-WASM + the data load happen client-side in the browser — anyone who can open the
page can download the parquet (can't gate "view but not download" with a static site).

## Validation cells (sanity-check after any rebuild)
- Call: known PDF cell — RCFD1606 = 110787 for RSSD 450810.
- 002: same RSSD 450810 reference used during the 002 build.
- Y-9C: check a big BHC (e.g., JPMorgan RSSD 1039502) BHCK2170 (total assets) vs published value.

## Roadmap / deferred ideas (not yet built)
- Hierarchical **NPL% by loan category** (map RC-N/HC-N aging cells to RC-C/HC-C balances).
- Prefer **PDF caption** over dictionary where the dictionary is terse (Call).
- Multiple visuals on one page / persistent Power-BI-style slicer pane.
- One-workbook export (chart + KPIs + call-report snapshot); saved "boards".
- Scheduled quarterly refresh.

## Notes for a future Cowork agent (environment quirk)
The sandbox **bash mount can go stale** and serve old/truncated copies of recently-edited files, so
`node --check` via bash may fail on files that are actually fine. The **file tools (Read/Write/Edit)
are authoritative** — verify edits by reading them, not by the bash mount. Newly-created files in a
fresh folder usually read correctly; heavily-edited large files often don't.
```
```
