# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **Verified facts — B正式核心完成：** 主V01.0T.00B，session16045 exit0、父11693已退出；native-v00b-real.log T1／T2／T3全過，未選Ollama對話測試。本輪新正例aac00a9f74e0426e80cbdda0cab868de通過69件geometry零失敗、單盤plate_1.gcode與package；反例704f7a75bfed4cacbc4644532b381431在geometry拒絕，未進print。706來源與完整population、104原資產前後未變；native-v00b-final-public-readback.json核REST／MCP／schema／本機同v80，公開報告逐項等持久化檔、獨立原件oracle零差，registered MCP全套與5項控制通過。
- **原態與載入：** native-v00b-final-native-restoration.json核144物件／113mesh／active144／0外部庫，raw geometry等原factory，原native SHA afe3afec6f72ce3e9ae7209c2736c5d1f409f5778a2d86f0096a3b0ba10edefc不變。選版仍models/lab-station/model-spec.json指定v80，原STL／3MF保留、沒有提升候選或啟動實體列印。B官方冷啟部署與控制復驗、隔離9例、完整source freeze及原始失敗／修復均保留在主tmp/current-native-qualification/native-v00b-*與native-v00a-shared-executor；不以早先008資格冒稱本輪。
- **Open failures — C／D尚未部署：** 附掛codex/native-revision-service已開發共用native job／NativeProductPort／同件STL→3MF→既有切片封裝、公開檔案規則與未知完成恢復；C的107相鄰例、96097完整static與31240全9例隔離factory過，709來源凍結零差。主native-v00c-job-integration保存63份working bytes與341746680-byte原始證據ZIP及SHA。附掛現V01.0T.00D補公開native流程核心gate、禁止驗證器提交後重送、同frame全件面／單盤歸屬與跳過旗標、面拓樸觀測；109相鄰例過，D full static首次僅import排序未過，已修、其餘尚在驗證。D公開正例／本版切片尚未執行，不當作可用資格。所有D來源與tmp/native-revision-v009/native-v00d-*保留；B源與runtime不含這些新行為。
- **Next step：** 完成主B checkpoint／push；先把附掛當前D完整working bytes另存並核SHA，才以mixed reset對齊新B提交，不能覆寫D工作。D檢查過後從附掛逐SHA整合主，再走官方installer冷啟部署，執行本版完整core（含新native公開正反控制／同件真切片）、公開讀回與原態恢復。禁止從附掛部署、禁止在live core中修改來源／VERSION或並行共用Blender。任何新live handle必須寫在這裡，觀察timeout不代表終止。
- **Engineering scope remains open：** v34→v80原零件演進、上下雙連桿、四點梯形、獨立探頭與上臂升降、約200mm／250mL共杯、折平HMI、後開通風／操作UX、最少五金、PLA 0.4／0.2、完整STL先於盡量單盤3MF。可拆支撐與brim，不可鑽孔、研磨或修整配合面。全機連續姿態、配合公差／支撐移除與工具空間、載重與實體配合均須量化，不能以軟體stage passed替代。硬體尺寸已問未答，不重問、不把佔位件當實尺寸；整體goal仍ACTIVE。
- **歷史：** 原逐輪交接已移至[B checkpoint快照](../archive/2026-10-27-native-v00b-checkpoint.md)；V008／009提交1be78fc／7695d4c保持原歷史，A失敗不是B通過證據。這份索引只保留可接手狀態，不再從舊live描述推斷進度。

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
