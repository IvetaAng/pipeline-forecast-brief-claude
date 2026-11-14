"""Run the forecast brief analysis without installing anything: python3 run_brief.py --help"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from forecast_brief.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
