# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **目前里程碑：** V01.0T.005核心完整通過，正在封存本輪控制與文件；整機工程資格仍ACTIVE。新增不可變螢幕鎖緊規格與共用Blender綁定器，五目標角、2020正反／save-read姿態與49拒絕控制通過；浮點儲存／實際RNA顯示解掉截斷與一步滯後。原件家族與逐輪失敗留在 [V005前史](../archive/2026-10-27-clamp-control-checkpoint.md)，不重建已完成工作。
- **V005核心終態與原檔：** session84103 exit0，父PID71127已終止，`tmp/current-native-qualification/clamp-shared-real.log` T1／T2／全部選定T3 PASS，對話未選取。新MCP註冊驗證各控制皆真，正例run `8ba88961a2c04bc0893e5c30bf848498`：69件幾何0失敗、實際3MF ZIP僅plate_1.gcode、封裝通過；反例 `dbc0324238ac40e7a1f56cb43846632d` 截斷STL於geometry拒絕且未進print。540來源及其檔案集合與freeze逐項相等；104原交付SHA相等，公開REST／MCPcatalog／schema例／本機選版相同，公開正反報告與持久化檔相同（`clamp-final-public-readback.json`）。按宣告manifest唯一native恢復144物件／113網格／0外部庫，原SHA仍afe3afec6f72ce3e9ae7209c2736c5d1f409f5778a2d86f0096a3b0ba10edefc（`clamp-final-native-restoration.json`）。checkpoint前不需重啟真機CI；再跑靜態與DCC封存文件即可。公開讀回私有診斷首次誤用不存在print.plate_count欄位已失敗保留，改讀既有verifier指定的3MF ZIP獨立計plate，不改驗收條件。
- **後續服務隔離開發：** 已附掛 `/Users/bearmacmini/.codex/worktrees/native-revision-service/Blender_MCP_drawer`，該處V006來源識別／完整來源暫存及NativeRevisionService準備階段已有單元與factory證據；未部署。V005封存後，以新commit調整其基線，保留全部V006變更，再用明確diff整合回本主目錄；不得整目錄覆蓋、混用兩輪證據或保留永久雙選版來源。模型修訂／完整同組STL後3MF仍未完成，不能將prepare_source當公開修訂能力。
- **等核心期間新增公差證據：** `tmp/current-native-qualification/head-height-coupled-contact-study/` 有三頭高各27正例共81姿態，6個前後越界控制皆被原前／後殼拒絕；三組雙向連通殼內含各270查詢皆0。`continuous-envelope-proof-02.json`以連續頭高／相依float與角度／body行程的保守包絡，補0.0001mm外向數值量及STL後圓包覆核對，6個完整面／雙向全頂點配對通過、3錯置包絡反例拒絕（前後殼>0.0001mm、固定Lid>0.01mm）。它取代初版local／fixed-Lid證明。`independent-extremes-negative-control.json`證明k3.35可用的f=-0.649，不能給k3.65共用，實際撞前後殼。仍非徑向／轉動鬆量、螺紋、實印公差、完整其他機構運動、工具與負載資格；目前±0.28控制尚未改成相依限制。






- **V005等核心期間的公差核對：** `screen-hardware-head-tolerance-review.json` 引NuFast ISO4014原廠圖M5頭高3.35..3.65與既有口袋名義面70.85..75.15，推得相對原underhead74.85的頭高相依浮動範圍[k-4,0.30]mm，聯集約[-0.65,0.30]，目前±0.28名義範圍不足，已拒絕完整公差資格；不可用獨立Cartesian極值代替相依限制。按這些名義假設，40規格Ls_min20光桿裕量約0.99999mm、35仍拒絕。口袋面來源只是既有CAD射線見證，非全口袋／實印證書。Böllhoff DIN986 M5封帽螺母表已查，但保證內部盲牙深度未建立，尚不接受為右端保護解法。全部在離線資料計算，未改540凍結來源；V005封存後要補頭高／間隙耦合限制、實際原面控制及端部UX，與共用原件修訂服務同屬必要餘項。
- **正式交付基線：** 共用ArtifactCatalog仍選 `models/lab-station/model-spec.json` 的v80；原native／69 STL／3MF未改，未發布研究候選或啟動列印。V004完整留證原文已搬到 [歷史快照](../archive/2026-10-27-contact-study-checkpoint.md#v004封存結果由任務索引搬移)，不作本輪替代證據。
- **下一個實作：** V005完成完整核心驗證與checkpoint後，把原件修訂配方、五金角色及導程約束納入共用AppRuntime服務與窄port，先RED再GREEN；沿用既有規劃／幾何／檢查器，不交付忽略目錄研究腳本。正式能力須經REST／MCP同服務驗證、另存原生檔與完整同組STL後才衍生單盤3MF。新模組前先查GitHub；工具盤點未見直接Blender connector，不另造socket owner。
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
