# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **目前工作：任務 17 的版本選擇 SSOT 修正（2026-10-26）。** 使用者指出入口仍要記版本，並要求移除這個責任。唯一宣告保留在 `models/lab-station/model-spec.json`；新增注入式應用目錄，domain schema 不含版本，REST／MCP 都可省略 spec 使用目前模型。舊 spec 副本與 v80 實機合約已原樣移到 archive；現行合約只宣告 `selection: current`。不修改模型／STL／3MF。
- **已取得證據：** T1/T2 已通過；替換宣告、缺失宣告不建 job、明確歷史模型、schema 預設值、掃描深度獨立、REST／MCP 預設提交等情境通過。正式介面讀回 JSON／REST／MCP／example 同選 v80，default_available=true，21 工具，預設提交不需 spec，證據 `tmp/current-selection-ssot/live-selection.json`。
- **本輪核心實機結果（2026-10-27）：** 完整核心 CI 全綠（`tmp/current-selection-ssot/ci-real.log`）；目前模型無 spec 正向 run `8007f1d66f724ab191d737c3731bcabe`：69件幾何通過、機構not_applicable、單盤切片與打包通過，保存spec.json與服務選擇一致。截斷STL反例run `6b5507fc839b48f8baaa6a6248738bbd`在geometry失敗。驗證器最後補強另跑53項檢查；最終T1/T2全綠（`ci-final.log`）。正式API已重載，freshness通過（PID 5957）；部署後JSON／REST／MCP同選v80、spec可省略、21工具、Claude報告仍可讀，證據 `post-deploy.json`。
- **Claude Code 實際驗證（2026-10-27）：** 正式 MCP 已Connected，CLI OAuth已恢復；實際Read／MCP讀回目前宣告一致。以原生前景等待選項執行同一個無版本參數的驗證器：53秒、終態PASS、無權限拒絕；正向run `ea52118d364d45ccb68978b200f55b1f`通過69件幾何／單盤切片／打包，保存spec與唯一宣告相等；反例run `533aae19471e470fa8e8884fb014d49f`在geometry確實失敗。工具呼叫與實際輸出在 `tmp/current-selection-ssot/claude-core-foreground.jsonl`；已另讀磁碟報告核對。第一次背景驗證被CLI結束中止，不列為通過，後端正向job已確認終態。
- **模型／實體範圍：** 目前交付為v80（沿用v78幾何，69列印件／113原生模型）；原件與根目錄歷史副本保留。spec v1 匯入管線不重驗保存模型的機構；實印、PLA配合、黏附與負載資格尚未完成，不啟動印表機。
- **接手：** 先確認同一個CI進程／handle是否仍在跑，勿並行操作Blender或重啟同一驗證；本輪核心CI與Claude管線均已終態、最終檢查通過，版本V01.0T.000。選版責任已收回應用服務；後續回任務16的整機工程資格與任務17其餘驗收，不需重建原模型或再指定版本。5S掃描175個候選皆以專案連結規則解析成功，DCC無斷鏈／孤兒。舊接手內容完整封存於 [歷史快照](../archive/2026-10-26-resume-history.md)，只在追溯指定事件時載入。

| State | Task | Priority |
|---|---|---|
| ACTIVE | [`17_mcp-complete-pipeline.md`](17_mcp-complete-pipeline.md) | 讓 MCP 完整——階段 1：`ModelSpec` 進、可列印包與機器驗證證據出；第一實例為工作站目前交付件匯入路徑；設計與計畫在 `docs/superpowers/` |
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
