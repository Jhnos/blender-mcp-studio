# MCP Complete — Phase 1 (printable mechanism, import path) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Any MCP host can submit a machine-readable `ModelSpec` and get back a printable package with machine-verified evidence (geometry, mechanism, print readiness and slicing, reproduction manifest), first on the user's delivered lab-station v78 artifact.

**Architecture:** A `DesignPipeline` application service runs five stages (import → geometry → mechanism → print → package) through new ports (`MeshIntegrityPort`, `SlicingPort`, `PackagingPort`, `MechanismSimulationPort`, `JobStorePort`); REST and MCP call the same service; every run writes `data/runs/<run_id>/report.json` plus artifacts. Hostnames, binaries and directories come only from `config/` and environment variables.

**Tech Stack:** Python 3.11, FastAPI, FastMCP 3.x, aiosqlite, pydantic 2 (API schemas only), `trimesh` (new runtime dependency, MIT), `cgal` (moved from dev to runtime), Bambu Studio CLI (AGPL-3.0, subprocess only), pytest/respx.

**Spec:** `docs/superpowers/specs/2026-10-21-mcp-complete-pipeline-design.md` (§4, §5, §5.2 decisions 1–8). Reuse evidence: `docs/superpowers/specs/2026-10-21-reuse-survey.md`.

## Global Constraints

- `src/core/domain` and `src/core/use_cases` import neither `bpy`, `fastapi`, `fastmcp` nor `trimesh`/`CGAL`; adapters do (`tests/unit/core/test_architecture_ssot.py` enforces the bpy half).
- No public MCP tool executes arbitrary code; the sandbox allowlist and `script_timeouts` stay as they are.
- Public DTOs already exported by REST/MCP keep their fields; new tools use new DTOs.
- Every Python file under `api/`, `src/`, `scripts/` stays ≤ 380 lines (`tests/unit/core/test_file_budgets.py`).
- New behaviour starts with a failing test; `scripts/ci.sh` (T1+T2) green before every commit; the real tier (`scripts/ci.sh --real`) is the acceptance evidence, run from this machine.
- Hostnames, binary paths and data directories are read from `config/tools.yaml` and environment variables only; the only Tailscale FQDN source is `tailscale status --self --json` or `BLENDER_MCP_PUBLIC_BASE_URL`.
- Hard timeouts are derived, not guessed: slicing timeout = 5 × the longest measured slice (v80: 69 parts) — record the measurement in the adapter docstring.
- Every change bumps `VERSION` (segment 3) and adds a CHANGELOG line in the same commit (`version.py bump patch`).
- Evidence dir: `data/runs/<run_id>/` (env `DESIGN_RUNS_DIR` overrides). Absent external tool = explicit `ToolUnavailableError` with the install hint; never a skipped-green stage.

## Review Focus

1. A `ModelSpec.source.root_dir` pointing outside the allowed artifact roots (`..`, absolute path to `/etc`) must be rejected before any file is read — Task 1 `test_imported_artifact_rejects_escape`.
2. An ASCII STL (starts with `solid`) or a zero-triangle binary STL must produce a geometry FAIL with the file named, not a crash — Task 2 `test_integrity_reports_unreadable_stl`.
3. The slicer binary missing or exiting non-zero must surface as a print-stage FAIL with the log tail, never as a passed stage — Task 3 `test_slice_reports_missing_binary` / `test_slice_reports_nonzero_exit`.
4. Two concurrent `run_design_pipeline` submissions: the second must wait for or be refused by the Blender lease, never interleave inside a stage — Task 5 `test_second_run_waits_for_blender_lease`.
5. A remote MCP host asking for an evidence file by name must not be able to read outside the run directory — Task 6 `test_run_file_download_rejects_traversal`.

---

### Task 0: Task file and index entry

**Files:**
- Create: `docs/tasks/17_mcp-complete-pipeline.md` (from `docs/tasks/templates/task_template.md`)
- Modify: `docs/tasks/00_INDEX.md` (table row `ACTIVE | 17_mcp-complete-pipeline.md`; task 16 stays ACTIVE for the physical qualification)
- Test: `tests/unit/core/test_docs_dcc.py` (existing)

