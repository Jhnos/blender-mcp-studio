# Printer Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make printers a selectable, vendor-neutral data catalog. Bambu Lab P2S goes through Bambu Studio and six Creality machines go through OrcaSlicer. No default machine exists anywhere, and every vendor has its own real slice gate.

**Architecture:** Each printer is one YAML file under `config/printers/<vendor>/`, and each slicer is one entry in `config/slicers.yaml`. A single `OrcaFamilyCli` adapter, configured per slicer, replaces `BambuStudioCli`. Profiles are resolved by JSON `name` from the installed app's bundle. Spec v2 makes `print_target.printer` required and checks compatibility at submit time. The new MCP/REST surface `list_printers` shows only printers whose slicer is installed on this host.

**Tech Stack:** Python 3.11, FastAPI, FastMCP 3.x, PyYAML, Bambu Studio 02.08.02.61 and OrcaSlicer 2.4.2 CLIs (AGPL-3.0, subprocess only), pytest.

**Spec:** `docs/superpowers/specs/2026-10-22-printer-catalog-design.md` (approved 2026-10-22). Research evidence is in the spec §6.

## Global Constraints

- No printer, vendor or material default exists in any code path. `PrintTarget` has no default `printer`, and nothing returns a "first" printer implicitly.
- Profiles are read at runtime from the installed app bundle, at `<App>.app/Contents/Resources/profiles/<Vendor>/{machine,process,filament}/`. They are never copied into the repo. Profiles are looked up by the JSON `name` field, not the filename.
- Slicers run as subprocesses only. The manifest `tools` entry records the slicer that actually ran, with its version and `AGPL-3.0-only`.
- The slice timeout is 5 × the slowest measured slice for that slicer. Record the measurement (date, model, part count, seconds) in a docstring.
- Binary paths come from `config/tools.yaml`, with environment variable overrides. No host names or home paths in code; `tests/unit/core/test_no_hardcoded_hosts.py` enforces this.
- Domain and use-case code imports only stdlib, `src.core.domain` and `src.core.ports`.
- Every Python file under `api/`, `src/` and `scripts/` stays at 380 lines or fewer. `src/core/use_cases/design_pipeline.py` is already at 380, so split before adding anything to it.
- Every exit (results, errors, job rows, reports, REST, MCP) carries no absolute host path. Use the existing `PathScrubber` choke point.
- New behaviour starts with a failing test, and `scripts/ci.sh` must pass before every commit.

## Review Focus

1. A spec naming a printer whose slicer is not installed must be rejected at submit, naming the missing slicer and its install hint. It must never be queued. → Task 4, `test_submit_rejects_printer_with_missing_slicer`.
2. A material that the catalog lists but the bundle's profile does not declare compatible (`compatible_printers` excludes the machine) must be rejected at submit. → Task 2, `test_incompatible_filament_rejected`; Task 4, `test_submit_rejects_incompatible_material`.
3. A v1 spec without `printer` keeps working, mapped to `bambu-p2s-0.4`. The report says so visibly, so the user never wonders which machine was used. → Task 4, `test_v1_spec_maps_to_legacy_printer_with_note`.
4. Two printer YAML files with the same `id`, or a YAML that names a slicer not in `slicers.yaml`, must fail loading with the file named. They must not be silently overwritten. → Task 1, `test_duplicate_printer_id_rejected` and `test_unknown_slicer_rejected`.
5. A profile name that resolves to no file in the bundle, for example after an app update renames a profile, gives a failed slice result naming the profile. It must not raise a bare KeyError. → Task 2, `test_unknown_profile_name_names_it`.

---

### Task 1: Printer and slicer catalog (domain + loader + data)

**Files:**
- Create:
  - `src/core/domain/printer_catalog.py`
  - `src/infrastructure/printer_catalog_loader.py`
  - `config/slicers.yaml`
  - `config/printers/bambu/bambu-p2s-0.4.yaml`
  - `config/printers/creality/creality-{k1c,k1,k1-max,k2-plus,ender-3-v3,ender-3-v3-ke}-0.4.yaml`
- Modify:
  - `config/tools.yaml`: add `orcaslicer_bin: /Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer`
  - `src/infrastructure/tools_config.py`: add `orcaslicer_bin`, with env override `ORCASLICER_BIN`
  - `docs/10-runtime-ssot.md`: document `ORCASLICER_BIN` and the two catalog files
- Test: `tests/unit/infrastructure/test_printer_catalog_loader.py`

