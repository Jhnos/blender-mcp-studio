from __future__ import annotations

from src.core.domain.design_run import (
    DesignRunReport,
    JobRecord,
    JobStatus,
    StageName,
    StageOutcome,
    StageReport,
)


def _stage(name: StageName, outcome: StageOutcome) -> StageReport:
    return StageReport(name=name, outcome=outcome, metrics=(), evidence=(), message="")


def _report(*outcomes: StageOutcome) -> DesignRunReport:
    names = list(StageName)
    stages = tuple(_stage(names[i], o) for i, o in enumerate(outcomes))
    return DesignRunReport(run_id="r1", spec_name="v78", stages=stages, run_dir="/x")


def test_report_passed_only_when_every_stage_passed_or_not_applicable():
    ok = _report(
        *[StageOutcome.PASSED, StageOutcome.PASSED, StageOutcome.NOT_APPLICABLE]
        + [StageOutcome.PASSED] * 2
    )
    assert ok.passed is True
    bad = _report(*[StageOutcome.PASSED, StageOutcome.FAILED] + [StageOutcome.PASSED] * 3)
    assert bad.passed is False


def test_empty_report_is_not_passed():
    assert _report().passed is False


def test_job_record_fields_and_statuses():
    job = JobRecord(
        job_id="j",
        run_id="r",
        status=JobStatus.QUEUED,
        stage=None,
        error=None,
        created_at=1.0,
        updated_at=1.0,
    )
    assert job.status == "queued" and job.stage is None


def test_stage_report_metrics_round_trip():
    stage = StageReport(
        name=StageName.GEOMETRY,
        outcome=StageOutcome.PASSED,
        metrics=(("stl_count", "113"),),
        evidence=("a.stl",),
        message="ok",
    )
    assert dict(stage.metrics)["stl_count"] == "113"


def test_partial_report_is_not_passed():
    # Every present stage passed, but the run stopped early: it must not read as passed.
    assert _report(StageOutcome.PASSED, StageOutcome.PASSED).passed is False
    full = [StageOutcome.PASSED] * 5
    assert _report(*full).passed is True
    out_of_order = DesignRunReport(
        "r",
        "n",
        tuple(_stage(n, StageOutcome.PASSED) for n in reversed(list(StageName))),
        "/x",
    )
    assert out_of_order.passed is False
    dup = DesignRunReport(
        "r", "n", tuple(_stage(StageName.IMPORT, StageOutcome.PASSED) for _ in range(5)), "/x"
    )
    assert dup.passed is False
