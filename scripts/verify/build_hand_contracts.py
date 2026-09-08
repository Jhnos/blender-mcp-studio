#!/usr/bin/env python3
"""Write, or check, the generated contracts for one registered hand instance.

The contracts under scripts/verify/contracts/ are generated artifacts that are
committed so they can be diffed. Run without --check after changing a spec or
the planning layer, then commit the result; `test_contract_builder` holds the
committed files to this output, so a stale file goes red in T2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.domain.hand_instances import HAND_INSTANCES  # noqa: E402
from src.core.planning.hand_plan import hand_plan  # noqa: E402
from src.verification.contract_builder import contract_mappings, render_contract  # noqa: E402

CONTRACTS = PROJECT_ROOT / "scripts" / "verify" / "contracts"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", choices=sorted(HAND_INSTANCES))
    parser.add_argument("--check", action="store_true", help="exit 1 if a committed file differs")
    args = parser.parse_args(argv)

    plan = hand_plan(HAND_INSTANCES[args.slug])
    stale = 0
    for name, mapping in contract_mappings(plan, PROJECT_ROOT).items():
        path = CONTRACTS / name
        text = render_contract(mapping)
        current = path.read_text() if path.is_file() else None
        if args.check:
            status = "OK" if current == text else "STALE"
            stale += status == "STALE"
            print(f"{status:5} {path.relative_to(PROJECT_ROOT)}")
            continue
        path.write_text(text)
        print(f"{'same ' if current == text else 'wrote'} {path.relative_to(PROJECT_ROOT)}")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
