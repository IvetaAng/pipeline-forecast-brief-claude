"""HTML email: Gmail-safe markup and complete content."""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, HERE)

from forecast_brief.email_html import render, subject  # noqa: E402
from test_answer_key import demo_brief  # noqa: E402


class Email(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief, _ = demo_brief()
        with open(os.path.join(HERE, "fixtures", "talking_points_16.11.2026.json"), encoding="utf-8") as fh:
            cls.tp = json.load(fh)
        cls.html = render(cls.brief, cls.tp)

    def test_no_css_backgrounds(self):
        # the Gmail connector strips them; fills must use bgcolor
        self.assertNotRegex(self.html, r"background\s*(-color)?\s*:")
        self.assertIn('bgcolor="#FCEBEB"', self.html)      # red tile (Marco Commit 0.62x)

    def test_no_unsupported_layout(self):
        self.assertNotRegex(self.html, r"(float|display:\s*(flex|grid))")

    def test_subject_and_test_banner(self):
        self.assertEqual(subject(self.brief), "[TEST] Forecast brief 16.11.2026 · Q4: 45 days left")
        self.assertIn("TEST MODE", self.html)
        live = dict(self.brief, test_mode=False, subject_prefix="")
        self.assertNotIn("TEST MODE", render(live))
        self.assertEqual(subject(live), "Forecast brief 16.11.2026 · Q4: 45 days left")

    def test_every_flagged_deal_and_change_linked(self):
        for r in self.brief["reps"]:
            for item in r["flagged_deals"] + r["changes"]:
                self.assertIn(f'href="{item["url"]}"', self.html, item["deal"])

    def test_numbers_and_talking_points(self):
        for s in ["0.83×", "1.41×", "2.69×", "0.62×", "1.34×", "1.99×", "715k", "490k",
                  "top 3 deals are 68%", "top 3 deals are 71%", "Pushed out of Q4"]:
            self.assertIn(s, self.html)
        for points in self.tp.values():
            for p in points:
                self.assertIn(p.split(",")[0].replace("&", "&amp;"), self.html)

    def test_names_escaped(self):
        b = json.loads(json.dumps(self.brief))
        b["reps"][0]["flagged_deals"][0]["deal"] = "A&B <script> - X"
        self.assertNotIn("<script>", render(b))


if __name__ == "__main__":
    unittest.main()
