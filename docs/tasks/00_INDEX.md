# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **目前原生資格調查（2026-10-27）：** 前輪已提交／checkpoint／推送 `817e5a3`（V01.0T.001）。本輪原模型未存檔，`tmp/current-native-qualification/native-structure.json` 保存階層／驅動；98個上下臂組合的孔軸誤差最大0.000158mm，32個主要連桿姿態無表面候選。全機106實體64姿態中，螢幕非15°定位角存在齒面穿透；CGAL確認5°／零退齒有88頂點內含，側移1／2mm的三個角度為零，不能據此宣稱完整退齒路徑合格。背蓋90°有46表面候選、1282頂點無內含，尚須檢查相交三角形與邊界，不能宣稱有穿透或零干涉。
- **本輪來源改動及下一步：** 既有 `mesh_integrity` 重用CGAL保真轉換，新增三態 `bounded_sides`；六個RED後，32個鄰近單元／adapter測試通過；實際原生捕獲資料13筆由共用檢查器重現，證據 `tmp/current-native-qualification/shared-containment-readback.json`。舊單方向射線出現假內含，不作本次原生判準。所有暫態變換已finally恢復；候選退齒移動尚未存成新版本，也未變更目前交付宣告。共用分類器完整回歸已通過，下一步完成提交與checkpoint，再將原生螢幕完整退齒／旋轉／就座操作做成既有契約流程的可重複案例、另存修訂，覆蓋全機碰撞及原件一致性後才考慮晉升。實印與材料資格仍未完成。
- **等待期間的離線進展：** 未操作Blender；以已捕獲的原件座標再取樣，背蓋90°的2668點最大內含深度0.000004424mm，低於0.001mm判讀界線；89.9°無內含，過轉90.1°有569點超界、最大0.007948mm，證據 `tmp/current-native-qualification/rear-boundary-positive-negative.json`。螢幕退齒2mm→旋轉→就座103姿態×3446頂點無內含，`tmp/current-native-qualification/screen-release-path-vertex-samples.json`；只支持可行候選，不含完整表面／五金／連續路徑資格。原生操作N1–N4已補入 [操作情境](../verification/lab-station/04-scenarios.md)，S1–S7明列歷史研究；下一步沿用這些契約修正原件另存新檔，仍不晉升目前選版。
- **離線補驗的邊界：** 原列印STL與捕獲原生點雖同為3446頂點，但極短邊令最近點匹配有歧義（最小次近距離0.000007983mm），嚴格匹配控制已拒絕，`tmp/current-native-qualification/reconstruct_screen_stl_pose.py` exit1；不放寬匹配條件，也不把近似重建升格為原生完整表面驗證。待同一CI終態後，直接從原生檔捕獲三角面／矩陣及全部五金再驗。驗證文件已移除完整T3約85秒的過時估時，不能因此誤判目前程序停止。
- **本輪核心CI已終態通過：** `scripts/ci.sh --real` session58281／PID76152 exit0，日誌 `tmp/current-native-qualification/ci-real.log`；T1/T2、研究直接46例、正式MCP11套46例與5控制、每套場景還原、模型重現與目前交付切片全過。正向run `217452aba52a474ca002188a6130f2ba`（69件幾何／單盤切片／打包），截斷STL反例run `909e88a200c649e590735cd8de693911` 在geometry拒絕。公開MCP證據 `tmp/current-native-qualification/final-public-readback.json`；原生模型已按選版與發布SHA恢復，144物件／113網格／0外部庫、未另存，`tmp/current-native-qualification/restored-native-readback.json`。沒有仍在執行的Blender驗證，來源V01.0T.002；提交前CI亦exit0（`tmp/current-native-qualification/ci-final-seal.log`），正式UI已連線並顯示原件、刷新成功／console零錯誤／production雜湊資產，畫面 `tmp/current-native-qualification/formal-ui.png`；5S175候選全部按實際DCC解析消解，零未解決（`tmp/current-native-qualification/5s-final-triage.json`）。本里程碑V01.0T.002封存後，直接捕獲原生完整網格與五金、接續N1–N4。對話T4本輪未選取。

