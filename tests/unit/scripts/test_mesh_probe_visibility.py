"""Read-only probes must work on deliberately hidden manufacturing layouts."""

from scripts.verify.mesh_probe_verify_real import probe_code


def test_ray_probe_reads_mesh_data_without_requiring_visible_evaluated_object():
    code = probe_code({})
    assert "body.ray_cast" not in code
    assert "local_tree.ray_cast" in code
    assert "local_mesh.from_mesh(body.data)" in code
    assert "local_mesh.free()" in code
