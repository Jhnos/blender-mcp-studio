# v4 — 場景矩陣

> 回導航 [[hand-framework/v0-INDEX]] · 相關 [[hand-framework/v2-hypotheses]]、[[hand-framework/v5-fixtures]]

每個場景是「對一組夾具施加一個受控變數」。**只變一個**,其餘固定。

## 純規劃層(T2,任何機器)

| ID | 假設／失效 | 受控變數 | 步驟 | 判準 |
|---|---|---|---|---|
| SF-1 | HF-2 / FF-8 | 無 | 對 `hand-v3` 跑契約生成器 | 輸出 `json.loads` 後 == 簽入的兩份 JSON |
| SF-2 | HF-6 | 零件 footprint 清單 | `LayoutPlan.pack()` | 四件佔地 242.0 × 103.5;第五件(再一個掌盤)換行成 242.0 × 217.0 |
| SF-3 | FF-10 | 指列數 4 → 3 | `ExpectedCounts` | 站台少一、掌寬少一節距 |
| SF-4 | FF-13 / HF-5 | 拇指凸出 22 → 23 | 建掌盤 | 23 被拒;22 通過且所有既有數字不變 |
| SF-5 | HF-4 / FF-15 | 力矩臂 (6.6,6.6) → (5.5,3.6) | `PhalanxPlan` | 零件號數 1 → 2 |
| SF-6 | FF-9 | 執行模組的 import 圖 | 靜態掃描 | 每個可達模組都在 `reload_modules` |
| SF-7 | FF-11 | 無 | 掃 `scripts/hand_*.py` 的字面值 | 只有 `0.0`、`1.0`、`0.001` |
| SF-8 | FF-12 | 兩個實例 | 一致性套件 | 前綴互異 |
| SF-9 | FF-3 | 無 | 母數守衛 | 五份文件宣告 = 產生器前綴 |

## 真機(T3,Mac 上的常駐 Blender)

| ID | 假設／失效 | 受控變數 | 步驟 | 判準 |
|---|---|---|---|---|
| SF-10 | HF-1 / FF-14 | 無 | 新產生器建 `hand-v3` 到 `tmp/`,對 `models/hand-v3/manifest.json` | 四 STL 面數精確、尺寸 ±0.1 |
| SF-11 | HF-1 | 無 | 兩份 V3 契約 | 20 項與 14 項全 PASS |
| SF-12 | HF-3 | 換連桿 | `hand_compact.json` + `hand_compact_finger.json` | 全 PASS |
| SF-13 | HF-7 | 無 | `ci.sh --real` 首跑 | 記錄秒數;> 10 分鐘則觸發 D-004 的另一半 |
| SF-14 | FF-17 | 每個新閘門 | 餵已知會紅的輸入 | 真的紅 |

## 文件(T2)

| ID | 失效 | 步驟 | 判準 |
|---|---|---|---|
| SF-15 | FF-1 | 圖表守衛 | 實例表每個數字 = 規格算出 |
| SF-16 | FF-2 | ref 守衛 | 非 `TODO_` 的 ref 都解析得到;`TODO_` 名字不在程式碼裡 |
| SF-17 | FF-16 | checkpoint | 唯一 ACTIVE 是 `08`,且在最後一個 commit 被更新 |
