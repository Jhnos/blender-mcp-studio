# 雙探頭量測工作站外殼

**Status:** ACTIVE

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

### Open failures

- 材料、精確瓶口／瓶高、零件型號、負載、工作溫度與液體尚未確定。
- 本階段是配置／試配原型，不得聲稱全機可直接裝配或固定力已通過。

### Next step

- V3 直上抽出修正保留為可重現 checkpoint；持續完成下列機構資格，不能宣告全目標完成。
- 優先完成探頭軟夾與滑座的實際固定、背架到腕部的螺栓介面、導桿防脫、根部與底座承力、平台連接、LCD PCB 保持、線材與全姿態／載荷驗證。
