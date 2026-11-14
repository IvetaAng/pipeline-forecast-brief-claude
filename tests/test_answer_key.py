"""Full run on the demo fixtures must reproduce the answer key (as of 16.11.2026) line by line.

Fixtures: one HubSpot export taken 14.11.2026 (2 pages), the Quotas sheet, snapshot 09.11.2026.
Order inside each list is ignored; every line must match exactly.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from forecast_brief.brief import build  # noqa: E402
from forecast_brief.load import load_deals, load_quotas, load_snapshot, parse_dmy  # noqa: E402
from forecast_brief.report import to_markdown  # noqa: E402

FIX = os.path.join(HERE, "fixtures")


def demo_brief():
    with open(os.path.join(ROOT, "config", "settings.json"), encoding="utf-8") as fh:
        settings = json.load(fh)
    as_of = parse_dmy("16.11.2026")
    deals, warnings = load_deals([os.path.join(FIX, "deals_16.11.2026.json")], settings)
    quotas = load_quotas(os.path.join(FIX, "quotas.csv"), as_of)
    snap_date, snapshot = load_snapshot(os.path.join(FIX, "snapshot_2026-11-09.csv"), settings)
    return build(deals, quotas, snap_date, snapshot, settings, as_of, True, warnings), settings


def sections(md):
    """Split markdown into blocks at headings / 'xxx:' sub-headings; each block = sorted lines."""
    out, key, block = {}, "top", []
    for line in md.splitlines():
        if line.startswith("## "):
            out[key] = sorted(block); key, block = line, []
        elif line in ("Changes since last week:", "Flagged deals:"):
            out[key] = sorted(block); key, block = key.split(" | ")[0] + " | " + line, []
        elif line.strip():
            block.append(line)
    out[key] = sorted(block)
    return out


class AnswerKey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief, cls.settings = demo_brief()

    def test_markdown_matches_answer_key(self):
        with open(os.path.join(HERE, "expected", "answer_key_16.11.2026.md"), encoding="utf-8") as fh:
            expected = sections(fh.read())
        actual = sections(to_markdown(self.brief))
        self.assertEqual(sorted(expected), sorted(actual))
        for k in expected:
            self.assertEqual(expected[k], actual[k], k)

    def test_top3_to_discuss(self):
        top = {r["rep"]: [(t["deal"].split(" - ")[0], t["reason"]) for t in r["top3_to_discuss"]] for r in self.brief["reps"]}
        self.assertEqual(top["Anna Keller"], [("Lemaniatech", "Commit stalled earlier"), ("Rigimech", "Pushed 4×"),
                                              ("Helvetinvest", "Unlikely to close in Q4")])
        self.assertEqual(top["Marco Rossi"], [("Toggenfracht", "Pushed 4×"), ("Kesslerlogistik", "Category above stage"),
                                              ("Schwarzwalddata", "Unlikely to close in Q4")])

    def test_coverage_colours(self):
        col = {r["rep"]: [c["status"] for c in r["coverage"]] for r in self.brief["reps"]}
        self.assertEqual(col["Anna Keller"], ["amber", "amber", "amber"])   # 0.83 / 1.41 / 2.69
        self.assertEqual(col["Marco Rossi"], ["red", "amber", "red"])       # 0.62 / 1.34 / 1.99

    def test_snapshot_and_writeback(self):
        # 150 open last week - Brienzsysteme won - Isartrans lost - Ruhrmaschinen lost + Seelandsysteme new
        self.assertEqual(len(self.brief["snapshot"]["rows"]), 148)
        self.assertEqual(self.brief["snapshot"]["filename"], "snapshot_2026-11-16.csv")
        # Phase 1 import already stamped this week's changes -> nothing to write (no double counting)
        self.assertEqual(self.brief["hubspot_updates"], [])
        self.assertEqual(self.brief["warnings"], [])

    def test_deal_links(self):
        f = self.brief["reps"][0]["flagged_deals"][0]
        self.assertEqual(f["url"], f"https://app-eu1.hubspot.com/contacts/149538010/record/0-3/{f['record_id']}")

    def test_waterfall_adds_up(self):
        for r in self.brief["reps"]:
            self.assertEqual(r["pipeline_last_week"] + sum(r["waterfall"].values()), r["pipeline_now"])

    def test_no_next_year_flags(self):
        for r in self.brief["reps"]:
            for f in r["flagged_deals"]:
                self.assertLessEqual(parse_dmy(f["close"]), parse_dmy(r["quarter_end"]), f["deal"])


if __name__ == "__main__":
    unittest.main()
