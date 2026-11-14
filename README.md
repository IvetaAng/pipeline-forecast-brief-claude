# Pipeline forecast brief (Claude + HubSpot)

Weekly forecast brief for sales managers, built with Claude, HubSpot Free, Google Drive and Gmail.
Rebuild of the n8n version. Full write-up follows in Phase 5.

## Status

- [x] Phase 0: setup
- [x] Phase 1: demo data (HubSpot import, quotas, snapshot 09.11.2026)
- [x] Phase 2: analysis script, validated against the answer key as of 16.11.2026
- [x] Phase 3: HTML email template (preview in `docs/preview/`)
- [ ] Phase 4: scheduled task (Monday 07:00 Europe/Zurich)
- [ ] Phase 5: README, public repo

## How a weekly run works

1. Claude fetches the inputs through its connectors and saves them as files:
   - HubSpot: one deal search (`sales_rep` in the reps from the Quotas sheet), about 2 pages of 200
   - Google Drive: Quotas sheet as CSV, newest `snapshot_*.csv` before the run date
2. `run_brief.py` does all calculations (deterministic, Python standard library only)
3. Claude writes 2–3 talking points per rep from the flags (`talking_points.json`), then
   `python3 render_email.py --brief brief.json --talking-points talking_points.json --html email.html`
   prints the subject and writes the email, which Claude sends with the Gmail connector
4. Unless in test mode: Claude saves this week's snapshot to Drive and writes the updates back to HubSpot

```
python3 run_brief.py \
  --deals page1.json page2.json \
  --quotas quotas.csv \
  --snapshot snapshot_2026-11-09.csv \
  --as-of 16.11.2026 --test-mode \
  --out brief.json --snapshot-out out/ --markdown out/key.md
```

Settings live in `config/settings.json` (asOfDate, testMode, stage IDs, thresholds, flag rules).
The output is described in `docs/output.md`.

## Tests

```
python3 -m unittest discover -s tests -v
```

- `tests/test_answer_key.py`: the full demo run must reproduce `tests/expected/answer_key_16.11.2026.md` line by line
- `tests/test_email.py`: Gmail-safe HTML (fills via `bgcolor`, no CSS backgrounds, no float/flex/grid), every flagged deal and change linked
- `tests/test_rules.py`: time zone, quarter boundaries, scope, flags, waterfall, write-back on synthetic data
