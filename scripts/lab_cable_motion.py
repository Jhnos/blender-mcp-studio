"""Choose one route family across declared assembly poses using shared geometric checks."""

from dataclasses import asdict, dataclass
from math import dist
from typing import Literal

from scripts import lab_cable_routes as routes
from scripts import model_lab_platform as model
from src.core.domain.cable_paths import sample_path
from src.core.planning.cable_path_plan import (
    RouteBoundary,
    RouteCandidate,
    RouteSearchSpec,
    candidates,
    continue_route,
)


@dataclass(frozen=True, slots=True)
class MotionFrame:
    moving: Literal["capillary", "pH_temp"]
    lift_mm: float
    boundaries: tuple[RouteBoundary, ...]
    obstacles: routes.RouteObstacles


@dataclass(frozen=True, slots=True)
class FrameEvidence:
    moving: str
    lift_mm: float
    hits: tuple[dict[str, object], ...]


def capture_frames(
    cases: tuple[routes.RouteCase, ...], lifts_mm: tuple[float, ...]
) -> tuple[MotionFrame, ...]:
    frames = []
    for moving in ("capillary", "pH_temp"):
        for lift in lifts_mm:
            model.pose("capillary", 0, lift if moving == "capillary" else 0)
            model.pose("pH_temp", 0, lift if moving == "pH_temp" else 0)
            boundaries = tuple(routes.measure(case) for case in cases)
            frames.append(MotionFrame(moving, lift, boundaries, routes.RouteObstacles()))
    return tuple(frames)


def select_motion_routes(
    cases: tuple[routes.RouteCase, ...],
    frames: tuple[MotionFrame, ...],
    search: RouteSearchSpec | None = None,
) -> tuple[tuple[tuple[RouteCandidate, ...], ...] | None, dict[str, object]]:
    """Sequential bounded search; one family must pass every frame before it is reserved."""
    if not cases or not frames or any(len(frame.boundaries) != len(cases) for frame in frames):
        raise ValueError("Motion requires cases and complete pose boundaries")
    search = search or RouteSearchSpec(candidate_count=256)
    selected: list[list[RouteCandidate]] = [[] for _ in frames]
    reports: list[dict[str, object]] = []
    for index, case in enumerate(cases):
        key = (case.head, case.channel)
        prefixes = [
            tuple(r for c, r in zip(cases[:index], row, strict=True) if (c.head, c.channel) == key)
            for row in selected
        ]
        neighbours = [
            tuple(
                (r, sample_path(r.curves))
                for c, r in zip(cases[:index], row, strict=True)
                if (c.head, c.channel) != key
            )
            for row in selected
        ]
        rejected = []
        chosen = None
        for seed in candidates(frames[0].boundaries[index], search):
            trial = []
            for frame_index, frame in enumerate(frames):
                candidate = continue_route(
                    seed,
                    frame.boundaries[index],
                    minimum_sampled_radius_mm=search.minimum_sampled_radius_mm,
                )
                hit = (
                    {"reason": "family_infeasible"}
                    if candidate is None
                    else routes.candidate_hit(
                        candidate,
                        sample_path(candidate.curves),
                        frame.obstacles,
                        prefix=prefixes[frame_index],
                        neighbours=neighbours[frame_index],
                        terminal=routes.probe_name(case) if case.segment == "head" else None,
                    )
                )
                if hit is not None:
                    rejected.append({"moving": frame.moving, "lift_mm": frame.lift_mm, **hit})
                    break
                assert candidate is not None
                trial.append(candidate)
            else:
                chosen = trial
                break
        report = {"case": asdict(case), "rejected": rejected, "found": chosen is not None}
        reports.append(report)
        if chosen is None:
            return None, {"routes": reports, "scope": "No family found in bounded sampled search"}
        report["parameters_mm"] = [r.parameters_mm for r in chosen]
        report["max_control_step_mm"] = max(
            (
                dist(a, b)
                for j in range(1, len(frames))
                if frames[j].moving == frames[j - 1].moving
                for old, new in zip(chosen[j - 1].curves, chosen[j].curves, strict=True)
                for a, b in zip(old.controls_mm, new.controls_mm, strict=True)
            ),
            default=0,
        )
        for row, candidate in zip(selected, chosen, strict=True):
            row.append(candidate)
    return tuple(tuple(row) for row in selected), {
        "routes": reports,
        "frame_count": len(frames),
        "scope": "Same handle family/side over sampled poses; no continuous swept-volume or material proof",
    }


def validate_motion(
    cases: tuple[routes.RouteCase, ...],
    frames: tuple[MotionFrame, ...],
    selected: tuple[tuple[RouteCandidate, ...], ...],
) -> tuple[FrameEvidence, ...]:
    """Replay all frames, including middle poses; do not trust the search success flag."""
    if not frames or len(selected) != len(frames):
        raise ValueError("Motion replay needs every frame")
    evidence = []
    for frame, row in zip(frames, selected, strict=True):
        if len(row) != len(cases):
            raise ValueError("Motion replay needs every segment")
        hits = []
        for index, (case, candidate) in enumerate(zip(cases, row, strict=True)):
            seed = selected[0][index]
            if (
                candidate.boundary != frame.boundaries[index]
                or candidate.parameters_mm[:4] != seed.parameters_mm[:4]
                or candidate.parameters_mm[4] * seed.parameters_mm[4] <= 0
            ):
                raise ValueError("Motion changed route family or anchors")
            key = (case.head, case.channel)
            prefix = tuple(
                r
                for c, r in zip(cases[:index], row[:index], strict=True)
                if (c.head, c.channel) == key
            )
            neighbours = tuple(
                (r, sample_path(r.curves))
                for c, r in zip(cases[:index], row[:index], strict=True)
                if (c.head, c.channel) != key
            )
            hit = routes.candidate_hit(
                candidate,
                sample_path(candidate.curves),
                frame.obstacles,
                prefix=prefix,
                neighbours=neighbours,
                terminal=routes.probe_name(case) if case.segment == "head" else None,
            )
            if hit is not None:
                hits.append({"route": candidate.boundary.name, **hit})
        evidence.append(FrameEvidence(frame.moving, frame.lift_mm, tuple(hits)))
    return tuple(evidence)
