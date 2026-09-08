# 02 — 需求展開與追溯矩陣

> 回導航 [[hand-framework]] · 相關 [[hand-framework/v1-scope]]、[[hand-framework/v7-matrix]]、[[hand-v3/02-requirements]]

規則與 [[hand-v3/02-requirements]] 完全相同,不重述;兩條最硬的再寫一次:

> **使用者看得到的需求,不得只由單元測試驗證。**
> **`Verified-by` 的每個 ref 必須是 repo 裡真的找得到的字串;還沒建的一律 `TODO_` 開頭,看得見。**

`Verified-by` 回答「怎麼驗」,不是「驗過了沒有」;跑了沒有寫在 [[hand-framework/v7-matrix]]。
本表由 `trace_check.py`(R1–R6)與 `tests/unit/core/test_docs_hand_framework_figures.py`
(ref 解析得到、`TODO_` 名字不得已存在於程式碼)兩者機器驗。

Population: 註冊表 `HAND_INSTANCES` 裡的每個實例與其命名空間下的物件——目前 hand-v3 的
`HJ_V3_`;`models/hand-v3/` 是重現差分的參考母數;`models/octopus-hand-v1|v2/`、
`models/biaxial-hinge-v6/` 排除,由各自契約獨立驗證;未跑的列標 vacuous,**永遠不併入 pass**。

| ID | Requirement | Tier | User-visible | Kind | Verified-by |
|---|---|---|---|---|---|
| VOC-1 | 框架重寫後,使用者拿到的 V3 印製包零件數、尺寸、面數不變 | voc | yes | constraint | artifact:TODO_regenerated_package_matches_shipped; artifact:test_versioned_hand_v3_print_package_matches_verified_meshes |
| VOC-2 | 使用者看得到每個實例的尺寸、力矩臂窗、整指長、相鄰間隙,數字由規格算出 | voc | yes | feature | artifact:test_the_instance_table_quotes_what_the_specs_compute |
| VOC-3 | 使用者不必開 Blender 就知道每個實例過了哪些檢查 | voc | yes | feature | artifact:TODO_test_the_results_template_marks_each_instance |
| VOC-4 | 人手尺寸的手是同一套程式的一個實例,不是分叉 | voc | yes | feature | artifact:TODO_hand_compact_contract; static:TODO_test_no_generator_names_a_link_dimension |
| PS-1 | 任何滿足 `FingerLinkSpec` 的連桿都能組成手且生成契約 | product | yes | feature | unit:TODO_test_every_registered_instance_conforms; artifact:TODO_build_hand_contracts |
| PS-2 | 力矩臂有梯度的手指建得出,零件號數是宣告值不是產生器限制 | product | yes | feature | artifact:TODO_expected_shared_mesh_count; unit:TODO_test_a_gradient_finger_plans_one_part_per_distinct_arm |
| PS-3 | 指列數是欄位不是常數 | product | no | feature | unit:TODO_test_a_three_finger_row_is_narrower_by_one_pitch |
| PS-4 | 契約由規格生成;V3 的兩份契約可被完整重現 | product | no | constraint | unit:TODO_test_the_builder_reproduces_the_committed_hand_v3_contracts |
| PS-5 | `ci.sh --real` 跑手契約與 V3 重現差分 | product | no | constraint | static:TODO_test_real_ci_gates_the_hand_contracts |
| ES-1 | 拇指根凸出量 ≤ 掌盤厚度 | engineering | no | constraint | unit:TODO_test_a_thumb_root_proud_of_the_palm_is_refused |
| ES-2 | 接觸判準與拇指凸出量由連桿推導;V3 推出來仍是 22.0 | engineering | no | constraint | unit:TODO_test_derived_palm_defaults_equal_the_v3_literals |
| ES-3 | 探針點落在實體內且避開銷孔壁 | engineering | no | constraint | unit:TODO_test_probe_points_lie_inside_the_body_and_clear_the_pin |
| ES-4 | 佈局規劃是純函式,離線可驗,放得進床身 | engineering | no | constraint | unit:TODO_test_the_layout_plan_wraps_rows_at_the_bed; artifact:layout_fits_bed |
| ES-5 | 執行層不做算術,名字全來自命名策略 | engineering | no | constraint | static:TODO_test_bpy_modules_read_plans_only |
| ES-6 | 產生器可達的每個模組都在契約 `reload_modules` 裡 | engineering | no | constraint | static:TODO_test_every_reachable_module_is_reloaded |
| ES-7 | 舊 V3 產生器刪除後無重複 primitive | engineering | no | constraint | static:test_script_primitive_ssot |
| DS-1 | 域層與規劃層不匯入 bpy | detail | no | constraint | static:test_architecture_ssot |
| DS-2 | 姿態取樣由關節上限推導,不寫死 50° | detail | no | constraint | unit:TODO_test_the_posture_grid_follows_the_articulation_limit |
| DS-3 | 凍結交付物位元組不變 | detail | no | constraint | artifact:test_versioned_octopus_print_package_matches_verified_meshes; artifact:test_versioned_octopus_v2_print_package_matches_verified_meshes |

## 怎麼讀這張表

- **Tier** 是需求在哪一層被說出來。`artifact` 指使用者真正會讀到的東西:印製包、契約 JSON、實例表、CI 輸出。
- ES-6 是本框架特有的失效類:常駐 Blender 對沒列進 `reload_modules` 的模組**跑舊碼且回報綠**。
  不是假想——V3 契約的 `reload_modules` 是手打的 13 個名字,新增一個模組就可能漏。
- 沒有 `Kind: flag` 的列,所以沒有 `differential:`;若日後出現開關,照 hand-v3 的規則補。
- PS-3 標 `User-visible: no`:兩個註冊實例都是四指列,使用者讀到的東西不會因這個欄位而變;第一個非四指實例出現時改 `yes` 並加 `artifact:` ref。

## 還沒有驗證器的需求

**沒有。** 未建的檢查以 `TODO_` 前綴列出,建好即改名;`TODO_` 歸零就是 M5 的定義。

## 這張表怎麼跑

```bash
python3 <requirement-traceability skill>/assets/trace_check.py docs/hand-framework/02-requirements.md
python3 -m pytest tests/unit/core/test_docs_hand_framework_figures.py -q
```
