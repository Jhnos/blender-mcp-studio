# 02 — 需求展開與追溯矩陣

> 回導航 [[hand-v3]] · 相關 [[hand-v3/v1-scope]]、[[hand-v3/v7-matrix]]

需求分四層展開,**每一層各自展開成自己的驗證**。最上層是使用者的聲音,
最下層是元件契約。規則只有一條但很硬:

> **使用者看得到的需求,不得只由單元測試驗證。** 單元、型別、lint 全綠從來不證明
> 交付物是對的——它們驗的是機制,不是使用者真正會讀到的那個東西。

矩陣用 requirement-traceability 的 `trace_check.py` 機器驗(R1–R6)。

**`Verified-by` 的每個 ref 必須是 repo 裡真的找得到的字串**——測試函式名、契約證據名、
或檔名。還沒建的檢查一律寫 `TODO_` 開頭,**看得見**。
這條規則本身由 `test_docs_hand_v3_figures.py` 機器驗:曾經整欄 22 個 ref 有 21 個
在 repo 裡不存在,而 `trace_check.py` 回報「all 22 traced」——因為 R1–R6 只驗格式
`tier:ref`,不驗那個 ref 指得到東西。**格式對的死連結,和沒有連結一樣糟,而且看起來更安全。**

Population: V3 自己產生的物件(前綴 `HJ_V3_`)與 `models/hand-v3/` 的檔案;
實體台架的母數為 10 件 YCB 級物體 × 每組 10 次;`models/octopus-hand-v1|v2/`、
`models/biaxial-hinge-v6/` 排除在 V3 的掃描之外,它們由各自的迴歸契約獨立驗證;
尚未量測的台架列標記 vacuous,**永遠不併入 pass**。

| ID | Requirement | Tier | User-visible | Kind | Verified-by |
|---|---|---|---|---|---|
| VOC-1 | 使用者看得到「充氣後抓得更牢」的實測數字,含母數、效果量與信賴區間 | voc | yes | feature | artifact:TODO_bench_slip_report_has_n_and_ci; differential:TODO_inflated_vs_deflated |
| VOC-2 | 使用者拿得到可直接送切片的檔案,並看得到每個檔的尺寸與三角面數 | voc | yes | feature | artifact:test_versioned_hand_v3_print_package_matches_verified_meshes |
| VOC-3 | 每個引用的外部設計,使用者看得到它的出處與授權條款 | voc | yes | constraint | static:NOTICE; artifact:TODO_notice_lists_every_external_source |
| VOC-4 | 使用者看得到手長什麼樣子與它的握姿,不必自己開 Blender | voc | yes | feature | artifact:TODO_render_set_present_and_uncropped |
| VOC-5 | 使用者看得到哪些主張還沒被量過 | voc | yes | constraint | artifact:TODO_results_template_marks_vacuous |
| PS-1 | 一條腱能把三個指節從全伸帶到全屈 | product | yes | feature | artifact:test_the_finger_that_shipped_carries_three_phalanges; unit:test_the_shipped_finger_closes_within_its_actuator_stroke |
| PS-2 | 指節依序閉合:近端先動,遠端後動 | product | yes | feature | artifact:TODO_closure_order_from_sweep_samples; unit:test_the_spring_gradient_is_what_orders_the_joints_now |
| PS-3 | 手掌是四指一排加一個對生拇指 | product | yes | feature | artifact:scene_list; unit:test_the_thumb_can_touch_the_index_fingertip |
| PS-4 | 夾層充氣後的外形不擋住手指閉合 | product | yes | constraint | artifact:test_the_finger_that_shipped_carries_three_phalanges; unit:test_the_interlayer_has_a_thickness_the_finger_cannot_exceed |
| PS-5 | 整隻手裝得進宣告的床身,且列印姿態可行 | product | yes | constraint | artifact:layout_fits_bed; unit:test_the_assembled_hand_is_deliberately_too_tall_for_the_bed |
| PS-6 | 外層改用不可延展手套時,夾層壓力才建得起來 | product | yes | flag | differential:TODO_outer_layer_elastic_vs_work_glove; artifact:TODO_bench_report_records_both_outer_layers |
| PS-7 | 加壓與抽真空共用同一組介面,兩種都能跑 | product | yes | flag | differential:TODO_pressure_vs_vacuum_slip_force; artifact:channel_probes |
| ES-1 | 腱從全伸到全屈的路徑長變化不超過致動器行程 | engineering | no | constraint | unit:test_the_shipped_finger_closes_within_its_actuator_stroke |
| ES-2 | 各關節力矩臂落在可用窗內,且不向指尖增大 | engineering | no | constraint | unit:test_moment_arms_outside_the_usable_window_are_refused; unit:test_the_moment_arms_never_grow_towards_the_fingertip |
| ES-3 | 彈簧勁度梯度與力矩臂比值兩者共同決定閉合順序 | engineering | no | constraint | unit:test_the_order_is_a_function_of_both_arms_and_springs; unit:test_the_spring_gradient_is_what_orders_the_joints_now |
| ES-4 | 袖口夾與進氣口存在,且壁厚不低於最小值 | engineering | no | constraint | artifact:channel_probes; unit:test_the_air_port_clears_the_cuff_clamp_band |
| ES-5 | 所有 V3 幾何水密、零非流形邊、零件數正確 | engineering | no | constraint | artifact:hand_v3.json |
| ES-6 | V1／V2／V6 的交付物一個位元組都沒被改動 | engineering | no | constraint | artifact:test_versioned_octopus_print_package_matches_verified_meshes; artifact:test_versioned_octopus_v2_print_package_matches_verified_meshes |
| ES-7 | V3 的域模型不繼承章魚手的規格 | engineering | no | constraint | static:test_the_v3_finger_is_not_a_subtype_of_the_octopus_hand |
| DS-1 | 指節鏈沿用 `HingePhalanxSpec` 既有的全部不變式 | detail | no | constraint | unit:test_hinge_chain |
| DS-2 | 不可製造的 V3 規格必須大聲失敗,不得靜默通過 | detail | no | constraint | unit:test_a_finger_that_cannot_work_is_refused_at_construction |
| DS-3 | 域層不匯入 `bpy`、FastAPI、FastMCP | detail | no | constraint | static:test_architecture_ssot |

## 怎麼讀這張表

- **Tier** 是需求在哪一層被說出來,不是它多重要。
- **Verified-by** 的 `tier:ref`,`tier` 只能是 `static / unit / integration / artifact
  / differential / monitor`。`artifact` 指的是**使用者真正會讀到的那個東西**——
  印製包、渲染圖、`NOTICE`、台架報告,不是中間資料結構。
- **Kind: flag** 的列必須有 `differential:` 驗證器。一個開關若開跟關產出分不出來,
  那它就是裝飾品。PS-6 與 PS-7 是這一類:外層材質、氣壓方向,都必須量到差異才算數。

## 還沒有驗證器的需求

**沒有。** 一列都沒有。R1 的規則是「每一列都要有驗證器」,一列沒有就整份紅。
若你新增需求而暫時想不到怎麼驗,那代表這條需求還沒想清楚,不是驗證還沒跟上。

## 這張表怎麼跑

```bash
python3 <requirement-traceability skill>/assets/trace_check.py docs/hand-v3/02-requirements.md
```

回 0 表示 R1–R6 全過。任何一條紅就是**規格不完整**,不是檢查器太嚴。
