# 印表機目錄：廠商解耦、不預設機器、可選印表機

**Status:** AWAITING-ACCEPTANCE

## Goal

印表機改成資料目錄：Bambu Lab P2S 用 Bambu Studio 切片，六台 Creality（創想三維）機器用 OrcaSlicer 切片。程式裡任何地方都沒有預設機器；LLM 或使用者從本機實際能切片的印表機裡挑一台。

## Context to read

1. `docs/superpowers/specs/2026-10-22-printer-catalog-design.md`：設計（使用者 2026-10-22 核准），§6 是 OrcaSlicer 研究摘要
2. `docs/superpowers/plans/2026-10-22-printer-catalog.md`：實作計畫，任務 1–6
3. `docs/tasks/17_mcp-complete-pipeline.md`：上游階段 1（V01.0S.000 已部署）

## Specification

- `config/printers/<vendor>/<id>.yaml` 每台印表機一個檔，切片器另列在 `config/slicers.yaml`；id 格式 `<vendor>-<model>-<nozzle>`。
- spec v2 的 `print_target.printer` 必填。送出時就檢查三件事：印表機是否已知、它的切片器是否已安裝、材料與製程是否跟這台機器相容。v1 一律對應到 `bambu-p2s-0.4`，並在報告上標示。
- 只寫一個 `OrcaFamilyCli` 轉接器，靠資料同時驅動 Bambu Studio 與 OrcaSlicer；設定檔依 JSON `name` 從已安裝 app 的 bundle 讀取。
- 新增 MCP 工具 `list_printers` 與 REST 路由 `/api/design/printers`，只列切片器有裝的印表機。工具總數從 21 變 22。

## Acceptance checks

- `scripts/ci.sh` 全綠，`scripts/ci.sh --real` 不中斷地全綠。
- 兩道真機閘門：
  - v78 的 69 件交給 `bambu-p2s-0.4`（Bambu Studio）
  - v78 的 69 件交給 `creality-k1c-0.4`（OrcaSlicer 2.4.2）
  - 兩道都要切成 1 盤、manifest 記下實際用的切片器、送出時拒絕不相容的材料作為負向對照。
- 移到 `archive/` 之前需要人工驗收。

## Hand-off

### Verified facts

- 2026-10-22：
  - 已安裝 OrcaSlicer 2.4.2，實測如下：
    - 官方 release 的 DMG 有 246,088,803 位元組，SHA-256 `e15e7bb1…0366`，跟 GitHub 公布的 digest 相符。
    - app 有 Notarized Developer ID 簽章（Li Jiang，XQK7C38HH5），Gatekeeper 接受。
    - 設定檔在 `Contents/Resources/profiles/{BBL,Creality}`。
    - 回退方式：`rm -rf /Applications/OrcaSlicer.app`。
  - 已安裝的 Bambu Studio bundle 也帶 52 個 Creality 機器設定檔。

- 2026-11-09（分支 `claude/printer-catalog`，最後 commit `9fcd931`）：
  - 任務 1–6 與最終修正輪（F1–F7）完成。全分支 opus 審查：0 Critical，4 Important 已修：
    - spec 範例不再寫死機器
    - 讀不到設定檔的印表機列為 unavailable
    - brim 由 job 決定，兩家廠商一致
    - 文件與程式不一致的地方已修正
  - 指揮官親跑 `scripts/ci.sh`：CI PASSED（T1＋T2）。
  - 合併前乾跑：分支碼起臨時 uvicorn 127.0.0.1:19599，`BLENDER_PORT=1`，ARTIFACT_ROOTS 指主 checkout，runs 放 scratchpad。
    - K1 Max 閘門 PASS：OrcaSlicer 2.4.2，1 盤；K1C 盤面放不下的負向對照在 print 階段失敗。
    - P2S 閘門 PASS：Bambu Studio 02.08.02.61；截斷 STL 的負向對照在 geometry 階段失敗。
    - 兩家實際送進切片器的 process.json 都是：brim_type outer_only、brim 3.0、support snug、prime tower 0。
  - 擴充試驗：只加一個 YAML（Ender-3 V3 Plus）就能用，不必改程式。

