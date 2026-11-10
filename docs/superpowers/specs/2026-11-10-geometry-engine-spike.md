# solidcraft vs build123d geometry-engine spike

> Prior-art evidence for phase 1b (user chose 2026-11-10: wire **both** engines behind one
> GeometryPort, solidcraft pinned to 0.30.1). This is a throwaway spike report, kept here because
> its working files lived in a session scratch directory that no longer exists. Inputs:
> solidcraft-cli 0.30.1 macos-universal (official release zip, SHA-256
> `1effd9b3…dc2f` matched SHA256SUMS.txt; Developer ID "Brennen Herbruck (G5QA5U5X2S)", notarized),
> build123d 0.13.0 in an isolated venv.
>
> **Controller re-checks (2026-11-09, first-hand):** reran the solidcraft bracket (0.47 s, B-rep
> volume 8723.18 mm³ against an analytic 8723.10); ran our `TrimeshCgalIntegrity` gate on all three
> solidcraft STLs (watertight, no self-intersection, genus 4/1/0); a too-large fillet gave exit 1, the
> one-line message "largest radius that fits is 4 mm", and no STL. Determinism: five runs gave
> identical bytes **after the 80-byte STL header**. The header embeds the output file name, so
> whole-file hashes differ when the names differ. Compare bodies, not whole files.

Everything below lived under `work/<engine>/<part>/` (script, .out/.err/.meta, .stl, .step, .check.json/.check.log) in the session scratch directory. Gate = `TrimeshCgalIntegrity` from the main checkout (read-only); wall times measured per process.

## Part definitions (written once, used for both engines; mm)
1. **Bracket**: flat plate X0-40 Y0-30 Z0-4; vertical plate X0-40 Y0-4 Z0-30 (they overlap in a 40x4x4 corner block, unioned). 4x D5 through-holes: flat plate at (x=10|30, y=15) through Z; vertical plate at (x=10|30, z=15) through Y. R3 fillet on the inner corner edge (along X at y=4,z=4). Bounds 40x30x30.
   Volume = 2*40*30*4 - 40*4*4 - 4*pi*2.5^2*4 + 40*3^2*(1-pi/4) = 9600 - 640 - 314.159 + 77.256 = **8723.10**. Genus 4.
2. **Knuckle**: block X0-20 Y0-12 Z0-6; boss D12 cylinder, axis Z (the 6 mm direction), centred at (x=20,y=6), z0-6 (half inside the block, half sticking out; the "12 mm edge" = the x=20 end edge). D4.2 pin hole through the boss axis along Z. 0.4 mm equal-distance chamfer on both pin-hole circular edges. Bounds 26x12x6.
   Volume = 20*12*6 + pi*6^2*6/2 - pi*2.1^2*6 - 2*(2*pi*2.2333*0.08) = 1440 + 339.292 - 83.126 - 2.245 = **1693.92**. Genus 1.
3. **Shelled box**: outer X0-50 Y0-30 Z0-20, 4 vertical edges R2, open top, 1.6 walls and floor (so inner vertical corner R0.4). Lip: cavity widened 1 mm per side for the top 3 mm (z17-20), pocket corner R1.4, leaving 0.6 mm wall at the rim. Bounds 50x30x20.
   Areas: out = 1500 - 4*4*(1-pi/4) = 1496.566; in (46.8x26.8, r0.4) = 1254.103; lip (48.8x28.8, r1.4) = 1403.76. Volume = 1496.566*20 - 1254.103*18.4 - (1403.76-1254.103)*3 = **6406.87**. Genus 0.

