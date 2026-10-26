# 讓 MCP 完整——階段 1：可列印機構管線（匯入路徑）

**Status:** ACTIVE

## Goal

任何 MCP host 以機器可讀的 `ModelSpec` 提交一個模型，拿回可送印的包與機器驗證證據（幾何、機構、列印切片、重現 manifest）；目前共用實例由 models/lab-station/model-spec.json 選定實驗室工作站（匯入既有產物，不經產生器）。

## Context to read

1. `docs/superpowers/specs/2026-10-21-mcp-complete-pipeline-design.md`（設計，含 §5 重用決策、§5.1 分層容器化、§5.2 reviewer 八題處置）
2. `docs/superpowers/plans/2026-10-21-mcp-complete-phase1.md`（實作計畫，任務 0–10，逐任務先紅後綠）
3. `docs/superpowers/specs/2026-10-21-reuse-survey.md`（可重用專案普查與授權）
4. `docs/01-architecture.md`、`docs/30-verification.md`

## Specification

- 新 port：`MeshIntegrityPort`、`SlicingPort`、`PackagingPort`、`MechanismSimulationPort`、`JobStorePort`；use case `DesignPipeline` 五階段（import→geometry→mechanism→print→package），證據寫 `data/runs/<run_id>/`。
- REST `/api/design/*` 與 MCP 工具（目錄由 11 增為 21）共用同一服務；證據檔經既有身分閘門下載。
- 主機名、二進位路徑、資料目錄只來自 `config/tools.yaml` 與環境變數；程式碼不得出現 Tailscale 網域或家目錄。
- 切片以 Bambu Studio CLI 子行程呼叫（AGPL-3.0，manifest 明標）；缺席＝明確失敗附安裝指引。
- 不開公開 `execute_code`；已發布包與既有 DTO 不變。

## Current-selection contract (2026-10-26)

- The selected delivery is declared only in `models/lab-station/model-spec.json`. Transport adapters, schema examples and real-verification contracts must not carry a second live ModelSpec.
- A narrow injected provider supplies that declaration to the shared application catalog. The domain schema remains pure. Replacing the declaration changes discovery, the example and default submission without editing Python or the verifier.
- REST and MCP both support submission without a spec: the application selects the current delivery. Explicit specs remain supported for deliberate historical/custom runs. A missing or malformed declaration fails before a job is created, never chooses an archive.
- The real gate resolves `selection: current` through public MCP, verifies discovery/example agreement and availability, then reuses the existing positive/negative checker. No new verification pipeline or model generation.
- BDD checks: given a changed declaration, all consumers observe it; given no declaration, default submission creates no job; given an explicit historical spec, that spec is used; given a stale discovery/example pair, the real gate rejects it before slicing.
- Reuse: existing config loader, application catalog, composition root and real gate. New modules: none. Prior art queried `site:github.com/python-injector/injector dependency injection python configuration provider` and `site:github.com/pydantic/pydantic-settings JSON config settings source`: both cover generic DI/config loading, already present here; reuse the local seams and standard JSON rather than add another framework.

## Acceptance checks

- 核心 T1/T2/T3 不中斷全綠，含「design pipeline on the current selected deliverable」；對話 T4 獨立驗證，不作為模型／MCP／切片的前置。選取方式見 [驗證 SSOT](../30-verification.md)。
- 透過本機自己的 Tailscale FQDN（動態取）呼叫 `run_design_pipeline` → `get_job_status` → `get_run_report`，選定交付件的 69 件列印 STL 幾何通過、單盤 3MF 切片成功、manifest 列出全部檔案；截斷 STL 的負對照以幾何階段失敗收場。
- `tests/unit/core/test_no_hardcoded_hosts.py` 綠（repo 無寫死主機名）。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

使用者授權核心與 Ollama 對話分開驗證，保留原對話真機檢查；結果及待辦見任務索引最新交接。

工作站的共用交付入口改為 [models/lab-station](../../models/lab-station/README.md)；規格v1匯入保留v78幾何的v80切片交付，不重新建立模型。現行驗證結果與未解除事項以[任務索引](00_INDEX.md)的最新交接為準；下列舊日期事實屬歷史脈絡，不能用來選回舊版或重做已完成的合併。

### Verified facts

