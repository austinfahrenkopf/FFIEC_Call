#!/usr/bin/env python3
"""
quick_enrich.py — re-enrich ffiec_call_segments_long.parquet using the existing
ffiec_call_dictionary.csv, without downloading the Fed MDRM.zip.

Use this instead of enrich_call.py when the Fed MDRM download is unavailable (e.g.
network restrictions). Produces the same ffiec_call_segments.parquet output;
the dictionary CSV was already written by a previous enrich_call.py run.

Run: python quick_enrich.py  (from FFIEC 031/ directory)
"""
import pandas as pd

SEG_IN  = "ffiec_call_segments_long.parquet"
SEG_OUT = "ffiec_call_segments.parquet"
DICT    = "ffiec_call_dictionary.csv"
CAP     = "ffiec_call_captions.csv"

dic = pd.read_csv(DICT)
sched_map = dict(zip(dic["mdrm"], dic["schedule"].fillna("")))
title_map = dict(zip(dic["mdrm"], dic["title"].fillna("")))

try:
    capdf = pd.read_csv(CAP)
    capt_map = dict(zip(capdf["mdrm"], capdf["caption"]))
except Exception:
    capt_map = {}

# Entries for synthetic RCFD deposit codes (not in MDRM but derived from RCON+RCFN)
for base in ("2200", "6631", "6636"):
    rcfd = "RCFD" + base
    rcon = "RCON" + base
    if rcon in sched_map:
        sched_map.setdefault(rcfd, sched_map[rcon])
        title_map.setdefault(rcfd, (title_map.get(rcon, "") + " (domestic+IBF, derived)").strip())

def info_schedule(code):
    if code.startswith("COMB"):
        base = code[4:]
        for pfx in ("RCFD", "RCON", "RIAD"):
            s = sched_map.get(pfx + base, "")
            if s: return s
    return sched_map.get(code, "")

def info_title(code):
    if code.startswith("COMB"):
        base = code[4:]
        for pfx in ("RCFD", "RCON", "RIAD"):
            t = title_map.get(pfx + base, "") or capt_map.get(pfx + base, "")
            if t: return t + " (RCFD/RCON/RIAD combined)"
        return "Combined RCFD/RCON/RIAD (" + base + ")"
    return title_map.get(code, "") or capt_map.get(code, "")

seg = pd.read_parquet(SEG_IN)
seg["schedule"]    = seg["mdrm"].map(info_schedule)
seg["description"] = seg["mdrm"].map(info_title)
seg.to_parquet(SEG_OUT, index=False)
print(f"wrote {SEG_OUT}: {len(seg):,} rows, {seg['mdrm'].nunique()} codes")
