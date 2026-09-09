# 刻意延後的抽象化

> 回導航 [[README]] · 相關 [[01-architecture]]、[[KNOWLEDGE]]

這裡記的**不是**違規（違規要當場修）。這裡記的是「明知可以再抽象，但現在刻意不做」的
決定——每一條都必須寫明**在等什麼**，以及**什麼條件一到就該動手**。沒有觸發條件的
延後就是技術債，不該寫在這裡。

狀態：`deferred`（等待中）→ `due`（觸發條件已成立）→ `done`（已處理）。

---

## D-001 · `scene_operations` 保留自己的一份 narrowing

**狀態**：`done`（2026-09-09；2026-09-05 記錄）——`BlenderPort` 改回傳 typed DTO（`scene_summary`／`object_details`／`viewport_screenshot`），
解碼搬到 `src/adapters/blender_scene_decoding.py`，截圖的暫存檔搬到 `src/adapters/viewport_capture.py`；use case 裡再沒有任何 narrowing，
`test_the_use_case_decodes_nothing` 釘住。訊息逐字保留，REST 的 422 detail 不變。

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

**狀態**：`done`（2026-09-09；2026-09-05 記錄）——`ExternalServiceError`（`VisionAnalysisError`／`TextTo3DError`）
由 vision 與 text-3D adapter 在邊界拋出，`api/main.py` 對映 502；`vision.py`／`pipelines.py`／`generate3d.py` 的四個整包
`except Exception` 刪除，pipeline 內的 Blender 斷線現在是 503 而非 500。`test_routers_do_not_translate_arbitrary_exceptions`
以預算棘輪擋住回流。2026-09-09 續：LLM adapter 也在邊界翻成 `LLMProviderError`（502）／`LLMConnectionError`（503），
use case 不再把一切包成「LLM chat failed」；`chat.py` 剩兩處是 WebSocket 每輪的錯誤幀（Starlette 的例外中介層不管 WS），
`ws_manager.py` 兩處是背景迴圈守衛——都在預算裡，只能往下。

**現況**：`api/routers/vision.py`、`pipelines.py`、`generate3d.py` 仍有
`except Exception → 500` 的整包捕捉。

**為何不動**：它們攔截的是 LLM／text-3D／pipeline 這些**外部服務**的任意例外，目前沒有
對應的 domain error 型別可以取代。硬改成讓例外傳播會把未分類的 500 變成未分類的 422，
那不是改善，只是換一種說謊方式。

**觸發條件**：`LLMPort`／`Text3DGenerationPort` 定義出自己的 domain error 型別時
（屆時可比照 `BlenderConnectionError` 註冊到 `api/main.py` 的 handler）。

---

## D-003 · `PreviewStage` 的 `react-hooks/refs` 定點豁免

**狀態**：`deferred`（2026-09-05 記錄；2026-09-09 重新評估——三個觸發條件都未成立：`ExportPanel` 仍用 `useImperativeHandle`、`eslint-plugin-react-hooks` 仍是 ^7.0.1、`react-hooks/refs` 的豁免在 `web/src` 只有這一處）

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

---

## D-004 · V1／V2／V6 的契約進 `ci.sh --real`

**狀態**：`done`（2026-09-09；2026-09-08 記錄、同日觸發——手契約三條閘門首跑合計 8 s）

**現況**：全部 13 份非手契約（V1、V2、V6，加上沒有包的 V4/V5 `inset_hinge*`、`hollow_side_hinge`，
含三份走 `mesh_probe_verify_real.py` 的 probe）都在 `ci.sh --real` 裡，依文件記載的場景重用順序；
真機各跑一次全過，合計約 59 s。`test_real_ci_runs_every_contract` 釘住：`contracts/` 下任何一個檔案
沒被 `--real` 跑、跑錯 checker、或 `--skip-generate` 前面沒有同產生器的生成，都紅。

**為何不一起接**：每份契約要在常駐 Blender 裡重建模型；四份加進來的秒數沒量過。
凍結交付物另有位元組層的包測試（`test_versioned_*_print_package.py`）在每次 CI 保護。

**觸發條件（任一成立就升為 `due`）**：
- 動到 V1／V2／V6 任一產生器；或
- 手契約閘門首跑實測 < 10 分鐘（`docs/hand-framework/v8-results.md` 的計時表）。

**目前的防護**：包測試逐位元組重讀 `models/octopus-hand-v1|v2/`、`models/biaxial-hinge-v6/`。

---