**Interfaces:**
- Produces (domain, frozen dataclasses):
  - `SlicerSpec(id: str, name: str, binary_key: str, profiles_subdir: str, license: str, error_codes: tuple[tuple[int, str], ...], install_hint: str)`
  - `PrinterProfile(id: str, vendor: str, model: str, nozzle_mm: float, slicer: str, profile_vendor_dir: str, machine: str, processes: tuple[tuple[str, str], ...], filaments: tuple[tuple[str, str], ...], bed_type: str, overrides: str | None)`
    - `processes` maps a layer-height string such as `"0.20"` to a profile name.
    - `filaments` maps a material such as `"PLA"` to a profile name.
    - `overrides` is a filename under `config/slicer-profiles/`.
  - `PrinterCatalog(printers: tuple[PrinterProfile, ...], slicers: tuple[SlicerSpec, ...])`, with methods `printer(id) -> PrinterProfile` (raises `UnknownPrinterError(DomainError)`, whose message lists every id) and `slicer(id) -> SlicerSpec`.
- Produces (infrastructure): `load_printer_catalog(config_dir: Path | None = None) -> PrinterCatalog`.

**Exact data:**
- `slicers.yaml`:
  - `bambu-studio`: name "Bambu Studio", binary_key `bambu_studio_bin`, profiles_subdir `Contents/Resources/profiles`, license `AGPL-3.0-only`, error codes `[]`.
  - `orcaslicer`: name "OrcaSlicer", binary_key `orcaslicer_bin`, the same profiles_subdir, license `AGPL-3.0-only`, error codes:
    - −2 invalid params
    - −3 file not found
    - −5 config file error
    - −13 export 3MF error
    - −17 process not compatible
    - −50 no suitable objects
    - −51 validate error
    - −60 no suitable objects after skip
    - −61 filament does not match bed type
    - −100 slicing error
- P2S: vendor_dir `BBL`, machine `Bambu Lab P2S 0.4 nozzle`, process `"0.20": "0.20mm Standard @BBL P2S"`, PLA `Generic PLA @BBL P2S`, bed `Textured PEI Plate`, overrides `p2s-pla-overrides.json`, slicer `bambu-studio`.
- Creality, all with slicer `orcaslicer` and vendor_dir `Creality`: copy the machine, process and PLA names verbatim from the table in `docs/superpowers/specs/2026-10-22-orcaslicer-research.md` §3. The controller pastes that table into the task brief.
  - K1 and K1 Max PLA must be `Creality HF Generic PLA`.
  - K1C PLA is `Creality Generic PLA @K1C-all` (exact name from the table).
  - K2 Plus PLA is `Generic PLA @K2 Plus-all` (exact name from the table).
  - Both Ender-3 V3 PLAs are `Creality Generic PLA @Ender-3V3-all`.
  - K-series bed is `Textured PEI Plate`. For the Ender-3 V3 bed, read `default_bed_type` from the machine_model file in the installed OrcaSlicer bundle; if none is declared, use `Textured PEI Plate` and leave a YAML comment citing the file checked.
  - Creality overrides are `null`.

- [ ] **Step 1:** Write the tests:
  - `test_loads_seven_printers_and_two_slicers`
  - `test_unknown_printer_error_lists_ids`
  - `test_duplicate_printer_id_rejected`
  - `test_unknown_slicer_rejected`
  - `test_no_default_printer_exists`: `PrintTarget` cannot be built without `printer`, and the catalog has no "default" attribute or function.
  - `test_orcaslicer_bin_env_override`
- [ ] **Step 2:** Run them. Expect FAIL with ImportError.
- [ ] **Step 3:** Implement the code and add the data files.
- [ ] **Step 4:** Run them. Expect PASS. Then run `scripts/ci.sh`.
- [ ] **Step 5:** Commit: `feat(printers): vendor-neutral printer and slicer catalog as data`.

### Task 2: Profile resolution by JSON name + compatibility check

**Files:**
- Modify: `src/adapters/slicing/bundle_profiles.py`. Replace the filename-based leaf lookup with a per-kind name index, built once per bundle and kind by reading each JSON file's `name`. `inherits` resolves through the same index. Delete `LEAVES_FILE`.
- Delete: `config/slicer-profiles/p2s-pla-profiles.json`, superseded by the P2S printer YAML.
- Test: `tests/unit/adapters/test_bambu_bundle_profiles.py`, extended with fixtures in `tests/fakes/bambu_bundle.py` where the filename differs from the name.

**Interfaces:**
- Consumes: `PrinterProfile` (Task 1).
- Produces:
  - `resolve_printer_profiles(bundle_profiles_root: Path, printer: PrinterProfile, layer_height: str, material: str) -> dict[str, dict[str, object]]` returns the keys `machine`, `process` and `filament`, each a flattened profile dict.
  - `check_compatible(profiles: dict[str, dict[str, object]], machine_name: str) -> None` raises `IncompatibleProfileError(DomainError)` naming the profile and the machine.
  - `UnknownProfileError(DomainError)`.