- [ ] **Step 1: Write the task file** — Goal: Phase 1 of the spec; Context: the spec and this plan; Acceptance checks: the real-tier gate from Task 9 green, `run_design_pipeline` reachable through the canonical MCP URL; Hand-off buckets empty.
- [ ] **Step 2: Run** `python -m pytest tests/unit/core/test_docs_dcc.py -q` — Expected: PASS (new doc reachable from README within 2 hops via the index).
- [ ] **Step 3: Commit** `docs: open task 17 for the MCP pipeline`.

### Task 1: Domain — `ModelSpec` and run/stage/job records

**Files:**
- Create: `src/core/domain/model_spec.py`, `src/core/domain/design_run.py`
- Test: `tests/unit/core/test_model_spec.py`, `tests/unit/core/test_design_run.py`

**Interfaces (produces):**
```python
# src/core/domain/model_spec.py  (frozen dataclasses, slots=True; no pydantic here)
class PrintTarget:  printer: str = "bambu-p2s"; material: str = "PLA"; layer_height_mm: float = 0.2; support: bool = True; brim_mm: float = 3.0
class ImportedArtifact:  root_dir: str; stl_glob: str = "STL/*.stl"; project_3mf: str | None = None
class MechanismChecks:  suites: tuple[str, ...] = ()        # registered suite ids; () = declared not applicable
class ModelSpec:  spec_version: str; name: str; source: ImportedArtifact; print_target: PrintTarget; mechanism: MechanismChecks
def parse_model_spec(payload: Mapping[str, object], *, artifact_roots: tuple[Path, ...]) -> ModelSpec   # raises ModelSpecError
class ModelSpecError(DomainError): ...
# src/core/domain/design_run.py
class StageName(StrEnum): IMPORT="import"; GEOMETRY="geometry"; MECHANISM="mechanism"; PRINT="print"; PACKAGE="package"
class StageOutcome(StrEnum): PASSED="passed"; FAILED="failed"; NOT_APPLICABLE="not_applicable"
class StageReport:  name: StageName; outcome: StageOutcome; metrics: tuple[tuple[str, str], ...]; evidence: tuple[str, ...]; message: str
class DesignRunReport:  run_id: str; spec_name: str; stages: tuple[StageReport, ...]; passed: bool; run_dir: str
class JobStatus(StrEnum): QUEUED="queued"; RUNNING="running"; DONE="done"; FAILED="failed"; CANCELLED="cancelled"
class JobRecord:  job_id: str; run_id: str; status: JobStatus; stage: StageName | None; error: str | None; created_at: float; updated_at: float
```

- [ ] **Step 1: Write failing tests** in `tests/unit/core/test_model_spec.py`:
```python
def test_parse_minimal_spec_resolves_root_inside_allowed_roots(tmp_path):
    (tmp_path / "v78").mkdir()
    spec = parse_model_spec({"spec_version": "1", "name": "v78", "source": {"root_dir": "v78"}}, artifact_roots=(tmp_path,))
    assert spec.source.root_dir == str(tmp_path / "v78") and spec.print_target.printer == "bambu-p2s" and spec.mechanism.suites == ()
def test_imported_artifact_rejects_escape(tmp_path):
    with pytest.raises(ModelSpecError): parse_model_spec({"spec_version": "1", "name": "x", "source": {"root_dir": "../etc"}}, artifact_roots=(tmp_path,))
def test_unknown_spec_version_is_rejected(tmp_path): ...  # "2" -> ModelSpecError
def test_unknown_keys_are_rejected(tmp_path): ...         # {"source": {"root_dir": "v78", "code": "x"}} -> ModelSpecError
```
and in `tests/unit/core/test_design_run.py`: `test_report_passed_only_when_every_stage_passed_or_not_applicable` (one FAILED stage → `passed is False`).
- [ ] **Step 2: Run** `pytest tests/unit/core/test_model_spec.py tests/unit/core/test_design_run.py -q` — Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** the two modules. `parse_model_spec` resolves `root_dir` against each allowed root with `Path.resolve()` and requires `is_relative_to`; unknown keys at any level raise `ModelSpecError`; `DesignRunReport.passed` is a property computed from stages.
- [ ] **Step 4: Run** the two test files — Expected: PASS. Run `python -m pytest tests/unit/core/test_architecture_ssot.py -q` — Expected: PASS (no bpy).
- [ ] **Step 5: Commit** `feat(domain): ModelSpec and design run records`.