## D-005 · 無銷關節的抽象層（`JointStyle`）

**狀態**：`deferred`（2026-09-08 記錄，使用者裁決）

**現況**：`FingerLinkSpec` 是「有銷」形狀（`pin_diameter_mm`、`bearing_*`）。先例查證
（`100_fingers` 活動鉸鏈、`RoninHand` 原地列印，見 `docs/hand-framework/v9-references.md`）
證明銷不是必需品。

**為何不建**：活動鉸鏈靠**疲勞**失效，那是材料性質，本專案的幾何契約量不到——為一個驗不了的
東西設計介面是投機的泛化。目前只有兩個有銷實作，沒有第二種關節型式可以逼出正確的抽象。

**觸發條件（任一成立就升為 `due`）**：
- 出現**第三種**連桿（任何無銷型式）；或
- `docs/hand-v3/v6b-coupon.md` 的試片量到 2 mm 銷孔公差不可達。

**目前的防護**：`docs/hand-framework/00-context.md` 的「明確不做」；本條。

---

## D-006 · 床身尺寸成為實例欄位

**狀態**：`deferred`（2026-09-08 記錄）

**現況**：`256.0` 是 `LayoutPlan.bed_mm` 的預設，也是 `hand_v3.json` `max_footprint_mm` 的來源。
只有一台印表機（拓竹 P2S）。

**觸發條件**：`layout_fits_bed` 在真機 FAIL；或出現非 256 mm 的床身。

**目前的防護**：`layout_fits_bed` 用兩條獨立路徑量佔地並要求一致。

---

## D-007 · 活動鉸鏈的疲勞驗證方法

**狀態**：`deferred`（2026-09-08 記錄）

**現況**：不存在。幾何契約只量幾何。

**觸發條件**：D-005 成立。

**目前的防護**：無；這是刻意留白，不是遺漏——`docs/hand-framework/v1-scope.md` 的範圍外表寫明。

---

## D-008 · 發布 `models/hand-compact/`

**狀態**：`done`（2026-09-08 記錄；2026-09-09 觸發並完成，V01.0R.000）

**結果**：使用者對三張渲染圖 Lane B 通過（2026-09-09「三張圖可以」）。`publish_print_package.py --package
hand-compact` 從 `tmp/hand-compact/` 發布五個 STL、blend、三張圖到 `models/hand-compact/`，manifest 記 sha256
與面數／尺寸；`test_hand_compact_print_package.py` 逐位元組對照，README 的尺寸、件數、可達性、靜止淨距由規格
機器對照;`ci.sh --real` 從此每次重生成並與包差分（面數精確、尺寸 ±0.1）。

**當時的現況**：精簡實例已註冊、契約由規劃生成並在真機 20/14 全過（2026-09-09），`PACKAGES` 已登錄，
三張渲染圖已交使用者；`models/hand-compact/` 不存在，直到使用者裁決。

**為何不發**：與 V3 同規則——發布前要有使用者對三張渲染圖的 Lane B 驗收
（像不像手、握姿順不順、針筒好不好推）。

**觸發條件**：使用者 Lane B 驗收通過。

**目前的防護**：`publish_print_package.py` 不會自動跑；`08_hand-framework.md` 的驗收條件。

---

## D-009 · `ObjectListNode` 的 `react-hooks/set-state-in-effect` 定點豁免

**狀態**：`deferred`（2026-09-09 記錄）

**現況**：`web/src/mdr/nodes/ObjectListNode.tsx` 的 `useEffect(() => { void refresh() }, …)` 帶一行
`eslint-disable-next-line react-hooks/set-state-in-effect`。被豁免的是「掛載與場景變動時非同步抓
物件清單再 `setState`」——setState 發生在 `await` 之後，是與外部系統同步的 effect，不是級聯 render。
理由寫在程式碼旁；本條讓它在 DEFERRALS 也看得見（與 D-003 同類：定點豁免不得只活在程式碼裡）。

**為何不動**：正解是把資料抓取交給 query hook（TanStack Query 一類）或 React 19 的 `use()`；為一個節點
引進資料層是抽象投資，目前只有一處。

**觸發條件（任一成立就升為 `due`）**：
- 第二個 MDR 節點需要同樣的豁免；或
- 專案引進資料抓取 hook 層；或
- `react-hooks` 規則能辨認「await 之後的 setState」。

**目前的防護**：豁免是定點的；`web/src` 的 lint 是硬閘門，任何新增的豁免都會在 review 的 diff 裡。
