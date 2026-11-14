# brief.json

Amounts are whole numbers (CHF). Dates are dd.mm.yyyy. Deal links use the HubSpot EU record URL.

| Key | What it is |
|---|---|
| `as_of`, `last_snapshot`, `quarter`, `quarter_end`, `days_left` | Run context |
| `test_mode`, `subject_prefix` | `[TEST] ` prefix when nothing may be written |
| `stage_medians[]` | Per stage: `median_days` in stage for won deals, `won_deals_need_days` from entering the stage to signature, `won_deals_counted` |
| `reps[]` | One block per rep in the Quotas sheet (see below) |
| `snapshot.filename`, `snapshot.rows[]` | This week's snapshot for the Drive `snapshots` folder |
| `hubspot_updates[]` | `record_id`, `deal`, `properties` to write, `reason` |
| `warnings[]` | Data problems (missing close date, missing stage date, unknown stage) |

## Per rep

| Key | What it is |
|---|---|
| `quota`, `won`, `bookings_pct`, `remaining`, `won_deals[]` | Bookings to target |
| `coverage[]` | Commit, Best case (incl. Commit), Pipeline: `amount`, `x` (coverage on remaining), `deals`, `status` (green, amber, red, quota reached) |
| `expected_landing`, `expected_landing_pct` | Won + Commit |
| `concentration` | `top3[]` of Best case, `pct`, `flag` (over 60%) |
| `pipeline_last_week`, `pipeline_now`, `waterfall` | Open current-quarter pipeline and what moved it (non-zero buckets only: new, pulled_in, amount_change, pushed_out, lost, won, reassigned) |
| `changes[]` | `type`, `deal`, `url`, `amount`, `detail`; sorted Won, Lost, Pushed out, Downgraded, Amount cut, Reassigned, Upgraded, Amount increased, Pulled in, New, Stage moved |
| `flagged_deals[]` | Current-quarter and overdue open deals with at least one flag: `flags` = list of [tag, text] |
| `top3_to_discuss[]` | Same fields as flagged deals plus `reason`: one deal per flag type in order Commit/Best case stalled earlier → Pushed N× → Category above stage → Unlikely to close; biggest amount first; overdue deals excluded |
