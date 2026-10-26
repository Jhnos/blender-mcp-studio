# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **基線與本輪：** `419334c`／V01.0T.002 已提交推送；本輪 V01.0T.003 涵蓋可重用網格重綁與螢幕控制建構元件；提交與checkpoint結果依Git紀錄核對。逐輪研究紀錄已原文搬入 [螢幕控制快照](../archive/2026-10-27-screen-control-checkpoint.md)，前輪證據見 [內含檢查快照](../archive/2026-10-27-native-containment-checkpoint.md)。整機資格未完成。
- **核心終態：** `scripts/ci.sh --real` 日誌 `tmp/current-native-qualification/ci-screen-real.log` 已結束並列 `CI PASSED — all selected hard gates green`；session20088 已釋放、原PID92364消失，沒有重啟。T1/T2、直接整套與正式MCP、切片／封裝均通過；對話未選取。正式 `tmp/lab-station-route-engine/mcp-verification.json` 為本輪新檔，11套46例及5個控制皆真，場景恢復。切片正例 `88fea7e7ab484b87ab6a4146646fc2b3` 通過69件、1盤；反例 `eaadad92d66942eb93296c1f3506a2c4` 在截斷的chassis STL geometry階段失敗，未進切片。
- **來源與正式狀態讀回：** `screen-source-freeze.json` 的533個程式／配置／VERSION指紋及檔案集合均未變；目前交付SHA256清單104檔全部相同。已從共用選版及其唯一原生檔恢復Blender，144物件／113網格／0外部庫，未保存原檔（`screen-final-native-restoration.json`）。公開catalog、schema example與本機唯一宣告相同，正反例報告與服務持久化檔完全相符（`screen-final-public-readback.json`）。原模型、69 STL與3MF仍是v80，沒有晉升研究候選或啟動列印。
- **文件整理：** 長接手原文搬移並連回索引；通用5S掃描175個候選由專案DCC解析規則核對（目錄入口／相對主題路徑），16個DCC正反控制通過、零未解決。`screen-final-5s.log`／`screen-final-docs.log` 保留輸出。
- **新增能力：** `blender_mesh_rebase.py` 保留原始列印座標／拓樸並補償子孫父逆矩陣，覆蓋共享網格、兩上游姿態及中斷回滾。`ScreenFoldSpec` 與窄介面adapter共用五階段名義控制，原場景／存檔append共404正反向姿態通過；曲線映射死區與無效綁定反例接入既有真機閘門。名義控制不是已閉合的實體螺紋／鎖緊機構。
- **已確認的實體缺陷：** 原螢幕左右螺栓頭承壓間隙約5／10mm；兩齒面對角線不同，往左就座0.05mm已交叉。離線同一規劃器只換兩件各384齒面三角形、所有頂點不動，原生／實際二進位STL讀回各50狀態通過並拒絕舊對角線反例；內部兩STL在 `stl-tooth-repair/`，不是完整交付包。連續名義表面路徑與雙側提案實驗通過的界線、所有指標見快照，不得當螺紋或實印合格。
- **下一步：** 本輪建構元件封存後，把離線同件拓樸修復與實際鎖緊配方納入共用註冊能力，另存新原生檔、完整同組STL，最後才衍生新3MF。螢幕先研究單側主動旋鈕＋另一側浮動支承，維持四個原五金身份，不以新增零件掩蓋干涉；尚未實作或驗收。`screen-single-clamp-hardware-plan.json`／`screen-single-clamp-hardware-surfaces.json` 僅四件標準五金參考包絡且CGAL通過，不能作列印件。
- **鎖緊研究的待驗參數：** 實際nut-seat間隙0.15mm（`screen-clamp-datums.json`）；主動側DIN464 M5×30頭徑20／頸徑10／總高11.5／輪高4；被動側反向ISO4762 M5×35頭徑8.5／高5，外置AF8高5防鬆螺母。供應商最小牙長22不保證光桿長，須指定實際光桿≥10mm。暫定body鎖定位−0.2mm、退齒至+2.0mm，左鬆2.4mm；右耳整合1mm止擋、Ø9.5頭部凹孔、Ø5.6功能孔。填舊孔→加止擋→一次切功能孔→頭部凹孔→最後統一齒面分割，每步須嚴格CGAL；不得直接依此未驗參數發布。須補螺紋導程、承壓閉合、軸向保持、裝入路徑／工具空間與全程干涉。
- **使用者界線及餘項：** 允許拆支撐；不接受鑽孔、研磨、修整配合面，已寫任務16驗收，不再詢問。幫浦／微壓／pH前端／供電板與線管外徑未知；先繼續不依賴輸入的N1–N4機構、電路接口、材料／列印資格。歷史V10滑座carrier自交仍待後續修，不能拿它替換雙上臂／四點梯形。任務17階段1等待體驗不代表整機資格完成。

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