- 2026-11-09（併入 main 90af34d 後，分支 HEAD `858a83e`，V01.0U.000）：
  - 合併 commit `c6b5386`。`BambuStudioCli` 已移除，刀路檢查改由 `OrcaFamilyCli` 依 `slicers.yaml` 的 `toolpath_inspection` 執行。
    - Orca 關閉。親驗：Orca G-code 有 0 個 `; FEATURE:`、96048 個 `;TYPE:`。
  - 乾跑找到並已修正三件事：
    - v92 的 3MF 是 production 格式，盤面檢查讀不了；改為跟著 `p:path` 讀，加上累計位元組上限、遍歷工作量上限（5×72546）、項目數上限（5×94）。v92 範圍 4.8–249.0 × 4.8–255.0 mm。
    - 可下載的切片 log 含主機路徑（階段 1 起就有，P2S 15 處；整合後 Orca `00000.log` 20 處）。現在打包前在單一處清洗，包含切片器整個 `.app`。
    - 安全審查兩項 MEDIUM（元件展開耗盡、log 未清切片器目錄）都已修，先 RED 後 GREEN。
  - 指揮官親驗：
    - `scripts/ci.sh` 綠。
    - 臨時 API 乾跑：目前選版 v92（P2S）PASS、K1 Max PASS，兩個負向對照照預期失敗。
    - 4 個 run 裡含 `/Users/`、`/private/`、`/var/folders`、`/Applications/` 的檔案數為 0。

- 2026-11-10 上線：
  - 使用者選 B：Codex 留在 main 工作區的 `00_INDEX.md` 修改原樣 commit 成 `9b0250f`，在 commit 訊息中註明作者。合併後 main 快轉到 `cf08098`。
  - 執行 `install.sh all`，三個服務都換了新 PID。經動態 FQDN `bearmacminimac-mini.tail56c751.ts.net/blender/api/health` 回 `{"status":"ok","blender":"connected"}`。
  - 整輪 `scripts/ci.sh --real`：exit 0，57 PASS、0 FAIL，包括：
    - design pipeline on the current selected deliverable（P2S）
    - Creality K1 Max via OrcaSlicer
    - public native revision
  - 正式 `data/runs` 中今天新產生的 5 個 run 掃描結果是 0 個檔案含主機路徑。
  - push：`a1981d6..cf08098`，共 43 個 commit，包含 Codex 先前沒 push 的 7 個。
  - 版號從 V01.0U.000 改成 V01.0W.000，原因是 V01.0U.000 到 V01.0V.001 已經是 `codex/universal-room` 分支的 tag。

### Open failures

- 已評估、刻意延後：
  - 讀不到 bundle 的印表機，submit 時的錯誤用詞（"not sliceable"）跟 list_printers（"bundle profiles cannot be read"）不同，只是措辭。
  - `SliceRequest.printer` 與 `printer_id` 重複。
- PETG 負向對照只走「不在目錄」路徑；bundle `compatible_printers` 拒絕只有單元測試，沒有真機閘門。
- `src/core/use_cases/design_pipeline.py` 379/380 行，下次加功能前先拆檔。
- OrcaSlicer 沒有刀路檢查：要支援，得另寫一個讀 `;TYPE:`／`;WIDTH:`／`;HEIGHT:` 的解析器。
- 部署前產生的舊 run（例如 2026-11-09 的 `eefae8bb…`、`4fa397e7…`）各有 1 個 log 含主機路徑，而且可以下載。要不要清掉，等使用者決定。
- 同一個 repo 有兩條產品線共用版號空間（本專案和 `codex/universal-room`）。之後 bump 版號前，先跑 `git tag -l` 確認沒有撞號。

### Next step

- 等使用者驗收任務 17 與 18，再移到 `archive/`。
- 下一個工作是階段 1b 幾何引擎：使用者選 A（solidcraft 0.30.1＋build123d，共用同一個 GeometryPort）。先用 brainstorming 寫設計文件給使用者審，小試報告的根據在 `scratchpad/spike/spike-report.md`。
