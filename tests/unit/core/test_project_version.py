"""Project release version must come from the VERSION SSOT."""

from pathlib import Path

from api.main import app

PROJECT_ROOT = Path(__file__).parents[3]


def test_fastapi_reports_the_project_version_ssot() -> None:
    expected = (PROJECT_ROOT / "VERSION").read_text().strip()

    assert app.version == expected
