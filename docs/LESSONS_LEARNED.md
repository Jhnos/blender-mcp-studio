# LESSONS_LEARNED

除錯根因抽象成 class + 缺失的 check。最新在最上。禁耦合細節——換專案還要成立。

---

## 2026-09-05

### 重啟被依賴的服務，不等於依賴它的那一端也回復了
- **觸發情境**：只重啟拓撲中的一個服務（引擎、資料庫、broker），而上游持有的是啟動時建立、不會自動重連的長連線。
- **該主動檢查**：誰在**啟動時**握了這條連線？重啟被依賴方之後，**上游是否也重啟過**？用一個會真的走完那條連線的請求去驗，不要只看單一服務的狀態。
- **為什麼沒抓到**：健康端點誠實回報了 `blender: disconnected`，但沒有人去讀它——而資料路徑上的失敗**偽裝成別的錯誤**：死掉的 socket 送出後收到空回應，於是變成「回傳的場景資訊缺少欄位」（422），而不是「引擎連不上」（503）。看到 422 的人會去查資料格式，不會去查連線。
- **如何預防**：① 單一服務的安裝／重啟目標，必須連同重建它的相依方（本專案：`install.sh blender` 現在會等 listener 就緒再重啟 API，與 `all` 同序）；② 死連線要能被辨識成連線失敗，而不是退化成內容錯誤——否則錯誤訊息會把人引到錯的方向；③ 重啟任何一環後的驗收，一律用**跨越該連線的端到端請求**，而不是各服務各自的狀態。

### 檔案系統同步服務會偽裝成 git、套件管理器與 agent 的錯誤
- **觸發情境**：專案位於會被雲端同步的目錄（macOS 的「桌面與文件」、Dropbox、OneDrive）。出現檔名帶「 2」的副本、0 bytes 的檔案、無法解釋的相依損壞，或不明高負載時。
- **該主動檢查**：先確認同步是否涵蓋這個專案——macOS 看 `ls -ld ~/Library/Mobile\ Documents/com~apple~CloudDocs/Desktop` 是否為指向 `~/Desktop` 的 symlink。再看 `ps aux | sort -rn -k3` 有沒有 `bird`／`cloudd`／`fileproviderd` 佔住 CPU。0 bytes 但邏輯大小非零的檔案是 dataless placeholder，是同步的指紋。
- **為什麼沒抓到**：每個症狀單獨看都像別的東西的錯——壞掉的 `refs/heads/main 2` 像 git 的問題，`node_modules` 裡建構子變成 object 像 npm 的問題，被掃進 commit 的 112 個副本像 agent 的問題。四者被當成四個獨立意外分別修掉，根因原封不動。
- **如何預防**：① 專案目錄不要放在同步範圍內，或至少排除 `.git`、`node_modules`、建置產物與暫存目錄；② 遇到上述指紋時**先驗環境再驗程式**；③ 高負載期間量到的逾時與效能數字一律不可信，先看是誰在吃 CPU；④ 相依損壞的確定性修法是依 lockfile 重裝（`npm ci`），但同步仍開著就會再發生。

### 閘門宣稱涵蓋的範圍，與它實際比對的集合，是兩個不同的東西
- **觸發情境**：任何以「名稱清單」界定偵測範圍的檢查器——型別名、關鍵字、副檔名、路徑前綴。它報 OK 時。
- **該主動檢查**：這個閘門的**掃描根目錄**涵蓋哪些樹？它比對的**名稱集合**是否包含同義的抽象型別或別名？兩者都要親自讀設定，不能看它印 OK 就當涵蓋。
- **為什麼沒抓到**：閘門對它讀不到的東西「零發現」，與真的乾淨長得一模一樣。此處是雙重的：`TARGET_TYPES` 只列字面的 `dict`/`list`，讓 `Mapping`／`Sequence` 的窄化整批繞過；而整個 `scripts/` 樹（含閘門自己的原始碼）根本不在任何 lint／型別／掃描的根目錄裡。閘門自己也沒有測試，所以沒有任何東西會質疑它的涵蓋範圍。
- **如何預防**：① 每個閘門都要有「範圍測試」——斷言它被以正確的根目錄呼叫（讀 CI 腳本本身）；② 名稱集合要涵蓋語意同義詞，不只字面拼寫，並用 should-fire fixture 逐一釘住；③ 閘門必須有 should-pass fixture，否則「永遠報錯」與「正常運作」無法區分；④ 同一族的閘門（lint／型別／自製掃描）**排除清單要一致**，範圍不一致會產生沒人能處理的發現。

