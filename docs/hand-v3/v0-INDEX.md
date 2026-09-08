# v0 — 驗證計畫導航

> 回導航 [[hand-v3]] · 相關 [[30-verification]]、[[hand-v3/02-requirements]]

這是 V3 的驗證計畫。它**設計怎麼證明**;實際跑閘門宣告完成是 [[30-verification]] 的事。
一句話分工:**這裡造尺,那裡量。**

## 這棵子樹

| 檔案 | 主題 | 何時該讀 |
|---|---|---|
| [[hand-v3/v1-scope]] | 邊界、術語、驗收準則 | 動工前先讀,定義「對」長什麼樣 |
| [[hand-v3/v2-hypotheses]] | 可證偽假設與優先序 | 設計任何檢查之前 |
| [[hand-v3/v3-failure-modes]] | **它會怎麼壞** | 同上;這一份最常被跳過,也最值錢 |
| [[hand-v3/v4-scenarios]] | 場景矩陣 | 要寫腳本 |
| [[hand-v3/v5-fixtures]] | 夾具與 dummy 規格 | 同上 |
| [[hand-v3/v6-scripts]] | 可執行腳本 + **實體台架協定** | 要跑量測 |
| [[hand-v3/v7-matrix]] | 覆蓋矩陣 | 想知道哪裡還有洞 |
| [[hand-v3/v8-results]] | 結果記錄模板 | 填數字 |
| [[hand-v3/v9-references]] | 來源 | 要引用 |

## 分角色閱讀路徑

| 你是 | 讀這幾份就夠 |
|---|---|
| 要寫幾何程式 | [[hand-v3/v1-scope]] → [[hand-v3/v3-failure-modes]] → [[hand-v3/v4-scenarios]] |
| 要跑實體台架 | [[hand-v3/v6-scripts]] 的台架段 → [[hand-v3/v8-results]] |
| 要判斷「這算完成了嗎」 | [[hand-v3/v7-matrix]] → [[hand-v3/v8-results]] |
| 要新增一條檢查 | [[hand-v3/v2-hypotheses]](它回答哪個假設?)→ [[hand-v3/v7-matrix]](補一列) |

## 核心迴圈

每一項驗證都是同一個四步,缺一不成立:

1. **夾具**——建立組態已知的受控對象。
2. **互動**——只變一個變數,其餘固定,**用腳本驅動,不是用手點**。
3. **比對**——與**事先寫好**的驗收準則比。
4. **證據**——記進矩陣,讓缺口看得見。
