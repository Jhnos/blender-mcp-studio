# v0 — 驗證計畫導航

> 回導航 [[hand-framework]] · 相關 [[30-verification]]、[[hand-framework/02-requirements]]、[[hand-v3/v0-INDEX]]

這是框架的驗證計畫。它**設計怎麼證明**;實際跑閘門宣告完成是 [[30-verification]] 的事。
與 [[hand-v3/v0-INDEX]] 同形;差別在**受測物是產生器與契約系統本身**,不是一隻手。

## 這棵子樹

| 檔案 | 主題 | 何時該讀 |
|---|---|---|
| [[hand-framework/v1-scope]] | 邊界、驗收準則、參考的技能 | 動工前先讀 |
| [[hand-framework/v2-hypotheses]] | 可證偽假設 | 設計任何檢查之前 |
| [[hand-framework/v3-failure-modes]] | **框架會怎麼壞** | 同上;最值錢的一份 |
| [[hand-framework/v4-scenarios]] | 場景矩陣 | 要寫腳本 |
| [[hand-framework/v5-fixtures]] | 夾具:規格物件、註冊表、命名空間 | 同上 |
| [[hand-framework/v6-scripts]] | 指令與腳本清單(含狀態) | 要跑閘門 |
| [[hand-framework/v7-matrix]] | 覆蓋矩陣 | 想知道哪裡還有洞 |
| [[hand-framework/v8-results]] | 結果記錄模板 | 填數字 |
| [[hand-framework/v9-references]] | 來源 | 要引用 |

## 分角色閱讀路徑

| 你是 | 讀這幾份就夠 |
|---|---|
| 要寫規劃層 | [[hand-framework/v1-scope]] → [[hand-framework/v3-failure-modes]] → [[hand-framework/04-plans]] |
| 要動執行層 | [[hand-framework/v3-failure-modes]] → [[hand-framework/05-execution]] → [[hand-framework/v4-scenarios]] |
| 要加一個實例 | [[hand-framework/08-instances]] → [[hand-framework/v5-fixtures]] → [[hand-framework/v7-matrix]] |
| 要判斷「這算完成了嗎」 | [[hand-framework/v7-matrix]] → [[hand-framework/v8-results]] |
| 要新增一條檢查 | [[hand-framework/v2-hypotheses]] → [[hand-framework/v7-matrix]] |

## 核心迴圈

每一項驗證都是同一個四步:**夾具 → 互動(腳本驅動)→ 比對(事先寫好的判準)→ 證據(記進矩陣)**。
本框架多一條:**每個新閘門上線前先餵一個已知會紅的輸入**。本輪有兩次新閘門第一次就綠、
而它其實在量錯的東西——`bound_box` 快取那次、以及一條沒有合法輸入能弄紅的淨距檢查。