- **前里程碑參照（任務16）：** 螢幕背殼來源／實際STL修復已完成技術驗證，版本V01.0T.001；核心與提交前CI均已通過，正式介面讀回完成；本里程碑提交後接續機構資格。下一步先核對共用服務選定的原生模型與原零件，不能拿研究模型的綠燈代替交付件資格。
- **前里程碑已驗證：** 完整 `scripts/ci.sh --real` exit0，日誌 `tmp/lcd-source-boolean/ci-final-candidate.log`。30來源階段、64探測、2實際STL；精確CGAL守衛覆蓋目前69個原STL與壓扁面反例。正式MCP11套46例、5控制及場景恢復全過，獨立讀回 `tmp/lcd-source-boolean/third-mcp-readback.json`。新CI前置防線與完整文件連結檢查通過。對話T4本輪未選取，不宣稱本輪實機對話通過。
- **目前模型：** 仍為v80、原件與歷史副本保留；共用應用服務讀唯一宣告，客戶端不選版本。原生模型已按發布SHA載入且未另存：144物件／113網格／0外部連結庫，正式MCP讀回144物件且未截斷，證據 `tmp/lcd-source-boolean/selected-native-readback.json`／`tmp/lcd-source-boolean/public-selected-scene.json`。此為前里程碑的原生場景讀回；本輪CI執行時會切換研究場景，終態後必須依共用服務選版與發布SHA恢復原生檔，不另存或以研究場景交付。
- **前里程碑交付實機管線：** 正向run `a20c5d6b66e14f76bdef8fe294e916cd`：69件幾何／單盤切片／打包通過，mechanism為not_applicable；反例run `bb85a043c35b419089756448923d6fca`在geometry失敗。服務宣告／schema／目錄／保存spec一致，21工具、spec可省略，證據 `tmp/lcd-source-boolean/final-public-readback.json`。Claude Code實際前景執行同一核心閘門的證據保留於前里程碑 `tmp/current-selection-ssot/claude-core-foreground.jsonl`。
- **未完成資格與待輸入：** 實際機構、連續動作、電路接口、PLA配合／黏附／負載及實印仍未完成。免後加工是否允許拆支撐／brim已透過文字選項詢問、尚未回答，不推定接受；幫浦／微壓／pH前端／供電板型號及線管外徑亦未確認。繼續不依賴這些答案的機構與軟體驗證，不啟動印表機。
- **來源待修（交付機構之後）：** V10研究manifest列出的29個試配STL中，27個精確CGAL通過；兩個舊滑座carrier自交，證據 `tmp/lcd-source-boolean/prototype-raw-audit.json`。它們不是目前v80的69件；不遺忘此來源問題，也不以舊滑座取代使用者要求的雙上臂／四點梯形結構。
- **接手與歷史：** 前里程碑CI及所有排空barrier均已終態；目前進程以本索引上方本輪紀錄為準。正式UI已確認已連線、目前交付模型可見、刷新預覽成功、console零錯誤、載入production雜湊資產，畫面 `tmp/lcd-source-boolean/formal-ui.png`。提交與checkpoint後核對原生機構；不要重跑已通過的大套件。失敗／修復／CI中止原因保留於 [本輪快照](../archive/2026-10-27-lcd-source-validation-history.md)，原任務長交接在 [工作站歷史](../archive/2026-10-27-lab-station-handoff-history.md)。任務17階段1已完成量化驗收，等待使用者體驗，尚未歸檔；後續階段仍屬全體目標。

