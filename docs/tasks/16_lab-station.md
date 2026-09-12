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

### Open failures

- 材料、精確瓶口／瓶高、零件型號、負載、工作溫度與液體尚未確定。
- 本階段是配置／試配原型，不得聲稱全機可直接裝配或固定力已通過。

### Next step

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
