# LESSONS_LEARNED

除錯根因抽象成 class + 缺失的 check。最新在最上。禁耦合細節——換專案還要成立。

---

## 2026-07-15

### 表面成功訊號 ≠ 語意真實（驗證必須用獨立 oracle + 鑑別性斷言）
- **觸發情境**：要證明「某條管線/整合真的在作用」時（尤其牽涉外部系統：DB、Blender、裝置、第三方服務）。
- **該主動檢查**：用一條**與受測系統的資料路徑物理獨立**的通道讀 ground truth，並讓斷言帶**只有真系統才產得出的鑑別特徵**（隨機 nonce、精確幾何/數值、狀態差分），而不是只看「有回應/有畫面/200 OK」。
- **為什麼沒抓到**：表面訊號會騙人——一個壞掉、斷線、甚至假的後端也能回 200、也能讓前端畫出一個方塊。缺的是「這訊號只有真系統在跑才可能出現嗎？」這一問。
- **如何預防**：驗證計畫先做 falsifiability 過濾（「假後端還會過嗎？會過就剔除」）；至少一個獨立 oracle + 一個非空 ground-truth 差分斷言。範例：Blender 管線用直連 socket `execute_code print(len(bpy.data.objects))` 當 oracle，斷言 nonce 物件的頂點數==8。

### health/status 訊號與其宣稱守護的相依性脫鉤
- **觸發情境**：一個服務有 `/health` 或就緒訊號，而它其實依賴另一個下游（DB、引擎、外部程序）。
- **該主動檢查**：health 是否**實際探測**它所守護的相依性，還是硬回成功？消費者（watchdog、前端徽章、驗證腳本）是否誤把「服務活著」當成「整條鏈就緒」？
- **為什麼沒抓到**：硬回 `ok` 的 health 永遠綠，於是「healthy」不代表下游可用；驗證若信它就假綠。同族：靜默退化成空/placeholder（不報錯），讓斷線與空狀態不可辨。
- **如何預防**：health 反映真實相依（探測或連線 flag），且用一個不同的 status 維度表達下游（例：`status:ok` 表本服務、`blender:connected/disconnected` 表引擎）；驗證絕不把 health 當下游就緒的證據。

### 入口點宣告了執行環境不會注入的相依 → runtime 首次連線才爆
- **觸發情境**：新增/修改框架路由 handler（HTTP / WebSocket / event handler），其參數靠框架依賴注入。
- **該主動檢查**：這個 route type 的執行環境**真的會提供**你宣告的每個參數型別嗎？（例：WebSocket route 不會有 HTTP Request）。有沒有一個 smoke test 真的去打這個入口點、斷言它不 crash？
- **為什麼沒抓到**：型別檢查/import 都過，錯誤延到「首次有連線進來」才 raise，且訊息指向表面（`missing 1 required positional argument`）而非根因（此 route 不注入該型別）。單元測試沒有真的 open 這個 endpoint。
- **如何預防**：每個 WS/事件入口點配一個「連上→送一則→不 crash」的 smoke test，進 release-readiness Lane A（機器可重複 gate），別靠使用者當測試員。

### 部署產物硬編值與配置 SSOT 漂移
- **觸發情境**：launchd plist / Dockerfile / systemd unit 等部署產物裡硬編了 port/path/label，而這些值另有 SSOT（如 services.yaml）。
- **該主動檢查**：部署產物內的硬編值是否與 SSOT 逐項對齊？重啟服務會不會因產物漂移而把它換到沒人用的 port？
- **為什麼沒抓到**：產物平時不被執行（服務可能由別的機制起在對的 port），漂移潛伏；一旦真的用該產物重啟就爆。sentinel 只檢查了 path 沒檢查 port。
- **如何預防**：sentinel 交叉比對部署產物的關鍵值 vs SSOT（不只 path，含 port/label）；產物盡量從 SSOT 生成或用 placeholder 替換，別硬編。
