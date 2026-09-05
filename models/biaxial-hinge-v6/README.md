# Biaxial hinge V6 — controlled print package

This directory is the version-controlled manufacturing package. Files under
`tmp/biaxial-hinge-v6/` remain reproducible working output and are not source-controlled.

## Choose a workflow

| File | Use |
|---|---|
| `separate_parts_2body_2pin_2clip_mm.stl` | First-fit coupon: two bodies, two grooved PINs, two C clips |
| `print_in_place_2body_double_head_mm.stl` | Two-body print-in-place coupon with two captive double-headed PINs |
| `body_mm.stl` | One repeatable body |
| `assembly_pin_mm.stl` | One removable grooved PIN |
| `retaining_clip_mm.stl` | One experimental printed C clip |
| `biaxial_hinge_v6.blend` | Editable Blender source and complete assembly |

## Slicer contract

- [實測] STL coordinates and dimensions are millimetres. Import at **100% in mm**.
- [實測] Independent readback dimensions and SHA-256 values are recorded in `manifest.json`
  and checked by `tests/unit/scripts/test_versioned_print_package.py`.
- [讀檔: `docs/verification/biaxial-hinge-v6.md`] Do not auto-arrange the individual shells
  of the print-in-place coupon; their assembled relationship is intentional.
- [推論] Print the six-part separate coupon first so bore, PIN and clip fit can be observed
  without trapping a failed joint. This is process advice, not a verified printer profile.
- [未實測] Printer model, nozzle, material, supports, breakaway behavior, holding force,
  fatigue and motor load remain unqualified. The software readiness result is `review`.

Regenerate and promote the package only after the V6 real-Blender contracts pass:

```bash
$HOME/miniconda3/envs/blender-mcp/bin/python \
  scripts/verify/generated_artifact_verify_real.py \
  scripts/verify/contracts/biaxial_hinge.json
$HOME/miniconda3/envs/blender-mcp/bin/python scripts/publish_print_package.py
```
