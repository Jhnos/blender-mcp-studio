# Living Actors 2.0.0 — traveler, guide, guard and artisan

Four original low-poly actors share the same seven-bone hierarchy and rigid skin weights.
Open living-actors.blend; select LW_traveler_rig, LW_guide_rig, LW_guard_rig or LW_artisan_rig and choose its named
idle/walk/interact Action in the Action Editor. Catalog roots sit at x=-1.65/-0.55/+0.55/+1.65;
reset a selected root to zero when rendering a sprite with LW_sprite_camera.

The actual World Kit sprite camera is reused: 128×192 RGBA, 64px/metre, foot anchor (64,144).
The anchor is the projected ground-root center, not the visible shoe silhouette; toe and lifted-foot
pixels vary naturally with facing and animation. LW_portrait_camera frames the whole face.
Each actor has 48 frames: rows down/left/right/up; each row idle 0–1, walk 2–7, interact 8–11.
No mirrored left/right frames. Portraits are 256×256. Colors and meshes remain editable.
Eighteen editable talk/quest/deliver/investigate/locked/exit badges have unavailable/available/completed states.

Rebuild in the Blender source checkout with the same command pattern as models/world-kit/README.md:
model_living_actors.py → model_living_markers.py → verify_living_actors.py → package_living_actors.py.
Use --background --factory-startup --python-exit-code 1 for each real Blender script.
The publisher checks alpha bounds, coverage, animation differences and reopened render agreement.
The zip preserves editable sources and generator source; complete rebuild also needs the repository's
shared primitive/wrapper modules and delivered models/world-kit/world-kit.blend.

The shared rig has four distinct original outfits: teal traveler with rucksack, ochre guide with hat, blue guard with helmet/shield, and purple artisan with apron/hammer. This collection does not include planned effects or creatures. No claim of measured human recognition.