- [ ] **Step 1:** Write the tests:
  - `test_name_index_resolves_when_filename_differs`
  - `test_inherits_resolves_by_name`
  - `test_unknown_profile_name_names_it`
  - `test_incompatible_filament_rejected`: a fixture filament whose `compatible_printers` excludes the machine.
  - `test_empty_compatible_printers_means_any`
- [ ] **Step 2:** Run the tests and confirm they fail.
- [ ] **Step 3:** Implement the code.
- [ ] **Step 4:** Regression check, run in the foreground and reported:
  - Flatten P2S through the new path from `/Applications/BambuStudio.app`. The result must be JSON-equal to the result of the old path at `HEAD`, run from a temp checkout or `git show`.
  - Flatten each of the 6 Creality printers from `/Applications/OrcaSlicer.app`.
  - Run `check_compatible` on all 7 printers. Any failure stops the task and gets reported.
- [ ] **Step 5:** Run `scripts/ci.sh`, then commit: `feat(slicing): resolve bundle profiles by JSON name, check printer compatibility`.

### Task 3: One Orca-family CLI adapter for both slicers

**Files:**
- Create: `src/adapters/slicing/orca_family_cli.py`. It replaces `bambu_studio_cli.py`. Keep the argv shape, the stale-output deletion, the `TemporaryDirectory` datadir and the timeout-as-result behaviour. The plate type comes from `printer.bed_type`. Overrides come from `printer.overrides`, or none at all.
- Modify:
  - `src/core/domain/slicing.py`: `SliceRequest` gains `printer_id: str`, and `printer`/`material` become plain carried values.
  - `src/core/ports/slicing_port.py`: the port becomes catalog-aware (see Interfaces).
  - `api/runtime.py`: build one adapter for the catalog.
- Delete: `src/adapters/slicing/bambu_studio_cli.py`, after its tests move to `tests/unit/adapters/test_orca_family_cli.py`.

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces:
  - `SlicingPort.printers() -> tuple[PrinterProfile, ...]` returns only the printers whose slicer binary is usable.
  - `SlicingPort.availability() -> tuple[ToolAvailability, ...]`, one entry per slicer in the catalog.
  - `SlicingPort.timeout_s(printer_id: str) -> float`
  - `SlicingPort.slice(request: SliceRequest) -> SliceResult`
  - `SlicingPort.tool_for(printer_id: str) -> ToolUse`, the AGPL entry for the manifest.

**Exit codes:** if `rc != 0`, map `rc` against `error_codes`, also trying `rc - 256` so a shell-wrapped negative code matches. The result message names the mapped meaning. `passed` stays `rc == 0 and the 3MF exists`.

**Timeouts:**
- Bambu Studio keeps `SLOWEST_SLICE_MEASURED_S = 171`.
- OrcaSlicer: measure one real run of v78's 69 parts on `creality-k1c-0.4`, in the foreground, through the adapter with the real binary. Record date, model, parts and seconds. Timeout = 5 × measured, rounded up to the next second.
  - If the real run fails, stop and report the log tail. Do not guess a value.
  - During that run, record whether `result.json` is written on macOS, and say so in the adapter docstring.

- [ ] **Step 1:** Move the Bambu tests across and write the new ones:
  - `test_each_printer_uses_its_slicer_binary`
  - `test_orca_negative_exit_code_mapped`: rc 156 maps to "slicing error".
  - `test_printers_lists_only_installed_slicers`
  - `test_tool_for_names_the_slicer_that_ran`
  - `test_bed_type_from_printer`
  - `test_no_overrides_for_creality`
- [ ] **Step 2:** Run the tests and confirm they fail.
- [ ] **Step 3:** Implement the adapter. Measure the OrcaSlicer timeout and record it.
- [ ] **Step 4:** Run `scripts/ci.sh`.
- [ ] **Step 5:** Commit: `feat(slicing): one Orca-family CLI adapter drives Bambu Studio and OrcaSlicer`.

### Task 4: Spec v2: printer required, submit-time checks

