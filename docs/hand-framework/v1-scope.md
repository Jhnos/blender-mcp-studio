# v1 — 驗證邊界與驗收準則

> 回導航 [[hand-framework/v0-INDEX]] · 相關 [[hand-framework/02-requirements]]、[[hand-v3/v1-scope]]

Doctrine consulted: `ddd-solid`(規格→規劃→執行三層,執行層不做算術,見 [[hand-framework/01-boundaries]]);
`tdd`(每一片先有會紅的測試,新閘門先餵已知會紅的輸入);`requirement-traceability`(ref 必須解析得到,
`TODO_` 看得見);`verification-plan-design`(本樹的形狀);`checker-first`(每個缺陷變永久閘門);
`pragmatic-reuse`(建模組前先查先例,見 [[hand-framework/v9-references]])。

## 在範圍內

- 框架**重現 V3**:`tmp/hand-v3/` 對 `models/hand-v3/manifest.json` 的面數與尺寸;兩份契約仍全過。
- 契約**由規格生成**且與簽入檔相等。
- 規劃層的每個純函式:佈局換行、站台、探針點、期望計數。
- 掌盤的五條新不變式(should-fire 與 should-pass 各一)。
- 梯度手指的建構與 `expected_shared_mesh_count`。
- 契約閘門與差分**進 `ci.sh --real`**,並被靜態測試釘住。
- `hand-compact` 實例:一致性套件、生成契約、真機通過。
- 母數:hand-v3 的物件前綴 `HJ_V3_`;`hand-compact` 的前綴在 M2 定案後加入。

## 在範圍外(而且要說出為什麼)

| 不驗 | 為什麼 |
|---|---|
| 無銷關節(活動鉸鏈、原地列印) | 使用者裁決不建抽象;疲勞是材料性質,幾何契約量不到。[[DEFERRALS]] D-005 |
| 列印公差、抓持力、壓力保持 | 屬 [[hand-v3/v6b-coupon]] 與 [[hand-v3/v6-scripts]] 的實體協定,那邊已有讀表與統計 |
| `models/hand-compact/` 的發布 | 等 Lane B,D-008 |
| V1/V2/V6 契約進 CI | D-004,觸發條件是動到它們的產生器或手契約閘門實測夠快 |
| 渲染圖的品味 | Lane B,只在 M6 之後交使用者 |

## 灰區

- **STL 不可位元組重現**:同樣的程式跑兩次,四個 STL 有三個雜湊不同(本輪已證)。所以「不變」的定義是
  **面數精確相等、尺寸 ±0.1**;sha 只在 manifest 裡防竄改。任何「雜湊變了所以壞了」的推論一律無效。
- **常駐 Blender**:真機驗證在同一個 Blender 裡重載模組。沒進 `reload_modules` 的模組跑舊碼還綠,
  所以 ES-6 是本框架獨有的閘門。

## 驗收準則

一片算完成,要同時滿足:

1. **Lane A 全綠**:[[hand-framework/v7-matrix]] 裡屬於這一片的每一列都有結果,沒有紅。
2. **沒有 vacuous 混進 pass**。
3. **V3 重現差分綠**——每一片之後都重跑,不只 M3。
4. **凍結交付物未動**:V1/V2/V6 包測試綠;`models/hand-v3/` 零位元組變動。
5. **新閘門有一對夾具**:should-fire 與 should-pass。

Lane B 只在 M6 之後、只有三題,與 V3 相同:像不像手、握姿順不順、針筒好不好推。
