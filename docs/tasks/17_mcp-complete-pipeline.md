# 讓 MCP 完整——階段 1：可列印機構管線（匯入路徑）

**Status:** ACTIVE

## Goal

任何 MCP host 以機器可讀的 `ModelSpec` 提交一個模型，拿回可送印的包與機器驗證證據（幾何、機構、列印切片、重現 manifest）；第一個實例是使用者交付的實驗室工作站 v78（匯入既有產物，不經產生器）。

## Context to read

1. `docs/superpowers/specs/2026-10-21-mcp-complete-pipeline-design.md`（設計，含 §5 重用決策、§5.1 分層容器化、§5.2 reviewer 八題處置）
2. `docs/superpowers/plans/2026-10-21-mcp-complete-phase1.md`（實作計畫，任務 0–10，逐任務先紅後綠）
3. `docs/superpowers/specs/2026-10-21-reuse-survey.md`（可重用專案普查與授權）
4. `docs/01-architecture.md`、`docs/30-verification.md`

## Specification

- 新 port：`MeshIntegrityPort`、`SlicingPort`、`PackagingPort`、`MechanismSimulationPort`、`JobStorePort`；use case `DesignPipeline` 五階段（import→geometry→mechanism→print→package），證據寫 `data/runs/<run_id>/`。
- REST `/api/design/*` 與 MCP 工具（目錄由 11 增為 19）共用同一服務；證據檔經既有身分閘門下載。
- 主機名、二進位路徑、資料目錄只來自 `config/tools.yaml` 與環境變數；程式碼不得出現 Tailscale 網域或家目錄。
- 切片以 Bambu Studio CLI 子行程呼叫（AGPL-3.0，manifest 明標）；缺席＝明確失敗附安裝指引。
- 不開公開 `execute_code`；已發布包與既有 DTO 不變。

## Acceptance checks

- `scripts/ci.sh` 綠；`scripts/ci.sh --real` 不中斷全綠，含新閘門「design pipeline on the v78 deliverable」。
- 透過本機自己的 Tailscale FQDN（動態取）呼叫 `run_design_pipeline` → `get_job_status` → `get_run_report`，v78 的 113 件 STL 幾何通過、單盤 3MF 切片成功、manifest 列出全部檔案；截斷 STL 的負對照以幾何階段失敗收場。
- `tests/unit/core/test_no_hardcoded_hosts.py` 綠（repo 無寫死主機名）。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- 2026-10-21：設計定稿（使用者裁決：第一實例＝匯入既有交付件；切片器裝這台 Mac；AGPL 子行程不另送法務）；計畫自檢通過；任務 0 建檔。

### Open failures

- 本機 `/Applications` 尚未安裝 Bambu Studio（普查實測）；任務 9 的真機閘門需要它，`tool_status` 會明確回報缺席。

### Next step

- 任務 1：`src/core/domain/model_spec.py` 與 `src/core/domain/design_run.py`，先寫 `tests/unit/core/test_model_spec.py` 看紅。
