# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手(2026-09-09,V01.0R.00D)

- **等驗收:** 12 第四個實例 `hand-gripper`(兩指＋對位拇指,三站九節)。真機首建即 20/14 全過,
  走**產品路徑**建成,使用者 Lane B 通過,`models/hand-gripper/` 已發布,`--real` 31 條全綠。
  機器面沒有未完項——剩下的只有實體。
- **在等使用者的:** ①07 印 V3 指節試片並量七項;②`hand-gripper` 也可以印了(九節,佈局 137 × 80.5 mm)。
- 使用者 2026-09-09 選定的三步順序(交付路徑 → 決定性閘門硬化 → 第四個實例)已走完。
  **四件包都已發布,四件都沒印過——下一個真正的資訊只能從印出來的東西來。**
- **在等使用者的:** 07 印 V3 指節試片並量七項(`scripts/analyse_coupon.py --instance hand-v3` 判讀)。
- **閘門只在 Mac 跑**;Windows 端改碼、只 stage 明確路徑。
- **在等使用者的:** 07 印 V3 指節試片並量七項(`scripts/analyse_coupon.py --instance hand-v3` 判讀)。
- **接手第一步:** `git log --oneline -5`,然後讀 10 號任務檔的 hand-off 段。
- **閘門只在 Mac 跑**;Windows 端改碼、只 stage 明確路徑。

| State | Task | Priority |
|---|---|---|
| AWAITING-ACCEPTANCE | [`12_hand-gripper.md`](12_hand-gripper.md) | **第四個實例:三站夾爪**——兩指＋對位拇指,九節。真機首建 20/14 全過,走產品路徑建成;使用者 Lane B 通過,包已發布,`--real` 31 條全綠。**實體列印未做** |
| WAITING-ON-USER | [`07_hand-v3-coupon.md`](07_hand-v3-coupon.md) | **印一件指節、量七項公差**——幾何側全部完成且真機驗證通過,往下每一件事都要從這一件實體反推。**使用者執行** |
| AWAITING-ACCEPTANCE | [`06_hand-v3.md`](06_hand-v3.md) | 靈巧手 V3:文件樹 21 檔 + 追溯矩陣 22 條;域規格、手指、掌盤、整手、佈局全部做完,兩份真機契約 11/11 全綠,印製包已發布;**實體列印與台架量測未做** |
| AWAITING-ACCEPTANCE | [`05_octopus-hand-v2.md`](05_octopus-hand-v2.md) | 章魚手 V2:角點對齊手臂 + 加強莖 + 瞄準式抓取墊 + 每臂電線孔 + 全面倒角;兩份契約真機全綠,包已發布;實體列印未做,視覺 rubric 未判 |
| AWAITING-ACCEPTANCE | [`04_octopus-hand-v1.md`](04_octopus-hand-v1.md) | 五臂章魚手 V1：五邊形掌盤 + 五隻 V6 萬向臂，兩份契約真機全綠；實體列印未做 |
| AWAITING-ACCEPTANCE | [`03_knowledge-dcc-and-abstraction.md`](03_knowledge-dcc-and-abstraction.md) | docs DCC tree, duplication removed, anti-regeneration gates; `--real` tier green 2026-09-05; only the taste calls remain |
| AWAITING-ACCEPTANCE | [`02_tendon-universal-joint.md`](02_tendon-universal-joint.md) | V6 PIN models checksum-controlled under models/ (PR #4 merged 2026-09-05, `901cb53`); physical print coupon remains |

`WAITING-ON-USER` = 機器側已完成,下一步只有使用者能做(印、量、裁決);它不是 ACTIVE,checkpoint 不會把它當進行中。

Accepted 2026-09-09: [`archive/11_determinism-budget.md`](archive/11_determinism-budget.md) — 碎片預算改由實測支撐:探針擴到所有 `chains` 與 `palm`,實測八個零件只有一個會動、差 2;`--real` 28 條全綠,`models/` 位元組未動;使用者「11 可以歸檔」(V01.0R.00B)。

Accepted 2026-09-09: [`archive/10_generation-delivery-path.md`](archive/10_generation-delivery-path.md) — 參數化產生器接上交付路徑:`POST /api/instances/{slug}/build` 與 `GET /api/instances`,sandbox 的豁免鍵在逐字相同的推導字串而非呼叫者;`--real` 27 條全綠,交付路徑閘門 5/5 重現已發布的包;使用者「10 可以歸檔」(V01.0R.009)。

Accepted 2026-09-09: [`archive/09_core-boundaries.md`](archive/09_core-boundaries.md) — 核心邊界收債:port 回傳 typed DTO、外部服務與 LLM provider 的 domain error → 502、孤島刪除;使用者「09 可以歸檔」(V01.0R.004)。

Accepted 2026-09-09: [`archive/08_hand-framework.md`](archive/08_hand-framework.md) — 靈巧手框架 M0–M6,使用者 Lane B 通過三張圖,`models/hand-compact/` 已發布(V01.0R.000)。

New tasks start from [`templates/task_template.md`](templates/task_template.md).
Accepted tasks are moved to [`archive/`](archive/). Historical feature campaigns are under
[`../archive/`](../archive/) and are not active work.
