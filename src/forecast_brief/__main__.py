"""Command line entry point.

python3 run_brief.py --deals page1.json page2.json --quotas quotas.csv --snapshot snapshot_2026-11-09.csv \
    --as-of 16.11.2026 --test-mode --out brief.json --snapshot-out out/
"""
import argparse
import csv
import json
import os
import sys
from datetime import date

from .brief import build
from .load import SNAPSHOT_COLUMNS, load_deals, load_quotas, load_snapshot, parse_dmy
from .report import to_markdown


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Weekly forecast brief: deterministic analysis")
    ap.add_argument("--deals", nargs="+", required=True, help="HubSpot deal export(s), JSON")
    ap.add_argument("--quotas", required=True, help="Quotas sheet, CSV")
    ap.add_argument("--snapshot", required=True, help="Last week's snapshot CSV")
    ap.add_argument("--settings", default=os.path.join(here, "..", "..", "config", "settings.json"))
    ap.add_argument("--as-of", help="dd.mm.yyyy (default: settings asOfDate, or today if that is empty)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--test-mode", dest="test_mode", action="store_true", default=None)
    mode.add_argument("--live", dest="test_mode", action="store_false")
    ap.add_argument("--out", default="brief.json")
    ap.add_argument("--snapshot-out", help="folder to write this week's snapshot CSV into")
    ap.add_argument("--markdown", help="also write the answer-key style markdown here")
    a = ap.parse_args(argv)

    with open(a.settings, encoding="utf-8") as fh:
        settings = json.load(fh)
    as_of = parse_dmy(a.as_of or settings.get("asOfDate") or date.today().strftime("%d.%m.%Y"))
    test_mode = settings.get("testMode", True) if a.test_mode is None else a.test_mode

    deals, warnings = load_deals(a.deals, settings)
    quotas = load_quotas(a.quotas, as_of)
    snap_date, snapshot = load_snapshot(a.snapshot, settings)
    brief = build(deals, quotas, snap_date, snapshot, settings, as_of, test_mode, warnings)

    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(brief, fh, ensure_ascii=False, indent=1)
    if a.snapshot_out:
        os.makedirs(a.snapshot_out, exist_ok=True)
        path = os.path.join(a.snapshot_out, brief["snapshot"]["filename"])
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=SNAPSHOT_COLUMNS)
            w.writeheader()
            w.writerows(brief["snapshot"]["rows"])
    if a.markdown:
        with open(a.markdown, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(brief))

    s = brief
    print(f"{s['subject_prefix']}Brief as of {s['as_of']} (snapshot {s['last_snapshot']}): "
          f"{len(s['reps'])} reps, {sum(len(r['flagged_deals']) for r in s['reps'])} flagged deals, "
          f"{len(s['snapshot']['rows'])} snapshot rows, {len(s['hubspot_updates'])} HubSpot updates, "
          f"{len(s['warnings'])} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
