# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **目前：** 任務16 ACTIVE、任務17階段1 AWAITING-ACCEPTANCE。主目錄V01.0T.006的來源識別／來源暫存與取消排空已正式載入；本次提交封存這個階段，不代表原生修訂或整機工程資格完成。歷史開發與失敗逐字保留 [V006交接快照](../archive/2026-10-27-native-source-checkpoint.md)，更早研究只按其連結追溯。
- **本輪完整核心已終態：** 同一session55541 exit0，父60690／末子14919已退出，`tmp/current-native-qualification/native-v006-real.log` 全部T1/T2/T3 PASS。註冊MCP11套與5控制皆真；當輪正例dfad4f94de454c7f8a4da4751fab8744完成69件geometry 0失敗、print／package PASS，實際3MF ZIP只有Metadata/plate_1.gcode；反例edc197aa3018424ab41046fb1ee511c4只走import／geometry並拒絕，未進print。沒有選對話套件，也沒有宣稱Ollama或Claude LLM對話通過。
- **同輪交付閉環：** 679來源／依賴／選版宣告與完整集合逐項相同，104原模型資產SHA皆相同；REST／MCPcatalog／schema例／本機唯一選版相等，default_native獨立本機oracle無差，公開正反report等於持久化檔。`native-v006-final-public-readback.json`與`native-v006-public-check.log`留證；唯一manifest native已恢復144物件／113mesh／active144／0外部庫，raw geometry等於獨立factory來源記錄且原SHA不變（`native-v006-final-native-restoration.json`）。本輪結果不可被005報告代替。
- **Claude與正式頁面：** 既有Claude Code project server blender-mcp-studio解析同canonical HTTP URL，再由標準MCP Client讀回104／69與21工具；`native-v006-claude-config-readback.json`是CLI配置＋實際MCP讀回，不是Claude LLM對話。正式production頁已實讀hashed assets，health connected，browser error／warning0；公開頁面的實際操作與未完成原生修訂不可用配置成功取代。模型仍由models/lab-station/model-spec.json選定v80，不新增入口／fallback。
- **後續開發保留：** 附掛`/Users/bearmacmini/.codex/worktrees/native-revision-service/Blender_MCP_drawer`、branch codex/native-revision-service有未commit V007。它將append／subset-save／原場景核對模組化，factory合成18例／目前v80 17例與新程序reopen通過；新增當次task／scope／逐字腳本授權的19例與鄰近73例通過，完整static15891 exit0。尚未把新authority及native runner接入正式AppRuntime，無新完整修訂STL／3MF，不能宣稱公開修訂完成。研究及來源備份已保留主tmp/current-native-qualification/native-v007-isolation（349＋414檔）；authority本輪材料仍須補存。不要從附掛目錄部署，先以明確diff整合。
- **下一步：** 完成本提交的checkpoint checker／push（同輪終態log在tmp/current-native-qualification，C1–C5以實際結果為準），再將附掛V007重新對齊封存006、檢查diff與核心。真正餘項仍是閉集合原件配方、native executor／來源還原、同一job／lease／REST／MCP、完整原身份STL先於新3MF；IPC逾時不能當作Blender worker已排空。持續goal下暫不切換context，checkpoint後繼續。
- **工程驗收仍開放：** 允許拆支撐／brim，不接受鑽孔、研磨或修整配合面；雙獨立探頭、雙上下臂、四點梯形、約200mm、250mL共杯、折平HMI、後開通風、PLA 0.4／0.2與完整STL先於單盤3MF均保留。頭高與軸向鬆量須耦合，現有±.28樣本不足完整公差；右端8mm保護／工具UX及實際配合／負載／全機連續姿態仍待量化。幫浦、感測器、pH／電源板、線管尺寸已問未答，不重問、不把佔位當尺寸。原檔保留，修訂另存，未啟動實體列印。

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