### 分析器提早放棄產生的綠燈，與程式碼真的沒問題無法區分
- **觸發情境**：靜態分析工具（lint 規則、型別檢查器）對某檔案回報零問題。
- **該主動檢查**：這個檔案裡有沒有會讓分析器**中止該區段分析**的構造（自我引用、無法解析的符號、動態存取）？移除那個構造後，同樣的檢查是否仍然零問題？
- **為什麼沒抓到**：一個 `useCallback` 在宣告完成前引用自己，讓 react-hooks 規則停在該處；同一元件更下方的 ref-during-render 違規因此從未被回報。重構移除自我引用後，那個違規立刻出現——它一直都在。
- **如何預防**：把「重構後**新增**的告警」與「重構後**才被看見**的告警」分開判定：用改動前的原始碼跑一次同樣的檢查，才知道是誰造成的。不要因為「改完才紅」就假設是自己弄壞的，也不要因為「改前是綠的」就相信改前沒問題。

### 前綴選取是資料邊界；輔助物件共用前綴會改變受驗產品
- **觸發情境**：用名稱前綴、標籤或 selector 定義要匯出、分析或部署的物件集合，同一流程又產生展示、診斷或暫存物件。
- **該主動檢查**：產品集合與輔助集合的 selector 是否互斥？選取數是否等於契約明定數量，而不是只檢查結果非空？
- **為什麼沒抓到**：輔助物件本身合法且畫面正確，但寬鬆前綴也將它們納入產品分析；成功選取與 `review` 狀態都無法指出集合已被擴大。
- **如何預防**：先分配互斥命名空間，再以精確 expected-count 和禁止 issue/truncation 共同守門；展示物件不得繼承產品 selector。

### 屬性已改動，不等於派生世界狀態已同步
- **觸發情境**：建立、複製、移動或隱藏場景物件後，立刻用世界變換、評估網格或空間索引做匯出與幾何驗證。
- **該主動檢查**：派生狀態是否已在明確同步邊界後更新？用一個非零位移物件比對局部位置與世界座標，並由世界座標 oracle 檢查預期半徑或接觸。
- **為什麼沒抓到**：來源屬性會先顯示新值，依賴它的世界矩陣或評估資料仍可能是舊快取；只看畫面、來源欄位或成功匯出都能形成假綠。
- **如何預防**：把 scene/dependency-graph refresh 放在「完成一批變換 → 匯出／BVH／量測」的共用邊界；契約同時守中立間隙與位移後的止擋接觸，讓 stale world state fail loud。

## 2026-09-04

### 單次請求序列化，不等於整個驗證交易隔離
- **觸發情境**：兩個程序共用同一有狀態 runtime，分別執行建立、選取、讀取與清除測試物件。
- **該主動檢查**：前一個完整驗證程序是否已結束？回報的物件名稱／nonce 是否與該次 oracle 的目標一致？
- **為什麼沒抓到**：socket 每次只處理一個請求，但不同程序仍可在「選取」與「檢查」之间穿插改變全域狀態；傳輸成功不代表語意快照一致。
- **如何預防**：將整段流程串行編排，等待程序結束再啟動下一段；若讀到其他 nonce 的物件，作廢整批證據後重跑。流程文件是操作約束，不宣稱已實作跨程序鎖。

## 2026-09-03

### 靜態裝配無碰撞，不等於運動包絡成立
- **觸發情境**：重複關節、連桿或其他運動機構只檢查中立姿態，便把設計角度當成已驗證能力。
- **該主動檢查**：將每個 mesh 轉到共同世界座標後，檢查中立姿態、展示姿態與包含正負端點的轉角採樣；同時檢查承力橋接結構，而不只檢查銷與耳孔。
- **為什麼沒抓到**：銷軸方向的間隙成立，但跨越該區域的橋接肋會隨轉角掃入相鄰零件。渲染清楚、單件流形及靜态配合都不能證明動態間隙。
- **如何預防**：由 swept-envelope 約束反推結構位置，將角度清單與預期碰撞數放進可重跑契約；缺少採樣或報告截斷必須 fail loud。明列有限採樣、表面交疊與實體負載驗證之間的界線，不宣稱連續碰撞或機械強度已認證。

## 2026-08-29

