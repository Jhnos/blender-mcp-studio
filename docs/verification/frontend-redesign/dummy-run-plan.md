# 前端 DUMMY RUN 驗證計畫（T3）

> 依據：`dummy-run-ladder`（MOCK≠DUMMY RUN、軸 M/軸 Q 分離、誠實宣告）＋ `verification-plan-design`（FICE + DFMEA）。
> 歷史姊妹文件：[`mcp-pipeline-verification-plan.md`](../../archive/2026-07-client-neutral-mcp/verification/mcp-pipeline-verification-plan.md)（T4 真機 MCP 鑑別性驗證）。

## 1. 這是什麼 / 為什麼需要

**DUMMY RUN ≠ MOCK**：
- **Mock**＝抽換**元件**（stub 掉 React 元件/引擎）→ 只驗「呼叫方在假設下的行為」，接縫沒被驗到。
- **Dummy run**＝保留**真元件**（真 React app、真 MDR 引擎、真 registry/dispatcher、真狀態管理），只換掉**輸入的資料**（後端）。

本計畫換的是**後端輸入**：用 MSW 攔截 HTTP + WebSocket，餵 fixture。**前端與 MDR 引擎全部是真的在跑。**

**為什麼要**：前端驗證不該被「Blender 有沒有開／後端健不健康／LLM 通不通」綁架。缺的是輸入，不是驗證能力（dummy-run-ladder 第一性原理）。此計畫讓**軸 M（機制）現在就能綠**，真後端到位時只剩軸 Q 一個變因。

**階梯位置**：階 4（手造 fixture）——純軸 M，不談輸出品質。

## 2. 怎麼跑

```bash
cd web && npm run dev -- --port 5173
# 瀏覽器開： http://localhost:5173/blender/?mock     ← ?mock 啟用 dummy 後端
```
- `?mock` 僅 DEV 生效（`main.tsx` 的 `import.meta.env.DEV` gate），**動態 import，不進 production bundle**。
- launchd 的 19504 服務是 production preview，刻意不啟用 `?mock` 或 Vite HMR。
- Harness：`web/src/mocks/`（`handlers.ts` HTTP+WS handlers、`fixtures.ts` dummy 資料、`browser.ts` worker）＋ `web/public/mockServiceWorker.js`。

## 3. 🔴 隔離自檢（第一步，不可跳過）

**dummy run 最危險的失敗不是跑不起來，是「看起來 mock 開著，其實真後端漏進來」。**

實例（2026-07-15 實際踩到）：WS mock 的 URL **寫死 `ws://localhost:5173/...`**，在其他埠（部署的 19504）就比對不到 → 真 WS 直連真後端 → 畫面變成「mock HTTP + 真 Blender viewport」的混種，而 mock 顯示為「已啟用」。**只有在真 Blender 正好在跑時才看得出來**。

**每次跑 dummy run 先做這三個判別**：

| 判別 | 隔離成立 | 漏水（fail） |
|---|---|---|
| 預覽畫面 | 顯示 `dummy viewport (mock)` SVG | 出現**真實 Blender 視窗**（有網格/工具列）|
| 「即時串流」徽章 | **不出現**（mock 不推 viewport_update）| 出現＝真後端在推 |
| Inspector 物件 | fixture 名單（Cube/Table_Top/Sun/Camera/Bezier）| 真 Blender 的名單（Camera/Cube/Light）|

> 通用規則：**mock 的攔截 URL 一律從 `location` 推導，永不寫死 host/port**——必須與 app 的 URL 推導邏輯（`useWebSocket`）逐字對齊，否則靜默 fallthrough。

## 4. 覆蓋的斷言（DFMEA 對應）

| 斷言 | 抓的失敗模式 |
|---|---|
| 三區版面在 1280 寬正確渲染；窄寬（768）水平捲動而非擠壞 | 版面溢位 |
| 漸進揭露：簡易模式隱藏「執行記錄」、進階顯示 | advanced 洩漏進 basic |
| MDR 從 `scene.list` 渲染填充 inspector、型別圖示正確 | schema→registry 派發錯誤 |
| 未知 `type` → 可見 fallback 佔位（非白屏）| 未知元件 crash（單元測試亦覆蓋）|
| chat：訊息 → AI 標記回覆 → 「已套用到場景·可復原」chip | 信任 signifier 缺失 |
| Refine overlay 開啟→執行→迭代卡（含可解釋理由）| tab→action 改造失效 |
| 互動元件皆有可及名稱；改名/刪除鍵盤可達 | a11y/可發現性回歸 |
| 破壞性動作有確認 | 容錯缺失 |
| Cmd/Ctrl+K 開啟 `role=dialog` 指令面板；搜尋框、listbox、option 與 active descendant 完整 | 鍵盤生產力與 screen reader 語意回歸 |
| 指令「全選批次目標」→ 輸入 mm 增量 → 單一 batch request → `Updated N objects` | registry→selection store→MDR→HTTP→operation store 接縫失效 |
| 最近操作最多五筆；只有明確附 callback 的 idempotent 操作顯示重試 | 非冪等場景 mutation 被重複執行 |

### 鍵盤生產力路徑

1. 按 `Cmd/Ctrl+K`，搜尋 `select all` 並按 Enter。
2. 在「批次變形」輸入 X 移動毫米值，套用至 fixture 物件。
3. 開啟「最近操作」，確認成功訊息與最多五筆標示。
4. 焦點位於 input、textarea、select 或 contenteditable 時，`Cmd/Ctrl+K` 與 Undo/Redo shortcut 必須保持文字編輯語意，不觸發 Studio action。

Headless gate 位於 `web/src/mdr/inspector.dummyrun.test.tsx`，使用真
`PreviewStage`、`InspectorShell`、MDR registry/dispatcher、Zustand stores 與
HTTP action；只把 scene/preview/batch response 換成 MSW fixture。

## 5. 誠實宣告（收尾必附）

**這次 dummy run（階 4，輸入＝手造 fixture / MSW）：**
- **證到（軸 M）**：真前端 + 真 MDR 引擎端對端跑通——schema→registry→dispatcher 派發、action 派發、漸進揭露過濾、三區版面、信任層、a11y 表面。前端機制在**與後端解耦**下成立。
- **證不了（軸 Q）**：真實 Blender 輸出品質、真實使用者易用性。fixture 的物件與 `dummy viewport (mock)` 是 **proxy，內容非真實 Blender 產出**。
- **紅線**：dummy run 的畫面**永遠不得**當成「MCP 有在作用」的證據。那需要 T4 真機 + 獨立 oracle → 見 [`mcp-pipeline-verification-plan.md`](../../archive/2026-07-client-neutral-mcp/verification/mcp-pipeline-verification-plan.md)（已於 2026-07-15 執行，H0–H7 過）。

## 6. 與 T4 的分工

| | DUMMY RUN（本計畫 / T3） | 真機（T4） |
|---|---|---|
| 換掉什麼 | **後端輸入**（MSW fixture）| 什麼都不換（真 Blender）|
| 證什麼 | 軸 M：前端/引擎機制 | 軸 M+Q：MCP 管線真實性 |
| 需要 Blender？ | **否** | 是（9876 監聽）|
| 獨立 oracle？ | 不適用（無真值可對）| 必要（socket 9876 execute_code）|
