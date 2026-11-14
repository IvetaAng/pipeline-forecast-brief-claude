"""Compare a run with the answer key: python3 check_answer_key.py --markdown out/key.md
Prints PASS, or FAIL plus every missing/unexpected line. Exit code 0 = PASS."""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))

from forecast_brief.report import compare  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--markdown", required=True, help="written by run_brief.py --markdown")
ap.add_argument("--expected", default=os.path.join(HERE, "tests", "expected", "answer_key_16.11.2026.md"))
a = ap.parse_args()
with open(a.markdown, encoding="utf-8") as fa, open(a.expected, encoding="utf-8") as fe:
    diffs = compare(fa.read(), fe.read())
print("PASS" if not diffs else f"FAIL ({len(diffs)} differences)")
for d in diffs:
    print(" ", d)
sys.exit(1 if diffs else 0)