### 只清自己的物件前綴，不等於 Blender 產圖已與原場景隔離
- **觸發情境**：可重跑的 Blender 生成器只刪除自己命名空間內的物件，接著在目前 scene 直接架相機、燈光與渲染；同一 Blender runtime 先前已載入其他模型或色彩／照明狀態。
- **該主動檢查**：同一生成器在空場景與髒場景產出的主體、背景、曝光與 framing 是否一致？渲染前是否明確隔離非本任務物件，並在完成或例外時恢復使用者的 visibility？
- **為什麼沒抓到**：幾何 oracle、物件數與存檔都正確，但第一張圖被毫米尺度的高能量燈洗白；改光後，舊場景物件仍進入背景並遮住標籤。只看生成物名稱與成功回傳無法辨識這類視覺污染。
- **如何預防**：概念產圖用尺寸不敏感的 Workbench 材質色與明確色彩管理；渲染期間暫時隱藏外部物件並以 `finally` 恢復。產圖後仍須用獨立視覺驗證逐項檢查裁切、遮擋、文字與對比，不能由生成器作者自行宣稱清楚。

## 2026-08-11

### Process 已啟動不等於它的相依服務已 ready
- **觸發情境**：部署多個有啟動順序的長期服務；服務管理器已把上游標成 running，便立刻啟動只在 startup 建立一次連線的下游。
- **該主動檢查**：在跨服務邊界驗證真正的 readiness invariant（listener、協定探測或語意 health），而不是只看 process/job state；再確認下游是在 readiness 成立後才啟動。
- **為什麼沒抓到**：部署 gate 只守「plist 成功載入」與最終各 port 存在，沒有守**時間順序**。上游稍後確實開始 listening，讓最終快照看似健康，但下游早先的一次性 connect 已失敗並永久停在 disconnected。
- **如何預防**：部署編排在相依邊界使用 bounded condition wait，超時 fail loud；用 source-order contract test 鎖定「上游 install → readiness wait → 下游 install」，最後再用下游的語意 health 與端到端 gate 驗證。固定 sleep 不是替代品。

## 2026-07-19

### 關閉 HMR server 不等於 production page 不會載入 dev client
- **觸發情境**：長期運行的 WebUI 直接由 Vite dev server 提供，反向代理又不轉送 Vite HMR 的 WebSocket subprotocol；為了消除瀏覽器 console error，只設定 `server.hmr=false`。
- **該主動檢查**：用真瀏覽器讀取正式 URL 的 script `src` 與 console。頁面是否仍載入 `/@vite/client`？console 是否仍嘗試 HMR WebSocket？只看設定檔或「畫面能開」都無法證明 production runtime 已移除 dev client。
- **為什麼沒抓到**：`hmr=false` 關掉 server 端 HMR，卻不保證 HTML 不注入 dev client；設定測試與頁面 smoke 都會綠，只有瀏覽器 runtime 證據能分辨。
- **如何預防**：長期部署先 `vite build`，再用 `vite preview`（或正式靜態伺服器）；dev 與 preview 共用 API/WS/MCP proxy SSOT。部署 sentinel 需同時檢查 plist 使用 preview、installer 先 build，並以瀏覽器確認只載入 hashed assets、console 無錯誤。

### `launchctl bootout` 返回不等於 job 已完全離開 registry
- **觸發情境**：安裝腳本緊接著執行 `bootout` 與 `bootstrap`；舊程序仍在終止期間，`bootstrap` 偶發回 I/O error。若只因當下 `launchctl print` 尚看得到 job 就當作成功，稍後 job 消失而服務沒有重建。
- **該主動檢查**：卸載後是否有 bounded wait，確認 label 真正不可查才 bootstrap？bootstrap 失敗是否 bounded retry？完成後是否同時驗證 launchd state、PID listening port 與 health，而非只信其中一個訊號？
- **為什麼沒抓到**：把非同步 lifecycle 當同步操作，也把「舊 job 還存在」誤判為「新 job 已載入」。兩個瞬間狀態都不能證明最終服務存活。
- **如何預防**：installer 封裝 wait-for-unload 與 bounded bootstrap retry；最後以 label、port、health 三個獨立訊號驗證。部署測試鎖定 wait/retry helper，避免後續簡化腳本時復發。

