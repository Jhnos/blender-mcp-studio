# Development documentation

本目錄是尚未落地功能的開發規範入口。文件各自只有一個責任，避免同一事實在多處可編輯而漂移。

| 問題 | SSOT | 責任 |
|---|---|---|
| MCP layer 應該是什麼、邊界在哪裡？ | [MCP_LAYER_DEVELOPMENT.md](MCP_LAYER_DEVELOPMENT.md) | 規範性架構、DDD/SOLID、工具契約、安全與生命週期 |
| 如何用 TDD 實作並證明它是真的？ | [MCP_LAYER_TDD.md](MCP_LAYER_TDD.md) | RED/GREEN/REFACTOR、測試替身、可證偽 gate、真 Blender oracle |
| 為何選 inbound adapter、又拒絕哪些方案？ | [MCP_LAYER_ADR.md](MCP_LAYER_ADR.md) | ADR-005 的 context、alternatives、consequences 與 status transition |
| 實際要依序改哪些檔案？ | [implementation plan](../superpowers/plans/2026-07-18-client-neutral-mcp-layer.md) | 逐 task、逐檔案、逐 command、逐 commit 的執行清單 |
| 專案目前已經採用什麼架構？ | [ARCHITECTURE.md](../ARCHITECTURE.md) | 已落地的全專案架構與 ADR |
| 過去踩過哪些坑？ | [LESSONS_LEARNED.md](../LESSONS_LEARNED.md) | 事故脈絡與同類錯誤防線 |

## 文件狀態

`MCP_LAYER_DEVELOPMENT.md` 與 `MCP_LAYER_TDD.md` 描述的是目標狀態；在 implementation plan 完成、`scripts/ci.sh --real` 通過以前，不得把它們當作已部署能力。

## 衝突處理

1. Port、DTO、工具名稱、annotation 與安全規則，以 `MCP_LAYER_DEVELOPMENT.md` 為準。
2. 測試層級、RED 證據與 gate，以 `MCP_LAYER_TDD.md` 為準。
3. 架構選擇與替代方案，以 `MCP_LAYER_ADR.md` 為準。
4. 實作順序與檔案路徑，以 implementation plan 為準。
5. Port、路由與 launchd 的機器設定仍受專案根目錄 `AGENTS.md`、`docs/ENGINEERING_STANDARDS.md` 與既有 SSOT 約束。
6. 若文件與可執行測試衝突，先判定規格是否改變；禁止為了讓測試綠燈而靜默改寫契約。

## 變更規則

- 新增或刪除公開 MCP tool：先改開發規範與 exact-catalog test，再改實作。
- 改 transport、authentication 或 socket ownership：視為 ADR 級變更，必須同時更新威脅模型與 assembly test。
- 單純調整 task 順序：只改 implementation plan，不複製到本目錄。
- 修正已發生的事故教訓：寫入 `LESSONS_LEARNED.md`，再把機械防線連回 TDD 文件。