### Task 2: `MeshIntegrityPort` + host-side CGAL/trimesh adapter

**Files:**
- Create: `src/core/ports/mesh_integrity_port.py`, `src/core/domain/mesh_integrity.py`, `src/adapters/mesh/trimesh_cgal_integrity.py`
- Modify: `pyproject.toml` (add `trimesh>=4.4,<6` to `dependencies`; move `cgal>=6.0.1,<6.1` from `dev` to `dependencies`)
- Test: `tests/unit/adapters/test_mesh_integrity_adapter.py`

**Interfaces:**
```python
# domain/mesh_integrity.py
class MeshVerdict:  path: str; vertices: int; triangles: int; watertight: bool; self_intersecting: bool; error: str | None
    @property passed -> bool  # error is None and watertight and not self_intersecting and triangles > 0
class MeshIntegrityReport:  verdicts: tuple[MeshVerdict, ...]; passed: bool
# ports/mesh_integrity_port.py
class MeshIntegrityPort(Protocol):
    async def check(self, stl_paths: tuple[str, ...]) -> MeshIntegrityReport: ...
# adapters/mesh/trimesh_cgal_integrity.py
class TrimeshCgalIntegrity:  # loads each STL with trimesh, builds {'vertices','faces'} and calls src.verification.mesh_integrity.require_triangle_surface; runs in a thread (asyncio.to_thread)
    async def check(self, stl_paths: tuple[str, ...]) -> MeshIntegrityReport: ...
```

- [ ] **Step 1: Write failing tests** (fixtures built with `trimesh.creation.box()` exported to `tmp_path`):
```python
async def test_closed_box_passes(tmp_path): ...                       # watertight True, self_intersecting False, passed True
async def test_open_box_fails_watertight(tmp_path): ...               # delete one face before export -> watertight False
async def test_integrity_reports_unreadable_stl(tmp_path): ...        # write b"solid x\n" -> verdict.error mentions the path, report.passed False, no exception
async def test_self_intersecting_pair_is_reported(tmp_path): ...      # two boxes overlapping concatenated into one mesh -> self_intersecting True
```
- [ ] **Step 2: Run** `pytest tests/unit/adapters/test_mesh_integrity_adapter.py -q` — Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** port, DTOs, adapter; install deps with `pip install -e ".[dev]"` in the conda env; verify `python -c "import trimesh, CGAL"`.
- [ ] **Step 4: Run** the test file and `python -m pytest tests/unit/scripts/test_mesh_integrity.py -q` — Expected: PASS both (existing CGAL tests untouched).
- [ ] **Step 5: Commit** `feat(mesh): MeshIntegrityPort with trimesh+CGAL adapter`.

### Task 3: `SlicingPort` + Bambu Studio CLI adapter + `config/tools.yaml`

**Files:**
- Create: `src/core/ports/slicing_port.py`, `src/core/domain/slicing.py`, `src/adapters/slicing/bambu_studio_cli.py`, `config/tools.yaml`, `src/infrastructure/tools_config.py`
- Modify: `src/infrastructure/config_loader.py` (add `load_tools(config_dir: Path | None = None) -> dict[str, object]`), `docs/10-runtime-ssot.md` (env vars `BAMBU_STUDIO_BIN`, `DESIGN_RUNS_DIR`, `BLENDER_MCP_PUBLIC_BASE_URL`, `ARTIFACT_ROOTS`)
- Test: `tests/unit/adapters/test_bambu_studio_cli.py`, `tests/unit/infrastructure/test_tools_config.py`

