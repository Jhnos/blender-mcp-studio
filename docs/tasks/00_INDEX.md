# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **任務與基線：** 任務16 ACTIVE，任務17階段1 AWAITING-ACCEPTANCE；基線 `dd42682`／V01.0T.003。V01.0T.004封存範圍為配對齒面規劃與內部原件研究，整機尚未驗收。原交付仍由共用 `ArtifactCatalog` 讀 `models/lab-station/model-spec.json` 選v80，原模型／69 STL／3MF不改，未發布研究候選或啟動列印。逐輪來源、失敗配方及研究證據保留於 [本輪前史](../archive/2026-10-27-contact-study-checkpoint.md) 與 [前輪快照](../archive/2026-10-27-screen-control-checkpoint.md)。
- **正式變更：** 純幾何 `serrated_contact_plan` 共用齒面週期三角分割，原頂點／非接觸面保留；14領域控制、鄰近23測試、Ruff／mypy通過。真機fixture加入既有齒槽閘門，正常就座／不同對角線／過行程正反例通過。初次靜態CI發現嵌入字串專案import未明確載入，已修正來源推導模組閉包，19守衛及fixture重跑通過；完整靜態session32248 exit0（Python1569／Web）。不得豁免該守衛。
- **本輪核心CI終態：** session32844 exit0，PID81232已消失，`tmp/current-native-qualification/ci-contact-real.log` 列 `CI PASSED — all selected hard gates green`。T1／T2與全部選定T3通過，對話未選取。新MCP報告11套46項與5控制皆真；選定v80正例run `9b2adc7f39924638bab73f3084b09c38` 69件0幾何失敗／1盤切片與封裝通過，反例 `f6df960077b0466f9522d581ef0aca20` 在截斷chassis STL geometry拒絕、未進print。536來源／VERSION指紋與檔案集合重核相同，104原交付SHA相同。核心執行來源已核對，後續改動另起版本；session71158 exit0，公開catalog／schema example／本機選版相同、正反例報告與服務持久化檔逐值相同（`contact-final-public-readback.json`）；按選版根目錄SHA清單唯一native恢復144／113／0庫、原檔SHA不變（`contact-final-native-restoration.json`），公開health connected（`contact-final-public-health.json`）。正式API PID80453、Blender唯一socket PID79738，埠位見 [runtime SSOT](../10-runtime-ssot.md)；不用再啟真機CI。
- **實際同件修訂：** `tmp/current-native-qualification/isolated-clamp-source-study/` 配方僅原back左端R3避空與原Lid小倒角止擋兩步；其他111網格點面完全相同。另存重開144物件／113網格嚴格CGAL／0庫／0無效driver，兩STL獨立讀回及50就座狀態通過；原對角線與0.21mm過行程反例拒絕。SHA及詳細報告在該目錄；無新列印零件。失敗的右側圓形頭部凹孔／填孔重切試驗保留，勿再盲調相位／求解器。
- **目前可操作候選：** `tmp/current-native-qualification/isolated-clamp-endstop-operation-study/screen-same-part-endstop-operation-study.blend` SHA `016fb81a7c87cead15d6c05be21bb8b277a33d25a72b32176e995aef131e898a`。沿用ScreenFoldSpec／rig.driver及原4五金身份；release2.2／screw2.4讓body到X2.0。session35070已終態，存檔重開404讀回最大4.89e-6mm／9.47e-7rad；缺隨行轉角／間隙兩反例拒絕。兩STL與前一操作候選逐位元相同，109非五金網格不變。session31785表面檢查exit0，只有nut/back及0、60°就座齒面接觸；session6951分類exit0，三案例完整面分離與雙向全頂點內含檢查通過（0.001mm數值帶，姿態誤差另計），無其他接觸pair。`stop-overtravel-controls.json` 是實際保存面5角度X2.0無交叉／X2.1撞止擋正反例，未證明整機連續或實體配合。session55566預覽exit0，`preview-readable/{working,folding,stowed}.png`已檢視，原native SHA不變；首次預覽檢查Addon collection用法失敗，已更正keys，原失敗log保留。
- **完整STL研究包：** `isolated-clamp-endstop-operation-study/complete-stl-study/` 與同目錄 `同原件-69件STL-螢幕止擋研究.zip` 已完成69檔嚴格CGAL及ZIP讀回；67原檔逐位元相同，僅back／Lid改動，provenance列完整來源與SHA。無新3MF；不是免修面或印製資格交付。預覽僅調渲染材質／燈光，未儲存修改native。文件5S175通用候選；本輪重寫索引誤複寫socket埠被DCC擋下，改連runtime SSOT後16例通過，`contact-final-docs-recheck.log`。
- **補充完整內含檢查與封存閘門：** `noncontact-containment.json` 覆蓋404姿態／106實體網格／14628非接觸候選對／29256雙向連通殼查詢，內含及邊界0；572個已分類接觸pair-state另由完整面及全頂點證據驗證。僅取樣名義資格。最終完整靜態session6016 exit0，`contact-final-static.log` 的T1／T2全部通過；新教訓對應既有真機正反例，不留只寫文件的處方。封存依本輪commit、checkpoint checker與推送留證；全球目標仍ACTIVE。
- **硬體與資格界線：** 右側標準M5×35因光桿不足拒絕，40規格名義包絡及外螺母完整牙段提案通過；較矮頭部的完整製造公差／右端8mm外露保護與工具空間仍未完成。軟體fold demo尚無全部可鎖定目標角度介面。候選是研究檔，不是共用MCP修訂能力、完整STL包或新3MF，不能宣稱免修面／負載／製造驗收。詳細尺寸／控制證據保留前史與原JSON。
- **下一個實作：** V004完成checkpoint後，把原件修訂配方、五金角色及導程約束納入共用AppRuntime服務與窄port，先RED再GREEN；沿用既有規劃／幾何／檢查器，不交付忽略目錄研究腳本。正式能力須經REST／MCP同服務驗證、另存原生檔與完整同組STL後才衍生單盤3MF。新模組前先查GitHub；工具盤點未見直接Blender connector，不另造socket owner。
- **使用者條件與餘項：** 允許拆支撐／brim；不接受鑽孔、研磨、修整配合面，契約已寫任務16。幫浦／微壓／pH前端／供電板及線管外徑未知，已詢問尚未答；繼續不依賴此輸入的N1–N4。雙獨立探頭、雙上／下臂、四點梯形、約200mm、250mL共杯及後開通風不得縮減。歷史V10滑座carrier自交仍須後續修，不能替換目前雙上臂／梯形。完整機構、電路接口、材料、負載與原件單盤列印資格未完，全球目標保持ACTIVE。

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