### Operator 宣告 `UNDO` 不等於程式化呼叫真的推入可復原 transaction
- **觸發情境**：用 Python 自訂 Blender operator，`bl_options` 已含 `UNDO`，再由另一段 Python／socket 腳本呼叫它，便宣稱「一次呼叫＝一筆 Undo」。
- **該主動檢查**：operator 的**呼叫端**有沒有明確啟用 undo 執行參數？官方 `bpy.ops` 呼叫契約把 `execution_context` 與 `undo: bool` 列為獨立 positional arguments；遠端程式化呼叫要用 `bpy.ops.x.y('EXEC_DEFAULT', True)`，不能只讀 class metadata 推論 runtime stack。測試必須建立兩個 nonce 物件、一次變形、一次 Undo，再由獨立 oracle 確認兩者保留且 transform 全復原。
- **為什麼沒抓到**：單元測試只檢查 generated code 含 `bl_options={'UNDO'}`，變形結果也正確；表面證據同時相容於「有推 stack」與「沒有推 stack」。真機第一次 Undo 直接退回上一個 seed transaction、把 fixture 物件刪掉，才揭露呼叫預設未建立 batch undo step。
- **如何預防**：① 對程式化 Blender mutation 同時檢查 operator 宣告與呼叫參數；② 把 `('EXEC_DEFAULT', True)` 做成 codegen 單元 sentinel；③ 真機 gate 用「一次 Undo 復原多個既存物件」的鑑別性斷言，不能只看 `/api/undo` 回 success。

---

## 2026-07-18

### 傳入 allowlist 不等於 guard 已啟用；安全選項的「資料」與「機制開關」要分開驗
- **觸發情境**：第三方 server/middleware API 同時接受 `allowed_hosts`、`allowed_origins` 等 allowlist，另有一個獨立的 protection mode/enable flag。看到 allowlist 已傳入，就直覺認為 request guard 已生效。
- **該主動檢查**：送一個明確不在 allowlist 的 Host/Origin，真的拿到 403 嗎？本輪 FastMCP 3.4 的 `allowed_*` 只是 guard 的參數，`host_origin_protection` 預設仍可為 false；資料存在但機制沒 mount，惡意 Origin 照樣 200。協定版本亦同：initialize 本身用 params 協商版本，不是驗證後續 request header 的鑑別點；要用 `tools/list` 帶錯誤 `MCP-Protocol-Version` 才會真正觸發 400。
- **為什麼沒抓到**：把「設定物件看起來完整」當成 runtime behavior；單看 source/config 會得到假綠。initialize 又是特例，用它測 header 讓測試本身失去鑑別力。
- **如何預防**：安全設定一律加 negative request sentinel：不可信 Origin→403、未支援 protocol header（非 initialize request）→400、缺 identity→401。先觀察 sentinel 在 guard 缺席時確實紅，再補 enable flag；禁止只 assertion config 文字或 constructor kwargs。

### 改了 plist env 卻「kickstart 重啟」→ 沒生效：kickstart 不 reload、載入的是另一份拷貝
- **觸發情境**：改了 launchd plist 的環境變數（CORS、feature flag、port…）然後「重啟服務」想讓它生效。
- **該主動檢查**：你的「重啟」真的 **reload 了 plist** 嗎？`launchctl kickstart -k` 只重啟**進程**、不重讀 plist；而且**載入中的 plist 往往是 `~/Library/LaunchAgents/` 的另一份拷貝**，不是你剛編輯的 repo/deploy 那份。驗證要讀「載入中進程的實際 env」——`launchctl print <domain>/<label>`，不是讀你剛改的檔。
- **為什麼沒抓到**：本輪我改了 `deploy/launchd/*.plist` + `kickstart`，宣稱「已部署＋已驗證」。但 kickstart 沒 reload、載入的是舊拷貝，env 根本沒變。更糟的是驗證**不夠鑑別**：我只測了一個「新舊設定都會擋」的 case（CORS Origin=19504，在舊的 [tailscale,19147] 與新的 [tailscale-only] 下**都**被擋），於是假綠，直到下一輪查別的才撞見。同族：本 session 一路的「表面訊號≠真實、驗證要鑑別性」。
- **如何預防**：① env 變更要用**會 reload** 的機制（本專案 = `bash deploy/launchd/install.sh <svc>`，做 bootout→等待 label 消失→bounded bootstrap retry→kickstart）；② 驗證讀 `launchctl print <label>` 的**實際載入 env**，或送一個「**只有新設定會通過、舊設定會擋**」的鑑別性請求（例：直打服務、帶/不帶新 header 各一次看 401 vs 200）；③ 別把「編輯了 repo 裡的 plist」當成「載入中的服務變了」——那是兩份不同的檔。

