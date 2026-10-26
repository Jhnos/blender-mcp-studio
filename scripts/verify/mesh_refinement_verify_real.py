"""Shared real-Blender mesh refinement and surface-preservation controls."""

import json
from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from scripts.verify.mesh_rebase_verify_real import verify_mesh_rebase
from scripts.verify.serrated_joint_verify_real import verify_serrated_joint_integration
from src.infrastructure.narrowing import as_str_keyed_exact, required
from src.verification.mesh_integrity import require_triangle_surface


def verify_generated_triangles(root: Path) -> None:
    """Independently inspect saved arm/platform/guide triangles and a collapsed-face control."""
    code = f"""import bpy, math, json
from pathlib import Path
names = [f'S_{{head}}_{{part}}' for head in ('capillary', 'pH_temp') for part in ('upper', 'platform')]
names += [f'LS_ROUTE_{{head}}_{{role}}' for head in ('capillary', 'pH_temp') for role in ('upper', 'lower')]
def inspect(points, faces):
    if not faces or not all(math.isfinite(x) for p in points for x in p):
        raise ValueError('Empty or nonfinite mesh')
    edges = {{}}
    for face in faces:
        if len(face) != 3:
            raise ValueError('Nontriangular output')
        a,b,c = [points[i] for i in face]
        u = [b[i]-a[i] for i in range(3)]
        v = [c[i]-a[i] for i in range(3)]
        cross = (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        if math.hypot(*cross) == 0:
            raise ValueError('Zero-area output triangle')
        for i,j in zip(face, face[1:]+face[:1]):
            edge = tuple(sorted((i,j)))
            edges.setdefault(edge, []).append((i,j))
    if any(len(pair) != 2 or pair[0] != pair[1][::-1] for pair in edges.values()):
        raise ValueError('Open or inconsistently oriented output')
    return len(faces)
report = {{}}
for name in names:
    mesh = bpy.data.objects[name].data
    mesh.calc_loop_triangles()
    points = [tuple(v.co) for v in mesh.vertices]
    faces = [tuple(p.vertices) for p in mesh.loop_triangles]
    try:
        report[name] = inspect(points, faces)
    except ValueError as error:
        raise ValueError(name + ': ' + str(error)) from error
    corrupted = list(points)
    corrupted[faces[0][1]] = corrupted[faces[0][0]]
    try:
        inspect(corrupted, faces)
    except ValueError as error:
        if str(error) != 'Zero-area output triangle':
            raise
    else:
        raise AssertionError('Collapsed output triangle accepted: ' + name)
output = Path({str(root / "tmp/lab-station-route-engine/generated-triangle-check.json")!r})
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report))
print('Eight saved arm/platform/guide meshes and collapsed-face controls passed:', report)
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))
    verify_closed_surfaces(root)


def verify_mesh_refinement(root: Path) -> None:
    """Exercise preservation and repair on valid, closed-degenerate and open controls."""
    verify_mesh_rebase(root)
    verify_mesh_preservation(root)
    verify_boolean_scale(root)
    verify_axis_cylinders(root)
    verify_chain_triangulation(root)
    verify_serrated_joint_integration(root)
    code = f"""import bpy, runpy, math
from types import SimpleNamespace
refine = runpy.run_path({str(root / "scripts/blender_mesh_primitives.py")!r})['refine_closed_mesh']
original_bmesh = refine.__globals__['bmesh']
vertices = [(0,0,0),(.001,0,0),(0,.001,0),(0,0,.001),(0,0,0)]
faces = [(0,2,4),(4,2,1),(0,4,3),(4,1,3),(0,3,2),(1,2,3)]
def snapshot(mesh):
    return ([tuple(v.co) for v in mesh.vertices], [tuple(p.vertices) for p in mesh.polygons])
