# 09 — 名詞

> 回導航 [[hand-framework]] · 相關 [[hand-v3/09-glossary]]

通用代號(DCC、Lane A/B、IDD、VOC、DFMEA)在 [[hand-v3/09-glossary]],不重述。這裡只有本樹新引入的。

| 名詞 | 意思 |
|---|---|
| **實例(instance)** | 一組具體規格:一種連桿 + 一組力矩臂 + 一組掌盤參數 + 一個命名空間。`hand-v3` 與 `hand-compact` 各是一個。註冊在 `hand_instances.py` |
| **規劃(plan)** | 純資料物件,把規格的數字變成「建什麼、叫什麼、擺哪裡、量哪裡」的具名指令。執行層只讀它 |
| **站台(station)** | 掌盤上一根手指的掛載點:標籤(`F1`…`F4`、`T`)、原點、基底、鏈 |
| **路徑(route)** | 穿過掌盤的一條孔:腱(掌側)或走線(背側),每站台各一 |
| **零件號(part id)** | 相異力矩臂的編號。V3 全等臂 → 一個零件號;梯度手指 → 每個相異臂一個 |
| **命名空間(namespace)** | `run_generator` 清場用的前綴。每實例一個,互不干擾 |
| **重現差分(reproduction differential)** | 用新產生器重建 `hand-v3`,對 `models/hand-v3/manifest.json` 比面數(精確)與尺寸(±0.1)。**不比 sha**——STL 匯出不可位元組重現 |
| **should-fire / should-pass** | 每個新閘門上線前必附的一對夾具:一個已知會紅、一個已知會綠。只有後者的閘門與「永遠通過」分不出來 |
| **vacuous** | 母數為零的檢查結果。是檢查在運作並如實說沒有資料,不是檢查還沒建;永遠不併入 pass |
| **`TODO_` ref** | 追溯矩陣裡還沒建的驗證器,前綴讓它看得見;建好即改名。守衛確保 `TODO_` 名字不已存在於程式碼 |
| **shim** | `scripts/model_finger_v3.py` 縮成的薄入口:因為契約、manifest、測試、regex 都指名它,所以檔名與那行 `run_generator(build, prefix="HJ_")` 不能動 |
