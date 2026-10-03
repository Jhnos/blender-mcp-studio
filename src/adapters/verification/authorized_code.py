"""Closed script derivation shared by the sandbox and the verification adapter."""

from functools import lru_cache
from pathlib import Path

from src.core.domain.verification import VerificationError, VerificationSuite
from src.verification.cable_route_cases import registered_suites
from src.verification.generator_imports import reload_modules_for

ROOT = Path(__file__).resolve().parents[3]
MARKER = "VERIFICATION_JSON:"
VERIFICATION_TIMEOUT_S = 300.0


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
