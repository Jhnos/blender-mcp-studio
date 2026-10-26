"""Real Blender controls for changing a mesh data frame without moving its children."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.infrastructure.narrowing import as_str_keyed_exact, required
from src.verification.mesh_integrity import require_triangle_surface


def verify_mesh_rebase(root: Path) -> None:
    code = f"""import bpy,json,runpy
from mathutils import Matrix,Vector
rebase = runpy.run_path({str(root / "scripts/blender_mesh_rebase.py")!r})['rebase_mesh']
objects_before=set(bpy.data.objects);meshes_before=set(bpy.data.meshes);materials_before=set(bpy.data.materials)
vertices=[(0,0,0),(3,0,0),(0,5,0),(0,0,7)]
faces=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
errors=[];rejections=0
try:
    parent=bpy.data.objects.new('REBASE_parent',None);bpy.context.collection.objects.link(parent)
    parent.location=(.031,.052,.017);parent.scale.x=-1;parent['turn']=0.0
    frame=Matrix.Translation((.011,-.008,.004)) @ Matrix.Rotation(.4,4,'Y') @ Matrix.Diagonal((-.001,.001,.001,1))
    mesh=bpy.data.meshes.new('REBASE_source');mesh.from_pydata([frame @ Vector(v) for v in vertices],[],faces)
    material=bpy.data.materials.new('REBASE_material');mesh.materials.append(material)
    body=bpy.data.objects.new('REBASE_body',mesh);bpy.context.collection.objects.link(body);body.parent=parent
    body.location=(.03,-.01,.01)
    sibling=bpy.data.objects.new('REBASE_shared',mesh);bpy.context.collection.objects.link(sibling)
    child=bpy.data.objects.new('REBASE_child',None);bpy.context.collection.objects.link(child);child.parent=body
    child.location=(.018,.013,.025)
    curve=child.driver_add('rotation_euler',0);curve.driver.type='SCRIPTED';variable=curve.driver.variables.new()
    variable.name='a';variable.type='SINGLE_PROP';variable.targets[0].id=parent;variable.targets[0].data_path='["turn"]';curve.driver.expression='a'
    tip=bpy.data.objects.new('REBASE_tip',None);bpy.context.collection.objects.link(tip);tip.parent=child;tip.location=(.02,0,0)
    original_source=[tuple(v.co) for v in mesh.vertices]
    def pose(turn):
        parent['turn']=turn;parent.rotation_euler.z=turn;parent.update_tag();bpy.context.view_layer.update()
    def observations():
        return [[tuple(body.matrix_world @ v.co) for v in body.data.vertices]] + [
            [tuple(o.matrix_world @ Vector(p)) for p in ((0,0,0),(.003,-.002,.004))] for o in (child,tip)]
    expected={{}}
    for turn in (0,.17):
        pose(turn);expected[turn]=observations()
    pose(0)
    naive=(body.matrix_world @ frame @ child.matrix_parent_inverse @ child.matrix_basis).translation
    assert (naive-child.matrix_world.translation).length > .001,'Fixture cannot detect uncompensated child frames'
    rebase(body,vertices,faces,frame)
    assert [tuple(v.co) for v in body.data.vertices] == vertices,'Canonical coordinates were rewritten'
    assert [tuple(p.vertices) for p in body.data.polygons] == faces,'Canonical topology was rewritten'
    assert body.data.materials[0] == material,'Material binding was lost'
    assert sibling.data == mesh and [tuple(v.co) for v in mesh.vertices] == original_source,'Shared source was mutated'
    for turn in (0,.17):
        pose(turn)
        actual=observations()
        errors.extend((Vector(a)-Vector(b)).length for group_a,group_b in zip(actual,expected[turn]) for a,b in zip(group_a,group_b))
    assert max(errors)<1e-7,'Rebase displaced the part or driven descendants'
    for invalid in (Matrix.Diagonal((0,1,1,1)),Matrix.Diagonal((float('nan'),1,1,1))):
        before=observations();source=body.data;count=len(bpy.data.meshes)
        try:rebase(body,vertices,faces,invalid)
        except ValueError:rejections+=1
        else:raise AssertionError('Invalid frame accepted')
        assert observations()==before and body.data==source and len(bpy.data.meshes)==count,'Rejected frame changed scene state'
    from types import SimpleNamespace
    original_api=rebase.__globals__['bpy'];calls=0
    def interrupted_update():
        global calls
        calls+=1
        if calls==1:raise KeyboardInterrupt('injected after frame mutation')
        original_api.context.view_layer.update()
    before=observations();source=body.data;mesh_count=len(bpy.data.meshes)
    rebase.__globals__['bpy']=SimpleNamespace(data=bpy.data,context=SimpleNamespace(view_layer=SimpleNamespace(update=interrupted_update)))
    try:
        try:rebase(body,vertices,faces,Matrix.Translation((2,0,0)))
        except KeyboardInterrupt:pass
        else:raise AssertionError('Interruption injection did not fire')
    finally:rebase.__globals__['bpy']=original_api
    assert body.data==source and observations()==before and len(bpy.data.meshes)==mesh_count,'Interrupted rebase was not atomic'
    result={{'max_world_error_mm':max(errors)*1000,'invalid_frames_rejected':rejections,'source_preserved':True,'interruption_restored':True,
        'surface':{{'vertices':[list(v.co) for v in body.data.vertices],'faces':[list(p.vertices) for p in body.data.polygons]}}}}
finally:
    for o in list(bpy.data.objects):
        if o not in objects_before:bpy.data.objects.remove(o,do_unlink=True)
    for m in list(bpy.data.meshes):
        if m not in meshes_before and m.users==0:bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials):
        if m not in materials_before and m.users==0:bpy.data.materials.remove(m)
print(json.dumps(result))
"""
    result = dict(BlenderSocketOracle("127.0.0.1", 9876).execute_json(code))
    surface = result.pop("surface")
    require_triangle_surface(
        required(surface, as_str_keyed_exact, message="Missing rebase surface", error=ValueError)
    )
    print("Mesh rebase, driven descendants and invalid-frame controls passed:", result)