for case in ('coincident', 'open', 'collinear', 'excessive'):
    mesh = bpy.data.meshes.new('REFINEMENT_control')
    controls = vertices if case != 'collinear' else vertices[:-1] + [(0,.0005,0)]
    if case == 'excessive':
        controls = vertices[:-1] + [(0,5e-8,0)]
    triangles = faces if case != 'collinear' else [(0,2,4),(4,2,1),(0,4,1),(0,1,3),(0,3,2),(1,2,3)]
    mesh.from_pydata(controls, [], triangles[:-1] if case == 'open' else triangles)
    obj = bpy.data.objects.new('REFINEMENT_control', mesh)
    bpy.context.collection.objects.link(obj)
    before = snapshot(mesh)
    try:
        if case == 'excessive':
            ops = SimpleNamespace(triangulate=original_bmesh.ops.triangulate,
                rotate_edges=original_bmesh.ops.rotate_edges,
                remove_doubles=lambda bm, **kw: original_bmesh.ops.remove_doubles(bm, verts=kw['verts'], dist=1e-6))
            refine.__globals__['bmesh'] = SimpleNamespace(new=original_bmesh.new, types=original_bmesh.types, ops=ops)
        if case in ('open', 'excessive'):
            try:
                refine(obj)
            except ValueError as error:
                expected = 'Refinement exceeds the vertex displacement budget' if case == 'excessive' else 'Refinement requires a finite closed mesh'
                assert str(error) == expected, (case, str(error))
                assert snapshot(obj.data) == before, 'Rejected refinement mutated the input'
            else:
                raise AssertionError('Invalid refinement accepted: ' + case)
        else:
            refine(obj)
            points, triangles = snapshot(obj.data)
            expected = (5,6) if case == 'collinear' else (4,4)
            assert (len(points),len(triangles)) == expected, 'Degenerate tetrahedron not repaired'
            assert set(points) == set(before[0]), 'Refinement moved control vertices'
            edges = {{}}
            for face in triangles:
                assert len(face) == 3
                a,b,c = [points[i] for i in face]
                u = [b[i]-a[i] for i in range(3)]
                v = [c[i]-a[i] for i in range(3)]
                cross = (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
                assert math.hypot(*cross) > 0, 'Refinement retained a zero-area triangle'
                for i,j in zip(face, face[1:]+face[:1]):
                    edge = tuple(sorted((i,j)))
                    edges[edge] = edges.get(edge,0)+1
            assert all(count == 2 for count in edges.values()), 'Refinement opened the mesh'
            saved = snapshot(obj.data)
            refine(obj)
            assert snapshot(obj.data) == saved, 'Refinement is not idempotent'
    finally:
        refine.__globals__['bmesh'] = original_bmesh
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)
print('Coincident/collinear repair, idempotence, atomic open/excessive-weld rejection passed')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))


