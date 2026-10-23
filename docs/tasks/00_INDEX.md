# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **v80共用入口整合（2026-10-23）：** `models/lab-station/model-spec.json`為共用選擇，正式交付由原manifest105個允許檔案逐位元複製至 `models/lab-station-v80/` 並納Git；根目錄v78/v79/v80原件不覆寫。MCP default_spec／describe例子／v80實機合約由T2鎖定一致，預設缺失不退回歷史版；正式FQDN讀回default_available=true且v80第一筆。3MF上限按實測23143845 B的5倍更新，Git blob全雜湊與原件一致，-text屬性避免CSV換行轉換。v80獨立正式MCP閘門52秒PASS，正向run `56f7c17ccfc04ef3addba0f86c72c4be`（import→geometry69通過→機構not_applicable→單盤print→package），截斷STL反例run `d7b51cbc578c4deb890820880765e4c3`在geometry正確FAILED；原檔未改，未啟動列印。證據 `tmp/claude-v80-handoff/v80-real-gate.log`、`live-shared-entry.json`，新run證據由MCP get_run_report／run資源讀取，不覆蓋歷史v80證據。T1/T2通過；完整不中斷實機CI已執行但在原有對話前置FAILED：Ollama單token探測600秒未回，日誌 `tmp/claude-v80-handoff/ci-shared-entry-real.log`，不能稱全CI綠；中止後Blender唯讀barrier通過，才跑上述獨立v80閘門。整合版號V01.0S.001。後續為恢復共用Ollama前置後再跑完整實機CI，以及原本尚未實印的黏附／負載資格。

- **Claude交付件入口（2026-10-23）：** 使用正式FQDN的MCP唯讀驗證：21工具，`list_artifacts`可列出v80的69 STL及已切片3MF，v80交付manifest全雜湊核對通過。已補 `docs/verification/lab-station/v80-claude-handoff.md`、可由現行ModelSpec parser接受的 `v80-model-spec.json`，並從CLAUDE.md與工作站導航連入。v80二進位件未納Git，其他clone/worktree不會自動取得；正式管線原範例仍為v78，不把模型幾何v78與切片交付v80混為一談。本次未改模型、未重切片／部署／送出列印，未替使用者向Claude傳訊；Claude端種類／實際連線仍待使用者提供，服務側可見性已證實。

- **正式 MCP／CI 收口（2026-10-21）：** 第八輪完整不中斷 `--real` CI 全綠（52 硬閘門），升版 V01.0R.02I 封存並部署。本輪修掉八個 class：LaunchAgent 漂移閘門誤報、共用 Ollama 排隊被報 unreachable、V10 手臂相切與鏈三角化（CDT `finish_link`）、rotary 偏航 bore 相位、驗證逾時單樣本校準（改為最慢套件 ×5）、共用圓柱改動波及已發布包（`exact_axes` 參數，手部包維持現狀）、Funnel 握手重置重試、API 啟動快照過期（新前置閘門）。pi5 的 `masvis-phase2-agent` 容器仍停著（回復：`ssh pi5 docker start masvis-phase2-agent`）。下一步：`docs/superpowers/specs/2026-10-21-mcp-complete-pipeline-design.md`（讓 MCP 完整的管線設計，含重用普查與分層容器化決定）等使用者裁決第一個實例與切片器位置後展開成任務 17。

- **實際單盤切片（2026-10-20）：** 新增 `雙上臂四點梯形-v80-單盤切片檢查/` 與 `雙上臂四點梯形-v80-已切片單盤與原零件.zip`，原v34/v78/v79不覆寫；69 STL與v78逐位元相同，原生113模型副本亦保留。官方Bambu Studio 02.08.02.61（DMG對官方SHA256通過）離線P2S 0.4／Generic PLA／0.2 mm／紋理PEI 55°C假設；一般snug支撐＋3 mm brim、三牆15%gyroid、首層20 mm/s、單盤69件，return_code 0、warning_message空。保存3MF含一份G-code且與輸出相同，--info重開exit0；69保存網格CGAL通過、拓撲相同、最大座標序列化差0.0000054 mm、無自動修網。獨立G-code讀回69件首層本體、支撐與brim，線寬外緣含圓弧XY約1.136～251.864 mm、床面外0。預估44h15m／1588g，超過單捲1kg；最小旋鈕首層3.79 mm²、長臂22～24 mm²，仍有黏附／直立強度風險、需移除支撐brim，未實印或啟動印表機。樹狀支撐托盤／頂蓋衝突、6mm brim約0.021mm外緣越界及旋鈕平放後新衝突皆保留失敗證據；通過／拒絕閘門在 `tmp/lab-station-slicing-v80/`，未接正式CI、未改MCP或服務、原軟體CI失敗未解除。原廠P2S結尾T65535會觸發CLI原始分析診斷，原樣保留並說明，未作韌體驗證。下一步確認實際材料／底板及足量供料，首層與PLA配合／負載實印驗證；不宣稱免後加工或物理黏附保證。