- 2026-10-21：設計定稿（使用者裁決：第一實例＝匯入既有交付件；切片器裝這台 Mac；AGPL 子行程不另送法務）；計畫自檢通過；任務 0 建檔。
- 2026-10-21：任務 1–3 完成，各自通過審查。每一輪都由指揮官親跑 `scripts/ci.sh`，T1＋T2 全綠。分支是 `worktree-mcp-complete-phase1`；commit 鏈與每條裁決記在 `.superpowers/sdd/mcp-complete-phase1/progress.md`（git 不追蹤的工作區帳本）。
  - 任務 1（7aacd0d、a4caf53）：`ModelSpec` 解析器把 `root_dir`、`stl_glob`、`project_3mf` 都限制在允許的根目錄內，symlink 也算在內。
  - 任務 2（9b34fb6、d3cbbe4、950cce1）：`MeshIntegrityPort`。自交與封閉分開評估；沒評估到的回 `None`，不回假的 `False`。共用守衛 `require_triangle_surface` 行為不變。
  - 任務 3（f533c82、1ef5eeb）：`SlicingPort` 加 Bambu CLI。v80 驗收過的列印覆寫參數改放 `config/slicer-profiles/p2s-pla-overrides.json`，已逐鍵比對，與 v80 相同。切片逾時＝5×171 秒，依據是 v80 實測最慢的一次 170.6 秒。
- 切片器二進位：`/Applications` 底下沒有，但主 checkout 的 `tmp/lab-station-slicing-v80/mounted/BambuStudio.app` 有一份可執行的 universal 版本，是 v80 從 dmg 抽出來的。任務 9 可以用 `BAMBU_STUDIO_BIN` 指向它。

- 2026-10-22：任務 4–9 與最終修正輪完成；全分支 opus 審查無 Critical，四個規格缺口已修（設定檔改從 app 讀取、場景工具 busy 防護、可開啟且有 sha256 的證據檔、LLM 用的 spec 說明工具）。最後 commit：`cbd9213`；版本 V01.0S.000。
- 合併前乾跑（分支碼、臨時 uvicorn 127.0.0.1:19599，`BLENDER_PORT=1`、`ARTIFACT_ROOTS`=主 checkout、`BAMBU_STUDIO_BIN`=v80 抽出的 app、runs 與 jobs.db 放 scratchpad），v78 閘門 PASS，41 秒。指揮官逐檔讀過 run 目錄：
  - import：69 個 STL，0 個略過
  - geometry：69 個全過
  - mechanism：標「階段 1 未評估」
  - print：rc 0，3MF 內恰有 `Metadata/plate_1.gcode`
  - package：11 個檔，AGPL ToolUse 為 bambu-studio 02.08.02.61
  - 負向對照：geometry FAILED，點名 `STL/列印零件/LS_FIT_chassis.stl`
  - 報告、manifest、`import.json` 裡都沒有絕對路徑。
- 切片器：v80 從 dmg 抽出的 app 已確認是 Bambu Lab 的 Developer ID 簽章、Apple 公證，Gatekeeper 接受，版本 02.08.02.61。

### Historical open failures (phase 1 pre-merge; current state is in the task index)

- 尚未在 main 上做真機驗收。部署中的 API 還是舊碼（11 項工具），合併、部署之後才算數。
- 技術債（在 main 上修）：conda 環境 `blender-mcp` 的 editable 安裝指向已刪除的舊 worktree（`_editable_impl_blender_mcp_studio.pth`），目前只是靠 cwd 剛好 import 得到 `src`。
- 已評估、刻意延後的項目（各附理由）：
  - manifest 的 `tools` 只依名稱排序：目前只有一個工具，等第二個工具出現再改排序鍵。
  - PathScrubber 只比對「前綴＋/」：已實測家目錄與暫存目錄都會被清掉。
  - 從沒啟動過的切片沒有 log。
  - 兩個原子寫入函式、兩份 stage 序列化，以及三處安全係數 5：之後在共用模組收斂。
  - 安裝提示只寫 Mac。
  - `print_readiness_verify_real.py` 371 行、`design_pipeline.py` 380 行，都已到預算上限：下次加東西前先拆檔。
  - `parse_model_spec` 的 `root_dir` 只對 `artifact_roots[0]` 解析：出貨的 `.`／`models` 根不受影響。
- 後續任務（不在本計畫內）：
  - 把交付件搬到專屬的上層目錄，之後才能把 artifact root `.` 收窄。
  - 階段 1b：參數範圍、把 V10 登錄為實例、build123d-mcp。
  - 容器化軌：無視窗執行器 dummy run、compose。
  - 階段 2：虛擬世界匯出。
  - 階段 3：MuJoCo；機構套件要綁定 spec 的模型。

### Historical next step (phase 1 pre-merge; not current execution instructions)

- 在 main 上依序做：
  1. 合併 `worktree-mcp-complete-phase1`。
  2. 修 conda 的 `.pth` 指向。
  3. 把 `tmp/lab-station-slicing-v80/mounted/BambuStudio.app` 複製到 `/Applications`。回退指令：`rm -rf /Applications/BambuStudio.app`。
  4. 執行 `bash deploy/launchd/install.sh all`。
  5. 經動態 FQDN 確認 21 項工具、`tool_status` 與 v78 閘門。
  6. 不中斷地跑完 `scripts/ci.sh --real`。
  7. checkpoint，清理 worktree。