def verify_mesh_preservation(root: Path) -> None:
    """A short, valid surface edge must survive finishing, including mirror baking."""
    code = f"""import bpy, runpy, json
from collections import Counter
from mathutils import Matrix
finish = runpy.run_path({str(root / "scripts/lab_station_arm.py")!r})['finish_arm']
vertices = [(0,0,0),(.001,0,0),(0,.001,0),(0,0,.001),(5e-6,0,0)]
faces = [(0,2,4),(4,2,1),(0,4,3),(4,1,3),(0,3,2),(1,2,3)]
def surface(mesh):
    return Counter(tuple(sorted(tuple(mesh.vertices[i].co) for i in p.vertices)) for p in mesh.polygons)
report = {{}}
for side in (-1,1):
    mesh = bpy.data.meshes.new('PRESERVATION_control')
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new('PRESERVATION_control', mesh)
    try:
        for stage in ('local', 'baked', 'repeat'):
            if stage == 'baked':
                mesh.transform(Matrix.Translation((.0042,0,0)))
                if side > 0:
                    mesh.transform(Matrix.Diagonal((-1,1,1,1)))
            before = surface(mesh)
            finish(obj)
            assert surface(mesh) == before, 'Finishing rewrote a valid surface: ' + str((side,stage))
            points = [tuple(v.co) for v in mesh.vertices]
            edges = {{}}
            volume = 0
            for p in mesh.polygons:
                face = tuple(p.vertices)
                assert len(face) == 3
                a,b,c = [points[i] for i in face]
                volume += (a[0]*(b[1]*c[2]-b[2]*c[1]) + a[1]*(b[2]*c[0]-b[0]*c[2]) + a[2]*(b[0]*c[1]-b[1]*c[0]))/6
                for i,j in zip(face,face[1:]+face[:1]):
                    edges.setdefault(tuple(sorted((i,j))),[]).append((i,j))
            assert volume > 0, 'Finishing left inward-facing triangles'
            assert all(len(pair)==2 and pair[0]==pair[1][::-1] for pair in edges.values())
            report[str((side,stage))] = len(mesh.polygons)
    finally:
        bpy.data.objects.remove(obj)
        bpy.data.meshes.remove(mesh)
from pathlib import Path
path = Path({str(root / "tmp/lab-station-route-engine/mesh-preservation-check.json")!r})
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report))
print('Valid short-edge preservation, both bake directions and idempotence passed')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))


def verify_boolean_scale(root: Path) -> None:
    """A disjoint subtraction must not round-trip an untouched body's coordinates."""
    code = f"""import bpy, runpy
from mathutils import Matrix
joint_boolean = runpy.run_path({str(root / "scripts/lab_station_joints.py")!r})['joint_boolean']
vertices = [(0.000131234,0,0),(.001234567,0,0),(0,.001314159,0),(0,0,.001271828)]
faces = [(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
created = []
try:
    for name in ('body','tool'):
        mesh = bpy.data.meshes.new('BOOLEAN_scale_' + name)
        mesh.from_pydata(vertices, [], faces)
        obj = bpy.data.objects.new('BOOLEAN_scale_' + name, mesh)
        bpy.context.collection.objects.link(obj)
        created.append((obj.name, mesh))
    body, tool = [bpy.data.objects[name] for name, mesh in created]
    body.matrix_world = Matrix.Translation((.031,.052,.017))
    tool.matrix_world = Matrix.Translation((.2,.2,.2))
    bpy.context.view_layer.update()
    points = {{tuple(v.co) for v in body.data.vertices}}
    frame = body.matrix_world.copy()
    joint_boolean(body, tool, 'DIFFERENCE')
    assert {{tuple(v.co) for v in body.data.vertices}} == points, 'Disjoint Boolean changed untouched coordinates'
    assert body.matrix_world == frame, 'Boolean failed to restore placement'
    assert len(body.data.polygons) == 4, 'Disjoint Boolean changed tetrahedron topology'
finally:
    for name, mesh in created:
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
print('Disjoint Boolean preserves coordinates and placement')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))


def verify_axis_cylinders(root: Path) -> None:
    """Axis-aligned cylinder caps remain exactly planar after a quarter turn."""
    code = f"""import bpy, runpy
add = runpy.run_path({str(root / "scripts/blender_mesh_primitives.py")!r})['add_cylinder']
created = []
try:
    reference = add('AXIS_control_Z', 11, 8, (0,0,0), 'Z')
    created.append(reference)
    points = [tuple(vertex.co) for vertex in reference.data.vertices]
    for axis, index in (('X',0),('Y',1),('Z',2)):
        obj = add('AXIS_control_' + axis, 11, 8, (12,23,34), axis)
        created.append(obj)
        actual = {{tuple(vertex.co) for vertex in obj.data.vertices}}
        assert len({{point[index] for point in actual}}) == 2, 'Cylinder end caps are not planar: ' + axis
        expected = {{(z,y,-x) if axis == 'X' else (x,-z,y) if axis == 'Y' else (x,y,z) for x,y,z in points}}
        assert actual == expected, 'Axis rotation perturbed the cylinder profile: ' + axis
        assert tuple(obj.rotation_euler) == (0,0,0), 'Cylinder retained a rotation transform'
finally:
    for obj in created:
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
print('Three cylinder axes preserve exact cap planes and radial profiles')
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))


