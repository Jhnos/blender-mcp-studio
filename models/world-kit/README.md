# World Kit 1.0.0

18 additional metre-scale low-poly modules; architecture, outdoors, and domestic/mechanism props.
Two palettes and four alternate states produce 44 RGBA sprites. Existing room assets are separate.

- Open `world-kit.blend`: named collections, each with an instance offset preserving its ground origin.
- Append a collection and use an instance to place its footpoint at the world-grid origin.
- Six `<palette>-<family>.blend` files contain assembled examples; source scaffolding is hidden in viewports.
- Sprites: 128×192, 64px/metre, orthographic from (0,-8,12), anchor (0.5,0.75).
- Floor and stairs use a 1m horizontal module. Furniture and landscape dimensions are in manifest.json.
- Each family atlas reserves frame 0 for the existing floor; up to 9 prop frames follow. Atlas: 512×768.
- `gate_closed/open`, `lever_off/on`, `plate_up/down`, `crystal_off/on` are visual state pairs.
  State sprites do not implement events, rewards or dynamic collision on their own.
- Published Tiled examples validate against Veilroom's existing reader. They are assembly blueprints,
  not new authored gameplay content packs.

Rebuild from this checkout:

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python scripts/model_world_kit.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python-exit-code 1 --python scripts/verify_world_kit.py
uv run --no-project --with pillow python scripts/package_world_kit.py /Users/bearmacmini/Project_Veilroom/src/veilroom/interface/web/static/game-content/universal-room
```

The publisher checks nonempty alpha, uncropped frames, palette pixel differences and state differences.
The independent Blender verifier reopens saved files and checks dimensions, origins, materials and
visibility. Neither synthetic verification nor a preview is evidence of human recognition rates.
