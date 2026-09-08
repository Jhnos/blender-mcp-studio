"""A resident Blender runs whatever it loaded last unless told to reload.

The contract runner imports each listed module and reloads it before running
the generator. A module the generator reaches that is not on the list keeps its
previous code and the run reports green against a hand it did not build. That
is ES-6, and the committed lists were written by hand.
"""

import json
from pathlib import Path

import pytest

from src.core.domain.hand_instances import HAND_INSTANCES
from src.verification.generator_imports import first_party_imports, reload_modules_for

ROOT = Path(__file__).resolve().parents[3]


def test_first_party_imports_are_read_from_source_not_by_importing(tmp_path: Path) -> None:
    """The generators import bpy at the top, so this has to work by reading."""
    module = tmp_path / "gen.py"
    module.write_text(
        "import bpy\n"
        "from scripts.a import x\n"
        "import scripts.b\n"
        "from src.core.domain.c import Y\n"
        "def f():\n"
        "    from scripts.d import z\n"
        "import json\n"
    )

    assert first_party_imports(module) == (
        "scripts.a",
        "scripts.b",
        "src.core.domain.c",
        "scripts.d",
    )


def test_the_closure_lists_leaves_before_the_modules_that_import_them(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "__init__.py").write_text("")
    (tmp_path / "scripts" / "leaf.py").write_text("X = 1\n")
    (tmp_path / "scripts" / "mid.py").write_text("from scripts.leaf import X\n")
    (tmp_path / "scripts" / "gen.py").write_text(
        "from scripts.mid import X\nfrom scripts.leaf import X as Y\n"
    )

    assert reload_modules_for(tmp_path, tmp_path / "scripts" / "gen.py") == (
        "scripts.leaf",
        "scripts.mid",
    )


def test_a_submodule_imported_from_its_package_is_followed_not_its_package(tmp_path: Path) -> None:
    """`from src.core.domain import opposition` imports a module, and that module reloads.

    Listing the package instead would reload its __init__ and leave the
    submodule stale — the exact silent-green this closure exists to prevent.
    """
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "__init__.py").write_text("")
    (tmp_path / "scripts" / "pkg").mkdir()
    (tmp_path / "scripts" / "pkg" / "__init__.py").write_text("")
    (tmp_path / "scripts" / "pkg" / "leaf.py").write_text("X = 1\n")
    (tmp_path / "scripts" / "pkg" / "other.py").write_text("Y = 2\n")
    (tmp_path / "scripts" / "gen.py").write_text("from scripts.pkg import leaf, other\n")

    assert reload_modules_for(tmp_path, tmp_path / "scripts" / "gen.py") == (
        "scripts.pkg.leaf",
        "scripts.pkg.other",
    )


def test_a_module_the_closure_names_but_the_tree_lacks_is_refused(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "gen.py").write_text("from scripts.ghost import X\n")

    with pytest.raises(FileNotFoundError, match="scripts.ghost"):
        reload_modules_for(tmp_path, tmp_path / "scripts" / "gen.py")


@pytest.mark.parametrize("slug", sorted(HAND_INSTANCES))
def test_every_reachable_module_is_reloaded(slug: str) -> None:
    instance = HAND_INSTANCES[slug]
    closure = reload_modules_for(ROOT, ROOT / instance.generator_script)
    for name in (instance.contract_name, f"{instance.contract_name}_finger"):
        contract = json.loads(
            (ROOT / "scripts" / "verify" / "contracts" / f"{name}.json").read_text()
        )
        missing = set(closure) - set(contract["reload_modules"])
        assert not missing, f"{name}.json would run stale code for {sorted(missing)}"
        assert tuple(contract["reload_modules"]) == closure, f"{name}.json: order or extras differ"
