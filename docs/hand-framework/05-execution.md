# 05 — 執行層:只執行,不算術

> 回導航 [[hand-framework]] · 相關 [[hand-framework/04-plans]]、[[hand-framework/07-contracts]]、[[verification/generated-artifacts]]

## 四個執行模組

| 模組 | 做什麼 | 從哪裡搬來 |
|---|---|---|
| `scripts/hand_geometry.py` | 照 `PhalanxPlan`/`StationPlan`/`RoutePlan` 建網格:mm→m、primitive、布林 | `finger_v3_geometry.py`、`palm_v3_geometry.py` 的 bpy 部分 |
| `scripts/hand_presentation.py` | 照 `LayoutPlan` 擺盤、照 `PresentationProfile` 出圖 | `finger_v3_presentation.py` |
| `scripts/hand_gates.py` | 建構時閘門:場景乾淨、膝節接上、殼數、只留手可見 | `model_finger_v3.py:39-139`,改讀 `ExpectedCounts` + `NamingPolicy` |
| `scripts/hand_generator.py` | `build(instance_slug, output_dir)`:串起以上三者 | `model_finger_v3.py:142-214` |

## 等臂守衛怎麼解

現況:`build_finger` 在 `phalanx_part_count != 1` 時 raise(`finger_v3_geometry.py:221-225`)。
它複製一個主體給三節,所以三節的腱孔必須相同——而**梯度手指正是要每節不同**。

解法(三選一,取第二):

| 選項 | 代價 | V3 風險 |
|---|---|---|
| 另寫一個 `build_finger_parts` | 複製迴圈——留兩套 | 零 |
| **每個相異力矩臂一份 datablock 拷貝,同臂共用** | 換掉 `:220-240` 一段 | 低:名字與 z 抬升不變;`finger_v3_mm.stl` 面數(10 302)與契約 `shared_mesh` 會抓到任何偏差 |
| 每節獨立網格 | 最小改動 | **破壞** `shared_mesh_count == 1`(`generated_artifact_verdict.py:72-79` 寫死) |

「一個零件號」從此是**實例宣告**:`spec.phalanx_part_count` 餵 `ExpectedCounts.layout_parts`
與契約新欄位 `expected_shared_mesh_count`(預設 1;V3 契約不寫 → 判決不變;梯度實例寫 N)。
產生器自己的守衛(`model_finger_v3.py:164-168`)也改成比對宣告值。

## shim 政策

`scripts/model_finger_v3.py` **保留**,縮成 ≤15 行:選實例、輸出目錄、呼叫 `hand_generator.build`,
並維持字面呼叫 `run_generator(build, prefix="HJ_")`。理由:`hand_v3.json:3`、`models/hand-v3/manifest.json`、
`test_hand_v3_print_package.py:42`、`test_docs_hand_v3_figures.py:192-196` 都指名這個檔與這行。

## 刪除清單(M3 差分綠之後)

`scripts/finger_v3_geometry.py`、`scripts/palm_v3_geometry.py`、`scripts/finger_v3_presentation.py`。
它們不是凍結交付物(只有 V1 的產生器凍結);留著就是兩套。
`tests/unit/scripts/test_script_primitive_ssot.py` 會確認刪完沒有 primitive 被重打。

## 執行層的三條禁令

1. 不出現字面尺寸——所有 mm 來自規劃物件。
2. 不出現字面名字——所有名字來自 `NamingPolicy`。
3. 不做布林以外的幾何決定——「切幾個座」「鑽到哪」在規劃層決定好。

`test_bpy_modules_read_plans_only`(ES-5)掃 `scripts/hand_*.py` 的浮點字面值與字串常數;
允許清單只有 `0.0`、`1.0`、`0.001`(mm→m)。
