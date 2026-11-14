"""Read the three inputs: HubSpot deals (JSON), Quotas sheet (CSV), last snapshot (CSV).

HubSpot stores close dates as UTC timestamps (e.g. 2026-09-30T22:00:00Z). They are
converted to the local timezone (Europe/Zurich) BEFORE any quarter logic, otherwise a
deal closing on 01.10 local time would land in Q3.
"""
import csv
import json
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def parse_dmy(s):
    d, m, y = s.strip().split(".")
    return date(int(y), int(m), int(d))


def fmt(d):
    return d.strftime("%d.%m.%Y") if d else ""


def to_local_date(value, tz):
    """HubSpot date/datetime value -> local calendar date (None if empty)."""
    if value in (None, ""):
        return None
    v = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):          # date-only property, no timezone
        return date.fromisoformat(v)
    if re.fullmatch(r"\d{10,13}", v):                   # epoch (s or ms)
        ts = int(v) / (1000 if len(v) == 13 else 1)
        return datetime.fromtimestamp(ts, timezone.utc).astimezone(tz).date()
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).date()


def _int(v):
    if v in (None, ""):
        return 0
    return int(round(float(re.sub(r"[^\d.\-]", "", str(v)) or 0)))


# ---------------------------------------------------------------- HubSpot
def _records(obj):
    """Accept any shape the connector produces: a search response {'results': [...]},
    the MCP text wrapper [{'type': 'text', 'text': '...'}], a list of pages, or a list of records."""
    if isinstance(obj, str):
        return _records(json.loads(obj))
    if isinstance(obj, list):
        out = []
        for x in obj:
            out += _records(x)
        return out
    if isinstance(obj, dict):
        if "results" in obj:
            return list(obj["results"])
        if obj.get("type") == "text":
            return _records(obj["text"])
        if "properties" in obj:
            return [obj]
    raise ValueError(f"Unrecognised HubSpot export shape: {str(obj)[:120]}")


def load_deals(paths, settings):
    """Returns (deals, warnings). Each deal is a plain dict, close dates in local time."""
    tz = ZoneInfo(settings["timezone"])
    stages = settings["stages"]
    stage_idx = {s["id"]: i for i, s in enumerate(stages)}
    cats = settings["categories"]
    seen, deals, warnings = set(), [], []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            recs = _records(json.load(fh))
        for r in recs:
            rid = str(r.get("id") or r["properties"].get("hs_object_id"))
            if rid in seen:
                continue
            seen.add(rid)
            p = r["properties"]
            if p.get("pipeline") != settings["pipeline"]:
                continue
            st = p.get("dealstage")
            if st == settings["wonStage"]:
                status, stage = "Won", None
            elif st == settings["lostStage"]:
                status, stage = "Lost", None
            elif st in stage_idx:
                status, stage = "Open", stage_idx[st]
            else:
                warnings.append(f"{p.get('dealname')}: unknown deal stage '{st}', skipped")
                continue
            deals.append(dict(
                id=rid,
                name=p.get("dealname") or "",
                rep=(p.get("sales_rep") or "").strip(),
                status=status,
                stage=stage,
                amount=_int(p.get("amount")),
                close=to_local_date(p.get("closedate"), tz),
                created=to_local_date(p.get("createdate"), tz),
                cat=cats.get(p.get("hs_manual_forecast_category")),
                moved=[to_local_date(p.get(s["movedProperty"]), tz) for s in stages],
                original_close=to_local_date(p.get("original_close_date"), tz),
                pushes=_int(p.get("close_date_push_count")),
                slipped=_int(p.get("total_days_slipped")),
            ))
    return deals, warnings


# ---------------------------------------------------------------- Quotas
def load_quotas(path, as_of):
    """Quota row per rep for the quarter that contains as_of.
    Columns: Sales Rep, Quarter, Quarter start, Quarter end, Quota."""
    out = {}
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
            if not row.get("Sales Rep") or not row.get("Quarter start"):
                continue
            start, end = parse_dmy(row["Quarter start"]), parse_dmy(row["Quarter end"])
            if start <= as_of <= end:
                out[row["Sales Rep"]] = dict(quarter=row["Quarter"], start=start, end=end, quota=_int(row["Quota"]))
    if not out:
        raise ValueError(f"No quota rows cover {fmt(as_of)}")
    return out


# ---------------------------------------------------------------- Snapshot
SNAPSHOT_COLUMNS = ["snapshot_date", "record_id", "deal_name", "sales_rep", "deal_stage", "forecast_category",
                    "amount", "close_date", "close_date_push_count", "total_days_slipped"]


def load_snapshot(path, settings):
    """Last week's snapshot -> (snapshot_date, {record_id: row})."""
    names = [s["name"] for s in settings["stages"]]
    rows, snap_date = {}, None
    with open(path, encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            snap_date = snap_date or parse_dmy(r["snapshot_date"])
            rows[str(r["record_id"]).strip()] = dict(
                id=str(r["record_id"]).strip(),
                name=r["deal_name"],
                rep=r["sales_rep"].strip(),
                stage=names.index(r["deal_stage"]) if r["deal_stage"] in names else None,
                cat=r["forecast_category"] or None,
                amount=_int(r["amount"]),
                close=parse_dmy(r["close_date"]) if r["close_date"] else None,
                pushes=_int(r["close_date_push_count"]),
                slipped=_int(r["total_days_slipped"]),
            )
    return snap_date, rows
