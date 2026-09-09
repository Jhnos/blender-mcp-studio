# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手(2026-09-09,V01.0R.008)

- **等驗收:** 10 參數化產生器接上交付路徑已完成,`--real` 27 條全綠。
  使用者 2026-09-09 選定的三步順序是 **10 → 決定性閘門硬化 → 第四個實例**;
  10 驗收後才動下一步。
- **在等使用者的:** 07 印 V3 指節試片並量七項(`scripts/analyse_coupon.py --instance hand-v3` 判讀)。
- **接手第一步:** `git log --oneline -5`,然後讀 10 號任務檔的 hand-off 段。
- **閘門只在 Mac 跑**;Windows 端改碼、只 stage 明確路徑。

| State | Task | Priority |
|---|---|---|
| AWAITING-ACCEPTANCE | [`10_generation-delivery-path.md`](10_generation-delivery-path.md) | **參數化產生器接上交付路徑**——port + use case + REST endpoint,走既有 `AppRuntime` 與同一條 socket;sandbox 的豁免鍵在逐字相同的推導字串而非呼叫者;MCP 九項 catalog 未動。`--real` 27 條全綠,交付路徑閘門 5/5 重現已發布的包 |
| WAITING-ON-USER | [`07_hand-v3-coupon.md`](07_hand-v3-coupon.md) | **印一件指節、量七項公差**——幾何側全部完成且真機驗證通過,往下每一件事都要從這一件實體反推。**使用者執行** |
| AWAITING-ACCEPTANCE | [`06_hand-v3.md`](06_hand-v3.md) | 靈巧手 V3:文件樹 21 檔 + 追溯矩陣 22 條;域規格、手指、掌盤、整手、佈局全部做完,兩份真機契約 11/11 全綠,印製包已發布;**實體列印與台架量測未做** |
| AWAITING-ACCEPTANCE | [`05_octopus-hand-v2.md`](05_octopus-hand-v2.md) | 章魚手 V2:角點對齊手臂 + 加強莖 + 瞄準式抓取墊 + 每臂電線孔 + 全面倒角;兩份契約真機全綠,包已發布;實體列印未做,視覺 rubric 未判 |
| AWAITING-ACCEPTANCE | [`04_octopus-hand-v1.md`](04_octopus-hand-v1.md) | 五臂章魚手 V1：五邊形掌盤 + 五隻 V6 萬向臂，兩份契約真機全綠；實體列印未做 |
| AWAITING-ACCEPTANCE | [`03_knowledge-dcc-and-abstraction.md`](03_knowledge-dcc-and-abstraction.md) | docs DCC tree, duplication removed, anti-regeneration gates; `--real` tier green 2026-09-05; only the taste calls remain |
| AWAITING-ACCEPTANCE | [`02_tendon-universal-joint.md`](02_tendon-universal-joint.md) | V6 PIN models checksum-controlled under models/ (PR #4 merged 2026-09-05, `901cb53`); physical print coupon remains |

`WAITING-ON-USER` = 機器側已完成,下一步只有使用者能做(印、量、裁決);它不是 ACTIVE,checkpoint 不會把它當進行中。

Accepted 2026-09-09: [`archive/09_core-boundaries.md`](archive/09_core-boundaries.md) — 核心邊界收債:port 回傳 typed DTO、外部服務與 LLM provider 的 domain error → 502、孤島刪除;使用者「09 可以歸檔」(V01.0R.004)。

Accepted 2026-09-09: [`archive/08_hand-framework.md`](archive/08_hand-framework.md) — 靈巧手框架 M0–M6,使用者 Lane B 通過三張圖,`models/hand-compact/` 已發布(V01.0R.000)。

New tasks start from [`templates/task_template.md`](templates/task_template.md).
Accepted tasks are moved to [`archive/`](archive/). Historical feature campaigns are under
[`../archive/`](../archive/) and are not active work.