### `narrow(x) or default` 把「畸形」訊號連同「空」一起塌掉——正確用了 SSOT，尾巴一個 `or {}` 又是 silent-fallback
- **觸發情境**：一個收窄／解析函式以 `None`（或空）表示「輸入畸形／不符預期」，呼叫端寫成 `narrow(x) or default`（`as_str_keyed(o) or {}`、`parse(s) or []`、`.get(k) or fallback`）。尤其在剛把某個 bug class 改成「一律走 narrowing SSOT」之後——會覺得「用了 SSOT 就安全了」。
- **該主動檢查**：`narrow` 回 `None` 的**語意**是什麼？若它同時代表「合法的空」與「畸形輸入」兩種情況，`or default` 就把兩者**塌成同一個值、且無聲**——呼叫端從此分不出「addon 回了 list/null」和「場景本來就空」。問：畸形這條路徑有沒有留下**可觀測**的痕跡（log/raise/metric）？
- **為什麼沒抓到**：`or default` 讀起來像無害的 defaulting，而且**它前面確實用了正確的 narrowing 工具**，所以 review 和 CI（mypy、container-narrowing gate）全綠——那些 gate 檢查「有沒有收窄」，不檢查「收窄失敗後有沒有靜默吞掉」。本輪 `get_scene_info` 就是：`as_str_keyed(...) or {}`，`as_str_keyed` 只在非字串 key 時警告，非 mapping 時回 `None` → `or {}` 靜默成 `{}`。與 07-15『health/靜默退化成空』、NO_SILENT_FALLBACK 同族。
- **如何預防**：收窄失敗要**明確分支**、留痕再回退：`n = narrow(x); if n is None: logger.warning(...); return default; return n`——別用 `or default` 把 `None` 一步吞掉。把「畸形 → 有 log / raise」當契約，並為它寫一個「餵畸形輸入、斷言有 warning」的測試（本輪這條測試正是抓到 bug 的那個）。延伸：**搶救「不是我建、即將丟棄」的 commit 前，先查它是否含 main 沒有的測試覆蓋**——那些測試可能正守著一個 main 已違反的契約（本 bug 就是併入被搶救的測試時當場 fail 才暴露的）。

### 純函式的「層」由它承載的知識決定，不由它的形狀（純度）決定
- **觸發情境**：一個 helper 看起來像 domain（純函式、無 I/O、只做資料轉換），但它**編碼了某個特定 backend 的知識**（某 addon 只吃哪些指令、產出某引擎的方言／DSL／SQL 方言／bpy 程式碼）。決定它放哪一層時。
- **該主動檢查**：這個函式**知道什麼**？若它知道「某個具體外部系統的限制或方言」，它屬 adapters 層，**不管它多純**。反問：domain 或 use case 匯入它，會不會就等於讓核心層知道了某個 addon/DB/引擎的存在？會＝放錯層。
- **為什麼沒抓到**：「純函式」直覺上很想放進 domain/use_case（無副作用、好測）。但純度是**機械性質**，跟**知識歸屬**無關。放進 use case 後，每條 dispatch 路徑都得自己記得呼叫它（本輪的 chokepoint bug 正是這樣長出來的：翻譯知識放在 use case，第二條 use case 忘了呼叫）。而且它一旦想下沉到唯一必經層（adapter），就會發現 domain/use_case→adapter 是反向匯入、動不了——放錯層在架構上是會「卡住」的。
- **如何預防**：放層看**知識**不看**純度**。backend-specific 的純函式（codegen/方言轉換/協定 quirk）放進該 backend 的 adapter，讓它成為那條路徑的唯一必經點；核心層只說領域語言，由 adapter 翻譯成方言。本輪：把 `blender_tool_codegen`（產 bpy code）從 `use_cases/` 移到 `adapters/mcp/`，翻譯下沉到 `BlenderMCPAdapter._dispatch`（execute+call_tool 都必經），最內層 `BlenderMCPClient` 對「仍是高階工具＝有人繞過」大聲失敗（runtime sentinel）——上一條『自稱唯一入口若無機制強制』的處方就此**機制化落地**（真 Blender 驗證：高階 create_object 過真 adapter 後 addon 回 exists＋8 頂點）。

