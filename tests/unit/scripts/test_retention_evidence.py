"""A captured pin must be stopped in both axial travel directions."""

from src.verification.mesh_measurements import measurements_pass


def test_retention_requires_all_declared_blocked_travel_samples():
    limits = {
        "dimensions_mm": [36, 36, 29.6],
        "radius_mm": 18,
        "slope_angles_deg": [35.84],
        "hole_ray_count": 1,
        "hardware_count": 1,
        "hardware_inner_radius_mm": 5.3,
        "hardware_pair_count": 1,
        "retention_sample_count": 2,
    }
    evidence = {
        "dimensions_mm": [36, 36, 29.6],
        "radius_mm": 18,
        "slope_angles_deg": [35.84],
        "hole_hits": [False],
        "hardware_count": 1,
        "hardware_inner_radius_mm": 6.8,
        "hardware_outer_radius_mm": 15.3,
        "hardware_overlaps": [0],
        "retention_overlaps": [8, 12],
    }
    assert measurements_pass(evidence, limits)
    for wrong in ([], [8], [8, 0], [True, 12], [8, -1]):
        assert not measurements_pass({**evidence, "retention_overlaps": wrong}, limits)
    del evidence["retention_overlaps"]
    assert not measurements_pass(evidence, limits)