- **列印排版延續（2026-10-20）：** 新增 `雙上臂四點梯形-v79-列印排版/` 與 `雙上臂四點梯形-v79-單盤排版候選與STL.zip`，v78不覆寫；69件STL逐位元相同。修正12個1.4 mm止扣豎放，全部平放；3 mm零件距離保留，盤邊由6改4 mm，在256 mm單build放齊69件、最高230 mm。解碼3MF CGAL／落地／間距通過，逐三角面對STL一致；舊止扣方向負對照拒絕、新方向通過。新3MF實際幾何預覽已檢視。8支長臂與部分外殼仍直立，支撐／brim未建立；本機無拓竹或Orca切片軟體，未切片／實印／負載驗證，不能宣稱免後加工或完成單次列印工作。試排與唯讀閘門在 `tmp/lab-station-print-layout-v79/`，未改正式MCP、CI或服務；下一必要步驟為實際機型切片及支撐／黏附檢查。

- **最新使用者模型交付（2026-10-13）：** 沿用v34原件，另存 `雙上臂四點梯形-v78/整機-雙上臂四點梯形-v78.blend`；103原模型名稱保留、新增10列印軸／止扣／上臂從動桿，總113模型。四點板接兩上臂／兩下臂，兩個獨立調整；驗證上臂0/7.5/15°、下臂0/15/30°，兩臂交叉加螢幕0/30/60°及後蓋0/45/90°共729姿態：表面交叉、接點失閉、桌面穿入皆0。121影格協同抬出／返回無交叉，三探頭工作高度維持v34、模型杯壁最小約0.75 mm；抬出時水平漂移最大0.000092 mm、探頭高於杯口約20/15 mm。螢幕支承加高6 mm，後蓋需完全取下兩顆旋鈕螺絲再開啟（旁置桌面示意）。69列印STL全部獨立CGAL封閉／自交通過且各為單一實體，44參考STL另外提供；單盤3MF沿用v15模組、逐三角面與當前STL一致、3 mm距離／6 mm邊界／最高230 mm，未切片、無材料／機型設定，未在拓竹軟體實測。本輪沒有改正式MCP生成器或服務，原CI28435失敗未解除，未提交部署。原v34與保留副本仍逐位元一致，v77早期包保留不覆寫。完整包 `雙上臂四點梯形-v78-模型STL與單盤3MF.zip`；研究／唯讀閘門與失敗中間檔在 `tmp/lab-station-trapezoid-v35/`。下一步依v78回饋、切片與PLA配合／鎖緊／負載實驗；不宣稱免支撐或免後加工。模型專用新閘門尚未接正式CI。

- **最新授權與交付（2026-10-07）：** 使用者指定原版前臂關節與從動臂干涉，要求修改既有零件、不得另造列印模型。新檔 `原版前臂干涉修正-v34/原版整機-前臂干涉修正.blend` 保留103模型；A鎖緊件翻至外側、原板修螺母槽並讓螺母跟隨板、原插銷／止扣修軸向間隙。24配對×91影格零表面交叉；26件前臂STL由保存模型直接匯出，獨立CGAL檢查全過。完整59列印件中LCD背殼仍自交；其他探頭／螢幕／走線干涉待修，不宣稱整機可印、未產3MF、未提交部署。既有CI失敗未解除。v31/v33布林結果有失敗STL，v34採各原件通過的切削結果；不可沿用失敗中間版。