### 部分 gate 給的是假覆蓋率：綠勾只涵蓋被跑到的子集，沒跑到的測試會靜默腐爛
- **觸發情境**：一個測試/檢查存在於 repo，但 CI 的 runner 只跑其中一部分（例：`pytest tests/unit`，而 `tests/e2e` 從不被跑）。任何時候看到「gate 只指向一個子目錄／一個標籤／一組檔案」都要警覺。
- **該主動檢查**：這個 gate 的涵蓋範圍，和「repo 裡實際存在的同類檢查全集」對得起來嗎？有沒有測試檔**存在但從不被任何 gate 執行**？綠燈是「全部通過」還是「被跑到的那些通過」？
- **為什麼沒抓到**：綠勾同時相容於「測試都過」與「有測試根本沒跑」——和 07-17『型別檢查器報綠≠有在檢查』、以及 health『訊號說的比它守的多』同族。本輪一個 e2e 斷言在產品行為正確變更後過期變紅，紅了一個月沒人知，正因為 `tests/e2e` 不在 gate 內；它是被『補一個新測試、順手擴大跑 e2e』意外撞見的，不是被機制抓到的。
- **如何預防**：gate 的涵蓋範圍要嘛是「全集」（跑整個 test root，而非某子目錄），要嘛對「刻意排除的部分」有顯式清單＋理由（一如 `# type: ignore`／deferral 要理由）。新增一批測試時，同時確認它落在被 gate 執行的路徑內——否則就是寫了個永遠不會 fail-loud 的測試。排除某些測試（需真硬體等）是合法的，但排除本身要可見、可 review，不能是「runner 剛好沒指到那裡」的沉默預設。

### 自稱「唯一入口 / single chokepoint」的宣稱若無機制強制，新增一條路徑就會靜默繞過它
- **觸發情境**：某個轉換／守衛／正規化被設計成「所有 X 都必須經過的單一收斂點」（docstring 或命名這樣寫），而呼叫它是**各呼叫端自律**、不是型別或架構強制。尤其當同一種操作有**多條 dispatch 路徑**時。
- **該主動檢查**：這個「唯一入口」實際被呼叫了幾次、在哪幾條路徑？把「所有會做這種 dispatch 的路徑」列全，逐條確認它們**都**經過那個收斂點——別信 docstring 的宣稱，用 grep 把呼叫點數出來。宣稱（claim）與強制（enforcement）是兩回事。
- **為什麼沒抓到**：宣稱寫在註解裡，沒有任何東西讓「繞過它」變成編譯錯或測試紅。第一條路徑正確接上後，收斂點看起來「就位了」；第二條路徑（可能後來才加、或本來就存在但沒人對照）直接 dispatch，型別檢查照過、單元測試各自 mock 掉真實下游也照過。本輪：一個把高階工具改寫成底層呼叫的 `translate` 自稱 single chokepoint，實際只有一條 use case 路徑用它，另一條生產 pipeline 路徑直送未翻譯的呼叫給只認底層工具的下游——與 07-17『同 class 只修了人看到那處』、checking-claims-are-enforced（宣稱≠強制）同族。
- **如何預防**：真要「單一入口」就用機制強制，不要靠自律——把收斂點下沉到**所有路徑都必經的那一層**（例：dispatch 的最底層 adapter），或用型別讓「未經收斂的值」無法被 dispatch（newtype / 只有收斂點能產出的型別）。若因為下游會變（不同 adapter 對應不同能力）而無法下沉，那它本來就不是 single chokepoint——就別這樣宣稱，並為每條路徑各自加一個「有沒有經過收斂」的哨兵測試。