**Interfaces:**
```python
# domain/slicing.py
class SliceRequest:  input_3mf: str; output_dir: str; printer: str; material: str; layer_height_mm: float; support: bool; brim_mm: float
class SliceResult:  passed: bool; output_3mf: str | None; settings_json: str | None; log_path: str; return_code: int; message: str
class ToolAvailability:  name: str; available: bool; path: str | None; version: str | None; install_hint: str
class ToolUnavailableError(DomainError): ...
# ports/slicing_port.py
class SlicingPort(Protocol):
    async def availability(self) -> ToolAvailability: ...
    async def slice(self, request: SliceRequest) -> SliceResult: ...
# infrastructure/tools_config.py
class ToolsConfig:  bambu_studio_bin: Path; design_runs_dir: Path; artifact_roots: tuple[Path, ...]
def load_tools_config(env: Mapping[str, str] | None = None, config_dir: Path | None = None) -> ToolsConfig   # yaml defaults, env overrides
# adapters/slicing/bambu_studio_cli.py
class BambuStudioCli:
    def __init__(self, binary: Path, *, profiles_dir: Path, timeout_s: float = SLICE_TIMEOUT_S, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run) -> None: ...
    async def availability(self) -> ToolAvailability: ...
    async def slice(self, request: SliceRequest) -> SliceResult: ...
SLOWEST_SLICE_MEASURED_S = <measured on v80, record the number>; SLICE_TIMEOUT_S = 5 * SLOWEST_SLICE_MEASURED_S
```
Command line is the v80-proven form (`tmp/lab-station-slicing-v80/slice_candidate.py:14`): `--datadir`, `--debug 2`, `--load-settings <machine.json>;<process.json>`, `--load-filaments <filament.json>`, `--curr-bed-type "Textured PEI Plate"`, `--arrange 0 --orient 0 --slice 0`, `--outputdir <out>`, `--export-3mf <name>.3mf`, `--export-settings <out>/effective-settings.json`, `<input.3mf>`. The three profile JSONs are generated from `request` into `output_dir` by the adapter (`machine.json`, `process.json`, `filament.json`) using the P2S/PLA templates copied from v80's `prepare_profiles.py` into `config/slicer-profiles/` (BSD-compatible JSON data, not binaries).
`config/tools.yaml` defaults: `bambu_studio_bin: /Applications/BambuStudio.app/Contents/MacOS/BambuStudio`, `design_runs_dir: data/runs`, `artifact_roots: [".", "models"]`.

- [ ] **Step 1: Write failing tests** with a fake `runner` that records argv and writes the expected output files:
```python
def test_tools_config_env_overrides_yaml(monkeypatch, tmp_path): ...          # BAMBU_STUDIO_BIN, DESIGN_RUNS_DIR, ARTIFACT_ROOTS (os.pathsep-separated)
async def test_availability_reports_missing_binary(tmp_path): ...             # available False, install_hint mentions "BambuStudio.app"
async def test_slice_reports_missing_binary(tmp_path): ...                    # raises ToolUnavailableError
async def test_slice_builds_the_v80_command_line(tmp_path): ...               # argv contains every flag above in order; export name "<input stem>-P2S-PLA.3mf"
async def test_slice_reports_nonzero_exit(tmp_path): ...                      # runner returncode 2 -> passed False, message has last log lines
async def test_slice_passes_when_output_3mf_exists(tmp_path): ...             # returncode 0 and the 3mf written -> passed True
```
- [ ] **Step 2: Run** both test files — Expected: FAIL (ImportError).
- [ ] **Step 3: Implement** config loader, adapter, yaml and profile templates; measure `SLOWEST_SLICE_MEASURED_S` by one real CLI run on the v78 3MF if the binary is installed, else record "not yet measured, provisional 600" and a TODO that the real-tier gate (Task 9) replaces it.
- [ ] **Step 4: Run** tests — Expected: PASS. `python -m pytest tests/unit/core/test_docs_dcc.py -q` — Expected: PASS (env vars listed only in 10-runtime-ssot).
- [ ] **Step 5: Commit** `feat(slicing): SlicingPort with Bambu Studio CLI adapter and tools config`.

