# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **目前工作：任務16目前交付模型的機構資格。** 本輪螢幕背殼來源／實際STL修復已完成技術驗證，版本V01.0T.001；核心與提交前CI均已通過，正式介面讀回完成；本里程碑提交後接續機構資格。下一步先核對共用服務選定的原生模型與原零件，不能拿研究模型的綠燈代替交付件資格。
- **本輪已驗證：** 完整 `scripts/ci.sh --real` exit0，日誌 `tmp/lcd-source-boolean/ci-final-candidate.log`。30來源階段、64探測、2實際STL；精確CGAL守衛覆蓋目前69個原STL與壓扁面反例。正式MCP11套46例、5控制及場景恢復全過，獨立讀回 `tmp/lcd-source-boolean/third-mcp-readback.json`。新CI前置防線與完整文件連結檢查通過。對話T4本輪未選取，不宣稱本輪實機對話通過。
- **目前模型：** 仍為v80、原件與歷史副本保留；共用應用服務讀唯一宣告，客戶端不選版本。原生模型已按發布SHA載入且未另存：144物件／113網格／0外部連結庫，正式MCP讀回144物件且未截斷，證據 `tmp/lcd-source-boolean/selected-native-readback.json`／`tmp/lcd-source-boolean/public-selected-scene.json`。Blender顯示目前交付的原模型，並非CI研究場景。
- **目前交付實機管線：** 正向run `a20c5d6b66e14f76bdef8fe294e916cd`：69件幾何／單盤切片／打包通過，mechanism為not_applicable；反例run `bb85a043c35b419089756448923d6fca`在geometry失敗。服務宣告／schema／目錄／保存spec一致，21工具、spec可省略，證據 `tmp/lcd-source-boolean/final-public-readback.json`。Claude Code實際前景執行同一核心閘門的證據保留於前里程碑 `tmp/current-selection-ssot/claude-core-foreground.jsonl`。
- **未完成資格與待輸入：** 實際機構、連續動作、電路接口、PLA配合／黏附／負載及實印仍未完成。免後加工是否允許拆支撐／brim已透過文字選項詢問、尚未回答，不推定接受；幫浦／微壓／pH前端／供電板型號及線管外徑亦未確認。繼續不依賴這些答案的機構與軟體驗證，不啟動印表機。
- **來源待修（交付機構之後）：** V10研究manifest列出的29個試配STL中，27個精確CGAL通過；兩個舊滑座carrier自交，證據 `tmp/lcd-source-boolean/prototype-raw-audit.json`。它們不是目前v80的69件；不遺忘此來源問題，也不以舊滑座取代使用者要求的雙上臂／四點梯形結構。
- **接手與歷史：** 本輪CI及所有排空barrier均已終態，沒有應接續的Blender驗證進程。正式UI已確認已連線、目前交付模型可見、刷新預覽成功、console零錯誤、載入production雜湊資產，畫面 `tmp/lcd-source-boolean/formal-ui.png`。提交與checkpoint後核對原生機構；不要重跑已通過的大套件。失敗／修復／CI中止原因保留於 [本輪快照](../archive/2026-10-27-lcd-source-validation-history.md)，原任務長交接在 [工作站歷史](../archive/2026-10-27-lab-station-handoff-history.md)。任務17階段1已完成量化驗收，等待使用者體驗，尚未歸檔；後續階段仍屬全體目標。

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