### 「debrief 點名了」不等於「程式碼修掉了」：一個 bug class 的防線若不進 CI，人肉巡檢就會漏
- **觸發情境**：把一個 bug class 的殘留清乾淨後，靠「手動 grep + 記在 LESSONS」當防線。承前一筆——那筆 debrief 明確**點名** `blender_mcp_adapter.get_scene_info` 是存活實例之一。
- **該主動檢查**：被 debrief 點名的每個實例，程式碼裡**真的改了嗎**？別把「已記錄」當「已修復」。本輪 `reveal_type` 實測：`get_scene_info` 直到今天仍回 `dict[Any,Any]`（fix 當時落在同檔另一個方法 `_decode_response`，被點名的那個方法沒動）——在 mypy --strict 全綠下又活了一天。
- **為什麼沒抓到**：唯一防線是「手動 grep `isinstance(.*, dict)`」＋人的記憶，兩者都沒有到期日、沒有 fail-loud。名字寫進文件不會讓 CI 變紅；下一個人（或 subagent）照抄髒 pattern 時，沒有任何東西擋。
- **如何預防**：把這個 class 做成**可執行 gate 進 CI**，別靠巡檢。做法採 **checker-first／顯式豁免**：gate 找出每個真實 `isinstance(_, dict|list)`（`dict[Any,Any]` 與 `list[Any]` 同樣靜音；用 AST，不誤配字串/註解裡的字面），除非①位於 narrowing SSOT 定義檔、②該處帶 `# narrow-ok: <理由>`（必須有非空理由，一如專案對 `# type: ignore` 的要求），否則 fail。**不要**讓 gate 去「自動判斷某處誠不誠實」——誠實只有 `reveal_type` 在取值點才證得出，CI 做不到；gate 若自作聰明判斷，就又是一個對這個 class 天生瞎的工具（重蹈 07-17→07-18 的覆轍）。gate 的職責是把整個 class **從沉默變可見、可 review**，不是證明誠實。本專案落地：`scripts/check_container_narrowing.py`，接在 `scripts/ci.sh` T1 mypy 之後。

### 「用檢查器列出同 class 全部實例」有個盲區：檢查器對第三方/`Any` 邊界結構性看不到 → 那個子類要用 grep
- **觸發情境**：清一個 bug class 的殘留（承 2026-07-17「同 class 只修了人看到那處」）。其中有些實例的值源自**未定型第三方 SDK 或宣告成 `object` 的欄位**——`isinstance(x, dict)` 後直接用／直接回傳。
- **該主動檢查**：這個 class 的實例裡，**哪些檢查器根本沉默**？值一旦退化成 `Any`（lazy-import 的未定型套件、`--ignore-missing-imports`、`object` 欄位經 `isinstance` 只到 `dict[Any,Any]`），檢查器對它零報錯＝零線索。這種子類**不能靠檢查器盤點**，要用結構性 grep：`isinstance(.*, dict)`、餵給 `open(`/`dict[str,object]` 回傳的 SDK 取值點。
- **為什麼沒抓到**：2026-07-17 的處方是「用檢查器去問其餘實例」——對 union/可空型別成立，但對「檢查器被 `Any` 蒙眼」的那一半實例**恰好失效**：你拿一個對這些實例天生瞎的工具去盤點，回報「乾淨」。本輪就有兩個殘留（`hunyuan3d_adapter` 直接 `open(Any)`、`blender_mcp_adapter.get_scene_info` 把 `dict[Any,Any]` 當 `dict[str,object]` 回傳）在 mypy --strict 全綠下存活。
- **如何預防**：① 盤點一個 bug class 時先分流——「檢查器看得到的」用檢查器、「值會退化成 `Any` 的邊界」用 grep，兩條都要跑，不可只信檢查器的綠燈；② 抽出防腐層 helper（本專案的 `src/infrastructure/narrowing.py`）那一刻，**同批掃完所有既有邊界**改用它，別只轉換觸發它誕生的那一處——否則未遷移的邊界就是這個 class 的下一批溫床（narrowing 誕生於 07-17，這兩處當時沒一起遷）。

---

## 2026-07-17

### 型別檢查器報綠 ≠ 它有在檢查：`Any` 是靜音區，零錯誤可能是零檢查
- **觸發情境**：為了讓型別檢查器過而做收窄／抑制（`isinstance`、`# type: ignore`、放寬成 `Any`）；或在 JSON／外部 API／未定型第三方套件的邊界標型別。把型別檢查升成 hard gate 之前尤其要問。
- **該主動檢查**：收窄之後的取值點，型別**實際**是什麼？`isinstance(x, dict)` 執行期無法檢查型別參數，只能收窄成 `dict[Any, Any]`——於是後面整條 `.get()` 鏈都是 `Any`，檢查器全程沉默卻報 Success。既有的每個 `# type: ignore` 是否正遮著一個真 bug？
- **為什麼沒抓到**：檢查器對 `Any` **不報錯**，所以綠燈同時相容於「都對」與「都沒看」。肉眼讀程式碼分不出這兩者——`x.get(a).get(b)` 看起來跟有檢查的版本一模一樣。抑制手段沒有到期日，壓下去就永遠沉默，且下一個人會當成既有慣例照抄（本輪就發生：subagent 忠實照抄了既有的洞，而那個「參考範例」是我指給它的）。
- **如何預防**：① 收窄後每一跳**明確重新標註回 `object`**（不是 `Any`），逼出下一個 isinstance——沒有這個標註，`.get()` 就回 `Any`、後面全盤失守；② 判斷修法誠不誠實的**唯一**方法是在關鍵取值點插 `reveal_type` 確認它**不是 `Any`**，這件事不能靠讀 code 判斷；③ 升 hard gate 前先抽查幾個外部資料邊界，確認綠燈不是盲區換來的；④ 每個 `# type: ignore` 必須附「為什麼安全」，否則視為**待驗 bug** 而非既成事實。

