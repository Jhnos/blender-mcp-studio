# v1 — 驗證邊界與驗收準則

> 回導航 [[hand-v3/v0-INDEX]] · 相關 [[hand-v3/02-requirements]]

Doctrine consulted: `ddd-solid`(V3 組合而非繼承章魚手規格,見 [[hand-v3/00-context]]);
`tdd`(每一片先有一個會紅的測試);`requirement-traceability`(需求→驗證的追溯規則);
`verification-plan-design`(本樹的形狀)。

## 在範圍內

- V3 自己產生的幾何:前綴 `HH_V3_` 的物件與 `models/hand-v3/` 的檔案。
- 腱路徑長、力矩臂、閉合順序、碰撞、掃掠——全部是幾何量。
- 軟層的**介面**幾何:袖口夾、進氣口。
- 實體台架量到的滑脫力與壓力保持。
- `NOTICE` 的授權署名完整性。

## 在範圍外(而且要說出為什麼)

| 不驗 | 為什麼 |
|---|---|
| **抓持力、摩擦係數** 的機器驗證 | 現有管線量不到力。`docs/verification/generated-artifacts.md` 自己寫著 retention probe「do not measure holding force」。改由實體台架量 |
| 材料強度、疲勞壽命 | 沒有設備。台架只量到「首次洩漏」為止,不外推 |
| 外層手套本身 | 現成品,不在介面契約內,見 [[hand-v3/07-interfaces]] |
| InMoov 的幾何品質 | 別人的交付物。Track 1 只把它當試驗台,不對它背書 |
| 列印會不會成功 | 只有實際印才知道。切片器警告會照實呈現,不判定 |

## 灰區(先說清楚,免得日後爭)

- **Track 1 與 Track 2 的腱力不可互比**——兩者機構不同(雙線 vs 單腱)。
  可互比的只有「充氣帶來的增量」。
- **視覺 rubric** 由全新 context 只看 PNG 判定,不看程式碼也不看本文件。

## 驗收準則

一片算完成,要同時滿足:

1. **Lane A 全綠**:[[hand-v3/v7-matrix]] 裡屬於這一片的每一列都有結果,且沒有紅。
2. **沒有 vacuous 混進 pass**:母數為零的列標 vacuous,**不算通過**。
3. **凍結交付物未動**:V1／V2／V6 的四份契約重跑全綠。
4. **Lane B 已交付可裁決物**:渲染圖或實體件已送到使用者面前。

Lane B 只有三題:像不像一隻手、握姿順不順、針筒好不好推。其餘都是 Lane A,
**不丟給使用者**。
