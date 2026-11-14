# Weekly run (followed by the Claude scheduled task)

The scheduled task clones this repo and follows these steps. Keep HubSpot calls to the minimum below.
Work in a scratch folder, e.g. `/tmp/brief/`. Dates in messages are dd.mm.yyyy.

## 0. Settings
Read `config/settings.json`: `asOfDate` (empty = today in Europe/Zurich) and `testMode`.
In test mode NOTHING is written to Drive or HubSpot; the email gets "[TEST]" and a banner.

## 1. Quotas (Google Drive)
`download_file_content` fileId `1ydIPRgIyxgmGq6cgqEEt7U_GkpEgYf4guj_4SkhqGqc`, exportMimeType `text/csv`.
Use the saved CSV file path as `--quotas`. The reps in this sheet for the quarter that contains asOfDate are
the reps for the HubSpot filter in step 3.

## 2. Last week's snapshot (Google Drive)
`search_files` query `parentId = '1PHNVdDfMj4gURJgcBZKA8hQk_7I-bBMw'`. Take the newest `snapshot_YYYY-MM-DD.csv`
whose date is BEFORE asOfDate, `download_file_content` it, use the saved path as `--snapshot`.

## 3. Deals (HubSpot): one search, paged
`search_crm_objects`, objectType `DEAL`, limit 200, sorts `hs_object_id` ASCENDING,
filterGroups `[{"filters":[{"propertyName":"sales_rep","operator":"IN","values":[<reps from step 1>]}]}]`,
properties: dealname, sales_rep, pipeline, dealstage, amount, closedate, hs_manual_forecast_category, createdate,
moved_to_qualification, moved_to_discovery, moved_to_solution_validation, moved_to_business_case,
moved_to_contract_negotiation, original_close_date, close_date_push_count, total_days_slipped.
Repeat with `offset` = the returned offset until offset >= total (354 deals = 2 pages on 14.11.2026).
Large results are saved to files by the connector: pass those file paths directly to `--deals`, in any order.
Do not re-type or summarise the data. Check that the number of deals loaded equals `total`.

## 4. Analysis
```
python3 run_brief.py --deals <page files> --quotas <quotas.csv> --snapshot <snapshot.csv> \
  --out /tmp/brief/brief.json --snapshot-out /tmp/brief --markdown /tmp/brief/key.md
```
If `warnings` in brief.json is not empty, list them in the run summary.
If asOfDate is 16.11.2026 (demo replay): `python3 check_answer_key.py --markdown /tmp/brief/key.md` → PASS / FAIL.

## 5. Talking points
Write `/tmp/brief/talking_points.json`: `{"<rep>": ["...", "..."], ...}`, 2–3 per rep, as short questions or
asks a sales manager would raise in the 1:1. Base them on the coverage tiles, concentration, top 3 deals and
changes. Use ONLY numbers that appear in brief.json; never calculate new ones. No deal not in brief.json.

## 6. Email
```
python3 render_email.py --brief /tmp/brief/brief.json --talking-points /tmp/brief/talking_points.json \
  --html /tmp/brief/email.html [--check PASS|FAIL]
```
The command prints the subject. Gmail `send_message`: to the recipient named in the scheduled task's prompt, subject as printed,
`htmlBody` = the full content of email.html (unchanged), `body` = one plain-text line:
"Forecast brief as of <date>. Open in an HTML-capable mail client."

## 7. Only when testMode is false
- Snapshot: `create_file` title `snapshot_<asOf YYYY-MM-DD>.csv`, parentId `1PHNVdDfMj4gURJgcBZKA8hQk_7I-bBMw`,
  contentMimeType `text/csv`, disableConversionToGoogleType true, textContent = the CSV written to /tmp/brief.
  Skip if a file with that title already exists (demo replays).
- HubSpot write-back: `manage_crm_objects` updateRequest with the `hubspot_updates` list from brief.json
  (objectType deals, max 10 per request). Standing approval by Iveta (14.11.2026) for exactly this list;
  write nothing else. Only fills gaps, see `src/forecast_brief/writeback.py`.

## 8. If a step fails
Send a short plain-text email to the same recipient, subject "[FAILED] Forecast brief <date>", saying which step
failed and the error. Do not send a partial brief.

## 9. Run summary
End with: subject sent, answer-key check (if replay), number of flagged deals, snapshot written yes/no,
HubSpot updates written (count), warnings.
