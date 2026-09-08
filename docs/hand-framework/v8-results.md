# v8 — 結果記錄模板

> 回導航 [[hand-framework/v0-INDEX]] · 相關 [[hand-framework/v6-scripts]]、[[hand-framework/v7-matrix]]

**還沒跑的東西,這裡就是空的。** 空白比猜測有價值:空白會被看見,猜測會被引用。

## 差分結果(SF-10)

一列一個 STL。面數要**精確相等**;尺寸 ±0.1。**不記 sha**。

| 日期 | 檔案 | manifest 面數 | 重建面數 | manifest 尺寸 | 重建尺寸 | 結果 |
|---|---|---|---|---|---|---|
| 2026-09-08 | phalanx_mm.stl | 3434 | 3434 | 24.0×22.0×67.0 | 24.0×22.0×67.0 | PASS(舊產生器) |
| 2026-09-08 | palm_mm.stl | 2686 | 2686 | 140.0×44.0×103.5 | 140.0×44.0×103.5 | PASS(舊產生器) |
| 2026-09-08 | finger_v3_mm.stl | 10302 | 10302 | 24.0×22.0×175.0 | 24.0×22.0×175.0 | PASS(舊產生器) |
| 2026-09-08 | hand_v3_mm.stl | 54196 | 54196 | 140.0×44.1×265.5 | 140.0×44.1×265.5 | PASS(舊產生器) |
| 2026-09-09 | phalanx_mm.stl | 3434 | 3434 | 24.0×22.0×67.0 | 24.0×22.0×67.0 | **PASS(新產生器)** |
| 2026-09-09 | palm_mm.stl | 2686 | 2686 | 140.0×44.0×103.5 | 140.0×44.0×103.5 | **PASS(新產生器)** |
| 2026-09-09 | finger_v3_mm.stl | 10302 | 10302 | 24.0×22.0×175.0 | 24.0×22.0×175.0 | **PASS(新產生器)** |
| 2026-09-09 | hand_v3_mm.stl | 54196 | 54196 | 140.0×44.1×265.5 | 140.0×44.1×265.5 | **PASS(新產生器)**;STL 時戳在同一次跑內 |

## 契約結果

| 日期 | 契約 | 產生器 | PASS | FAIL | 備註 |
|---|---|---|---|---|---|
| 2026-09-08 | hand_v3.json | 舊(`model_finger_v3.py`) | 20 | 0 | 第一次由 `ci.sh --real` 跑 |
| 2026-09-08 | hand_v3_finger.json | 舊(同場景,`--skip-generate`) | 14 | 0 | 同上 |
| 2026-09-09 | hand_v3.json(**由規劃生成**) | 舊產生器 | 20 | 0 | reload 清單 13 → 18 |
| 2026-09-09 | hand_v3_finger.json(**由規劃生成**) | 舊產生器 | 14 | 0 | 同上 |
| 2026-09-09 | hand_v3.json | **新產生器**(`hand_generator` 讀規劃) | 20 | 0 | 第一次 8 個 PHALANX_ 被 stale-scene 閘門擋下(見「推翻」) |
| 2026-09-09 | hand_v3_finger.json | **新產生器** | 14 | 0 | |

## `--real` 計時(SF-13)

| 日期 | 閘門 | 秒數 | 備註 |
|---|---|---|---|
| 2026-09-08 | hand-v3 contract(生成 + 20 項) | 7 | 時間戳差,含 Blender 重建整手 |
| 2026-09-08 | hand-v3 finger contract(同場景) | 1 | |
| 2026-09-08 | regenerated package matches shipped | 0.2 | 直接計時 0.16 s |
| 2026-09-08 | 整個 T3(含既有五條) | 13 | 整支 `ci.sh --real` 約 35 s |
| 2026-09-09 | 十三份非手契約(D-004) | 59 | 依文件順序、同場景重用;三份 probe 走 mesh_probe |

## 每個實例過了哪些檢查(VOC-3)

| 實例 | 一致性套件 | 契約生成 | 真機契約 | 差分 | 發布 |
|---|---|---|---|---|---|
| `hand-v3` | vacuous | **生成 == 簽入** | **新產生器 20/14** | **新產生器 4/4** | 已發布 |
| `hand-compact` | vacuous | vacuous | vacuous | 不適用 | 未發布(D-008) |

`vacuous` = 檢查存在但沒有對這個實例跑過;**永遠不併入 pass**。

## 推翻了什麼

這一段留給**與預期相反**的結果。它比符合預期的結果更值錢,一定要寫下來:

| 日期 | 原本的說法 | 量到的 | 改寫了哪份文件 |
|---|---|---|---|
| 2026-09-09 | 兩份 V3 契約的 `reload_modules` 是完整的 | import 圖 18 個模組,契約列 13 個;`finger_link`(擁有 `bearing_seat_cuts`)、`rotation`、runner、兩個 domain 規格從未被重載 | [[hand-framework/07-contracts]];契約重生並簽入 |
| 2026-09-09 | v4 猜的「五件換行成 182.5 × 100.5」 | 算法給 242.0 × 217.0 | [[hand-framework/v4-scenarios]] |
| 2026-09-09 | 「import 閉包掃描器看得到每個模組」 | `from pkg import submodule` 被列成 `pkg`;`opposition` 切出來當天契約就列錯 | `generator_imports._from_import_targets`;[[LESSONS_LEARNED]] |
| 2026-09-09 | 「零件的主體就是叫那個名字的物件」 | Blender 對重名加 `.001`;第二條鏈起主體全落單,場景 8 個 PHALANX_ | `hand_geometry.build_finger` 按位置認主體;[[LESSONS_LEARNED]] |

舉例:若 HF-8 被推翻(15 mm 深掌盤掃不出對生解),那是設計發現——寫在這裡,改 [[hand-framework/08-instances]],
不做平放拇指的 fallback。
