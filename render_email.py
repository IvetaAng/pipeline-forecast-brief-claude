"""Render brief.json as the HTML email: python3 render_email.py --brief brief.json --talking-points tp.json --html email.html"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from forecast_brief.email_html import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