def verify_chain_triangulation(root: Path) -> None:
    """A solver ngon with a collinear chain must triangulate without chain-skipping slivers.

    The fixture is a real hub-side polygon from the V10 lower arm: a quad whose
    one edge carries nine vertices where the tooth plate's base crossed it. The
    stock ear-clip/beautify triangulation skips chain vertices and emits
    nanometre-high slivers; those are the readiness oracle's zero-area faces and
    intersecting pairs once the part is placed metres from the origin.
    """
    code = f"""import bpy, bmesh, runpy
from mathutils.geometry import intersect_point_line
triangulate = runpy.run_path({str(root / "scripts/blender_mesh_triangulation.py")!r})['triangulate_faces']
coords = [(0.0367484912276268, -0.01147078350186348, -0.0747155249118805), (0.04263240098953247, -0.012569084763526917, -0.05636713653802872), (0.04166342690587044, -0.014107558876276016, -0.05614849925041199), (0.03577951341867447, -0.01300925761461258, -0.07449689507484436), (0.03586612269282341, -0.012871747836470604, -0.0745164304971695), (0.035900868475437164, -0.01281658560037613, -0.07452426850795746), (0.0359356664121151, -0.012761333957314491, -0.07453212141990662), (0.036143045872449875, -0.012432069517672062, -0.0745789185166359), (0.03617791831493378, -0.012376701459288597, -0.07458678632974625), (0.03638496249914169, -0.012047967873513699, -0.07463350147008896), (0.03659234568476677, -0.01171870343387127, -0.07468029856681824), (0.0366271436214447, -0.011663452722132206, -0.0746881514787674)]
def stats(bm):
    bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    heights = []; skips = 0
    for face in bm.faces:
        assert len(face.verts) == 3, 'Triangulation left a polygon'
        points = [v.co for v in face.verts]
        longest = max((points[i] - points[(i + 1) % 3]).length for i in range(3))
        heights.append(2 * face.calc_area() / longest)
        members = {{v.index for v in face.verts}}
        for i in range(3):
            a, b = points[i], points[(i + 1) % 3]
            for vertex in bm.verts:
                if vertex.index in members:
                    continue
                point, t = intersect_point_line(vertex.co, a, b)
                if 0 < t < 1 and (vertex.co - point).length < 1e-9:
                    skips += 1
    return len(bm.faces), min(heights), skips
report = {{}}
for method in ('stock', 'shared'):
    mesh = bpy.data.meshes.new('CHAIN_control')
    mesh.from_pydata(coords, [], [list(range(len(coords)))])
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        before = {{tuple(v.co) for v in bm.verts}}
        if method == 'stock':
            bmesh.ops.triangulate(bm, faces=list(bm.faces))
        else:
            triangulate(bm)
        faces, height, skips = stats(bm)
        assert {{tuple(v.co) for v in bm.verts}} == before, 'Triangulation moved or dropped vertices'
        assert faces == len(coords) - 2, 'Triangulation changed the face count: ' + str(faces)
        report[method] = (height, skips)
    finally:
        bm.free()
        bpy.data.meshes.remove(mesh)
assert report['stock'][1] or report['stock'][0] < 1e-8, 'Chain fixture no longer discriminates: ' + str(report)
assert report['shared'][1] == 0 and report['shared'][0] > 1e-8, 'Shared triangulation skipped chain vertices: ' + str(report)
print('Collinear-chain ngon triangulates without skips; stock method still fails on it:', report)
"""
    print(BlenderSocketOracle("127.0.0.1", 9876, timeout=30).execute(code))


def verify_closed_surfaces(root: Path) -> None:
    """Independently check every mesh in the saved scene, including hidden meshes."""
    code = """import bpy, bmesh, json
rows = {}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    mesh = obj.data.copy()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.to_mesh(mesh)
        mesh.calc_loop_triangles()
        rows[obj.name] = {'vertices': [list(v.co) for v in mesh.vertices], 'faces': [list(f.vertices) for f in mesh.loop_triangles]}
    finally:
        bm.free()
        bpy.data.meshes.remove(mesh)
print(json.dumps(rows))
"""
    meshes = BlenderSocketOracle("127.0.0.1", 9876, timeout=60).execute_json(code)
    if not meshes:
        raise ValueError("No meshes available for independent surface verification")
    report: dict[str, object] = {}
    errors: dict[str, str] = {}
    for name, raw in meshes.items():
        mesh = required(raw, as_str_keyed_exact, message="Malformed mesh payload", error=ValueError)
        try:
            report[name] = require_triangle_surface(mesh)
        except ValueError as error:
            errors[name] = str(error)
    output = root / "tmp/lab-station-route-engine/closed-surface-check.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"passed": report, "errors": errors}, indent=2))
    if errors:
        raise ValueError(f"Independent surface verification failed: {errors}")
    print(f"All {len(report)} scene meshes passed independent surface verification")
