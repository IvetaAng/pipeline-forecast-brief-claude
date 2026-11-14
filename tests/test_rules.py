"""Edge cases on small synthetic data."""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from forecast_brief.brief import build  # noqa: E402
from forecast_brief.load import load_deals, to_local_date  # noqa: E402

with open(os.path.join(ROOT, "config", "settings.json"), encoding="utf-8") as _fh:
    SETTINGS = json.load(_fh)
Z = ZoneInfo("Europe/Zurich")
AS_OF = date(2026, 11, 16)
Q4 = dict(quarter="2026 Q4", start=date(2026, 10, 1), end=date(2026, 12, 31), quota=500_000)


def rec(i, rep="Anna Keller", stage="qualifiedtobuy", amount=100_000, close="2026-12-14T23:00:00Z",
        cat="PIPELINE", moved=("2026-10-01", "2026-11-01", None, None, None), pushes=0, slipped=0, orig=None):
    p = dict(dealname=f"Deal {i}", sales_rep=rep, pipeline="default", dealstage=stage, amount=str(amount),
             closedate=close, hs_manual_forecast_category=cat, createdate="2026-09-30T22:00:00Z",
             close_date_push_count=str(pushes), total_days_slipped=str(slipped), original_close_date=orig)
    for s, m in zip(SETTINGS["stages"], moved):
        p[s["movedProperty"]] = m
    return {"id": i, "properties": p}


def load(records, shape=lambda r: {"results": r}):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(shape(records), fh)
    return load_deals([fh.name], SETTINGS)[0]


def snap(i, stage=1, cat="Pipeline", amount=100_000, close=date(2026, 12, 15), pushes=0, slipped=0, rep="Anna Keller"):
    return {str(i): dict(id=str(i), name=f"Deal {i}", rep=rep, stage=stage, cat=cat, amount=amount, close=close,
                         pushes=pushes, slipped=slipped)}


def run(deals, snapshot, quotas=None):
    return build(deals, quotas or {"Anna Keller": Q4}, date(2026, 11, 9), snapshot, SETTINGS, AS_OF, True)


class Timezone(unittest.TestCase):
    def test_utc_to_zurich(self):
        self.assertEqual(to_local_date("2026-09-30T22:00:00Z", Z), date(2026, 10, 1))   # CEST: Q4, not Q3
        self.assertEqual(to_local_date("2026-12-31T23:00:00Z", Z), date(2027, 1, 1))    # CET: next year
        self.assertEqual(to_local_date("2026-10-15", Z), date(2026, 10, 15))            # date-only untouched
        self.assertEqual(to_local_date("1790805600000", Z), date(2026, 10, 1))          # epoch ms

    def test_quarter_boundary_in_coverage(self):
        deals = load([rec(1, close="2026-09-30T22:00:00Z"), rec(2, close="2026-12-31T23:00:00Z")])
        r = run(deals, {})["reps"][0]
        self.assertEqual(r["coverage"][2]["deals"], 1)        # only deal 1 is in Q4


class Loader(unittest.TestCase):
    def test_export_shapes(self):
        rs = [rec(1), rec(2)]
        for shape in (lambda r: {"results": r}, lambda r: r,
                      lambda r: [{"type": "text", "text": json.dumps({"results": r})}],
                      lambda r: [{"results": r[:1]}, {"results": r[1:]}]):
            self.assertEqual(len(load(rs, shape)), 2)

    def test_other_pipeline_and_duplicates_skipped(self):
        other = rec(3); other["properties"]["pipeline"] = "partner"
        self.assertEqual(len(load([rec(1), rec(1), other])), 1)


class Scope(unittest.TestCase):
    def test_partner_reps_excluded(self):
        deals = load([rec(1), rec(2, rep="Lena Huber", amount=999_000)])
        b = run(deals, {})
        self.assertEqual([r["rep"] for r in b["reps"]], ["Anna Keller"])
        self.assertEqual(b["reps"][0]["coverage"][2]["amount"], 100_000)
        self.assertEqual([x["sales_rep"] for x in b["snapshot"]["rows"]], ["Anna Keller"])

    def test_medians_only_from_quota_reps(self):
        won_anna = rec(1, stage="closedwon", cat="CLOSED", close="2026-06-29T22:00:00Z",
                       moved=("2026-01-01", "2026-01-11", "2026-02-10", "2026-03-12", "2026-04-11"))
        won_lena = rec(2, rep="Lena Huber", stage="closedwon", cat="CLOSED", close="2026-06-29T22:00:00Z",
                       moved=("2026-01-01", "2026-03-01", "2026-05-01", "2026-06-01", "2026-06-15"))
        med = [s["median_days"] for s in run(load([won_anna, won_lena]), {})["stage_medians"]]
        self.assertEqual(med, [10, 30, 30, 30, 80])

    def test_next_year_not_flagged_overdue_flagged(self):
        deals = load([rec(1, close="2027-01-14T23:00:00Z"), rec(2, close="2026-10-30T23:00:00Z")])
        flagged = run(deals, {})["reps"][0]["flagged_deals"]
        self.assertEqual([f["deal"] for f in flagged], ["Deal 2"])
        self.assertEqual(flagged[0]["flags"][0][0], "Close date passed")


class Changes(unittest.TestCase):
    def test_pushed_out_and_waterfall(self):
        deals = load([rec(1, close="2027-02-11T23:00:00Z"), rec(2, amount=80_000), rec(4)])
        s = {**snap(1), **snap(2), **snap(3, rep="Anna Keller")}
        r = run(deals, s)["reps"][0]
        types = sorted(c["type"] for c in r["changes"])
        self.assertEqual(types, ["Amount cut", "New", "Pushed out of Q4", "Reassigned"])
        self.assertEqual(r["waterfall"], {"new": 100_000, "amount_change": -20_000, "pushed_out": -100_000,
                                          "reassigned": -100_000})


class WriteBack(unittest.TestCase):
    def test_push_recorded_once(self):
        deals = load([rec(1, close="2026-12-29T23:00:00Z")])          # close moved 15.12 -> 30.12
        u = run(deals, snap(1))["hubspot_updates"]
        self.assertEqual(u[0]["properties"], {"close_date_push_count": 1, "total_days_slipped": 15,
                                              "original_close_date": "2026-12-15"})
        deals = load([rec(1, close="2026-12-29T23:00:00Z", pushes=1, slipped=15, orig="2026-12-15")])
        self.assertEqual(run(deals, snap(1))["hubspot_updates"], [])  # already recorded -> nothing

    def test_stage_stamp_only_when_empty(self):
        deals = load([rec(1, stage="presentationscheduled", moved=("2026-10-01", "2026-11-01", None, None, None))])
        u = run(deals, snap(1, stage=1))["hubspot_updates"]
        self.assertEqual(u[0]["properties"], {"moved_to_solution_validation": "2026-11-16"})
        deals = load([rec(1, stage="presentationscheduled", moved=("2026-10-01", "2026-11-01", "2026-11-12", None, None))])
        self.assertEqual(run(deals, snap(1, stage=1))["hubspot_updates"], [])


class Coverage(unittest.TestCase):
    def test_quota_reached(self):
        deals = load([rec(1, stage="closedwon", cat="CLOSED", close="2026-11-09T23:00:00Z",
                          moved=("2026-09-01", "2026-09-10", "2026-10-01", "2026-10-15", "2026-11-01"), amount=600_000)])
        r = run(deals, {})["reps"][0]
        self.assertEqual(r["remaining"], -100_000)
        self.assertEqual([c["status"] for c in r["coverage"]], ["quota reached"] * 3)


if __name__ == "__main__":
    unittest.main()
