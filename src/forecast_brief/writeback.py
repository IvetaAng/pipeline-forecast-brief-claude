"""This week's snapshot rows and the HubSpot write-back updates.

Write-back rules (only fill gaps, never overwrite):
- Stage changed since last week (or new deal) and the 'Moved to <stage>' field is empty
  -> stamp it with the as-of date.
- Close date moved LATER since last week and HubSpot's push count still equals the
  snapshot's -> push count +1, total days slipped += days moved, original close date
  = last week's close date if empty. If the push count already went up, someone (or an
  import) recorded the push already, so nothing is written. This makes re-runs safe.
"""
from .load import SNAPSHOT_COLUMNS, fmt


def snapshot_rows(deals, reps, as_of, stage_names):
    rows = []
    for d in sorted(deals, key=lambda x: (x["rep"], x["close"], x["name"])):
        if d["status"] != "Open" or d["rep"] not in reps:
            continue
        rows.append(dict(zip(SNAPSHOT_COLUMNS, [
            fmt(as_of), d["id"], d["name"], d["rep"], stage_names[d["stage"]], d["cat"] or "", d["amount"], fmt(d["close"]),
            d["pushes"], d["slipped"]])))
    return rows


def hubspot_updates(deals, reps, snapshot, as_of, settings):
    stages = settings["stages"]
    updates = []
    for d in deals:
        if d["status"] != "Open" or d["rep"] not in reps:
            continue
        s = snapshot.get(d["id"])
        props, why = {}, []
        if (s is None or s["stage"] != d["stage"]) and not d["moved"][d["stage"]]:
            props[stages[d["stage"]]["movedProperty"]] = as_of.isoformat()
            why.append(f"entered {stages[d['stage']]['name']}")
        if s and s["close"] and d["close"] > s["close"] and d["pushes"] == s["pushes"]:
            days = (d["close"] - s["close"]).days
            props["close_date_push_count"] = d["pushes"] + 1
            props["total_days_slipped"] = d["slipped"] + days
            if not d["original_close"]:
                props["original_close_date"] = s["close"].isoformat()
            why.append(f"close date pushed {fmt(s['close'])} → {fmt(d['close'])} (+{days}d)")
        if props:
            updates.append(dict(record_id=d["id"], deal=d["name"], properties=props, reason="; ".join(why)))
    return updates