| State | Task | Priority |
|---|---|---|
| AWAITING-ACCEPTANCE | [`17_mcp-complete-pipeline.md`](17_mcp-complete-pipeline.md) | 讓 MCP 完整——階段 1：`ModelSpec` 進、可列印包與機器驗證證據出；第一實例為工作站目前交付件匯入路徑；設計與計畫在 `docs/superpowers/` |
| ACTIVE | [`16_lab-station.md`](16_lab-station.md) | 雙探頭量測工作站：250 mL 共杯、約 20 cm 伸距、P2S；獨立電極臂、齒槽與折平螢幕；全機工程資格待完成 |
| AWAITING-ACCEPTANCE | [`15_scene-list-and-chat-gate.md`](15_scene-list-and-chat-gate.md) | **場景清單不再只有十個**——上游 addon 截斷到 10;改由 adapter 有上界地讀,碰到上界會說。H6 綠了,對話路徑第一次有真機閘門;`--real` 32 條全綠 |
| TODO | [`14_hand-long.md`](14_hand-long.md) | **第五個實例:每指三關節**——`joint_count` 第一次建在 2 以外;主要風險是指掌比 |
| WAITING-ON-USER | [`07_hand-v3-coupon.md`](07_hand-v3-coupon.md) | **印一件指節、量七項公差**——幾何側全部完成且真機驗證通過,往下每一件事都要從這一件實體反推。**使用者執行** |
| AWAITING-ACCEPTANCE | [`06_hand-v3.md`](06_hand-v3.md) | 靈巧手 V3:文件樹 21 檔 + 追溯矩陣 22 條;域規格、手指、掌盤、整手、佈局全部做完,兩份真機契約 11/11 全綠,印製包已發布;**實體列印與台架量測未做** |
| AWAITING-ACCEPTANCE | [`05_octopus-hand-v2.md`](05_octopus-hand-v2.md) | 章魚手 V2:角點對齊手臂 + 加強莖 + 瞄準式抓取墊 + 每臂電線孔 + 全面倒角;兩份契約真機全綠,包已發布;實體列印未做,視覺 rubric 未判 |
| AWAITING-ACCEPTANCE | [`04_octopus-hand-v1.md`](04_octopus-hand-v1.md) | 五臂章魚手 V1：五邊形掌盤 + 五隻 V6 萬向臂，兩份契約真機全綠；實體列印未做 |
| AWAITING-ACCEPTANCE | [`03_knowledge-dcc-and-abstraction.md`](03_knowledge-dcc-and-abstraction.md) | docs DCC tree, duplication removed, anti-regeneration gates; `--real` tier green 2026-09-05; only the taste calls remain |
| AWAITING-ACCEPTANCE | [`02_tendon-universal-joint.md`](02_tendon-universal-joint.md) | V6 PIN models checksum-controlled under models/ (PR #4 merged 2026-09-05, `901cb53`); physical print coupon remains |

`WAITING-ON-USER` = 機器側已完成,下一步只有使用者能做(印、量、裁決);它不是 ACTIVE,checkpoint 不會把它當進行中。

Accepted 2026-09-09: [`archive/13_conversation-reaches-the-generators.md`](archive/13_conversation-reaches-the-generators.md) — 對話能產出可印的零件:`list_instances` / `build_instance` 進對話工具清單,與公開九項目錄分離且有守衛;使用者「13 可以歸檔」(V01.0R.012)。

Accepted 2026-09-09: [`archive/12_hand-gripper.md`](archive/12_hand-gripper.md) — 第四個實例三站夾爪:兩指＋對位拇指九節,真機首建 20/14 全過,走產品路徑建成,使用者 Lane B 通過後發布 `models/hand-gripper/`;使用者「12 可以歸檔」(V01.0R.00E)。

Accepted 2026-09-09: [`archive/11_determinism-budget.md`](archive/11_determinism-budget.md) — 碎片預算改由實測支撐:探針擴到所有 `chains` 與 `palm`,實測八個零件只有一個會動、差 2;`--real` 28 條全綠,`models/` 位元組未動;使用者「11 可以歸檔」(V01.0R.00B)。

Accepted 2026-09-09: [`archive/10_generation-delivery-path.md`](archive/10_generation-delivery-path.md) — 參數化產生器接上交付路徑:`POST /api/instances/{slug}/build` 與 `GET /api/instances`,sandbox 的豁免鍵在逐字相同的推導字串而非呼叫者;`--real` 27 條全綠,交付路徑閘門 5/5 重現已發布的包;使用者「10 可以歸檔」(V01.0R.009)。

Accepted 2026-09-09: [`archive/09_core-boundaries.md`](archive/09_core-boundaries.md) — 核心邊界收債:port 回傳 typed DTO、外部服務與 LLM provider 的 domain error → 502、孤島刪除;使用者「09 可以歸檔」(V01.0R.004)。

Accepted 2026-09-09: [`archive/08_hand-framework.md`](archive/08_hand-framework.md) — 靈巧手框架 M0–M6,使用者 Lane B 通過三張圖,`models/hand-compact/` 已發布(V01.0R.000)。

New tasks start from [`templates/task_template.md`](templates/task_template.md).
Accepted tasks are moved to [`archive/`](archive/). Historical feature campaigns are under
[`../archive/`](../archive/) and are not active work.