### Task 4: `PackagingPort` + manifest adapter

**Files:**
- Create: `src/core/ports/packaging_port.py`, `src/core/domain/packaging.py`, `src/adapters/packaging/manifest_packager.py`
- Test: `tests/unit/adapters/test_manifest_packager.py`

**Interfaces:**
```python
# domain/packaging.py
class PackagedFile:  path: str; sha256: str; bytes: int; triangles: int | None
class PackageManifest:  run_id: str; spec_name: str; files: tuple[PackagedFile, ...]; manifest_path: str
# ports/packaging_port.py
class PackagingPort(Protocol):
    async def package(self, run_id: str, spec_name: str, run_dir: str, files: tuple[str, ...]) -> PackageManifest: ...
# adapters/packaging/manifest_packager.py
class ManifestPackager:  # copies nothing; hashes files already under run_dir, counts STL triangles with trimesh, writes run_dir/manifest.json
```

- [ ] **Step 1: Write failing tests**: `test_manifest_lists_every_file_with_sha256_and_triangles`, `test_manifest_rejects_file_outside_run_dir` (raises `ValueError`), `test_manifest_is_byte_stable_for_same_inputs` (two calls → identical bytes).
- [ ] **Step 2: Run** — Expected: FAIL. **Step 3: Implement.** **Step 4: Run** — PASS. **Step 5: Commit** `feat(packaging): PackagingPort with manifest adapter`.

### Task 5: `JobStorePort`, SQLite job store, Blender lease, `DesignPipeline` use case

**Files:**
- Create: `src/core/ports/job_store_port.py`, `src/adapters/jobs/sqlite_job_store.py`, `src/core/ports/mechanism_simulation_port.py`, `src/adapters/simulation/registered_suites_simulation.py`, `src/core/use_cases/design_pipeline.py`, `src/core/use_cases/blender_lease.py`
- Test: `tests/unit/adapters/test_sqlite_job_store.py`, `tests/unit/core/test_design_pipeline.py`

**Interfaces:**
```python
# ports/job_store_port.py
class JobStorePort(Protocol):
    async def create(self, run_id: str) -> JobRecord: ...
    async def update(self, job_id: str, *, status: JobStatus, stage: StageName | None = None, error: str | None = None) -> JobRecord: ...
    async def get(self, job_id: str) -> JobRecord | None: ...
# adapters/jobs/sqlite_job_store.py  (same shape as SQLiteSessionStore: _DEFAULT_DB = Path("data") / "jobs.db", __init__(self, db_path: Path | None = None))
# ports/mechanism_simulation_port.py
class MechanismSimulationPort(Protocol):
    async def run(self, suites: tuple[str, ...]) -> tuple[VerificationReport, ...]: ...
# adapters/simulation/registered_suites_simulation.py
class RegisteredSuitesSimulation:  def __init__(self, verification: VerificationQueryPort) -> None  # delegates to verification.run(suite_id)
# use_cases/blender_lease.py
class BlenderLease:  # asyncio.Lock wrapper; async with lease.hold(stage: StageName): ...; property holder -> StageName | None
# use_cases/design_pipeline.py
class DesignPipeline:
    def __init__(self, *, integrity: MeshIntegrityPort, simulation: MechanismSimulationPort, slicing: SlicingPort, packaging: PackagingPort, jobs: JobStorePort, lease: BlenderLease, runs_dir: Path, artifact_roots: tuple[Path, ...]) -> None: ...
    async def submit(self, payload: Mapping[str, object]) -> JobRecord: ...      # parses spec, creates run dir + job, schedules run() as an asyncio task
    async def run(self, job_id: str) -> DesignRunReport: ...                     # stages in order; writes report.json after every stage; mechanism/print stages hold the lease
    async def status(self, job_id: str) -> JobRecord | None: ...
    async def report(self, run_id: str) -> DesignRunReport | None: ...           # reads run_dir/report.json
    def run_file(self, run_id: str, name: str) -> Path: ...                      # rejects traversal (ValueError)
```
Stage semantics: `import` copies nothing, lists STLs matching `stl_glob` under `root_dir` and the optional `project_3mf`, FAIL if zero STLs; `geometry` = `integrity.check(stls)`; `mechanism` = `NOT_APPLICABLE` when `spec.mechanism.suites == ()`, else PASSED only if every report `.passed`; `print` = `slicing.slice(project_3mf)` when provided else FAIL "no project 3MF to slice" (print readiness over imported STLs is Phase 1b because it needs them loaded into Blender); `package` = manifest over run_dir outputs. A FAILED stage stops the run; later stages are absent from the report.

