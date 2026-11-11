# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

目前工程任務是 [16｜雙探頭工作站](16_lab-station.md#hand-off)。本次自動續作已結束，等使用者在新對話指定接續。

- **正式交付**　[共用模型宣告](../../models/lab-station/model-spec.json) 選用 EC78 r4。[操作與列印](16_lab-station.md#ec78-r4-操作與列印) 提供原生檔、78 件 STL 與 P2S 單盤。
- **工程候選**　HMI 前後殼鎖付、542 mm USB 低位路線及三片箱壁試片已有數位證據，候選尚未升格。主專案工程索引為 `tmp/EC78-維修姿態行程-6CDcEn99/README.md`，包含切片檔及可追溯的收據指紋。
- **待驗**　P2S 實印、免修整裝配、固定座抗拔、插頭殘留拉力與實際載重。箱壁試片的三件單盤已通過公開 MCP，估計 6.04 g PLA、21 分鐘。最近一次 30 秒 LAN 探索無公告，未啟動列印。
- **歷史查證**　只有追溯特定問題時，才讀[工程紀錄快照](../archive/2026-11-11-workstation-evidence-history.md)。

| State | Task | Priority |
|---|---|---|
| AWAITING-ACCEPTANCE | [`18_printer-catalog.md`](18_printer-catalog.md) | 印表機目錄：Bambu／Creality 解耦，不預設機器，可選印表機；P2S 用 Bambu Studio、六台 Creality 用 OrcaSlicer，每家一道真機閘門 |
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

[任務模板](templates/task_template.md) · [已驗收任務紀錄](../archive/2026-09-09-accepted-task-receipts.md)

Accepted tasks are moved to [`archive/`](archive/). Historical feature campaigns are under
[`../archive/`](../archive/) and are not active work.
