"""Closed script derivation shared by the sandbox and the verification adapter."""

from functools import lru_cache
from pathlib import Path

from src.core.domain.verification import VerificationError, VerificationSuite
from src.verification.cable_route_cases import registered_suites
from src.verification.generator_imports import reload_modules_for

ROOT = Path(__file__).resolve().parents[3]
MARKER = "VERIFICATION_JSON:"
#: Slowest registered suite as measured on the real machine: 274.98 s for the five
#: seated-transfer cases (task 16 hand-off, 2026-09). Raise it only from a fresh
#: measurement, never to make a gate pass.
SLOWEST_SUITE_MEASURED_S = 275.0
#: A deadline is the last resort, not the expected duration: five times the slowest
#: measurement. The previous 300 s sat at 1.09x and tripped on 2026-10-21 when the
#: shared host's load average reached 15 on 10 cores; the adapter then reported a
#: live, busy Blender as unavailable and the real tier stopped.
VERIFICATION_TIMEOUT_S = 5 * SLOWEST_SUITE_MEASURED_S


def verification_code(suite: VerificationSuite) -> str:
    if suite not in registered_suites():
        raise VerificationError("Unregistered verification specification")
    path = ROOT / "scripts/verify/lab_cable_route_checks.py"
    return f"""import importlib,runpy,json,sys
if {str(ROOT)!r} not in sys.path:
    sys.path.insert(0, {str(ROOT)!r})
for name in {reload_modules_for(ROOT, path)!r}:
    importlib.reload(importlib.import_module(name))
suite=runpy.run_path({str(path)!r})
result=suite['run_registered']({suite.suite_id!r})
print({MARKER!r}+json.dumps(result))
"""


@lru_cache(maxsize=1)
def authorized_verification_code() -> frozenset[str]:
    return frozenset(verification_code(suite) for suite in registered_suites())
