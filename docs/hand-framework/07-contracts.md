# 07 — 契約:生成、簽入、接進 CI

> 回導航 [[hand-framework]] · 相關 [[hand-framework/04-plans]]、[[hand-framework/v6-scripts]]、[[verification/generated-artifacts]]、[[30-verification]]

## M2 之前的現況(親驗,已改)

`scripts/verify/contracts/hand_v3.json` 與 `hand_v3_finger.json` 每一個值**曾是**手打的 V3 字面值:
前綴 `HJ_V3_*`、探針 `±6.6`、掌盤探針橫座標 `±15/30/45/71` 與 `−43.1`、pivot `27.0`、
shares `[1.0, 0.625]`、床身 `256`、站台 `F1–F4, T`、件數 `3/4`、`reload_modules` 13 個手打名字。
這輪修過一次「契約還在講四節的手」;字面值只要存在就會再漂一次。

## 生成而非手寫(M2 起)

`src/verification/contract_builder.py`:`HandPlan → mapping → JSON`,數字渲染到小數六位。
`scripts/verify/build_hand_contracts.py <slug>` 寫出 `contracts/<slug>.json` 與 `<slug>_finger.json`;`--check` 只比對。

**契約是簽入 git 的生成產物**:diff 可讀,而且 T2 測試斷言「生成器輸出 == 簽入檔(`json.loads` 後)」,
任何手改契約或改規劃都會紅。這比「用測試對照手寫契約」少一份真相源。

M2 的紅測試就是這一條。重生後與手打版的差異只有三種:`reload_modules` 13 → 18(下一節)、產物順序、`0` → `0.0`。
重生的契約在真機仍 20/14 全過。

## 證據鍵對照(判準已有的,不新發明)

| 契約宣告 | 判準證據鍵 | fail-closed 規則 |
|---|---|---|
| `object_prefix` + `expected_count` | `object_count`、`rotations`、`scene_list` | 缺任何觀測值即 FAIL |
| `center_probe_object` + `center_channel_expected_open` | `center_channel` | 非布林即 FAIL |
| `bore_probe_points_mm` | `open_bores` | 長度不符或任一命中即 FAIL |
| `collision_groups` | `collision:<prefix>` | 缺記錄即 FAIL |
| `disjoint_groups` | `disjoint_groups` | 任一配對缺或非 0 即 FAIL |
| `channel_probes` | `channels:<obj>\|<axis>` | open 需全未命中且 solid 需全命中 |
| `expected_shells_per_object` | `one_solid_per_part` | 任一物件未量即 FAIL |
| `closure_trajectory` | `closure_trajectory` | 步數不符或任一非 0 即 FAIL |
| `joint_sweep` | `joint_sweep` | 角度序列不符即 FAIL |
| `readiness.max_footprint_mm` | `layout_fits_bed` | 兩條獨立量測不一致即 FAIL |
| `expected_shared_mesh_count`(預設 1;M5 起) | `shared_mesh` | 觀測 ≠ 宣告即 FAIL;V3 契約不寫 → 判決不變;夾具宣告 2 |

## `reload_modules` 是失效點(ES-6)

真機驗證在**常駐** Blender 裡重載模組再跑產生器。沒列進 `reload_modules` 的模組會跑**上一次載入的舊碼**,
而且回報綠——這是靜默假通過的教科書案例。生成器用 `src/verification/generator_imports.py` **讀原始碼**
(產生器頂層 `import bpy`,不能用 import 來找)推導 import 閉包、葉子在前;`test_every_reachable_module_is_reloaded` 比對。
**首跑就紅**:手打清單漏了 `finger_link`(擁有 `bearing_seat_cuts`)、`rotation`、`blender_generator_runner`、
`hollow_side_hinge`、`biaxial_hinge`。

## 接進 CI(使用者已裁決:進 `--real`)

在 `scripts/ci.sh` 既有的「addon socket 有人聽」分支(`:84-91`,port 見 [[10-runtime-ssot]])之後加三條 `_run hard`:

1. `generated_artifact_verify_real.py scripts/verify/contracts/hand_v3.json`
2. `generated_artifact_verify_real.py scripts/verify/contracts/hand_v3_finger.json --skip-generate`
3. `regenerated_package_matches_shipped.py --package hand-v3`

Blender 沒開 → 既有 `else` 印 SKIP(`:92-96`),**絕不假綠**。API 沒開 → FAIL,與既有 readiness 閘門同極性。
釘住:`test_real_ci_gates_the_hand_contracts`,照 `tests/unit/core/test_architecture_ssot.py:153-157` 的形。
首跑實測三條合計 8 s([[hand-framework/v8-results]]),遠低於 D-004 的 10 分鐘門檻——D-004 因此升為 `due`。
