"""Shared route engine: real-mesh contact controls and data-driven head-route cases."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.verification.generator_imports import reload_modules_for


def verify_cable_routes(root: Path) -> None:
    adapter = root / "scripts/lab_cable_routes.py"
    oracle = BlenderSocketOracle("127.0.0.1", 9876, timeout=300)
    path = root / "tmp/lab-station-module-configurations/cable-clearance.blend"
    print(oracle.execute(f"import bpy\nbpy.ops.wm.open_mainfile(filepath={str(path)!r})"))
    code = f"""import bpy,runpy,importlib,json
from pathlib import Path
from dataclasses import replace
for name in {reload_modules_for(root, adapter)!r}:
    importlib.reload(importlib.import_module(name))
routes=runpy.run_path({str(adapter)!r})
paths=runpy.run_path({str(root / "src/core/domain/cable_paths.py")!r})
model=runpy.run_path({str(root / "scripts/model_lab_platform.py")!r})
output=Path({str(root / "tmp/lab-station-route-engine")!r})
output.mkdir(parents=True,exist_ok=True)
def line(start,end):
    return paths['sample_path']((paths['CubicPath']((start,paths['mix'](start,end,1/3),paths['mix'](start,end,2/3),end)),))
def request(start,end,direction=(1,0,0)):
    return routes['RouteBoundary']('fixture',start,end,direction,direction,60)
bpy.ops.mesh.primitive_cube_add(size=.02,location=(2,2,2))
fixture=bpy.context.object
fixture.name='ROUTE_CHECK_solid'
fixture.scale.x=-1
try:
    obstacles=routes['RouteObstacles']()
    start,end=(1980,2000,2020),(2020,2000,2020)
    assert obstacles.first_hit(line(start,end),request(start,end)) is None
    crossing_start,crossing_end=(1980,2000,2000),(2020,2000,2000)
    hit=obstacles.first_hit(line(crossing_start,crossing_end),request(crossing_start,crossing_end))
    assert hit and hit['object']==fixture.name
    embedded_start,embedded_end=(2000,2000,2000),(2005,2000,2000)
    hit=obstacles.first_hit(line(embedded_start,embedded_end),request(embedded_start,embedded_end))
    assert hit and hit['reason']=='start_inside'
    top_start,top_end=(2000,2000,2040),(2000,2000,2010)
    top=request(top_start,top_end,(0,0,-1))
    assert obstacles.first_hit(line(top_start,top_end),top,fixture.name) is None
    bad_end=(2000,2000,2009)
    hit=obstacles.first_hit(line(top_start,bad_end),replace(top,end_mm=bad_end),fixture.name)
    assert hit and hit['reason']=='terminal_not_on_outward_face'
    hit=obstacles.first_hit(line(start,end),replace(request(start,end),cable_radius_mm=11))
    assert hit and hit['object']==fixture.name
finally:
    bpy.data.objects.remove(fixture,do_unlink=True)
loop=paths['sample_path']((paths['CubicPath'](((0,0,0),(20,20,0),(-20,20,0),(0,0,0))),))
assert routes['nonlocal_self_hit'](loop,3) is not None
assert routes['nonlocal_self_hit'](line((0,0,0),(30,0,0)),3) is None
controls={{'self_contact_rejected':True,'clear_path':True,'crossing_rejected':True,'embedded_rejected':True,'outward_face_allowed':True,'penetrating_terminal_rejected':True,'radius_inflation_rejected':True,'mirrored_fixture':True}}
rows=[]
for head,channel,length,lift in (('capillary',0,220,0),('capillary',0,220,100),('pH_temp',0,150,0),('pH_temp',1,150,0)):
    for obj in list(bpy.data.objects):
        if obj.name.startswith('RESEARCH_route_'):
            bpy.data.objects.remove(obj,do_unlink=True)
    for label in ('capillary','pH_temp'):model['pose'](label)
    model['pose'](head,0,lift)
    case=routes['RouteCase'](head,channel,'head',length)
    selected,report=routes['select_route'](case,routes['RouteSearchSpec'](candidate_count=256))
    rows.append({{'lift_mm':lift,'pass':selected is not None,**report}})
    (output/'engine-verification.json').write_text(json.dumps({{'controls':controls,'rows':rows}},indent=2))
    if selected is None:
        raise ValueError('No geometric candidate for '+str(case))
    if head=='capillary':
        routes['draw_route'](selected,(.04,.05,.06,1))
        scene=model['configure_electrode_view']()
        scene.render.resolution_x=1000;scene.render.resolution_y=850;scene.render.resolution_percentage=100
        scene.render.filepath=str(output/('capillary-'+str(lift)+'.png'))
        bpy.ops.render.render(write_still=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(output/('capillary-'+str(lift)+'.blend')))
print('Shared route engine: 8 controls and 4 one-route pose cases passed')
bpy.ops.wm.open_mainfile(filepath=str(model['OUTPUT']/'arm-seated.blend'))
"""
    print(oracle.execute(code))


if __name__ == "__main__":
    verify_cable_routes(Path(__file__).resolve().parents[2])