### 同 class 的 bug 只修了「人剛好看到的那處」——因為檢查器在另一處被 `Any` 蒙住眼
- **觸發情境**：修一個「值的形狀不如預期」的 bug（union 成員、可空、多型回應、外部 API 回傳）時，同一個 class 在 repo 別處還有實例。
- **該主動檢查**：這個 bug class 還有哪些實例？要用**檢查器**去問，而不是靠 grep 或記憶。若某處檢查器沉默，先問「它是不是被 `Any` 蒙住了」，而不是當成那處沒問題。
- **為什麼沒抓到**：前一筆 commit 修了 A 檔的 `content[0].text`（union 首元素不一定是該型別），**同一筆 commit 就改到 B 檔**，但 B 檔同一個 bug 活下來——因為那裡的呼叫匹配不到 SDK overload → 回傳退化成 `Any` → 檢查器無法指出。人只修了自己肉眼掃到的那處，並合理地以為修完了。**同檔內甚至自相矛盾**：另一個方法正確地做了型別過濾，錯的那處就在它上面幾十行。
- **如何預防**：修完一個 bug class，把「檢查器能否列出其餘實例」當成收尾條件；檢查器在某處沉默＝那處的型別要先修好，它不是清白證明。跨檔案同 class 掃描要問「哪裡的型別資訊被抹掉了」，而不只是 grep 同樣的字面寫法。

### 教訓落了檔、處方沒進 gate → 同一個洞繼續長出新 bug
- **觸發情境**：上一輪 debrief 開了預防處方（「每個 X 入口點都該有 Y 測試」），但沒有任何機器在檢查它有沒有被實作。
- **該主動檢查**：上次開的處方**實際兌現了嗎**？有機器 gate 在守嗎？動工修 bug 前先查同 class 教訓（consult-first），命中就先看處方是否已實作——沒實作的處方就是這個 bug 的溫床。
- **為什麼沒抓到**：LESSONS_LEARNED 是**文件不是 gate**。寫下「應該要有 smoke test」不會生出 smoke test；文件被寫下的那刻感覺像問題解決了，其實只是被記錄了。本輪的真 bug 正好長在上一輪明文指出「這裡缺測試」卻沒補的那個函式裡。
- **如何預防**：處方必須落成**可執行的 check**（測試／lint／CI gate），否則明確標成 TODO 並排程；debrief 收尾時回頭確認上一條同族教訓的處方是否已兌現，未兌現就當本輪的待辦，不要再寫一次一樣的話。

---

## 2026-07-15

### 測試替身的攔截目標寫死 → 靜默 fallthrough，真依賴漏進「隔離」測試
- **觸發情境**：用 mock/stub/service-worker（MSW、nock、VCR…）攔截網路以做隔離測試時，攔截規則裡出現具體 host/port/URL。
- **該主動檢查**：攔截 URL **是否從執行期環境推導**（`location` 等）、並與**受測程式的 URL 推導邏輯逐字對齊**？跑測試時，是否有**觀測得到的判別**證明攔截真的生效（而非只看到「mock enabled」的 log）？
- **為什麼沒抓到**：攔截比對不到時多半**不報錯**——請求直接走真網路。於是「mock 開著」與「mock 生效」被混為一談；更陰險的是**只有在真依賴剛好活著時才看得出來**（真依賴沒開時，失敗看起來就像普通連線失敗）。
- **如何預防**：① 攔截 URL 一律推導、永不寫死；② 每個隔離測試先跑**隔離自檢**——挑一個「只有真依賴會產生、fixture 絕不會產生」的可觀測特徵，斷言它**不存在**（例：dummy run 的預覽必須是 fixture 圖，出現真實視窗＝漏水）。同族：`表面成功訊號≠語意真實`（下一條）——都是「訊號在說謊」。

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