- **使用者最新否決（2026-10-07）：** v20 原位列印改型與 v21–v24 整合軸候選皆不採用；使用者要求找回既有留檔。停止幾何修改，不沿用候選。原始 `rear-hatch-closed.blend` SHA-256 仍為 bc23d4bcef5be723189174ee87264ec5687b55732c9828df19434888010c0809；已將它及三點肘部 v3 原檔逐位元一致複製至根目錄 `原始保留版-未修改/`。以下原位列印進度均為被拒候選歷史，不是目前設計方向。

- **被否決候選歷史（2026-10-07）：** 當時改為 PLA 原位列印手臂模組；不與盒體連印，允許輕扳鬆開、少量模組組裝。新候選 `tmp/lab-station-pip-v20/`，公開目錄 `原位列印手臂-PLA-v20/`；舊 v14/v15 與來源 blend 未覆寫。
- **被否決候選的當時驗證：** 共用生成／規格／測試位於 `tmp/lab-station-pip-v16/`，5 個規格測試通過；單臂 6 實體、雙臂 12 實體 STL 經 CGAL 封閉／自交檢查通過，全數落地，45° 下表面篩選零違例。固定上臂的 q=-10..10、r=40..60 每 2° 共 121 姿態無表面交叉，六關節 ±3 mm 共 12 防脫取樣有阻擋。v17 同範圍 23 次碰撞為保留失敗證據，v18 起加大桿距、v20 收起列印姿態。雙臂交錯同盤範圍 x=3..250.62、y=3..253.25、z=0..12 mm；取樣最小距離 2.08 mm。3MF 兩個完整模組物件、單位與網格讀回一致。
- **被否決候選的當時待辦（不再採用）：** 鎖緊螺絲／螺母與彈片預緊、正式盒體及探頭夾頭轉接、獨立探頭角度、肩部全行程、切片與 PLA 實印資格；不能宣稱整機免後加工可用。每支暫擬 3 組 M3 鎖緊五金。STL 已先交付再產生 3MF；這是候選手臂包，不是整機製造包。未改公開 MCP／正式生成器，未提交或部署；下列既有 CI 失敗仍未解除。

- **目前在做（2026-10-03）:** 任務16，共用網格修復與永久獨立CGAL守衛已改碼；完整CI28435於8ec3ed terminal exit1，上游V10 arm readiness失敗。未提交／發布，正式場景已恢復。
- **最近機器閘門:** T1/T2、REST/MCP/chat/readiness/batch、lab fit/lift/clamp全PASS；arm gate抓cap下臂／上臂3退化及下臂2相交。b300eb讀回Blender空閒。副本refine六件均可返回，但f8e62a CGAL仍caplower3／capupper7／pHlower6對自交，未採用此修復。無live工作。
- **下一步:** 追V10上／下臂finish、apply_transform及匯出前後的幾何，修復共用primitive變更對舊消費者的影響；先修實際失敗再重跑CI。ci-surface-preservation.log與20261003-225549-lab-station-arm-parts-same-scene.log保存。全機資格未完，SWIG metadata warnings待處理。

- **等驗收:** 15 場景清單不再只有十個;對話路徑第一次有真機閘門(`--real` 32 條全綠)。下一個是 14 第五個實例。
- 13 已驗收歸檔:對話現在能呼叫本專案自己的產生器。
- **在等使用者的:** 印。工作單已交付——07 的 V3 試片七項,以及 `hand-gripper` 九節。
  **四件包都已發布,四件都沒印過**;下一筆實體資料會是這個專案的第一筆。
- **接手第一步:** `git log --oneline -5`,然後讀最上面那個任務檔的 hand-off 段。
- **閘門只在 Mac 跑**;Windows 端改碼、只 stage 明確路徑。

| State | Task | Priority |
|---|---|---|
| ACTIVE | [`17_mcp-complete-pipeline.md`](17_mcp-complete-pipeline.md) | 讓 MCP 完整——階段 1：`ModelSpec` 進、可列印包與機器驗證證據出；第一實例為 v78 交付件匯入路徑；設計與計畫在 `docs/superpowers/` |
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
