# 雙探頭量測工作站外殼

**Status:** ACTIVE

導航：[目標](#goal) · [規格](#specification) · [驗收](#acceptance-checks) · [現行接手](#hand-off) · [歷史驗證](#歷史驗證紀錄)

## Goal

以 Blender MCP 專案設計動態氣泡表面張力計與 pH／溫度計共用的可列印外殼。

## Specification

- 使用者確定：拓竹 P2S；250 mL 燒杯或廣口瓶；三探頭共用一杯；約 20 cm 可調伸距。
- 共用桌面底座、LCD 可調與折平、兩組分節旋鈕鎖定臂；一組毛細管，一組 E201-C 與防水 DS18B20。
- hatch-pet 是誤選，不做動畫或寵物造型。
- 幫浦、微壓感測器、pH 前端、供電板未定案；不得把佔位模型當真實安裝尺寸。
- 第一階段交付尺寸化配置模型與外殼試配 STL；關節鎖定、探頭夾持、LCD 固定與走線需後續工程驗證。

## Acceptance checks

- 官方觸控 LCD 圖為 127.70 × 87.45 mm 玻璃，與頁面摘要尺寸分開。
- 兩節臂解析長度、可達性與每件 P2S 包絡由單元測試守衛。
- Blender 真模型、獨立 STL mm 尺寸與水密檢查；實際畫面檢視。
- 完整制造交付前：安裝孔、螺絲工具空間、探頭玻璃軟夾、防滑鎖定、連續姿態風險、抗傾倒與實體試片。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- V01.0R.01U：focused 74702 exit 0（`tmp/electrode-shoulder-indexed.log`），完整 `scripts/ci.sh --real` 43531 exit 0，所有 hard gates green（`tmp/lab-station-electrode-shoulder-teeth/ci-shoulder-teeth.log`）。18 domain tests 先紅後綠；完整 lint／format／mypy、回歸與交付守衛通過。
- 現行输出 `tmp/lab-station-electrode-shoulder-teeth/`；`electrode-concept.blend` 保留原裝配間隙，`elbow-seated.blend` 僅肘部已就座，肩部仍保留間隙。working、shoulder-released、indexed-shoulder-raised 已檢視；上輪各輸出目錄保留。
- 肩部支座／上臂內嵌 24 齒／15°，整個前臂組沿共同軸向退開 2 mm，保持探頭、夾具、被動軸連接；固定支座與肩螺栓／旋鈕保持原位。兩頭各工作角和 +15° 肩位共 40 局部齒面、84 軸向取樣通過；新增肩 +15°／肘 +15° 姿態约後退 24.05／抬高 89.79 mm，閉鏈／避碰／肘部就座通過。
- 杯與承液盤共同右移 3.5 mm；移回杯的負對照在 1.2 mm 退開時撞溫度探頭，退開上臂卻宣稱咬合亦拒絕，還原後通過。未增加五金，仍 16 螺絲／16 螺母。
- 原 46 單頭位置、11 共同前伸、298 拆裝、2760 被動軸及肘部 120 收隙狀態保留；新增兩個肩位各 15 肘部收隙狀態，存檔重新讀取通過。這些都是有限剛體幾何取樣，不代表預緊／承載。
- 第二處齒槽布林曾破壞原有效曲面；`tmp/electrode-shoulder-topology.json` 定位切除後 141 非流形邊。細部 Boolean 改本地毫米運算並還原後，封閉性／接面／就座全通過；原失敗日誌保留，教訓回寫。
- 5S：驗證移至既有 closure／check，局部出圖移至既有 render；main 366、check 323、closure 259、render 329、joints 308 行。無新模組或公開介面；R36 對應肩部正反例與圖。舊接手事实移至本檔歷史段，進度只由索引導引。

### Open failures

- 肩部整組收隙／就座、兩肩齒位之間的完整轉位路徑、腕部齒槽離合及就座尚未完成。
- 螺紋／彈性預緊、其餘五金裝入及工具空間、探頭軟襯保持力、底座承力、LCD 保持與走線、載荷及實體列印資格未取得；沒有現行整機製造 STL 發布。
- 精確容器、探頭與板件尺寸、負載、材料、溫度及液體資料仍缺；佔位尺寸不可當固定孔依據。深度微調精度未回覆；15° 為粗定位。

### Next step

- 74702、43531 均 terminal exit 0，無執行中的驗證。下一步以固定支座與整前臂位移為基準，建立肩部收隙模型及實際接觸面量測，再驗完整肩轉位與腕齒槽。
- `pose(label)` 會先還原全部矩陣，再套用肩／肘鬆開量；一般連續姿態兩關節各退 2 mm。指定整齒姿態才用 `elbow_release=0`，肩部亦回原間隙。額外肩位透過 `indexed_target(..., shoulder_step=1)`。
- `apply_take_up` 與 `apply_shoulder_release` 都是相對位移，禁止累加當絕對姿態。舊中立檢查先 reset pose 或讀原間隙檔；就座檔不適合直接作中立基線。
- 保留杯／承液盤 +3.5 mm 配置；退齒碰杯的負對照已納入 real gate。新模組若有必要，建立前先查 GitHub；保持所有真機流程串行，等待逾時先確認原工作排空。

## 歷史驗證紀錄

以下為逐輪證據與當時的下一步；接手只依上方現行段落與任務索引，不能將歷史下一步重新當成主線。

### V01.0R.01R–01T 接手事實（歷史）

- 01T 緊湊平台 focused 81981 exit 0：`tmp/electrode-platform-mirror-fixed.log`。輸出 `tmp/lab-station-electrode-compact-platform/`，兩平台實測 40 mm（舊 50 mm）、零非流形，144 孔周材料取樣與過寬／缺材料負對照通過，原運動／拆裝／就座讀回保留。領域偏置先紅後綠，38 domain／DCC tests 通過。首輪上臂破面，診斷 `tmp/electrode-platform-topology.json` 定位清理由 0→19 邊；保留有效三角化並讓鏡射沿用後通過。平台每步布林整理亦修復螺母座開口。未新增模組。完整 `scripts/ci.sh --real` 4805 exit 0，所有 hard gates green，日誌 `tmp/lab-station-electrode-compact-platform/ci-compact-platform.log`。

- 2026-10-03 短腕版 focused 43488 exit 0：`tmp/electrode-short-head-integrated.log`。毛細管／pH 溫度夾座中心落差由 22／44 改 20／38 mm，外角半徑 4 mm，腕盤夾蓋讓位。實際夾蓋底緣到腕軸 29／47 mm，過長接頭負對照拒絕；46 單頭位置、11 共同前伸、298 拆裝、2760 止擋與就座存檔重讀通過。working／extended／clamp-detail 已檢視。38 domain／DCC tests 與四檔 lint／format／mypy 通過。初期 18 mm 毛細管撞旋鈕，36 mm pH 在共同前伸撞另一夾蓋，均未採用；各輪失敗日誌保留。上一輪因執行中修改來源造成讀回 import 不同步，固定来源後本輪重驗通過；之後完整驗證期間不得改碼。
- 前輪未完成的肩部退齒 helpers／泛化改名已從生產來源移除；原工作差異保存在 `tmp/shoulder-and-short-head-wip.patch`，避免未接入驗證的試作混入此輪。此為當時未完成試作；本輪肩部及杯座由現行模組實作並重新驗證。

- 現行候選輸出在 `tmp/lab-station-electrode-shoulder-teeth/`（01U）；前版 `tmp/lab-station-electrode-compact-platform/`（01T）保留；上輪 `tmp/lab-station-electrode-short-head/` 與更早 `tmp/lab-station-electrode-seated/` 保留。`electrode-concept.blend` 是原間隙的運動基線，`elbow-seated.blend` 是四對承壓面同時就座的檔案。已檢視 `elbow-seated.png` 並重讀就座檔量測通過。
- 肘部名義收隙行程 0.7 mm：螺母先入座、螺栓頭接觸旋鈕、旋鈕接觸下臂，再合齒。八個整齒位配置各 15 個狀態，共 120 個；每步射線查齒面三半徑各 192 角點和三平面各 12 角點，並查障礙與螺栓外露。這是剛體就座，未證明預緊力。
- 修復齒面近似不匹配：原實測間隙約 0.13–0.27 mm，配對面與每齒區改用一致三角分割後，各齒位均能就座。齒面側 Ø5.6 mm 局部孔讓位，主孔最小仍 Ø5.4 mm，避免五條破邊。前兩次整合失敗與表面量測日誌保留於 `tmp/electrode-closure-*`、`tmp/electrode-seated-integrated-*.log`。
- focused 真機 26022 exit 0，日誌 `tmp/electrode-seated-integrated-third.log`；既有齒位／移動／夾具／止擋檢查保留。領域收隙先紅後綠，五個 joints tests 通過。
- V01.0R.01R 完整 CI 77945 exit 0，日誌 `tmp/lab-station-electrode-seated/ci-seated.log`。所有 hard gates green；未就座負對照與保存檔重讀也通過。

- 01S 5S：沿用四個既有模組，主生成器 364 行、checker 357 行、clamp 277 行；沒有新模組或公開介面。舊模型與失敗日誌保留，未驗的肩部试作移出來源；R34 追溯實際包絡與共同前伸，四張視圖已檢視。完整 CI 18874 exit 0，整機仍未具製造／載荷資格。

- 01T 5S：沿用既有模組，生成器 375 行、checker 376 行、arm 368 行，皆低於 380 行警戒；後續擴充需先分離職責，若新增模組仍先查 GitHub。working／extended／clamp-detail 已檢視，`platform-comparison.json` 獨立讀取新舊檔證實 50→40 mm；R35 與網格清理教訓已回寫。無新增五金或製造資格。

### V1–V9 已驗證事實

- 使用者接受整體概念，但指出頭部不能連在一起、必須各自活動。暫沿用先前兩臂分組；已詢問是否三探頭都需獨立，尚未收到答覆。
- 末端改為左右分離、前後錯開 16 mm、高度錯開 30 mm。新增各臂獨立的 yaw／shoulder／elbow／head tilt／probe slide 控制，真 Blender 10 組隔離試驗通過，另一頭的 matrix delta 均為 0；產出 `independent-motion.png/json`。
- 官方機械圖已下載至 `tmp/lab-station-v1/references/`。
- API 首查 disconnected；查詢正式 scene 後自動重連，health 回 connected；沒有重啟服務。
- `test_lab_station.py` 首跑因缺少 domain module 失敗，實作後 4/4 通過；新增腕部間隙測試先紅再綠，最後 5/5。
- 已建 `.blend`、四個實際模型視角、六件外殼試配 STL；說明見 `docs/verification/lab-station/10-model.md`。
- 獨立 STL parser 六件尺寸符合設計，誤差小於 0.01 mm，單件 X/Y 均小於 240 mm。
- 正式 FQDN MCP + artifact contract 10/10 通過；六件各一個連通實體。readiness=review（薄壁／懸垂提醒），並非無條件列印通過。
- `scripts/ci.sh` 與 `scripts/ci.sh --real` 全綠。腕部微調後 focused tests 5/5、ruff／format／mypy 通過；最後另重建本模型並重跑專屬 real contract。
- 檢測副本首輪在隱藏前未更新 world matrix，oracle 誤判重疊；移動後、隱藏前立即 view-layer update 修正，零重疊由 real contract 守衛。射線改讀可見的實際上蓋，避免 hidden mesh 無 evaluated data。這是既有教訓，不另複製一條。

- V2 使用者確認放射狀齒槽。新增 24 齒／15° 試片、單側齒槽螢幕支架、2 mm 軸向釋放與 0–75° 控制；兩臂仍獨立。
- 新增 domain tests 與真網格 motion probes：8 個單元測試；16 個螢幕角度與 4 個齒盤狀態。齒面由每齒 4 段改為 8 段，修正粗三角化導致的互穿。
- V2 齒盤布林合併需先完成簡單耳座與孔，再合併齒盤。左右固定雙齒盤改成單側鎖定／對側滑動，避免無法退出；縮短臂根軸佔位以避開收納後罩。

- V2 專屬 real contract 10/10 通過，九件各一個封閉連通實體；獨立 STL parser 九件尺寸誤差小於 0.01 mm。MCP 保留薄壁／懸垂 review。
- 增長觸發 400 行檔案預算測試；將渲染拆至 `scripts/lab_station_render.py`，預算測試恢復通過。

- V2 最終 `scripts/ci.sh --real` 全部 hard gates 通過（涵蓋 T1/T2/T3）；完整日誌 `tmp/lab-station-v2/ci-real.log`。實際檢視工作／折平／齒盤特寫；V2 試配包含 23 個設計與驗證檔，另附 CI 日誌。

- V3 已重現 V2 失敗：35 mm 提升後 pH 底端 73.5 mm，低於 120 mm 清杯平面（`tmp/lab-station-v3/red-v2.json`）。先新增 domain 失敗測試再實作；行程有效性再做一輪紅綠，focused 共 13 個通過。
- 使用驗證規劃、VOC 追溯、DDD/SOLID、TDD、SDD 與 checkpoint 技能；技能／工具盤點、GitHub 相似機構查找與沿用決策記於 `docs/verification/lab-station/`。追溯表 8 條通過結構檢查，不能因此聲稱所有需求已完成。
- V3 增加兩組 Ø8 導桿、背架／端座、滑座；腕點後退 40 mm，兩頭各有 100 mm 直上行程。13 件試配 STL；完整探頭軟夾、臂連桿與五金仍不是已完成製造件。
- 真模型：兩頭各 21 個升降位置、其他物件矩陣與探頭 XY 不變；直線凸包掃掠無交叉。毛細管底端 175 mm，pH/溫度 138.5 mm；杯口 110 mm。`probe-lift.json` 記錄證據與限制。
- 雙頭提起後，左右各 16 個向外旋轉取樣通過（0–45°，每 3°），`probe-parking.json`；已檢視 `probe-raised.png`、`probe-parked.png`。
- readiness 超過單次取樣上限時如實失敗；改成外殼 9 件／升降 4 件兩份 contract，皆要求沒有截斷，不放寬門檻。

- V3 最終靜態／單元／Web gate：`scripts/ci.sh` → `tmp/lab-station-v3/ci-final.log` 全綠；real run 的 T3 34 項全通過，包括兩份工作站 contract。整次初始 real 命令 exit 1，因當時 lint／型別／版本更新與測試收集競態；修正後 T1/T2 重跑全綠，不能把初始命令說成 exit 0。彙整見 `verification-summary.json`。
- 螢幕在升程 0／100 mm 各 16 個角度通過；STL 獨立 parser 13 件尺寸誤差 <0.01 mm。V01.0R.014 封存此工程 checkpoint，保留 ACTIVE；依使用者持續推進指示不要求清除上下文。
- 5S：模型說明由舊 `lab-station-v1.md` 移入單一 DCC 目錄，無重複進度表；來源／結果分離；生成件留 `tmp/`；AGENTS／技能未膨脹。

- V4：23 件 STL 三份 real contract 通過；兩片式軟襯、可拆夾蓋、導桿壓蓋及 8 組金屬五金參考；拆夾路徑 126 個取樣無表面干涉。螢幕收折已加入 LS_HW_，選取測試先紅再綠；focused 42 passed，ruff 通過。
- V01.0R.015：`scripts/ci.sh --real` exit 0，T1／T2／T3 全部 hard gates green，完整紀錄 `tmp/lab-station-v4/ci-real.log`；共用 oracle 排序修正通過所有既有模型回歸。23 件試配與模型未正式發布，保留 ACTIVE。
- 本輪 5S：幾何、夾具檢查與渲染分檔；輸出留 tmp，無新增執行通道；來源與裝配限制同步 DCC。下一步先完成滑座 M4 鎖緊五金與防滑保持，再完成腕部到背架承力介面。

- V5：先由真模型重現缺少滑座鎖緊螺絲，再加入兩組 M4×12 名義五金。`tmp/lab-station-v5/red-missing-lock.log` 為失敗證據；fit contract 通過，52 focused tests 與 ruff 通過。實際間隙 0.50002／0.50001 mm；0.49 mm 旋入無卡阻、0.7 mm 過行程能抓到撞桿。已檢視 clamp-detail.png。
- V01.0R.016：完整 `scripts/ci.sh --real` exit 0、全部 hard gates green，紀錄 `tmp/lab-station-v5/ci-real.log`；補充追溯文件後 DCC 16 passed。保持力、二次防墜、旋鈕操作包絡與鎖緊狀態防誤升降仍未取得證據，不能宣告滑座承載合格。
- 5S：沿用既有五金與升降檢查模組，沒有新增通道；V5 輸出獨立於 V4；新增 S7／R12 與失效追溯，AGENTS／技能不變。下一步完成腕部到背架的實際螺栓連接；已詢問探頭含線重量、最高溫度與液體種類，未答覆不阻止幾何裝配工作。

- V6 前置實測發現 V5 腕部並非已裝配介面：左右背架／腕圓柱有 16／14 對表面交叉，背架／下臂 57／59，腕圓柱／下臂 19／15。證據 `tmp/lab-station-v6/red-wrist-interface.json`。新增真模型拒絕穿插的守衛，目前預期 RED，尚未修復；不可把舊全綠當作腕部合格。
- 負對照已結束 exit 1，錯誤為 `Wrist reference is not an assembled interface`；紀錄 `tmp/lab-station-v6/red-wrist-contract.log`。下一步必須重建腕部叉耳／轉動件並調整下臂末端，不能只補螺栓或刪除檢查。工作樹未提交，尚未封存新版本。

- V6 修正：腕軸後退到探頭後方 60 mm，中間轉動件與背架合一、叉耳與下臂合一。橋接改到腕軸上方，修掉原後方橋接在螢幕 65° 時碰右下臂。布林相切面造成下臂 231 條非流形邊，改用有重疊且不共面的接合後消除；25 件各單一封閉實體。
- 新 `scripts/lab_station_wrist.py` 沿用既有 primitive／Boolean；已有 GitHub 前置查找紀錄。補兩支下臂試配 STL，仍未完成肘端安裝與腕部鎖定保持。`probe-lift.json` 加入腕部兩側各 11 個 −15°..15° 局部姿態，包含軸與螺母干涉；全行程升降、拆夾、螢幕收折通過。48 focused tests 通過，已檢視 assembly.png；完整 gate 尚未跑。
- 升降／夾具契約均已通過、無截斷，輸出 `tmp/lab-station-v6/verification-lifts.log`／`verification-clamps.log`。下一步核對結果、補腕軸裝入與螺母保持，再補完整 CI／版本 checkpoint。現有穿軸是名義 M5×35，無墊片、無防鬆／力矩資格，不得稱完整機構完成。

- V6 腕部補兩側墊片；缺件負對照 `red-wrist-washers.log`。原位裝右墊片被另一臂擋住，改為雙頭提起、另一臂外轉 45° 的裝配姿態；兩側共 126 個 2 mm 步距插入位置通過，紀錄 `wrist-assembly.json`。48 focused tests／ruff 通過。V01.0R.017：初次 `scripts/ci.sh --real` exit 1，唯一失敗是已修正的 wrist_samples 型別註記；T3 共 35 項通過。修正後 `scripts/ci.sh` exit 0，T1／T2 全綠。兩份日誌与 verification-summary.json 位於 tmp/lab-station-v6，不宣稱初次命令全綠。
- V6 5S：來源／輸出分開；腕部幾何模組沿用 primitive／Boolean；25 件試配描述與 manifest 對齊；無公開 execute_code、無新增執行通道。此 checkpoint 保留 ACTIVE，下一步腕部保持與工具空間，以及肘端實際連接。
- 下輪先完成完整 gate／checkpoint；腕部扳手空間、防鬆、預緊保持力與肘端连接仍需完成，不能把本輪當全機製造合格。

- V7：先以真模型重現實心腕軸頭阻擋六角扳手（`tmp/lab-station-v6/red-wrist-tools.log`），補六角孔後工具就位包絡通過。工具視圖與檢查共用 `wrist_tool_envelopes`；新增圖片腕部前視被背架遮擋，已改後視待完整重建。ruff／兩檔 explicit-package-bases mypy 通過。V01.0R.018 完整 `scripts/ci.sh --real` exit 0，全部 hard gates green；日誌 `tmp/lab-station-v7/ci-real.log`。已檢視新後視圖，工具入口可辨認。5S：工具包絡由同一 helper 供檢查與渲染，診斷形體不留在模型或 STL，25 件數量不變。
- 下一步轉到肘端的實際装配：齒盤／上下臂連接、穿軸、釋放間隙與硬體保持；腕部工具手柄擺幅、保持力與防鬆仍未取得資格，未解除全機 H6。

- V8 肘端實測：舊版上下臂互穿，且軸穿過實心連桿，完整配對證據 `tmp/lab-station-v8/red-elbow-interface.json`。領域 elbow_necks 先紅再綠，11 個 domain tests 通過。
- 新 `scripts/lab_station_arm.py`：上下臂各 ±14 mm 側向接座，先沿 YZ 離齒盤 30 mm 再回接連桿；齒盘與各自臂一體布林，打通 Ø5.4 軸孔，補名義 M5×60 螺栓與螺母。原布林後再穿孔造成 139 條非流形邊，改成先穿孔再接齒盤修復；目前 25 件專屬 fit contract 通過，中立姿態上下臂／軸／螺母無表面干涉。
- 尚未封存 V8。下一步：新增上臂 STL，將上下臂獨立 readiness 分批；加入肘部軸向脫齒控制、鎖定／釋放轉角負對照及五金保持／裝入。不得以中立姿態通過宣稱可調角或承重；root/shoulder 仍為參考組裝。

- V8 肘部新控制 `elbow_release_mm`：缺控制先紅，加入軸向 0..2 mm 位移後通過兩側各五狀態（0°合齒、7.5°合齒必須撞齒、7.5°脫齒無交叉、15°脫齒與合齒無交叉）。這只查上下臂局部網格，不能當全臂可動證據。
- 上臂新增 STL，重命名下臂為 arm_lower，清除 V8 輸出內舊 lower 檔；合計 27 件。readiness 獨立 arm 4 件／lift 4 件，新增 `lab_station_arms.json` 與 CI gate。首次手臂契約抓到退化面 1 與自交 3，先三角化後局部 0.01 mm 合點、0.005 mm 退化清理後 arm contract 通過、無截斷，沒有放寬契約。證據 `tmp/lab-station-v8/verification-arms.log`。
- 尚未封存版本；已將脫齒加入兩頭隔離檢查，最新生成正在執行：exec session `88576`，tmp/lab-station-v8/verification.log。先輪詢同一 handle，再跑其餘三份 skip-generate 契約與完整 gate。仍需肘部五金保持／裝入、全臂姿態、肩根承力；readonly angle samples 不替代負載測試。

- V8 最新生成通過，隔離案例 12 個；四份契約曾全部通過。封存前補查脫齒五金，先紅重現螺栓跟隨下臂平移撞上臂（red-elbow-release-hardware.log）；改成 bolt 隸屬上臂、nut 隸屬下臂，五狀態檢查重新通過。ruff／三檔 explicit-package-bases mypy 通過。
- V01.0R.019 完整 `scripts/ci.sh --real` exit 0，所有 hard gates green，包含四份工作站契約；日誌 `tmp/lab-station-v8/ci-real.log`。肩根仍為參考幾何，肘部墊片／裝入／保持、全臂動作與承力均未完成，不能解除 H6。
- 5S：新增 arm 模組僅處理偏置接座與既有齒盤接合；臂件独立 readiness 分批，無放寬取樣或退化判準；V8 清除旧命名的兩件下臂 STL，輸出 27 件與契約一致。下步補肘部保持／裝入再轉肩根，不重跑已封存的設計工作。

- V9：肘部兩側墊片缺件先紅（tmp/lab-station-v8/red-elbow-assembly.log），補入後 216 個名義裝入位置通過。新增軸向餘量檢查：刻意把螺母向外移 4 mm，0 mm 穿出量被拒絕，證據 tmp/lab-station-v9/red-axial-coverage.json。49 focused tests、兩檔 mypy 通過；正例重建通過：合齒穿出約 4 mm、脫齒穿出約 2 mm。
- V01.0R.01A：完整 CI 的 T3 全部通過；命令 exit 1，唯一失敗為 model_lab_station.py 排版，已以 ruff 修正。T1/T2 重跑 exit 0、全部 hard gates green，紀錄 tmp/lab-station-v9/ci-final.log；原始完整日誌 tmp/lab-station-v9/ci-real.log。肩根連接仍是下一個結構缺口；肘部防鬆／保持力沒有因軸向覆蓋而取得資格。

### 歷史 V9 未完成項目

- 材料、精確瓶口／瓶高、零件型號、負載、工作溫度與液體尚未確定。
- 本階段是配置／試配原型，不得聲稱全機可直接裝配或固定力已通過。

### 歷史 V9 後續與版本紀錄

- V3 直上抽出修正保留為可重現 checkpoint；持續完成下列機構資格，不能宣告全目標完成。
- 優先完成探頭軟夾與滑座的實際固定、背架到腕部的螺栓介面、導桿防脫、根部與底座承力、平台連接、LCD PCB 保持、線材與全姿態／載荷驗證。

- V9 5S：沿用 arm 模組，未新增執行通道；27 件輸出、契約與說明一致，生成件保留 tmp；已檢視 probe-raised.png。下一步完成肩根到機箱底部的實際承力連接。


- V10 肩根基線已量測，舊 root／固定齒盤／上臂／軸有多處互穿；證據 tmp/lab-station-v10/red-shoulder-interface.json。肩根守衛先拒絕舊模型，domain shoulder_neck 測試先紅再綠。
- 沿用 arm 模組，將接合／五金 helper 命名為 connect_serrated_joint／joint_hardware，加入肩部一體支座、上臂活動齒盤與 shoulder_release_mm。新增兩件肩部 rotor，契約改 29 件；肩部局部五狀態曾通過，完整回歸仍待通過。
- 修復布林軸孔共面造成一／兩條四面共邊：齒盤孔半徑 2.75、軸座 2.7。縮短肩部軸向尺寸並加入螺栓頭／墊片座，因直接沿用肘部寬接座會擋住折平 LCD。最後一次失敗為 LCD 後罩與右肩支座／螺栓互穿，已將固定接頸外移 1 mm、減薄螺栓頭；重建中 exec session `96569`，tmp/lab-station-v10/verification.log。先輪詢此 handle，勿並行啟動 Blender 驗證。
- 夾具場景完整性改為必要零件逐名核對，原 >=50 因合併件數失效；新名單 48 件，缺件負對照仍待補。58 focused tests、四檔 mypy 通過；版本未 bump、未提交。支座到機箱的軸承／底板承力連接未完成，不能聲稱整機可承重。

- 使用者最新修正：質疑線性滑座對 3D 列印的適用性，提出增加活動臂／自由度。接下來優先評估以獨立平行四連桿取代末端導桿滑座；不得繼續把直線滑座當定案。V10 最新 fit 生成 exit 0（session 96569 已結束），肩部／折屏修正獲得局部與 fit 契約證據；其餘 readiness、完整 CI、版本 checkpoint 未跑。
- 純解析候選：130 mm 平行桿，自 -22.62° 到 +22.62° 提升 100 mm，最大水平偏移 10 mm，向 -Y 運動時原有三探頭在假設 ID66 mm 圓筒內保有正間隙。tmp/lab-station-v10/rotary-lift-concept.json；尚非實體四連桿、臂間／瓶口掃掠或承載驗證。下一步依此候選建可見的旋轉式升降概念並檢查機構空間，保留兩頭獨立。

- 四連桿候選已建立 scripts/model_lab_rotary.py 與純領域 RotaryLiftSpec。先紅再綠的閉合／行程測試，13 個領域測試通過。以實際桿端局部座標驗證旋轉後的閉合；停掉單桿驅動會被拒絕（red-broken-link.json），重新啟用後正例通過。
- 第一輪整機探測發現下桿撞支撐與右側螢幕；改成末端架向外 66 mm、支撐由軸後方接入，最新 202 個探頭取樣與 42 個整機姿態通過；固定支撐對外殼／HMI 無非名義接觸，見 tmp/lab-station-rotary/assembly-motion.json。已檢視 working／both-raised 圖；生成器再現 motion 與負對照通過，非製造資格。
- 新真機入口 scripts/verify/lab_rotary_verify_real.py 已接入 ci.sh --real，沿用既有 oracle；無新增公開執行通道。三個動作圖、模型、報告由同一生成器再現；來源參考與限制寫於 11-rotary-concept.md。
- V01.0R.01B 準備完整 gates；未提交。四連桿所有移動件相互干涉、全組合／線材、實體轉軸與鎖定／平衡、機箱承力仍未完成；使用者資料缺口仍保留。

- V01.0R.01B 完整 CI 執行中：exec session `21530`，tmp/lab-station-rotary/ci-real.log。接手輪詢此 handle，勿並行重建 Blender。5S：新增概念頁納入導航，舊滑座頁標示為基線；新模組沿用原語意與工具，單檔低於 400 行，生成件留 tmp。

- V01.0R.01B 最終完整 `scripts/ci.sh --real` exit 0，全部 hard gates green；日誌 tmp/lab-station-rotary/ci-final.log，session 46584 已結束。初次 ci-real.log 的六件手臂超過 20000 面分析上限而失敗，且執行中改 CI 檔造成尾端解析錯誤 exit 2；已凍結腳本並完整重跑，不能把初次命令說成成功。
- V10 六件臂分成左右各三件 readiness，新增 lab_station_arms_right.json，維持禁止截斷；四連桿 gate 則只驗運動與場景表面碰撞，沒有冒用 readiness。新候選三張圖皆已實際檢視，文件與來源已入導航，DCC 16 passed。
- 下一步以 rotary 候選為主：補四連桿所有移動件互相干涉及雙頭同動；將支撐／轉軸佔位改成真正可裝配、可鎖定且能保持的機構，完成機箱底板承力。V10 夾具新逐名完整性守衛的缺件負對照尚需納入；不回到線性滑座主方案。

- 使用者明確要求四連桿僅負責升降，保留其他位置的原鉸鍊自由度。已加入每頭 base_yaw_deg／shoulder_deg／elbow_deg／wrist_deg，加上 lift_mm 共五個獨立控制；腕部手動調角，不自動對地補償。真 Blender 10 個隔離案例通過；支撐仍是包絡，尚非可鎖定的實體關節。
- 本輪未提交：新增 M5 名義轉軸／三墊片／螺母／雙軸套包絡，末端外移由 66 改 74 mm；同頭移動件配對、雙頭 121 高度組合、折屏取樣及交叉侵入負對照均由 focused 真機生成通過，日誌 tmp/lab-station-rotary/articulation-verification.log（exit 0）。新增控制最初 driver 無效，完整建立屬性／父子關係後重新編譯解決；缺控制負對照 red-missing-articulation.log。尚未跑本輪完整 CI／版本 checkpoint。下一步補支撐實體齒槽關節與抬起後側移姿態碰撞，更新概念頁並完成 gates；不能把五個控制的隔離測試當任意姿態安全或承力證據。

- V01.0R.01C focused 重建 exit 0，新增停用 yaw 驅動的 red-articulation.json 通過，恢復後 10 項正例通過；入口主動 reload 三個既有 helper。已檢視 pivot-detail.png，五金可見。5S：沿用既有模組（最大 337 行），更新概念頁與 R18 追溯；生成件留 tmp，沒有公開任意執行通道。準備完整 CI，尚未提交。

- 首次 V01.0R.01C 完整 CI exit 1，唯一失敗為嵌入字串內的專案 import 守衛，真機項目通過；修正為沿用 reload_modules_for 推導完整相依閉包，並設定根目錄後以資料清單載入。該守衛 5 個 focused tests 通過，無放寬規則；將重新完整跑 CI。

- V01.0R.01C 最終完整 scripts/ci.sh --real exit 0，全部 hard gates green，日誌 tmp/lab-station-rotary/ci-01C-final.log，session 62719 已結束。首次失敗紀錄保留 ci-01C.log。下一步將 rotary 肘部支撐包絡改為實體兩成員與齒槽／脫齒介面，再驗證轉動和裝入；肩／腕、底座承力與全姿態仍未完成。

- V01.0R.01D：舊 rotary 肘部被 integrated tooth 守衛拒絕後，沿用 connect_serrated_joint／joint_hardware 建兩成員齒盤與 2 mm 脫齒。右側下臂斜穿齒盤，改回接路徑後又碰升降桿；最後改從齒盤後上方繞回，focused 生成 exit 0，兩側五狀態與整機升降／折屏通過，tmp/lab-station-rotary/elbow-verification.log。新增 elbow-detail.png 與脫齒隔離項，待完整 CI。5S：僅沿用既有模組，沒有新增模組／公開執行通道；來源與 tmp 生成件分離，R19 與概念頁同步。

- V01.0R.01D 完整 scripts/ci.sh --real exit 1，唯一失敗為新增 rows 的 mypy 容器型別推導；T3 真機全數通過。補明確 list[dict[str, object]] 註記後 scripts/ci.sh exit 0，T1／T2 全綠。證據分別 ci-01D.log 與 ci-01D-static-final.log；不宣稱第一次完整命令成功。肘部 10 狀態、含脫齒 12 隔離案例與局部圖已核對。下一步肘部五金裝入／工具空間、支撐網格製造契約，再進肩／腕／底座承力，仍 ACTIVE。

- V01.0R.01E：網格基線 elbow-mesh-baseline.json 抓到四件支撐各 15／438／107／711 非流形邊，部分有退化面。固定接頸改實心 beam，不再挪用含孔圓耳的 bar，沿用 finish_arm 後四件單殼／零非流形／零退化通過。裝入檢查抓到立起 HMI 阻擋內側墊片；先收折到 tilt_step=0 後 216 取樣通過。曾誤用 tilt_deg 與反向端點，已依 screen_control 既有定義修正，沒有改變螢幕語意。focused 重建 exit 0，日誌 support-mesh-verification.log。準備完整 CI 與開面負對照。5S：沿用既有梁、收尾與裝入驗證，模組最多 349 行；生成件留 tmp，R20 同步。

- V01.0R.01E 完整 scripts/ci.sh --real exit 0，所有 hard gates green，tmp/lab-station-rotary/ci-01E.log，session 17752 已結束。support-mesh.json 四件均單殼／零非流形／零退化；red-support-mesh.json 開面後 3 邊拒絕；elbow-assembly.json 216 取樣通過。新局部圖已檢视，固定接頸無多餘圓耳孔。下一步工具空間、四件支撐自交／匯出契約，再肩／腕／底板承力，整機仍未完成。

- V01.0R.01F：工具基線 red-elbow-tools.log 重現實心螺栓頭擋住扳手，rotary 螺栓補 4 mm 名義內六角孔；兩側六角扳手與套筒四項就位、封孔負對照通過，focused log elbow-tools-final.log exit 0。沿用現有 arm／motion 模組，最大 356 行，新增 R21；不更動 V10 螺栓或公開工具。待完整 CI。自交／匯出契約、手柄掃掠與承力仍需完成。

- V01.0R.01F 完整 scripts/ci.sh --real exit 1，唯一失敗為 model_lab_rotary.py 格式，所有真機項目通過。ruff format 後 scripts/ci.sh exit 0，T1／T2 全綠；證據 ci-01F.log／ci-01F-static-final.log，不將初次命令稱為成功。已檢視六角孔局部圖，elbow-tools.json 四項零表面碰撞、red-elbow-drive.json 封孔拒絕。下一步優先補四件支撐自交／匯出契約，再處理工具掃掠與肩／腕／底座承力。

- V01.0R.01G：先紅拒絕缺少 LR_CHECK／STL 的場景（red-support-contract.log），新增四件獨立副本與毫米 STL、左右 readiness 契約。第一次副本碰撞量測讀到隱藏前的舊矩陣，調整為位移→update→hide 後重新生成，左右契約首次均 exit 0，無禁止問題或截斷。support-export-final.log 四 STL 對世界頂點尺寸差 ≤0.02 mm；沿用 binary_stl_metrics 與既有契約框架，無新增 Python 模組。5S：模型 371 行，輸出留 tmp，R22 同步。準備完整 CI，整機未完成。

- V01.0R.01G 首次完整 CI exit 1：checks 缺註記、STL 比對未使用收窄工具、契約沿用場景來源未被架構守衛辨識。改 list[str]、as_sequence／as_finite_number，第一份支撐契約明確生成、第二份沿用；12 架構 tests 通過。最終 scripts/ci.sh --real exit 0、所有 hard gates green，ci-01G-final.log，session 83040 已結束。首次 log 保留 ci-01G.log。四件 STL 仍為試配，未發布整機；下一步肩部／腕部實體介面與底座承力，工具手柄掃掠、載荷／線材仍未完成。

- 使用者指出「一堆實體與連接組件都斷開」。已中止原先逐件擴充，查明新肩部兩側各有 2 殼（disconnected-audit.json），薄梁 6 mm 套用原接頸偏置形成間隙；肩接頸中心由 ±13 改 ±12 mm。移除獨立 support_envelope_2，前臂與接回段／叉耳整合，固定框加入舌片／82 mm 後置腕部橋接與穿軸。腕部曾撞肘部／斜接段，改後置並先上升再橫接。14 件結構網格、肩部五狀態、腕部 −15／0／15° 共同孔／實體／五金檢查及既有回歸 focused exit 0；日誌 reconnect-verification.log。
- V01.0R.01H 待完整 CI，新增腕部斷接負對照；渲染搬到既有 lab_station_render，沒有新模組。底座仍只接觸上蓋、沒有機箱固定／底板承力，不能說全部斷接已修完。下一步先完成底座機箱連接，並維持整條實際介面檢查；不以單件水密代替整機連接。

- V01.0R.01H 首次完整 CI 唯一失敗為共用肩部偏置變更使舊 V10 肩座擋折屏；改 neck_plane_mm 參數，預設保留 13 mm，rotary 顯式 12 mm。最終 scripts/ci.sh --real exit 0，所有 hard gates green，ci-01H-final.log，session 4868 已結束。新 working.png 已檢視；14 結構件、14 控制隔離、10 肩部狀態與 6 腕部同軸介面案例核對，red-wrist-disconnection.json 移開叉耳會被拒絕。5S：渲染移到既有 render 模組、契約 reload 清單更新，無新模組或放寬判準。下一步最高優先：底座至機箱的實際固定／底板承力，然後全臂介面／載荷／線材；不可宣稱所有斷接已完成。

- V01.0R.01I：底座未保持的 RED 已確認（red-base-retention.log）；新增獨立 lab_station_base，旋轉腳軸頸／金屬軸套／M5×90 穿軸與薄螺母／上下墊片，支承柱接 6 mm 底板與側壁，8 mm 底腳避讓頭部。泵浦佔位內移 10 mm。base-final.log focused exit 0，兩侧十個止擋位移、共同開孔、中立間隙與移走墊片負對照通過；base-section.png 已檢視，為切開副本。5S：新模組前已查 GitHub，沿用原語意工具；model 375 行，生成件留 tmp，R24／參考／限制同步。準備完整 CI，尚未提交。下一步新機箱／旋轉腳網格匯出契約、穿軸／工具裝入與整體受力；不可宣稱整機可印可承重。

- V01.0R.01I 首次完整 CI 全綠（ci-01I-final.log），但尺寸複查發現新支柱高出上蓋底面 0.2 mm，原守衛漏掉機箱／上蓋配合。補查先紅（red-base-lid.log），支柱頂端降至 75.9 mm，上蓋底面 76 mm；加入凸柱穿入負對照。首次全綠不足以接受修改後模型，需完整重跑。

- 使用者中止複雜機構方向並明確要求「開始」簡化。01I 舊底座補查後 CI rechecked exit 0，但新主線改為 `model_lab_simple.py`：雙節臂每頭 150+150 mm，四調整點，取消四連桿／長穿軸／軸套／墊片；HMI 支座整合上蓋。`SimpleArmSpec` 先紅後綠，15 domain tests；新真機入口驗 202 個探頭／杯壁取樣、另一頭不動、22 個單臂空間姿態與三個雙臂展示姿態，移走上臂材料必須失敗。右臂原撞 LCD，鏡射局部錯位後通過；先挖孔再聯集留下內部蓋面，改實體聯集後開孔，實體孔檢查通過。`/tmp/lab-simple-final.log` exit 0。新主線仍為光滑關節概念，齒槽、埋入螺母、探頭夾紧、五金裝入、完整收折路徑／受力未完成，不能冒稱製造模型。準備本輪完整 CI。

- 簡化版首次完整 CI exit 1（tmp/lab-station-simple/ci-simple-final.log），新簡化 gate 通過，但旧 V10 重建被「使用中函式庫不可覆寫」拒絕。簡化生成器直接 append 會保留原來源，改沿用 rotary 的獨立 baseline 副本載入；清回已知生成場景後 focused independent-load.log exit 0。入口增加禁止持有可重建來源庫的檢查。需完整重跑，不將首次整體執行稱為成功。

- V01.0R.01I 最終 `scripts/ci.sh --real` exit 0，所有 hard gates green，tmp/lab-station-simple/ci-simple-rechecked.log，session 14080 結束。獨立 baseline 修復已由整套重建確認；簡化模型 202 探頭／杯壁取樣、22 單臂空間取樣與三展示姿態通過，斷接材料負對照會拒絕。working／parked 圖已檢視。5S：新主線導航 12-simple-concept、R25、範圍與五金表同步；新生成器 <300 行，重用原語、domain／oracle，生成件留 tmp。下一步只細化簡化版齒槽、埋入螺母、探頭夾緊與完整取出／停放路徑，保持減件方向；未發布 STL 或承重資格。

- 使用者拒絕獨立五連桿候選，要求參考常見設計，再接受 Agilent／ELMETRON／GOnDO 電極臂方向並要求延伸。已停用 five-bar domain，候選原稿留 tmp/lab-station-platform/rejected-fivebar；保留 simple 基線。新增 ElectrodeArmSpec 先紅後綠，16 domain tests。model_lab_platform 改成肩鉸鍊＋前臂平行雙桿＋三角末端，手調探頭角度；借用商用品用途，不冒稱整臂自動水平。
- electrode focused 真機入口 exit 0（/tmp/lab-electrode-verified.log）：46 單頭位置、六結構件全配對自碰／共同孔軸、雙頭／HMI／外殼／杯壁、16 折屏角度與移走 follower 負對照通過；已檢視 working／raised。修正舊夾座碰三角板、內側 follower 擋 LCD、夾座側移後兩頭相碰；改一體外側夾座、follower 外側錯層與根部 yaw 補償保持共杯位置。這些是既有「全配對／閉合」失效類別，沿用實網格守衛。
- 五金範圍：12 螺絲／12 螺母，4 列印被動軸包絡，零軸套／獨立墊片；被動軸尚無防脫，不是製造件。下一步被動軸保持、旋鈕齒槽與夾頭固定；全五金互碰／連續掃掠／線材／負載仍未驗。5S：新說明 13-electrode-arm 接入導航及 R26，生成件留 tmp，沿用 oracle 入口，不新增公開通道。完整 CI 待跑。

- V01.0R.01J 完整 `scripts/ci.sh --real` exit 0，全部 hard gates green，日誌 tmp/lab-station-electrode/ci-real.log，session 69710 結束。四張視圖皆已檢視；前臂及螢幕仍為有明確驗證邊界的概念模型。5S：模組 250 行、沿用驗證入口，未發布 STL；下一步在此電極臂上完成被動軸防脫、齒槽／旋鈕與夾緊，禁止回到被拒絕的五連桿候選。

- 使用者回饋「好一點但還是跟參考產品有差」。已透過瀏覽器實際檢視 GOnDO 兩張原廠圖；先前未充分核對照片比例，這輪將 Ø36 端盤→Ø22、梁寬16→12、桿距40→24、平台偏置45→28。上臂內藏連動不能僅憑照片宣稱同款；沒有套用 Agilent 的整臂自動水平功能。輸出分離至 tmp/lab-station-electrode-compact，01J 保存原檔供比較。尺寸測試先紅後綠，16 domain tests；focused real /tmp/lab-electrode-compact.log exit 0，46 位置／16 折屏／斷接負對照通過，working 已檢視。完整 CI 待跑。

- V01.0R.01K `scripts/ci.sh --real` exit 0，全部 hard gates green；tmp/lab-station-electrode-compact/ci-real.log，session 49468 結束。四張新視圖均已檢視。5S：沿用兩個生成器與既有驗證入口，修改 link 增加保留預設的端盤半徑參數，舊 simple 不受影響；比例說明覆寫 13-electrode-arm，舊實體輸出保留對照。仍需被動軸防脫、旋鈕／齒槽與夾具，未聲稱完全還原商用電極架。

- 2026-10-02 接手：01K 工作樹乾淨，上輪屬已完成 checkpoint 的進展。Blender LaunchAgent 為 exited／addon socket 無監聽，kickstart 同一已安裝服務後 PID 95354、addon socket LISTEN，重載 compact 模型。新增實網格基線 tmp/lab-station-electrode-compact/passive-pin-baseline.json：四被動軸於三高度共 12 案例對六結構件無表面交叉。passive-pin-retention-red.json 的 20 軸向位移案例證實：四軸向內 −2 mm 皆被 follower 擋住，向外 +2／5／10／20 mm 取樣皆無阻擋；現有單頭軸缺另一側止擋。未改模型、未執行新完整 CI、未新增製造資格。下一步補可裝入的列印防脫構造，再將中立間隙／雙向止擋與移除止擋負對照接入既有 real gate。

- 01L：missing-retainer 先紅；四被動軸加入 Ø3.4 × 1.8 mm 溝槽、厚 1.4 mm 的 C 形卡扣（Ø9／Ø3.8／開口 3 mm），不加金屬件。focused /tmp/lab-pin-focused.log exit 0，46 位置合計 2760 個軸向止擋／槽肩／拔插取樣通過；working 已檢視。32 domain／DCC tests 通過（首次 DCC 拒絕接手筆記重複埠號，改引用 addon socket），ruff／兩檔 mypy 通過。完整 CI session 59559 執行中，ci-retainer.log 目前服務檢查因三個 /tmp 日誌缺檔失敗；先等同一 handle 結束，再重裝 api/web 與完整重跑。卡扣彈性未驗，不能以剛體止擋宣稱實體保持力。5S：沿用現有模組，model 329 行，無新模組／公開通道，新增 R27 與局部圖，輸出仍留 tmp。

- 01L 首次完整 CI session 59559 exit 1，共 8 gate 失敗：服務日誌缺檔、readiness 缺報告／回報其他模型的 bounds、交付 502；新增電極臂 gate（含 displaced-retainer 負對照）通過。已檢視 retainer-detail.png，卡扣開口可見。使用正式 install api／web 恢復服務，health connected、Web 正式 preview 監聽後重跑 session 73908，日誌 ci-retainer-rechecked.log；不要並行操作 Blender。版本已 bump 01L，尚未提交。

- 01L 第二次完整 CI session 73908 exit 1：服務一致性已通過，但仍有 5 個回應缺失／錯配相關 gates 失敗。追查共用 socket，發現 timeout／cancel 後沿用舊串流會誤收遲到回應。新增 loopback 兩案例先紅（red-late-reply.log 都收到 request 1 而非 2），改中止時 disconnect、不 replay，22 adapter tests 全綠。沿用原模組，無新增通道／公開 DTO；LESSONS 新增無 request ID 之中止隔離失效類別，T2 納入守衛。API 正式重載修正後需第三次完整 CI。

- V01.0R.01L 第三次完整 scripts/ci.sh --real exit 0，全部 hard gates green，ci-retainer-final.log，session 13650 結束。實際載入新 socket 修正後，前兩輪的 report 缺失／錯配與 REST 交付失敗均未重現；初次／二次日誌保留。新卡扣局部圖與 working 已檢視，2760 軸向取樣、46 位置、16 折屏及 displaced-retainer 負對照通過。5S：沿用兩 CAD／驗證模組與既有 socket adapter/test，無新模組／公開 DTO；新失效守衛納入 T2。下一步完成緊湊臂旋鈕／齒槽與夾具，卡扣彈性／材料、全五金／線材／負載與製造匯出仍未取得資格；整體目標保持 ACTIVE。

- 01M：旋鈕缺件守衛先紅；沿用 lab_station_joints 增加六個帶六角孔的列印旋鈕、六角螺栓頭與臂件內螺母座。肩／肘 Ø25，末端 Ø17；較大的末端旋鈕曾撞夾座，縮徑後 /tmp/lab-knob-focused.log exit 0。46 位置下同頭旋鈕碰撞、頭／螺母中立間隙與 30° 相對止轉通過；working 已檢視。三檔 ruff／mypy 通過。5S：沿用三模組，主生成器 393 行，無新模組／公開通道；新增 R28，金屬件仍 12 螺絲／12 螺母。完整 CI session 60392 執行中，ci-knobs.log；先輪詢，不並行操作 Blender。旋鈕承壓鏈同時閉合與預緊、裝入路徑、齒槽與實際鎖緊力未完成，不能稱全關節可鎖定。

- 01M 完整 CI session 60392 尚在執行，已知失敗：T2 主生成器 393 行觸發 380 行預警；simple/electrode 與 rotary oracle 等待逾時。Blender 日誌確認逾時後仍繼續渲染；程序取樣 blender-sample.txt 顯示主執行緒仍在執行 Python，並非停住，電腦另有其他高負載工作，未終止它們。不要重啟同一驗證或並行操作 Blender；先輪詢 60392，最新 child 為 rotary support contract。
- 旋鈕真機階段已結束後，將旋鈕五金與 retained_pivot 建立抽到既有 lab_station_joints（無新模組），主生成器降回預算內；verify_knobs 在每姿態快取不動的 BVH，保留全部碰撞／30°咬合檢查。21 budget／DCC tests、兩檔 mypy 與 ruff 通過。這些整理尚未重新通過真機；版本 01M 已 bump 但未提交，不得當已封存。等待當前 CI terminal 後，先 focused 重建量測耗時／看圖／驗 red-knob-drive，再完整 CI，成功才 checkpoint。下一機械工作仍是旋鈕承壓與裝入、齒槽與夾具。

- 接手重驗 37 domain／DCC／budget tests 與 ruff 通過，上一 goal turn 屬具體幾何／守衛進展。60392 已確認持續執行，但已有確定失敗且使用整理前來源，故明確終止該 CI 及所屬子程序（exit 143），並非誤把觀察逾時當停止；Blender read-only barrier 成功回覆，確認先前工作已排空。現以整理後程式 focused 重建，exec 46829，knobs-refactored.log，含實際 elapsed_seconds；等待此 handle，勿並行生成。

- 整理後 focused 46829 的等待於 300 秒逾時（exit 1，knobs-refactored.log），不能推論 Blender 已停。knobs-sample.txt 取樣主執行緒主要為 C_BVHTree_FromPolygons／平衡與頂點讀取；共用 model_lab_simple.verify_clearance 仍在每配對重建相同 BVH，是下一修正目標。已排入只讀空間檢查的計數負對照，exec 9163／red-clearance-rebuild.log，將在前一主執行緒工作後執行；目前仍 live。不要另啟生成或重啟 Blender，先輪詢 9163，再查 red-clearance-rebuild.json。預期舊版每物件多次建 BVH，修正為每姿態一次且保留全配對，將計數守衛納入既有 real 入口。修正尚未寫入；旋鈕與 extracted helpers 的 real acceptance 仍未完成。

- 01M 計數負對照 9163 exit 1，red-clearance-rebuild.json 實測 31 物件／580 次 BVH／單物件最多 27 次，確定為重複計算。model_lab_simple.verify_clearance 改每呼叫一次局部快取，保留原全配對；正例變 31／31／1，移右上臂入左臂拒絕、還原通過。既有 real 入口加入計數與 red-cross-arm 守衛，LESSONS 記錄同姿態重建失效類別。四檔 ruff／mypy 通過。
- 整理後完整 lab_simple real 入口 exec 8736 exit 0，knobs-cache-verified.log：simple／electrode 重建、卡扣／旋鈕與快取負對照全部通過；working 已重新檢視。完整 CI exec 51041 正執行，ci-knobs-final.log，先輪詢同一 handle；未提交。主生成器 372 行、既有 joints 215 行，無新增模組。

- 01M CI 51041 的 REST o_names 發生 JSONDecodeError，MCP/chat 後續通過；檢查找到整段 stdout 當 JSON、artifact 只取末行的脆弱解析。以背景日誌前後夾入資料的案例重現同類失敗（red-oracle-logging.log、red-artifact-logging.log），REST/chat 名單、REST 頂點數、protocol/artifact JSON 都改沿用標記解析且維持 schema 檢查；11 parser tests、四檔 mypy 通過。停止已失敗且過期的 CI 51041（143），目前排空確認與新版 execute_json 真機呼叫 exec 47523 等待中；先輪詢此 handle，不要並行操作 Blender。成功後重新完整 CI，尚未封存。

- 47523 exit 0 回報 drained=True，確認排空及新版 artifact 標記解析真機通過。第三輪完整 CI exec 48990 執行中，ci-knobs-rechecked.log；目前 T1/T2、REST/MCP/chat 與 readiness fixtures 通過。先輪詢此 handle，不並行 Blender；所有尚未封存的 01M 修改仍需本輪全部 gates 通過。

- 01M 第三輪 CI 48990 仍 live，但 batch-transform 在 seed oracle 的 20 秒等待逾時，隨後 lab-station 生成 oracle 也逾時。REST/MCP/chat/print-readiness 已通過，未復發場景清單 JSON 雜訊錯誤。將 Blender 帶回前景仍無足夠證據支持 App Nap 推論；CUA getApp 觀察亦逾時，不能當應用程式已停證據。PID 95354 仍在運算，其他高負載程序存在但未干預。保留目前 CI 以收集其餘結果，先輪詢 48990／ci-knobs-rechecked.log，不並行 Blender，不宣稱完整通過或 checkpoint。

- 01M：第三輪 CI 48990 已確認失敗後仍跑依賴場景，明確停止所屬程序（143）；只讀 barrier 78019 exit 0，drained=True。既有 test_ci_failure_log 新增真機失敗後不得續改場景，2 red → 6 green；ci.sh 真機 hard failure 現立即退出，靜態仍彙整。完整靜態 CI 97855 exit 0（ci-failfast-static.log）。正在單獨重驗先前 batch seed 逾時，exec 23852／batch-isolated.log；這筆結束前不要並行操作 Blender。最新 working 圖已檢視，方塊夾頭與軸端整合仍與參考有差；未改這些幾何，也未封存01M。

- batch isolated 23852 exit 0，2/2 通過且已清理測試物件。修正後完整 CI exec 47627 正執行，ci-knobs-failfast.log；先輪詢這個 handle，真機失敗即停，不在運行中改 CI、不並行生成。靜態 CI 全綠不替代本次完整真機資格，01M 仍未提交。

- 01M 完整 CI 47627 exit 1，前面所有已執行 gates（含工作站與現行臂）通過，尾端 REST generation delivery 502，fail-fast 阻止後續 determinism。只讀 barrier 通過；舊 API 單獨重驗29325在31.155秒再次502。定位到30秒通用期限，TimeoutError 又被 MCPClient 一般例外分支變成空錯誤的腳本失敗。新增真 loopback 分類與三個期限案例先紅後綠；只為 registry 完整生成碼注入900秒，一般操作30秒不變。54 tests、mypy、ruff通過，API已正式重載75026 exit 0；focused REST 69589／delivery-timed-fixed.log 執行中，不並行生成。無新模組／公開DTO，01M未提交。

- focused REST 69589 exit 0（delivery-timed-fixed.log），5/5 STL重現與API回報一致，耗時28.854秒；這次低於原30秒，長期限邊界由真loopback與接線守衛證明，不將此單次耗時當超時邊界證據。最新完整 CI 58285／ci-knobs-deadline.log 正執行，先輪詢同一handle。前次47627已terminal；不要重跑或並行生成。01M未提交，下一步待全綠後checkpoint；夾頭造型／軟襯與鎖緊仍未完成。

- V01.0R.01M 最終完整 `scripts/ci.sh --real` exit 0，session58285結束，ci-knobs-deadline.log所有hard gates green，包括先前失敗的REST交付及末項determinism。新API已正式載入期限／分類修正。最新工作／抬起視圖與旋鈕負對照已檢視。5S：主生成器372行、socket adapter351行、專案技能150行；既有模組重用、現行與歷史規格分開，新增來源查找紀錄，生成件留tmp。沒有整機製造資格；下一步可側拆軟襯夾頭、軸端與關節過渡，再齒槽／承壓／裝配與負載。
