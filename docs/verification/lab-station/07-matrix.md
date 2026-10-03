# VOC 追溯

Population: R1–R16 為歷史 V10 的 LS_，R17–R24 為 rotary，R25 為 simple，R26–R45 為電極臂系列，現行為 electrode-guides-aligned。每個範圍皆涵蓋其兩頭、三探頭、單杯與 HMI；排除檢測佈局副本與診斷物件，任何必要族群為零即 FAIL。歷史證據只屬於該模型，不能當成現行電極臂的製造資格；現行規格見 [01-scope](01-scope.md)。

| ID | Requirement | Tier | User-visible | Kind | Verified-by |
|---|---|---|---|---|---|
| R1 | 探頭能直上離杯至少 10 mm | voc | yes | behavior | artifact:probe-lift.json/H1 |
| R2 | 兩頭可單獨提起 | voc | yes | behavior | artifact:probe-lift.json/H2 |
| R3 | 提起途中不撞杯或自己 | product | yes | behavior | artifact:probe-lift.json/H3 |
| R4 | 全行程保有導向 | engineering | yes | behavior | artifact:probe-lift.json/H4 |
| R5 | 使用者看得到前後差別 | voc | yes | behavior | artifact:probe-raised.png |
| R6 | 製造包有可靠固定與裝配 | voc | yes | behavior | artifact:manufacturing-qualification/H6 |
| R7 | 不以自動調平假裝實體機構 | product | yes | behavior | artifact:README.md/limitations |
| R8 | 純領域與幾何／渲染／檢查解耦 | engineering | no | behavior | static:scripts/ci.sh |
| R9 | 夾爪五金可裝入且探頭可側向拆換 | engineering | yes | behavior | artifact:clamp-assembly.json,jaw-service.json |
| R10 | 導桿上下具有幾何防脫止擋 | engineering | yes | behavior | artifact:clamp-assembly.json |
| R11 | 螢幕收折檢查納入探頭五金 | engineering | yes | behavior | artifact:joint-motion.json |
| R12 | 鬆開滑座鎖定可升降，旋入可接觸導桿 | engineering | yes | behavior | artifact:probe-lift.json/slide_locks |
| R13 | 腕部兩成員可轉動且不穿插 | engineering | yes | behavior | artifact:probe-lift.json/wrist_interface_samples |
| R14 | 腕軸與墊片可依順序裝入 | engineering | yes | behavior | artifact:wrist-assembly.json |
| R15 | 肘端先脫齒才可越過半齒角，五金不堵行程 | engineering | yes | behavior | artifact:elbow-release.json |
| R16 | 肩端齒盤與上臂／支座接合，脫齒時五金不堵行程 | engineering | yes | behavior | artifact:shoulder-release.json |
| R17 | 以旋轉連桿取代滑座，抬升時維持直立且兩頭獨立 | voc | yes | behavior | artifact:rotary/motion.json,rotary/assembly-motion.json |
| R18 | 四連桿之外保留底座／肩／肘／末端独立調整 | voc | yes | behavior | artifact:rotary/articulation.json,rotary/red-articulation.json |
| R19 | rotary 肘部兩成員齒盤接合，脫齒後能調角 | engineering | yes | behavior | artifact:rotary/elbow-release.json |
| R20 | rotary 肘部支撐單連通且閉合，五金可依序裝入 | engineering | yes | behavior | artifact:rotary/support-mesh.json,rotary/elbow-assembly.json |
| R21 | rotary 肘部六角扳手與套筒直段可就位 | engineering | yes | behavior | artifact:rotary/elbow-tools.json,rotary/red-elbow-drive.json |
| R22 | 四件 rotary 支撐匯出單位正確且無契約禁止的網格缺陷 | engineering | yes | behavior | artifact:lab_rotary_support_capillary.json,lab_rotary_support_pH_temp.json |
| R23 | 肩／腕具有實體兩成員介面，腕部斷接必須被拒絕 | voc | yes | behavior | artifact:rotary/shoulder-release.json,rotary/wrist-interface.json,rotary/red-wrist-disconnection.json |
| R24 | rotary 底座具共同穿軸與位移止擋，移走擋件必須被拒絕 | voc | yes | behavior | artifact:rotary/base-retention.json,rotary/red-base-stop.json,rotary/red-base-lid.json |
| R25 | 簡化為兩支獨立雙節臂，調整機構 10 螺絲／10 螺母且不需軸套與獨立墊片 | voc | yes | behavior | artifact:simple/verification.json,simple/red-disconnection.json |
| R26 | 參考實驗室電極臂，前臂雙桿加三角平台；肩與前臂共同定位，兩頭獨立 | voc | yes | behavior | artifact:electrode/verification.json,electrode/red-disconnection.json |
| R27 | 電極臂被動軸具雙向軸向止擋，移走卡扣被拒絕；不含彈性保持資格 | engineering | yes | behavior | artifact:electrode-compact/verification.json,electrode-compact/red-retainer.json |
| R28 | 肩肘腕六旋鈕與六角螺母座中立避碰，相對轉角產生止轉接觸；螺栓脫離被拒絕 | engineering | yes | behavior | artifact:electrode-compact/verification.json,electrode-compact/red-knob-drive.json |
| R29 | 圓角夾蓋與分片軟襯可拆，具軸向止口；抬高後探頭側取通過，杯內側取及移走夾蓋被拒絕 | engineering | yes | behavior | artifact:electrode-clamps/verification.json,electrode-clamps/red-service-in-cup.json,electrode-clamps/red-clamp-stop.json |
| R30 | 六旋鈕螺栓完整伸出螺母且外露不超過 1.5 mm，四對承壓面各自於預算內接觸；長螺栓與脫離頭部被拒絕 | engineering | yes | behavior | artifact:electrode-fasteners/verification.json,electrode-fasteners/red-bolt-exposure.json,electrode-fasteners/red-knob-drive.json |
| R31 | 肘部齒槽內嵌兩片封閉臂件，半齒咬合阻擋、退開 2 mm 可調；鬆開不可誤判咬合 | engineering | yes | behavior | artifact:electrode-teeth/verification.json,electrode-teeth/red-elbow-engagement.json,electrode-teeth/elbow-released.png |
| R32 | 完整平行前臂於四個整齒位保持連接，鬆開後可在齒位間移動；兩齒之間強制咬合被拒絕 | engineering | yes | behavior | artifact:electrode-indexed/verification.json,electrode-indexed/red-between-indices.json,electrode-indexed/indexed-raised.png |
| R33 | 肘部四對承壓面於同一狀態就座，收隙過程無阻擋且螺栓外露受限；未就座與不匹配齒面被拒絕，另驗存檔狀態 | engineering | yes | behavior | artifact:electrode-seated/verification.json,electrode-seated/red-unseated-chain.json,electrode-seated/seated-file-check.json |
| R34 | 末端接頭收短、保留手動角度與可拆夾蓋；雙頭共同前伸不互撞 | voc | yes | behavior | artifact:electrode-short-head/verification.json,electrode-short-head/red-head-depth.json |
| R35 | 三角平台收至 40 mm 寬，腕軸偏置 22 mm；保留孔周圍材料、閉合及原活動範圍 | voc | yes | behavior | artifact:electrode-compact-platform/verification.json,electrode-compact-platform/red-platform-envelope.json,electrode-compact-platform/red-platform-material.json |
| R36 | 肩部內嵌齒面可阻擋半齒，整前臂退開保持連接並避杯；另驗完整肩齒位及錯誤咬合／偏杯負對照 | engineering | yes | behavior | artifact:electrode-shoulder-teeth/verification.json,electrode-shoulder-teeth/red-shoulder-engagement.json,electrode-shoulder-teeth/red-shoulder-cup-position.json |
| R37 | 雙前臂同側排列並縮減桿件厚度；反向被動軸保持止擋，前傾後能拆裝，分層／夾具五金碰撞／未前傾拆裝皆被拒絕 | voc | yes | behavior | artifact:electrode-coplanar/verification.json,electrode-coplanar/red-forearm-stack.json,electrode-coplanar/red-clamp-bolt-collision.json,electrode-coplanar/red-service-untilted.json,electrode-coplanar/service.png |
| R38 | 腕旋鈕由 10 收至 7.5 mm，五金軸向包絡不超過 24.8 mm，保留 2.5 mm 承壓底；外凸與削薄被拒絕，活動／拆裝不退化 | voc | yes | behavior | artifact:electrode-slim-wrist/verification.json,electrode-slim-wrist/red-wrist-stack.json,electrode-slim-wrist/red-wrist-floor.json,electrode-slim-wrist/wrist-detail.png |
| R39 | 平台被動軸改為可浮動 2 mm 的列印插銷／卡扣，保留退齒、止擋與維修抽出路徑；卡扣缺失與另一頭擋路被拒絕 | voc | yes | behavior | artifact:electrode-slim-wrist/verification.json,electrode-slim-wrist/red-carrier-retainer.json,electrode-slim-wrist/red-pin-service-blocked.json,electrode-slim-wrist/service-file-check.json |
| R40 | 肩部四對承壓面收隙且支座固定，整組前臂保持連接；肩肘同時就座保存檔讀回，未就座宣稱必須拒絕 | engineering | yes | behavior | artifact:electrode-shoulder-seated/verification.json,electrode-shoulder-seated/red-unseated-shoulder.json,electrode-shoulder-seated/seated-file-check.json,electrode-shoulder-seated/arm-seated.blend |
| R41 | 肘保持就座時肩部退齒、剛體轉一齒位與再就座，探頭隨轉、支座及另一頭固定；障礙拒絕且終點存檔讀回 | engineering | yes | behavior | artifact:electrode-shoulder-transfer/shoulder-transfer.json,electrode-shoulder-transfer/red-shoulder-transfer-blocked.json,electrode-shoulder-transfer/transfer-file-check.json,electrode-shoulder-transfer/transfer-end-pH_temp.blend |
| R42 | 腕部 24 齒定位、2 mm 退開與隨平台計算維修角；整齒通過／半齒及錯角拒絕，實際間隙和保存檔讀回 | engineering | yes | behavior | artifact:electrode-wrist-seated/verification.json,electrode-wrist-seated/red-wrist-half-index.json,electrode-wrist-seated/red-wrist-off-index.json,electrode-wrist-seated/wrist-release-file-check.json,electrode-wrist-seated/wrist-released.blend |
| R43 | 腕部四接面同時就座，調整後可重鎖，肩轉位保持腕部貼合 | engineering | yes | behavior | artifact:electrode-wrist-seated/verification.json,electrode-wrist-seated/red-unseated-wrist.json,electrode-wrist-seated/red-wrist-seating-blocked.json,electrode-wrist-seated/seated-file-check.json,electrode-wrist-seated/service-seated-file-check.json,electrode-wrist-seated/transfer-file-check.json,electrode-wrist-seated/wrist-seated-detail.png |
| R44 | 四件可換導線夾隨正確連桿移動，通道與止擋實測，運動／拆卸無碰撞；缺件／穿桿／裝錯桿拒絕 | engineering | yes | behavior | artifact:electrode-guides/verification.json,electrode-guides/guide-controls.json,electrode-guides/guide-file-check.json,electrode-guides/guide-detail.png |
| R45 | 通道同側而桿身中心保留；反轉實際通道網格拒絕，孔壁／止擋／動作與保存檔仍驗；不含線材路徑資格 | engineering | yes | behavior | artifact:electrode-guides-aligned/verification.json,electrode-guides-aligned/guide-controls.json,electrode-guides-aligned/guide-file-check.json,electrode-guides-aligned/guide-detail.png |
| R46 | 同一產生器讀取不可變配置，夾座／探頭／杯位由資料驅動；重建不累積偏移，腕部接口與另一頭不變 | engineering | yes | behavior | artifact:module-configurations/configuration-readback.json,module-configurations/baseline.blend,module-configurations/cable-clearance.blend |
| R47 | 共用線路邊界／候選／實體檢查；保守取樣包絡、端面接觸限定、穿入／自接觸／線徑放大拒絕，案例變更只換資料；不含整束線與材料資格 | engineering | yes | behavior | artifact:route-engine/engine-verification.json,route-engine/capillary-0.png,route-engine/capillary-100.png |
| R48 | 測試以資料＋共用執行器＋獨立配件重用，失敗必清理且完整覆蓋；不擴大資格範圍 | engineering | yes | behavior | artifact:route-engine/engine-verification.json,route-engine/modular-equivalence.json |
| R49 | 登錄測試經共享MCP／REST服務執行，逐例證據完整且恢復目前場景；未知名稱／程式碼／缺模型拒絕 | engineering | yes | behavior | artifact:route-engine/mcp-verification.json |
| R50 | 三條探頭端線路共同避碰，兩條線的半徑及取樣餘量均納入；工作／單頭抬高分開驗證，穿越與故意阻擋線被拒絕 | engineering | yes | behavior | artifact:route-engine/engine-verification.json,route-engine/mcp-verification.json |
| R51 | 三條線各自串接底座／跨肘／探頭端，同線接點及方向一致並拒絕跨段自碰，異線全部區段共同避碰；三個離散姿態，不含連續變形或接口實體 | engineering | yes | behavior | artifact:route-engine/engine-verification.json,route-engine/mcp-verification.json,route-engine/chain-working.png |
| R52 | 同一曲線分支於兩頭各11升降姿態維持定長與淨空；兩端淨空的中途方塊反例須拒絕；固定步距不宣稱連續掃掠 | engineering | yes | behavior | artifact:route-engine/engine-verification.json,route-engine/mcp-verification.json,route-engine/motion-pH_temp-050.png |
