# 印表機目錄：廠商解耦、不預設機器、可選印表機

**Status:** ACTIVE

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

### Open failures

- 任務 17 的整輪 `--real` CI 卡在 chat 閘門的前置條件：另一個專案的 `com.local.shb.ollama`（11435）長時間吃滿 CPU。依使用者選擇不去動它；背景有 wait-then-CI 腳本在等，等 Ollama 有空再跑。

### Next step

- 任務 1：先寫 `tests/unit/infrastructure/test_printer_catalog_loader.py` 並確認紅燈。