- [ ] **Step 1: Write failing tests** with fakes for every port (`tests/unit/core/test_design_pipeline.py`):
```python
async def test_run_writes_report_after_each_stage(tmp_path): ...               # report.json exists with 1,2,...,5 stages as fakes succeed
async def test_geometry_failure_stops_before_mechanism(tmp_path): ...          # integrity fake fails -> stages == (import, geometry), passed False, job FAILED
async def test_mechanism_not_applicable_when_no_suites(tmp_path): ...
async def test_second_run_waits_for_blender_lease(tmp_path): ...               # two runs with a slow slicing fake: lease.holder sequence never overlaps
async def test_run_file_rejects_traversal(tmp_path): ...                       # run_file(run_id, "../x") raises ValueError
```
and `tests/unit/adapters/test_sqlite_job_store.py`: `test_create_update_get_round_trip(tmp_path)`.
- [ ] **Step 2: Run** — Expected: FAIL. **Step 3: Implement.** **Step 4: Run** both files + `test_architecture_ssot.py` — PASS. **Step 5: Commit** `feat(pipeline): DesignPipeline use case with jobs and Blender lease`.

### Task 6: REST routes and runtime wiring

**Files:**
- Create: `api/routers/design.py`
- Modify: `api/runtime.py` (new `AppRuntime` fields `design_pipeline: DesignPipeline`, `tools: ToolsConfig`; construct adapters: `TrimeshCgalIntegrity()`, `RegisteredSuitesSimulation(verification)`, `BambuStudioCli(tools.bambu_studio_bin, profiles_dir=PROJECT_ROOT/"config/slicer-profiles")`, `ManifestPackager()`, `SQLiteJobStore()`, `BlenderLease()`), `api/main.py` (`_publish_runtime_state` copies the two fields; `include_router(design.router)`), `api/schemas.py` (`DesignRunRequest(spec: dict[str, object])`), `tests/e2e/test_mcp_streamable_http.py::make_fake_runtime` (add the two fields with fakes)
- Test: `tests/e2e/test_design_http.py`

**Routes** (prefix `/api`): `POST /design/runs` → `JobRecord` (202); `GET /design/jobs/{job_id}` → `JobRecord` (404 when unknown); `GET /design/runs/{run_id}/report` → `DesignRunReport`; `GET /design/runs/{run_id}/files/{name}` → `FileResponse` (400 on traversal, 404 when missing); `GET /design/tools` → `tuple[ToolAvailability, ...]`. The identity middleware already covers them (nothing added to `_EXEMPT_PATHS`).

- [ ] **Step 1: Write failing e2e tests** (hermetic, `create_app(runtime=make_fake_runtime(), require_identity=False)`): `test_submit_returns_job_and_report_is_reachable`, `test_unknown_job_is_404`, `test_run_file_download_rejects_traversal` (expects 400), `test_tools_endpoint_lists_slicer_availability`.
- [ ] **Step 2: Run** `pytest tests/e2e/test_design_http.py -q` — FAIL. **Step 3: Implement** router + wiring. **Step 4: Run** `pytest tests/e2e -q` — PASS (every existing e2e still green). **Step 5: Commit** `feat(api): design pipeline routes`.