Tolerances: bounds 0.05 mm on size (not origin), volume 1 %, watertight + self_intersecting=False from the gate. Genus = (2*bodies - euler)/2 with a union-find body count (trimesh's own split needs scipy/networkx, which the gate env lacks; that is an env gap, not an engine issue).

## Results (6 cells)
| engine | part | attempts | gate watertight / self-int | size | volume (err vs analytic) | genus | wall | script lines | first error (head) |
|---|---|---|---|---|---|---|---|---|---|
| build123d | bracket | 1 | True / False | 40x30x30 ok | 8723.34 (+0.003 %) | 4 | 4.70 s | 23 py | - |
| build123d | knuckle | 2 (a1 failed) | True / False (a2) | 25.998x12x6 ok | 1693.82 (-0.006 %) | 1 | 3.07 s (a1, failed), 2.29 s (a2) | 17 py | `AttributeError: 'ShapeList' object has no attribute 'filter'. Did you mean: 'filter_by'?` |
| build123d | box | 1 | True / False | 50x30x20 ok | 6406.78 (-0.001 %) | 0 | 2.14 s | 19 py | - |
| solidcraft | bracket | 1 | True / False | 40x30x30 ok | 8724.39 (+0.015 %) | 4 | 0.46 s | 9 json | - |
| solidcraft | knuckle | 1 | True / False | 25.997x12x6 ok | 1693.82 (-0.006 %) | 1 | 0.25 s | 6 json | - |
| solidcraft | box | 1 | True / False | 50x30x20 ok | 6405.57 (-0.020 %) | 0 | 0.16 s | 9 json | - |

Wall times include Python/venv startup + OCCT import for build123d (~2 s floor), and the whole process for solidcraft (STL+STEP both exported in the same run). Exact numbers: `work/<engine>/<part>/*.meta`, `*.check.json`.

Features not expressible: none in either engine for these three parts. Notes: solidcraft has no "hole chamfer" parameter on `solid.hole` that covers both ends (countersink is one-sided), so I used `solid.chamfer` on circular edges picked by a point on each edge. build123d needed an explicit edge filter. Solidcraft's rounded-lip pocket needed an explicit sketch plane+extrude cut; build123d the same (BuildSketch + extrude subtract).

## Comparison
**First-try / final success.** build123d 2/3 first-try, 3/3 final (1 repair). solidcraft 3/3 first-try, 3/3 final. With n=3 per engine this is **not** a statistically meaningful difference (see honesty).

**Error-message quality for self-repair** (probe runs that were NOT counted as attempts; `work/probes/probe_results.json`, `probe_b123.json`):
- solidcraft quotes the step index + command and tells the fix: `error: step 2 (solid.fillet): invalid parameters for solid.fillet: [1, 1, 1] is where 3 edges meet: give a point along one edge, such as its midpoint`; `... the blend is larger than the neighbouring faces; the largest radius that fits is 4 mm`; `unknown command solid.cube (did you mean solid.cone?)`; `step 2 (solid.hole): position [10, 15, 10] is not on a face of a body; pick a point on the face to drill`. One weak spot: a misspelled parameter (`len` instead of `length`) reports `length must be a number or an expression` (missing-required, not "unknown key len").
- build123d is a Python traceback; the real message is on the last line. Good: `NameError ... Did you mean: 'Curve'?`, `ValueError: Failed creating a fillet with radius of 9, try a smaller value or use max_fillet() to find the largest valid fillet radius`. Weak: an *empty edge selection* surfaces as the same "Failed creating a fillet with radius of 1" message, which sends the repair toward the radius, not the selection (misleading).
- Both fail loudly with exit 1 on error. solidcraft writes no STL on failure (`stl_written: false` in all six probes), so a stale file cannot be mistaken for output.

**Expressiveness gaps.** None hit by these parts. Observed friction: solidcraft picks edges/faces by a world-coordinate point on them (need a point strictly on the edge, not a vertex); this is simple on axis-aligned parts but I did not test curved or heavily patterned parts. build123d selects via Python filters (more powerful, more ways to write a wrong filter). Boolean/fillet/chamfer/shell/hole/extrude-cut were all available in both.

**Headless / CLI ergonomics for subprocess wrapping.**
- solidcraft: `solidcraft-cli run script.json --out a.stl --out a.step`; stdout = JSON measurement of the bodies (volume, area, bbox, closed flag, face types, mass); errors on stderr as one line, exit 1; no network; ~0.2-0.5 s per run; STL and STEP in one call; `--allow-errors`, `--json-out`, `--param-check`, `eval`, `snapshot` also exist (not exercised except `run`). The built-in `closed: true` + volume in stdout is a free pre-gate.
- build123d: needs a Python process per script (arbitrary code execution: the sandboxing problem is the host's to solve); ~2-5 s per run; the script itself chooses the output path.
- **Determinism** (`work/probe.py`, same script run twice, sha256): solidcraft STL identical (`c789f0cd...d89099`) and STEP identical (`bd69b703...cdd3c`); build123d STL identical (`303c2be6...af7c1`) but STEP differs between runs (`dd2737cf...` vs `ce36d82c...`, almost certainly a STEP header timestamp; I did not verify the cause).

**Licence.** solidcraft: `MIT OR Apache-2.0` per its README and bundled LICENSE-MIT / LICENSE-APACHE files, plus THIRD-PARTY-LICENSES.txt in the zip (I did not audit that file). It is distributed as a signed binary, so using it means shipping/depending on a vendor binary (v0.30.1, early; README says "Early but usable for simple parts"). build123d: Apache-2.0 (from its package metadata, not re-read here: UNVERIFIED) on OpenCascade (LGPL-2.1 with exception, UNVERIFIED here), installed from PyPI. Neither licence blocks optional use behind a port from what I read; a real legal review of THIRD-PARTY-LICENSES.txt and OCCT is UNVERIFIED.

## Honesty
- **Bias.** I know build123d from training data far better than a 2026 Rust CAD's JSON command language, yet solidcraft still won first-try. But I was handed `solidcraft-cli commands` (a 570-command registry with per-command parameter docs, which I grep'ed for the params of ~10 commands) before writing; a real MCP host's LLM would need an equivalent tool-schema for the same effect. build123d's single failure was a trivial API slip (non-existent `ShapeList.filter`), not a modelling failure. I (the same model) wrote both sides and chose the part definitions after seeing both tools' capabilities, so the specs are not neutral.
- **Sample.** 3 simple, axis-aligned, single-body parts, one run each; one repair event decides the first-try gap. No curved sweeps, lofts, threads, assemblies, tolerances stacked on fillet-heavy topology, parametric changes, or large models. Not generalizable.
- **Gate coverage.** Integrity is checked on tessellated STL; solidcraft's STL tessellation tolerance and build123d's differ (`quality` default `standard` for solidcraft, build123d default tolerance); volume errors are all <= 0.02 % so this does not matter at 1 %. STEP outputs were produced but NOT validated by any gate (UNVERIFIED).
- **Not verified:** solidcraft MCP mode (`solidcraft-cli mcp`) was not run; Linux/Windows availability; behaviour under failures in later steps of long scripts; fillet-edge-picking robustness on non-trivial geometry; solidcraft's maturity (single vendor, v0.30.x); whether the `closed` flag in its stdout is equivalent to our CGAL gate (our gate is the one that was run).

## Recommendation
**Adopt solidcraft as an optional engine behind GeometryPort, not as a replacement for build123d** (keep build123d as the reference/fallback), because on this tiny sample it matched build123d on correctness, was ~10x faster, wrote no output on failure, is deterministic for both STL and STEP, and gives repair-friendly one-line errors with a data-only JSON script (no arbitrary code execution); the evidence is too thin (n=3, simple parts) to go further than "optional".
