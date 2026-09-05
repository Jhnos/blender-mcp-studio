# 刻意延後的抽象化

> 回導航 [[README]] · 相關 [[01-architecture]]、[[KNOWLEDGE]]

這裡記的**不是**違規（違規要當場修）。這裡記的是「明知可以再抽象，但現在刻意不做」的
決定——每一條都必須寫明**在等什麼**，以及**什麼條件一到就該動手**。沒有觸發條件的
延後就是技術債，不該寫在這裡。

狀態：`deferred`（等待中）→ `due`（觸發條件已成立）→ `done`（已處理）。

---

## D-001 · `scene_operations` 保留自己的一份 narrowing

**狀態**：`deferred`（2026-09-05 記錄）

**現況**：`src/core/use_cases/scene_operations.py` 有 `_require_mapping`／`_require_str`／
`_require_int`／`_require_bool`／`_require_sequence`，與 `src/adapters/blender_response.py`
的謂詞邏輯重複；訊息措辭也幾乎相同。

**為何不合併**：`src/core/**` 目前**不 import 任何 `src.core` 以外的東西**。讓它去 import
`src/infrastructure/narrowing.py` 會打破這個純度，而純度是這個專案分層規則裡最容易驗證、
也最容易一旦破例就回不去的一條。兩害相權，留一份重複比開一個向外的口子好。

**真正的根因**：`BlenderPort` 回傳的 `ToolResult.output` 型別是 `object`，所以**解碼外部
系統的方言這件事被推給了 use case**。narrowing 重複只是這個設計的症狀。正解是讓 port
回傳 typed DTO，由 adapter 負責解碼——那是一個獨立的 task，不是重構的順手工。

**觸發條件（任一成立就升為 `due`）**：
- `BlenderPort` 的契約改為回傳 typed DTO；或
- 出現**第三份**同樣的 narrowing 實作；或
- `date >= 2026-12-01`（屆時重新評估這個延後是否還划算）

**目前的防護**：`scripts/check_container_narrowing.py` 涵蓋這些位置，兩處帶
`narrow-ok:` 說明它們誠實重建了型別；`tests/unit/scripts/test_check_container_narrowing.py`
確保這個閘門本身沒有盲區。

---

## D-002 · `_run_undo_redo` 之外的裸 `except Exception`

**狀態**：`deferred`（2026-09-05 記錄）

**現況**：`api/routers/vision.py`、`pipelines.py`、`generate3d.py` 仍有
`except Exception → 500` 的整包捕捉。

**為何不動**：它們攔截的是 LLM／text-3D／pipeline 這些**外部服務**的任意例外，目前沒有
對應的 domain error 型別可以取代。硬改成讓例外傳播會把未分類的 500 變成未分類的 422，
那不是改善，只是換一種說謊方式。

**觸發條件**：`LLMPort`／`Text3DGenerationPort` 定義出自己的 domain error 型別時
（屆時可比照 `BlenderConnectionError` 註冊到 `api/main.py` 的 handler）。

---

## D-003 · `PreviewStage` 的 `react-hooks/refs` 定點豁免

**狀態**：`deferred`（2026-09-05 記錄）

**現況**：`web/src/components/PreviewStage.tsx` 的 `commands = useMemo(...)` 帶一行
`eslint-disable-next-line react-hooks/refs`。被豁免的是 `openPrintReadiness` 與
`rerunPrintReadiness`——它們讀 `exportPanelRef.current`，而 `createStudioCommands`
在 render 期被呼叫。

**為何判定安全**：`createStudioCommands` 只是把這些 callback 存進
`CommandDefinition.run`，**從不呼叫它們**；ref 是在使用者執行指令時才被讀取。

**這不是新問題**：它在本次重構前就存在，只是 `refreshPreview` 有個自我引用的
callback，讓規則在分析到那裡時就停住、沒往下看。移除自我引用後它才浮現。
**一個因為分析器提早放棄而「通過」的 lint，跟真的沒問題長得一模一樣**——這與
`LESSONS_LEARNED.md:101`（部分 gate 給假覆蓋率）同族。

**觸發條件（任一成立就升為 `due`）**：
- `ExportPanel` 不再用 imperative handle（改以 props/state 驅動開啟與重跑）；或
- `react-hooks` 規則支援「這個函式只儲存不呼叫」的標註；或
- 同樣的豁免需要出現在**第二個**元件（代表這是模式問題，不是單點例外）

**目前的防護**：豁免是定點的（`eslint-disable-next-line`，不是整檔關閉），且
理由寫在程式碼旁供 review。
