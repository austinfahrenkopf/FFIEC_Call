# Local dashboard deployment (SharePoint/OneDrive folder + one-click launcher)

## Target folder layout (inside your synced SharePoint/OneDrive folder)

```
FFIEC_Call\                    <- your synced SharePoint folder
   Open Dashboard.bat          <- the ONLY thing users need to see / double-click
   app\                        <- all dashboard files (optionally mark Hidden: attrib +h app)
       serve.ps1
       index.html
       ffiec_call.parquet
       ffiec_call_hierarchy.json
       custom_formulas.json    <- created automatically when a user clicks "Save formulas"
```

## Setup steps (once)

1. Copy the `app\` subfolder into `FFIEC_Call\`.
2. Put `Open Dashboard.bat` at the top level (next to `app\`, not inside it).
3. (Optional, to hide the plumbing) In a terminal in `FFIEC_Call\`: `attrib +h app`
4. (Recommended) Right-click `Open Dashboard.bat` -> Send to -> Desktop (create shortcut).
   Rename the shortcut "FFIEC 031 Dashboard".
5. OneDrive: right-click the `FFIEC_Call` folder -> **"Always keep on this device"**
   so the parquet is stored locally (not cloud-only).

## How it works
Double-click the launcher -> a terminal opens running serve.ps1 -> the browser opens to
http://localhost:8001/ automatically. Keep the terminal window open while using it.

"Save formulas" writes `custom_formulas.json` into `app\` (inside the synced folder),
so OneDrive/SharePoint syncs it to other machines.

## Updating to a new build
Replace `app\index.html`, `app\ffiec_call.parquet`, and `app\ffiec_call_hierarchy.json`.
Keep `serve.ps1`, `Open Dashboard.bat`, and `custom_formulas.json` as they are.
