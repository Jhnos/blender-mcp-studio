# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **checkpoint修正：** 008功能提交1be78fc已保留；提交前diff檢查發現archive檔尾空行但命令仍繼續提交，現在以009文件修正版獨立修正，不改寫歷史。後續檢查須使用失敗即停的執行方式。009未改產品程式，核心證據仍明確標為008；載入版號須重驗。
- **正式V008基線與選版：** 主目錄VERSION為V01.0T.009（008程式的checkpoint文件修正）；原模型仍由models/lab-station/model-spec.json唯一選定v80。原模型／STL／3MF保留，沒有公開native revision工具，未啟動實體列印。任務16 ACTIVE、任務17階段1 AWAITING-ACCEPTANCE。
- **V008完整核心證據：** 同一R2 session76740 exit0、父27815已退出，native-v008-r2-real.log全部T1／T2／T3過。正例5cba3e20b4f442f4929ad8a2cb647c04完成69件geometry零失敗與單盤切片／package；反例7cf5dcb0a49e4175918c2769fb557b1c在geometry拒絕，未進print。當輪registered MCP套件及5控制過。698來源及完整population、104原資產前後未變；REST／MCP／schema／本機同v80，公開報告等持久化檔、獨立來源oracle零差。證據在主tmp/current-native-qualification/native-v008-r2-final-public-readback.json及native-v008-r2-terminal.json；不得移用007或008R1結果。
- **V008原態恢復：** native-v008-r2-final-native-restoration.json核144物件／113mesh／active144／0外部庫，raw geometry逐項等原factory；唯一native SHA afe3afec6f72ce3e9ae7209c2736c5d1f409f5778a2d86f0096a3b0ba10edefc未變。當輪MCP報告另存native-v008-r2-mcp-verification.json，SHA2862c8c03d60841bf003c49e69d62c69d316eeb3f33ed8c38d9f3dfc64862534。
- **V008原件與候選交付：** 共用封閉配方只修原Back／Lid，原場景身份／清理及13材料／CGAL階段正反例過；NativeStlWriter交完整69件、67件bytes不變。PlateProject唯一有向面座標綁定、保留原擺位、清舊切片及namespace相容，真Bambu loader與同件真切片過。主native-v008-print-candidate有先交完整STL ZIP、整機native及單盤3MF；3MF SHA62bb2558a93bb530892c920ec6640c09cb66a72f28a1fd2fac4eb1b664815740，同frame69件全部讀回、無略過／床外、支撐與interface／brim存在，估159212秒／1588.28g。此候選未提升為選版，仍非免修面／負載資格。
- **附掛V009：** .codex/worktrees/native-revision-service/Blender_MCP_drawer未commit V01.0T.009，對齊新基線時須再升版以免與主文件修正版混淆。原四件S_SCREEN五金烘焙座標造成188.56mm離軸真RED已修：保留mesh身份，在原controller共用短角度driver補償Y／Z；共用driver先核RNA UTF-8容量，ASCII／多byte超限在曲線建立前拒絕，255-byte邊界可完整保存。真原件5目標與3反例／完整重開2020樣本、最大軸誤差0.00013411mm；generic2020樣本／59控制／5邊界roundtrip過。PreparedNativeRevision由實際factory使用，spec／print target／request／source只擷取一次；35鄰近例及完整static過。sources與多輪實測在主native-v009-controls及guard-supplement，SHA均已核對。
- **V009本輪port守衛：** AppRuntime注入同一lease與LeasedBlenderPort給所有REST／MCP／對話服務；同task重入，外task及繼承context子task拒絕。timeout／送出後EOF／reset／不可解析回覆保留未知完成，取消或未知完成後隔離新修改及排隊者；未送出失敗不隔離。SSE同原則、UTF-8跨封包正常；MCP保留原因、REST busy／unknown皆503。87相關例含真loopback及授權腳本過；第一次static僅兩個import排序失敗，修正後87015完整CI exit0。主native-v009-controls/lease-runtime-supplement保留60檔sources／logs並核SHA，後續補充另存。仍無持久化遠端終態／重啟恢復或公開NativeRunner，不可冒稱公開流程完成。
- **下一步：** 封存V008 checkpoint後備份附掛working bytes再對齊新提交，不從附掛部署。接共享NativeRunner：使用captured context、既有job／STL／PlateProject／SlicingPort、同task lease及RequestScriptAuthority。遠端callback須有nonce／program hash及可信terminal／restoration收據，未知完成持續隔離；啟動處理未終態job。不可以socket timeout或排空本機await當遠端完成，不新增平行job／切片框架。V009須自己的完整核心／公開正反報告／實際新切片及原態恢復。
- **工程範圍保持完整：** 可拆支撐／brim，不可鑽孔、研磨或修整配合面；獨立雙探頭、上下雙連桿、四點梯形、約200mm伸距、250mL共杯、折平HMI、後開通風、PLA 0.4／0.2、完整STL先於盡量單盤3MF。全機連續姿態、公差耦合、支撐移除與免修面、工具UX、載重及實體配合尚待完成；幫浦／感測器／pH與供電板／線管尺寸已問未答，不重問，不以佔位模型當實尺寸。goal仍ACTIVE，checkpoint後繼續，不要求使用者清context。
- **歷史：** 封存前各輪進度與失敗嘗試見[V008交接快照](../archive/2026-10-27-native-v008-plate-project-checkpoint.md)；V007封存commit8203d0c、checkpoint42365 C1–C5過並已push。V008 R1未進T3，CI繼承flag的5失敗已真RED→GREEN修正；R2才是本輪核心證據。歷史handle不可當live，不因觀察timeout重啟實際仍存活的程序。

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
