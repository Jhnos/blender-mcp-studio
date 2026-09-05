# 知識架構 DCC 重整 + 程式碼抽象去重 + 防再生閘門

**Status:** AWAITING-ACCEPTANCE

## Goal and context

`docs/` 的 8 個頂層檔互相複寫同一批事實（埠號 7 處、CI 指令 6 處），`INTEGRATION.md`
從任何導航面都到不了，而進度 SSOT 本身停在「PR #4 open」——PR 早已合併。程式碼側同理：
同一段錯誤處理手抄 21 次、JSON 窄化寫了 5 套、Blender 幾何 helper 抽好了卻被重寫。

目標不是「讓程式碼變短」，而是讓每一類重複**在機器層面無法再長回來**。

## What changed

### 知識層

- `docs/` 重組為 DCC 樹：`README.md` 導航表（含「何時該讀」欄）+ 編號主題檔
  （`00-context`／`01-architecture`／`10-runtime-ssot`／`11-mcp-clients`／`12-deployment`／
  `20-conventions`／`30-verification`）+ `[[wikilink]]` 互指。改名走 `git mv`，history 跟著檔案。
- 7 組複寫事實收斂到單一 SSOT：埠與位址只在 `10-runtime-ssot`，驗證指令只在 `30-verification`。
- `KNOWLEDGE.md` 改寫為純粹的知識放置地圖（導航移到 README，移除第二個會漂移的導航面）。
- 新增 `DEFERRALS.md`：三條刻意不抽象的決定，每條附觸發條件。
- 修正過時陳述：PR #4 狀態、LaunchAgent 數量（文件說 2 個、實際 3 個）、服務定位措辭、
  `deploy/launchd/README.md` 漏列的 `blender` 安裝 target。

### 程式碼層

- domain error → HTTP status 集中到 `api/main.py`（原本 4 個 router 手抄 14 處）。
- use case 改在 `api/runtime.py` 組裝（原本 3 個 router 在請求時現場組）。
- `api/routers/scene.py` 749 行 → 8 個 router，最大 171 行；OpenAPI 路由集合逐字不變。
- 所有 `bpy` 原始碼移入 `src/adapters/blender_scripts/` ACL。
- 5 套 JSON 窄化收斂到 `src/infrastructure/narrowing.py`（謂詞層 + `required()` 組合子，
  例外型別與訊息仍由呼叫端持有——那些字串會原封不動變成 REST 的 422 detail）。
- 前端 5 處非同步樣板收斂到 `runTracked`。
- 7 個零引用檔案歸檔到 `scripts/archive/`（不刪）。

### 修掉的 bug

`POST /api/refine` 呼叫 `adapter_factory.create_llm_adapter()`——該方法在 port 與 concrete
factory 上**都不存在**。四道 gate 全綠沒抓到，因為 `app.state` 回傳 `Any`（mypy 看不見），
而測試替身是無 spec 的 `MagicMock`（任何方法名都答應）。該端點原本零測試。

## Verified

`scripts/ci.sh` — **all hard gates green**。逐項證據：

| 宣稱 | 證據 |
|---|---|
| 錯誤映射零行為變更 | `tests/e2e/test_rest_error_contract.py` 19 項，測試碼一字未改，重構前後皆綠 |
| 拆檔沒漏路由 | OpenAPI 路由集合前後 `diff` 為空（28 條） |
| `/api/refine` 已修 | `tests/e2e/test_refine_http.py` 2 項，對舊版本會紅 |
| 檢查失敗會進 OperationStatusCenter | `ExportPanel.test.tsx` 2 項，對舊版本會紅 |
| 閘門真的會擋 | 每個閘門都有 should-fire + should-pass fixture |
| `scripts/` 已納管 | ruff／format／mypy strict／narrowing 四道，全綠 |

## Open failures and limitations

- **T3 未跑**：`scripts/ci.sh --real` 需要 Blender addon 在 socket 上就緒。本次全部變更都是
  結構性重構，但 REST／MCP 對真實 Blender 的行為**尚未在本輪驗證**。
- `docs/DEFERRALS.md` 三條延後項仍為 `deferred`。
- `docs/tasks/02_tendon-universal-joint.md` 的實體列印驗收不受本任務影響，仍未完成。

## Next step

1. 跑 `scripts/ci.sh --real`，確認 REST／MCP 對真實 Blender 的行為未受重構影響。
2. Lane B（品味）三項待使用者裁決：`docs/README.md` 導航表的分類與命名、列印就緒檢查
   通知的措辭與時機、8 個 router 的檔名是否符合心智模型。
