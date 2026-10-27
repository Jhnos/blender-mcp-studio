# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **目前：** 任務16 ACTIVE；任務17階段1 AWAITING-ACCEPTANCE。正式主目錄V01.0T.007，模型仍由models/lab-station/model-spec.json唯一選定v80。原模型／69 STL／3MF均保留，無公開native revision工具；沒有啟動實體列印。
- **V007里程碑證據：** 同一session65198 exit0，父31268與registered子65415已退出，native-v007-real.log全部T1/T2/T3 PASS。當輪正例6fe2616942ea4966b8993ce512810d78完成69件geometry零失敗、單盤真切片及package；反例022f4d17c6b24fa5a20210d5e0fcc261在geometry拒絕且未進print。registered MCP11套及5控制通過。685來源與完整集合、104原資產均逐項未變；公開REST／MCP／schema／本機選版相同，獨立來源oracle零差，公開正反report等於持久化檔。主tmp/current-native-qualification/native-v007-final-public-readback.json、native-v007-mcp-verification.json為當輪證據，不移用V006 run。
- **V007原場景恢復與邊界：** 最後已恢復唯一manifest native（SHA afe3afec6f72ce3e9ae7209c2736c5d1f409f5778a2d86f0096a3b0ba10edefc），144物件／113mesh／active144／0外部庫，raw geometry與獨立factory來源逐項相同；native-v007-final-native-restoration.json留證。原態保存及逐task授權已通過本輪核心，NativeRunner／AppRuntime注入／同job全流程尚未完成，不能稱公開原件修改已交付。完整舊交接逐字保留[里程碑快照](../archive/2026-10-27-native-v007-scene-lifetime-checkpoint.md)。
- **V008附掛開發：** /Users/bearmacmini/.codex/worktrees/native-revision-service/Blender_MCP_drawer，branch codex/native-revision-service，未commit V01.0T.008；基線仍33c851f，含未封存007。先備份所有working bytes再對齊本次007提交；只從主目錄正式部署。原件screen-clamp閉集合配方重用既有Boolean／CDT／rebase，只修改原Back避空與原Lid止擋；原場景與保存重開／13材料與CGAL階段／三個拒絕控制通過，仍144／113；完成69 STL，67件bytes不變，只有原Back／Lid新export。完整ZIP已先交付，主native-v008-isolation/evidence/all-final/none/same-parts-screen-clamp-69-STL.zip，SHA6c49be3d70dfe535e5636b59180a0dfc8e171e81870daf883cab91ec570d90e7。不得以爆炸空間擺放代替列印配置。
- **V008模組化與檢查：** 該附掛的資料API修訂明確collection／depsgraph，避免operator落原window；window=None曾在獨立worker crash139，證據保留且禁止重試。19／18 lifetime與full STL factory已過；原STL／3MF綁定以唯一正向換軸、頂點雙射及完整有向三角面集合核對，原Back／Lid誤差小於0.000006mm，18例含拒絕控制已過。all-binding-frozen／20734 exit0，696來源前後完全相同；static43279 exit0。主native-v008-isolation已保留1981檔＋plate-binding-supplement749檔，均核SHA；新PlateProject正在附掛開發，尚須完成同一模組＋實際新3MF切片驗證，較新進度不能由這些舊報告推定。
- **封存檢查：** 首次seal-static因archive快照搬移後的18個相對連結失效而失敗；原文精確副本保留native-v007-index-prearchive-exact.md，只修正新快照的相對連結。65804 seal-static-links-fixed完整exit0、links／DCC17過、git diff --check過；5S指示檔77／16行、project skill150行。
- **下一步：** 封存V007後，先保留V008 working bytes並對齊新基線；接續同原件69 STL生成去除舊Gcode／預覽的3MF，再以既有SlicingPort真切片。原件NativeRunner仍須綁validated request、一次captured ModelSpec／print target／source receipts、共享AppRuntime／job／lease與同task grant；IPC timeout不能當遠端worker terminal，須有完成／恢復證據才釋放或隔離lease。
- **完整工程範圍不縮減：** 可拆支撐／brim，不可鑽孔、研磨或修整配合面；雙獨立探頭、上下雙連桿、四點梯形、約200mm伸距、250mL共杯、折平HMI、後開通風、PLA 0.4／0.2、完整STL先於盡量單盤3MF。全機連續姿態、公差耦合、右端8mm工具UX、載重與實體配合尚待驗證。幫浦／感測器／pH與供電板／線管尺寸已問未答，不重問，不以佔位模型當實尺寸。持續goal仍ACTIVE，checkpoint後繼續，不請使用者清context。

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