**Files:**
- Modify:
  - `src/core/domain/model_spec.py`: `SUPPORTED_SPEC_VERSIONS = ("1", "2")`. In v2, `print_target.printer` is required and `PrintTarget` has no default printer. In v1, a missing printer maps to `LEGACY_V1_PRINTER = "bambu-p2s-0.4"`, and the parse records `legacy_default: True`.
  - `src/core/domain/model_spec_schema.py`: `describe_model_spec(printers: tuple[PrinterProfile, ...])` describes v2. Its `printer` enum holds the installed printer ids, and its example uses `bambu-p2s-0.4`.
  - The use-case submit path goes in a new `src/core/use_cases/design_targets.py`, which keeps `design_pipeline.py` within budget. It does three checks, in this order:
    1. The printer is known in the catalog. If not, the error lists all ids.
    2. The printer's slicer is installed. If not, the error names the slicer and its install hint.
    3. The material and process are compatible, via Task 2's `check_compatible`.
  - The import or print stage report carries the message `"printer bambu-p2s-0.4 used by spec v1 legacy default"` when `legacy_default` is set.
- Test: `tests/unit/core/test_model_spec_v2.py` and `tests/unit/core/test_design_targets.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: `check_print_target(target: PrintTarget, slicing: SlicingPort) -> PrinterProfile`. It raises `ModelSpecError` with the messages above.

- [ ] **Step 1:** Write the tests:
  - `test_v2_requires_printer`
  - `test_submit_rejects_unknown_printer_listing_ids`
  - `test_submit_rejects_printer_with_missing_slicer`
  - `test_submit_rejects_incompatible_material`
  - `test_v1_spec_maps_to_legacy_printer_with_note`
  - `test_describe_model_spec_v2_example_parses`
- [ ] **Step 2:** Run them and confirm they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `scripts/ci.sh`.
- [ ] **Step 5:** Commit: `feat(spec): v2 requires an explicit printer, checked against the catalog at submit`.

### Task 5: `list_printers` over MCP and REST

**Files:**
- Modify:
  - `src/adapters/mcp_server/design_tools.py`: add the read-only tool `list_printers()`.
    - For each installed printer it returns `id`, `vendor`, `model`, `nozzle_mm`, `materials`, `layer_heights`, `bed_type` and the slicer's name and version. It carries no paths.
    - `tool_status` returns one entry per slicer.
    - `slice_for_print(input_3mf, printer)` has `printer` required, with no default value.
    - The `run_design_pipeline` and `describe_model_spec` descriptions point to `list_printers`.
  - `api/routers/design.py`: `GET /api/design/printers` returns the same payload.
  - `src/adapters/design_payloads.py`: `printer_dict`.
  - Tests and docs: `tests/unit/adapters/test_mcp_server.py` (`EXPECTED_TOOLS`/`POLICY`) and the e2e count go from 21 to 22 tools. Update `docs/11-mcp-clients.md`, `docs/README.md` and `docs/01-architecture.md`.
- Test: `tests/unit/adapters/test_mcp_printer_tools.py` and `tests/e2e/test_design_http.py`

- [ ] **Step 1:** Write the tests:
  - `test_list_printers_only_installed`
  - `test_list_printers_has_no_paths`
  - `test_slice_for_print_requires_printer`
  - `test_rest_printers_matches_mcp`
- [ ] **Step 2:** Run them and confirm they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `scripts/ci.sh`.
- [ ] **Step 5:** Commit: `feat(mcp): list_printers and printer-required slicing`.

### Task 6: One real gate per vendor

**Files:**
- Modify: `scripts/verify/contracts/design_pipeline_v78.json`. Set `spec_version` to `"2"` and `print_target.printer` to `"bambu-p2s-0.4"`. Expected numbers stay the same.
- Create: `scripts/verify/contracts/design_pipeline_v78_creality_k1c.json`. It has the same source and `printer: "creality-k1c-0.4"`, and expects 69 STLs, 1 plate, and a manifest tool `OrcaSlicer 2.4.2 AGPL-3.0-only`.
- Modify:
  - `scripts/verify/design_pipeline_verify_real.py` and `design_gate_checks.py`:
    - assert the manifest tool name and version taken from the contract;
    - add a negative control per contract: the same spec with an incompatible material for that printer, or an unknown printer, must be rejected at submit with a message naming it.
  - `scripts/ci.sh`: wire a second `_run hard "design pipeline on the v78 deliverable (Creality K1C via OrcaSlicer)" …` line right after the existing one.
- Test: `tests/unit/verification/test_design_pipeline_gate.py`

- [ ] **Step 1:** Write the tests:
  - `test_gate_asserts_tool_from_contract`
  - `test_submit_negative_control_message_check`
  - `test_ci_runs_both_vendor_gates`
- [ ] **Step 2:** Run them and confirm they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `scripts/ci.sh`.
- [ ] **Step 5:** Commit: `test(real): one real slice gate per vendor`.

The real run happens after merge and deploy, done by the controller.