### Task 7: MCP tools

**Files:**
- Modify: `src/adapters/mcp_server/server.py` (keyword-only params `design: DesignPipeline | None = None`, `generation: InstanceCatalogPort | None = None`, `integrity: MeshIntegrityPort | None = None`, `slicing: SlicingPort | None = None`), `api/main.py:184-189` (pass the new services), `tests/unit/adapters/test_mcp_server.py` (`EXPECTED_TOOLS` and `POLICY` rows), `docs/11-mcp-clients.md` (tool catalog)
- Test: `tests/unit/adapters/test_mcp_server.py`

**Tools** (names exact, annotations in the existing `POLICY` style): `run_design_pipeline(spec: dict) -> JobRecord` (readOnlyHint False, timeout 30), `get_job_status(job_id: Name) -> JobRecord` (readOnly), `get_run_report(run_id: Name) -> DesignRunReport` (readOnly), `check_mesh_integrity(stl_paths: list[str]) -> MeshIntegrityReport` (readOnly; paths resolved under `artifact_roots` via `parse`-style check, timeout 300), `slice_for_print(input_3mf: str, printer: str = "bambu-p2s") -> SliceResult` (timeout `SLICE_TIMEOUT_S + 30`), `list_instances() -> tuple[InstanceSummary, ...]`, `build_instance(slug: Name) -> InstanceBuild` (timeout `GENERATOR_TIMEOUT_S + 30`), `tool_status() -> tuple[ToolAvailability, ...]`. Catalog grows from 11 to 19; the old 11 keep names and semantics. Evidence files are exposed as MCP resources `run://{run_id}/{name}` backed by `DesignPipeline.run_file`.

- [ ] **Step 1: Update `EXPECTED_TOOLS`/`POLICY`** in the test (RED). **Step 2: Run** `pytest tests/unit/adapters/test_mcp_server.py -q` — FAIL on the catalog assertion. **Step 3: Implement** the tools (each `try/except (DomainError, BlenderConnectionError) → _tool_error`). **Step 4: Run** the file + `tests/unit/verification/test_verification_deadline_derivation.py` — PASS. **Step 5: Commit** `feat(mcp): design pipeline, integrity, slicing and instance tools`.

### Task 8: Hostname and path decoupling

**Files:**
- Create: `src/infrastructure/public_base_url.py` (`def public_base_url(env: Mapping[str, str] | None = None, *, tailscale_status: Callable[[], str] | None = None) -> str` — order: `BLENDER_MCP_PUBLIC_BASE_URL` env, else `tailscale status --self --json` `.Self.DNSName` → `https://<fqdn>/blender`, else `ValueError`)
- Modify: `api/main.py:88-92` (CORS list uses `public_base_url()` origin), `scripts/verify/mcp_verify_real.py:39`, `scripts/verify/mcp_verify_chat.py:42`, `scripts/verify/mcp_verify_rest.py:29`, `scripts/verify/print_readiness_verify_real.py:38`, `scripts/verify/batch_transform_verify_real.py:31`, `scripts/run_mcp_stdio_proxy.py:10`, `scripts/tailscale-serve-register.sh:15` (read `tailscale status`), `scripts/run_blender.sh` and `scripts/blender_autostart.py` docstring (`BLENDER_BIN` env), `docs/10-runtime-ssot.md`
- Test: `tests/unit/infrastructure/test_public_base_url.py`, plus a repo-wide guard `tests/unit/core/test_no_hardcoded_hosts.py` (AST/regex scan of `api/`, `src/`, `scripts/` for `tail56c751` and `bearmacmini` → must be empty; the scan file itself and `docs/` excluded)

