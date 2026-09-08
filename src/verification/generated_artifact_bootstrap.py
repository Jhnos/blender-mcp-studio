"""The snippet that makes a live Blender re-run a generator from source.

Split out of `generated_artifact_contract` at its line budget. The seam is
real: everything left there describes what a contract *is* and how it parses,
while this emits Python for another interpreter to run. They change for
different reasons and neither reads the other.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.verification.generated_artifact_contract import GeneratedArtifactContract


def build_generator_code(
    contract: GeneratedArtifactContract,
    project_root: Path,
) -> str:
    modules_json = json.dumps(list(contract.reload_modules))
    script_json = json.dumps(str(contract.generator_script))
    project_root_json = json.dumps(str(project_root))
    return f"""\
import importlib, runpy, sys
project_root = {project_root_json}
if project_root not in sys.path:
    sys.path.insert(0, project_root)
for module_name in {modules_json}:
    module = importlib.import_module(module_name)
    importlib.reload(module)
runpy.run_path({script_json}, run_name='__main__')
"""
