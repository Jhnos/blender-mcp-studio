# 靈巧手框架 — 導航

> 回導航 [[README]] · 相關 [[tasks/00_INDEX]]、[[hand-v3]]、[[30-verification]]

把「換一種連桿」從**另開一支產生器**變成**換一個參數**。V3(借來的連桿,銷 4 mm + 軸承)
與人手尺寸的手(精簡連桿,銷 2 mm、無軸承)是同一套程式的兩個**實例**;
未來任何滿足 `FingerLinkSpec` 的連桿是第三個。

一句話方法:**域層算數字,純規劃層把數字變成有名字的指令,bpy 只執行指令、不做算術。**
契約 JSON 由規劃層生成、簽入 git、可 diff——「契約字面值漂移」這一類缺陷從此結構性消失。

**這棵樹是平鋪的**,因為 [[README]] 的孤兒閘門只走兩跳。樹內互指一律寫
`[[hand-framework/04-plans]]` 這種從 `docs/` 根算起的完整路徑。
軟層、介面、先例、名詞留在 [[hand-v3]] 那棵樹,**指過去,不複製**。

## 設計文件

| 檔案 | 主題 | 何時該讀 |
|---|---|---|
| [[hand-framework/00-context]] | 為什麼要框架、V3 教了什麼、明確不做什麼 | **第一次接觸** |
| [[hand-framework/01-boundaries]] | 模組地圖、層規則、bpy 不准做什麼、必須重用什麼 | 動任何模組之前 |
| [[hand-framework/02-requirements]] | 需求展開與**追溯矩陣** | 動任何一片之前 |
| [[hand-framework/03-domain-spec]] | 掌盤參數化、推導預設、新不變式、對生函式切分 | 改規格 |
| [[hand-framework/04-plans]] | 規劃層物件 + **字面值→欄位帳本** | 改幾何 |
| [[hand-framework/05-execution]] | bpy 執行器、閘門、shim 政策、等臂守衛的解法 | 改產生器 |
| [[hand-framework/06-naming]] | 命名策略、站台標籤、命名空間 | 讀契約或場景 |
| [[hand-framework/07-contracts]] | 契約生成器、簽入政策、證據鍵對照、CI 接線 | 改契約 |
| [[hand-framework/08-instances]] | 實例表(數字由規格算出,機器對照) | 加實例 |
| [[hand-framework/09-glossary]] | plan、station、route、part id、差分 | 看不懂名詞 |

## 驗證計畫

| 檔案 | 主題 | 何時該讀 |
|---|---|---|
| [[hand-framework/v0-INDEX]] | 驗證計畫導航與分角色路徑 | **宣告完成之前** |
| [[hand-framework/v1-scope]] | 驗證邊界與驗收準則 | 同上 |
| [[hand-framework/v2-hypotheses]] | 可證偽假設 | 設計任何檢查之前 |
| [[hand-framework/v3-failure-modes]] | 框架的失效模式表(它會怎麼壞) | 同上 |
| [[hand-framework/v4-scenarios]] | 場景矩陣 | 寫驗證腳本 |
| [[hand-framework/v5-fixtures]] | 夾具規格 | 同上 |
| [[hand-framework/v6-scripts]] | 可執行腳本與指令 | 要跑閘門 |
| [[hand-framework/v7-matrix]] | 假設 × 場景 × 證據 × Lane | 想知道哪裡還有洞 |
| [[hand-framework/v8-results]] | 結果記錄模板 | 填數字 |
| [[hand-framework/v9-references]] | 親自存取過的來源 | 要引用 |

## 接手 SOP

1. 讀 [[tasks/00_INDEX]] 找框架的任務列,再讀 [`08_hand-framework.md`](../tasks/08_hand-framework.md) 的 hand-off。
2. 讀 [[hand-framework/00-context]],知道範圍與不做什麼。
3. 讀 [[hand-framework/02-requirements]],確認你要動的那一條需求由誰驗。
4. 依上表**只載入這一步需要的檔**。不要重掃 repo。
