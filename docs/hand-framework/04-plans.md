# 04 — 規劃層與字面值帳本

> 回導航 [[hand-framework]] · 相關 [[hand-framework/01-boundaries]]、[[hand-framework/06-naming]]、[[hand-framework/07-contracts]]

規劃層的每個物件都是**凍結 dataclass**,輸入規格、輸出具名指令,**不匯入 bpy**。
它存在的理由:目前這些算術全困在 `import bpy` 後面,沒有 Blender 的機器**連 import 都做不到**。

## 規劃物件

| 物件 | 輸入 | 輸出 | 取代的字面值 |
|---|---|---|---|
| `PhalanxPlan` | 手指規格 + 命名策略 | 每節的名字、腱孔/走線孔偏移、`bearing_seat_cuts`、公母端尺寸 | 下表 P-1…P-6 |
| `StationPlan` | 掌盤規格 + 命名策略 | 每站台的標籤、原點、3×3 基底、鏈 | 下表 S-1…S-3 |
| `RoutePlan` | 站台 + 手指規格 | 每條孔的中心與長度 | 下表 R-1 |
| `LayoutPlan` | 零件 footprint 清單 + 床身 + 間隙 | 每件擺位 + 總佔地 | 下表 L-1…L-3 |
| `ExpectedCounts` | 掌盤規格 | 每指節數、整手單元數、佈局件數、站台清單、相異零件號數 | 下表 E-1…E-3 |
| `ProbePlan` | 掌盤規格 + 站台 | 手指探針、通道探針、進氣口探針、掃掠角、閉合軌跡參數 | 下表 Q-1…Q-4 |
| `HandPlan` | 以上全部 | 交給執行層與契約生成器的**唯一**輸入 | — |

## 字面值 → 欄位帳本(每一個都要有 V3 預設,搬動後 V3 逐位元組不變)

| # | 字面值 | 現在在哪(親驗) | 變成 |
|---|---|---|---|
| P-1 | 頸寬比 `0.72` | `finger_v3_geometry.py:85, 134` | `PhalanxPlan.neck_width_ratio` |
| P-2 | 頸高 `9.0` | `:85, 134` | `neck_height_mm` |
| P-3 | 頸與本體咬合 `±1.0` | `:88, 127` | `neck_overlap_mm` |
| P-4 | 鑽孔溢出 `+4.0` / `+6.0` | `:56, 108, 157` | `bore_overrun_mm` |
| P-5 | 圓柱段數 `24` | `:37`(`palm_v3_geometry.py:26` 也匯入它) | `bore_segments` |
| P-6 | `HJ_MALE_*`、`HJ_CUT_*`、`HJ_V3_PHALANX_{i}` | `:80-235` 多處 | `NamingPolicy` |
| S-1 | 站台標籤三套(`F{i}`/`T`、`"{i}"`/`"THUMB"`、`ARM_{i}`) | `palm_v3_geometry.py:121-122, 199-203, 231-234` | `NamingPolicy.station_label` |
| S-2 | 拇指基底矩陣寫兩次 | `:99-108`、`:220-228` | `StationPlan.basis`,算一次 |
| S-3 | 抬升 `2 × joint_center_offset` | `:238` | `StationPlan.lift_mm` |
| R-1 | 路徑寫死 `(TENDON, -arm[0])`、`(WIRING, +offset)` | `:123-126` | `RoutePlan` |
| L-1 | 床身 `256.0` | `finger_v3_presentation.py:33` | `LayoutPlan.bed_mm`(實例欄位:[[DEFERRALS]] D-006) |
| L-2 | 間隙 `10.0` | `:54` | `gap_mm` |
| L-3 | 換行擺盤算術 | `:64-83` | `LayoutPlan.pack()`,**離線可測** |
| E-1 | `4 *` | `model_finger_v3.py:130` | `row_finger_count` |
| E-2 | 站台清單 `["F1","F2","F3","F4","T"]` | `:198` | `ExpectedCounts.stations` |
| E-3 | 佈局件數 `4` | `hand_v3.json` `expected_selection_count` | `phalanx_part_count + 1` |
| Q-1 | 手指探針 `±6.6` | `hand_v3.json` `bore_probe_points_mm` | `(0, -arm[0])`、`(0, +wiring)` |
| Q-2 | 掌盤通道探針 `±15/45, −71`、對照 `±30, 0` | `hand_v3.json` `channel_probes` | 站台 × 腱路徑;對照 = 站台中點 |
| Q-3 | 進氣口探針 `−43.1` | 同上 | `air_port_center_mm` |
| Q-4 | 掃掠 `±50 每 10°`、pivot `27.0`、shares `[1.0, 0.625]` | `hand_v3_finger.json` | 由 `maximum_articulation_deg`、`joint_center_offset_mm`、`joint_travel_shares` 推導 |

**帳本是驗收條件**:M2 結束時,舊產生器裡不得再有任何一個上表的字面值;ES-5 的靜態測試掃它。

## 死碼

`palm_v3_geometry.py:191-204 finger_mount_frames` 零呼叫者(親驗 grep)。**刪除,不搬。**
