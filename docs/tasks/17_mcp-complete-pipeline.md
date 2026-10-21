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
- 2026-10-21：任務 1–3 完成，各自通過審查。每一輪都由指揮官親跑 `scripts/ci.sh`，T1＋T2 全綠。分支是 `worktree-mcp-complete-phase1`；commit 鏈與每條裁決記在 `.superpowers/sdd/mcp-complete-phase1/progress.md`（git 不追蹤的工作區帳本）。
  - 任務 1（7aacd0d、a4caf53）：`ModelSpec` 解析器把 `root_dir`、`stl_glob`、`project_3mf` 都限制在允許的根目錄內，symlink 也算在內。
  - 任務 2（9b34fb6、d3cbbe4、950cce1）：`MeshIntegrityPort`。自交與封閉分開評估；沒評估到的回 `None`，不回假的 `False`。共用守衛 `require_triangle_surface` 行為不變。
  - 任務 3（f533c82、1ef5eeb）：`SlicingPort` 加 Bambu CLI。v80 驗收過的列印覆寫參數改放 `config/slicer-profiles/p2s-pla-overrides.json`，已逐鍵比對，與 v80 相同。切片逾時＝5×171 秒，依據是 v80 實測最慢的一次 170.6 秒。
- 切片器二進位：`/Applications` 底下沒有，但主 checkout 的 `tmp/lab-station-slicing-v80/mounted/BambuStudio.app` 有一份可執行的 universal 版本，是 v80 從 dmg 抽出來的。任務 9 可以用 `BAMBU_STUDIO_BIN` 指向它。

### Open failures

- 任務 4（c023cdb、33eacae）已完成，通過範圍複審。改用共用 STL 讀取器後，整合性 adapter 的 7 種測試網格判定與修改前完全相同。manifest 加了 `tools` 清單，用來標示 AGPL 授權。
- 技術債，任務 10 在 main 上修：conda 環境 `blender-mcp` 的 editable 安裝指向一個已刪除的舊 worktree（`_editable_impl_blender_mcp_studio.pth`），現在只是剛好靠 cwd 才 import 得到 `src`。
- 留給最終審查：
  - CGAL 把零面積三角形算成自交。判定仍然失敗、原因也正確，但要補一行說明。
  - 兩個「未評估」的早退分支沒有各自的測試。
  - manifest 的 `tools` 只依名稱排序；同名不同版本時，輸出位元組會依呼叫順序而變。排序鍵改成 `(name, version or "", license, invocation)`。

### Next step

- 任務 4 複審通過後，派任務 5（`DesignPipeline`），帶兩條要求：
  - 每個讀檔路徑展開時，再用 `resolve().is_relative_to(root)` 檢查一次。
  - 切片有跑的時候，把 Bambu Studio 以 `ToolUse(license="AGPL-3.0-only", invocation="subprocess")` 傳進 manifest。