- [ ] **Step 1: Write the guard test and the helper tests** (RED: 7 files currently match). **Step 2: Run** — FAIL listing the 7 files. **Step 3: Implement** helper and replace every hardcode. **Step 4: Run** `scripts/ci.sh` — PASS; then `python scripts/verify/mcp_verify_real.py` against the running API — PASS (the real URL still resolves through tailscale). **Step 5: Commit** `refactor: resolve the public base URL from config and tailscale, no hostnames in code`.

### Task 9: Real-tier gate on the v78 deliverable

**Files:**
- Create: `scripts/verify/design_pipeline_verify_real.py`, `scripts/verify/contracts/design_pipeline_v78.json` (spec payload: `root_dir: "雙上臂四點梯形-v78"`, `stl_glob: "STL/*.stl"`, `project_3mf: "整機69件-單盤排版-v78.3mf"`, `mechanism.suites: []`)
- Modify: `scripts/ci.sh` (after `hand-compact build determinism within budget`: `_run hard "design pipeline on the v78 deliverable (import → geometry → print → package)" "$PY" scripts/verify/design_pipeline_verify_real.py scripts/verify/contracts/design_pipeline_v78.json`), `.gitignore` (keep `/雙上臂四點梯形-*` ignored; the gate reads the directory from disk and SKIP-with-FAIL when absent: "deliverable not present on this host")
- Test: `tests/unit/verification/test_design_pipeline_gate.py` (the gate's assertions on a fake report: fails when any stage is not passed/not_applicable; fails when `report.json` lacks evidence paths; wiring test that ci.sh runs it)

The gate submits the spec through the canonical MCP URL (`run_design_pipeline`), polls `get_job_status` with the heartbeat pattern from `mcp_verify_chat.wait_for_ollama` (budget = `SLICE_TIMEOUT_S + 300`), then fetches `get_run_report` and asserts: `import` lists 113 STLs, `geometry` passed with 113 verdicts, `mechanism` not_applicable, `print` passed with an output 3MF whose plate count equals 1 (read with `lib3mf` or zip listing), `package` manifest has 115 files. Negative control in the same script: a copy of one STL with its header truncated submitted as a second spec must end with `geometry` FAILED naming that file.

- [ ] **Step 1: Write the unit tests** (RED). **Step 2: Implement the gate.** **Step 3: Run** `pytest tests/unit/verification/test_design_pipeline_gate.py -q` — PASS. **Step 4: Install prerequisite** (host): Bambu Studio in `/Applications` (user action; `tool_status` must report available). **Step 5: Run** the gate alone, then `scripts/ci.sh --real` uninterrupted — Expected: all hard gates green including the new one. **Step 6: Commit** `test(real): design pipeline gate on the v78 deliverable`.

### Task 10: Docs, version, checkpoint

**Files:**
- Modify: `docs/11-mcp-clients.md` (19 tools), `docs/30-verification.md` (new gate), `docs/10-runtime-ssot.md` (env vars, data dirs), `docs/tasks/17_mcp-complete-pipeline.md` (hand-off buckets), `docs/tasks/00_INDEX.md`, `CHANGELOG.md`, `VERSION` (`version.py bump minor` → segment 2, because public API grew)

- [ ] **Step 1: Update docs**; run `pytest tests/unit/core/test_docs_dcc.py -q` — PASS. **Step 2: Bump + CHANGELOG + sealing commit.** **Step 3: Run** `bash "$HOME/.codex/skills/milestone-checkpoint/scripts/checkpoint_check.sh" .` — CHECKPOINT OK. **Step 4: Deploy** `bash deploy/launchd/install.sh all`; read back `tool_status` and `run_design_pipeline` through the public base URL.

---

## Out of this plan (next plans)

- Phase 1b: `InstanceSource` with declared parameter ranges (spec §5.2 decision 2), lab-station V10 registered as an instance, build123d-mcp black box.
- Containerization track (spec §5.1): headless Blender runner dummy run, compose for API/web/host tools, MHH registry entries.
- Phase 2 virtual export, Phase 3 MuJoCo simulation.
