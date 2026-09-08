#!/usr/bin/env python3
"""Judge the first printed phalanx from the seven coupon readings.

The user measures; this decides. Prints one markdown row per reading, ready to
paste under the coupon section of docs/hand-v3/v8-results.md, then a summary.
Exit 0 only when all seven items pass; a missing or single reading is vacuous
and exits 1, because a coupon nobody finished measuring has not passed.

    python3 scripts/analyse_coupon.py --c1 4.52 4.48 --c2 yes --c3 8.05 8.12 \\
        --c4 yes --c5 yes --c6 yes --c7 yes
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.domain.hand_instances import HAND_INSTANCES  # noqa: E402
from src.verification.coupon_judgement import (  # noqa: E402
    BOOLEAN_CHECKS,
    Measurement,
    coupon_bands,
    coupon_passed,
    judge_coupon,
    result_rows,
)


def _yes_no(value: str) -> bool:
    if value in {"yes", "y", "pass", "true"}:
        return True
    if value in {"no", "n", "fail", "false"}:
        return False
    raise argparse.ArgumentTypeError(f"expected yes or no, got {value!r}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--instance", default="hand-v3", choices=sorted(HAND_INSTANCES))
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    parser.add_argument("--c1", type=float, nargs="+", metavar="MM", help="pin bore, two readings")
    parser.add_argument(
        "--c3", type=float, nargs="+", metavar="MM", help="bearing seat, two readings"
    )
    for item, what in BOOLEAN_CHECKS.items():
        parser.add_argument(f"--{item.lower()}", type=_yes_no, metavar="yes|no", help=what)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    # The user's machine is Windows, whose console defaults to a code page that
    # cannot print "Ø" or "–"; the rows are meant to be pasted into a UTF-8 file.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    link = HAND_INSTANCES[args.instance].palm.finger.link
    measurements: dict[str, Measurement] = {
        "C1": args.c1,
        "C3": args.c3,
        **{item: getattr(args, item.lower()) for item in BOOLEAN_CHECKS},
    }
    verdicts = judge_coupon(link, measurements)

    print(f"instance {args.instance}; bands from its link:")
    for band in coupon_bands(link):
        print(f"  {band.item} {band.what}: nominal {band.nominal_mm:.2f}, accept {band.text}")
    print("| 日期 | 項目 | 量到 | 結果 | 說明 |")
    print("|---|---|---|---|---|")
    for row in result_rows(verdicts, args.date):
        print(row)
    passed = coupon_passed(verdicts)
    counts = {
        status: sum(1 for v in verdicts if v.status == status)
        for status in ("PASS", "FAIL", "VACUOUS")
    }
    print(("COUPON PASS" if passed else "COUPON NOT PASSED") + f" — {counts}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
