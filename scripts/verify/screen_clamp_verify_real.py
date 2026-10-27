"""Real dependency-graph controls for active lead and passive float, not a fit test."""

from pathlib import Path

from scripts.verify.generated_artifact_verify_real import BlenderSocketOracle
from src.verification.generator_imports import reload_modules_for


def build_screen_clamp_script(root: Path) -> str:
    modules = reload_modules_for(root, root / "scripts/lab_station_screen_clamp.py")
    return f"""import bpy,importlib,math,json,sys
project={str(root)!r}
if project not in sys.path:sys.path.insert(0,project)
for name in {modules!r}:importlib.reload(importlib.import_module(name))
bind=importlib.reload(importlib.import_module('scripts.lab_station_screen_clamp')).bind_screen_clamp_control
specs=importlib.import_module('src.core.domain.screen_clamp')
joints=importlib.import_module('src.core.domain.lab_station_joints')
from mathutils import Matrix,Vector
from pathlib import Path
before=set(bpy.data.objects);maximum_mm=0.;maximum_rad=0.;maximum_deg=0.;samples=0;controls=0;boundary=0
capacity=bpy.types.Driver.bl_rna.properties['expression'].length_max
assert capacity>0
try:
 for target in (0,15,30,45,60):
  def make(name):
   o=bpy.data.objects.new('CLAMP_SEQUENCE_'+str(target)+'_'+name,None);bpy.context.collection.objects.link(o);return o
  screen,left,nut,pin,retainer=[make(n) for n in ('body','active','nut','pin','retainer')]
  screen.location=(0,-.049,.124);screen['fold_angle_deg']=60
  screen.id_properties_ui('fold_angle_deg').update(min=0,max=90,description='Continuous angle readback')
  left.location=(-.100,-.049,.124);nut.location=(-.100,-.049,.124)
  pin.location=(.07485,-.049,.124);retainer.location=(.10185,-.049,.124)
  bpy.context.view_layer.update()
  spec=specs.ScreenClampSpec(sequence=joints.ScreenFoldSpec(release_mm=2.2,screw_mm=2.4,target_angle_deg=target))
  identities=[(o,o.data) for o in (screen,left,nut,pin,retainer)]
  rig=importlib.import_module('scripts.lab_station_rig')
  try:rig.driver(left,screen,'location',0,'v',('v',),property_paths=('收折進度',),rna_paths=('location[0]',))
  except ValueError:controls+=1
  else:raise AssertionError('Ambiguous property paths accepted')
  try:rig.continuous_property(screen,'fold_angle_deg',float('nan'))
  except ValueError:controls+=1
  else:raise AssertionError('Nonfinite continuous property accepted')
  assert screen['fold_angle_deg']==60 and screen.animation_data is None and left.animation_data is None
  for expression in ('0'*capacity,'π'*((capacity+1)//2)):
   try:rig.driver(left,screen,'location',0,expression,(),identity_mapping=True)
   except ValueError:controls+=1
   else:raise AssertionError('Oversized engine expression accepted')
   assert left.animation_data is None and screen.animation_data is None
  probe=make('expression_boundary')
  text='0'+'+0'*((capacity-2)//2)
  rig.driver(probe,screen,'location',0,text,(),identity_mapping=True)
  assert probe.animation_data.drivers[0].driver.expression==text
  bpy.context.view_layer.update();assert probe.animation_data.drivers[0].driver.is_valid
  bpy.data.objects.remove(probe,do_unlink=True);boundary+=1
  for invalid in ('duplicate','rotated','parented_active','bound','scaled','active_tilt','nonfinite'):
   screen.location.x=float('nan') if invalid=='nonfinite' else 0.
   screen.scale=(2,1,1) if invalid=='scaled' else (1,1,1)
   left.rotation_euler.y=.1 if invalid=='active_tilt' else 0.

   screen.rotation_euler.x=.1 if invalid=='rotated' else 0
   left.parent=screen if invalid=='parented_active' else None
   if invalid=='bound':screen['收折進度']=0.
   try:bind(screen,screen if invalid=='duplicate' else left,nut,pin,retainer,spec)
   except ValueError:controls+=1
   else:raise AssertionError('Invalid clamp binding accepted: '+invalid)
   assert pin.parent is None and retainer.parent is None and nut.parent is None
   assert left.animation_data is None and screen.animation_data is None
   if invalid=='bound':del screen['收折進度']
  screen.location.x=0.;screen.scale=(1,1,1);left.rotation_euler.y=0.;screen.rotation_euler.x=0.;left.parent=None;bpy.context.view_layer.update()
  bind(screen,left,nut,pin,retainer,spec)
  assert all(o.data is data for o,data in identities)
  metadata=screen.id_properties_ui('fold_angle_deg').as_dict()
  assert metadata['min']==0 and metadata['max']==90 and metadata['description']=='Continuous angle readback'
  path=Path({str(root / "tmp/lab-station-route-engine")!r})/('clamp-controller-'+str(target)+'.blend');path.parent.mkdir(parents=True,exist_ok=True)
  bpy.data.libraries.write(str(path),{{screen,left,nut,pin,retainer}})
  with bpy.data.libraries.load(str(path),link=False) as (source,destination):
   names=tuple(source.objects);destination.objects=list(names)
  loaded=dict(zip(names,destination.objects))
  for o in destination.objects:bpy.context.collection.objects.link(o)
  for body,active,ln,rp,rn in ((screen,left,nut,pin,retainer),tuple(loaded[o.name] for o in (screen,left,nut,pin,retainer))):
   assert type(body['fold_angle_deg']) is float,(target,body.name,type(body['fold_angle_deg']).__name__)
   observed=[]
   def update(p,f):
    body['收折進度']=float(p);body['樞軸軸向間隙']=f
    for o in (body,active,rp,rn):o.update_tag()
    bpy.context.view_layer.update()
   update(0,0);baseline=(ln.matrix_world.translation.x-active.matrix_world.translation.x)*1000
   local_axis=active.matrix_world.inverted()@Vector((0,-.049,.124))
   for p in list(range(101))+list(range(100,-1,-1)):
    f=(p%3-1)*.28;update(p,f);q=p/20
    # Independent phase cases, not the production pose evaluator.
    if q<=1:angle,r,s=60,0,2.4*q
    elif q<=2:angle,r,s=60,2.2*(q-1),2.4
    elif q<=3:angle,r,s=60+(target-60)*(q-2),2.2,2.4
    elif q<=4:angle,r,s=target,2.2*(4-q),2.4
    else:angle,r,s=target,0,2.4*(5-q)
    lead=(ln.matrix_world.translation.x-active.matrix_world.translation.x)*1000-baseline-.8*(body.rotation_euler.x-active.rotation_euler.x)/(2*math.pi)
    errors=(abs(body.location.x*1000-(-.2+r)),abs(active.location.x*1000-(-100+r-s)),abs(rp.matrix_world.translation.x*1000-(74.85-.2+r+f)),abs((rn.matrix_world.translation.x-rp.matrix_world.translation.x)*1000-27),abs(lead))
    axis=active.matrix_world@local_axis
    errors=(*errors,abs(axis.y+.049)*1000,abs(axis.z-.124)*1000)
    angle_error=abs(body.rotation_euler.x-math.radians(angle-60));display_error=abs(body['fold_angle_deg']-angle)
    maximum_mm=max(maximum_mm,*errors);maximum_rad=max(maximum_rad,angle_error);maximum_deg=max(maximum_deg,display_error)
    assert max(errors)<.001 and angle_error<1e-6 and display_error<.0001,(target,p,errors,angle_error,display_error)
    observed.append(tuple(round(v,6) for v in (body.location.x,body.rotation_euler.x,active.location.x,active.rotation_euler.x,rp.location.x,rn.location.x)))
   assert observed[:101]==list(reversed(observed[101:]));samples+=len(observed)
   for o in (body,active,rp,rn):
    assert all(c.driver.is_valid and not c.keyframe_points and not c.modifiers for c in o.animation_data.drivers)
   if target==0:
    curve=active.animation_data.drivers.find('rotation_euler',index=0);saved=curve.driver.expression;curve.driver.expression='-2*pi*2.4/.8';update(60,0)
    lead=(ln.matrix_world.translation.x-active.matrix_world.translation.x)*1000-baseline-.8*(body.rotation_euler.x-active.rotation_euler.x)/(2*math.pi)
    assert abs(lead)>.13;controls+=1;curve.driver.expression=saved
    curve=rn.animation_data.drivers.find('location',index=0);saved=curve.driver.expression;curve.driver.expression=repr(.10185);update(40,.28)
    assert abs((rn.matrix_world.translation.x-rp.matrix_world.translation.x)*1000-27)>.27;controls+=1;curve.driver.expression=saved
  for o in list(bpy.data.objects):
   if o not in before:bpy.data.objects.remove(o,do_unlink=True)
 print(json.dumps({{'samples':samples,'targets':5,'maximum_position_error_mm':maximum_mm,'maximum_rotation_error_rad':maximum_rad,'maximum_display_error_deg':maximum_deg,'negative_controls':controls,'driver_expression_capacity_bytes':capacity,'boundary_roundtrips':boundary}}))
finally:
 for o in list(bpy.data.objects):
  if o not in before:bpy.data.objects.remove(o,do_unlink=True)
assert set(bpy.data.objects)==before
"""


def verify_screen_clamp_control(root: Path) -> None:
    result = BlenderSocketOracle("127.0.0.1", 9876).execute_json(build_screen_clamp_script(root))
    assert result["samples"] == 2020 and result["negative_controls"] == 59
    capacity = result["driver_expression_capacity_bytes"]
    assert type(capacity) is int and capacity > 0 and result["boundary_roundtrips"] == 5
    print("Screen clamp active/passive controls passed:", result)
