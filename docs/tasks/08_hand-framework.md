# 靈巧手框架 — 把「換連桿」變成參數

**Status:** ACTIVE

## Goal

一套連桿參數化、規格驅動、契約驗證的手產生器:先**逐面數、逐尺寸**重現 `models/hand-v3/`,
再讓精簡連桿以**同一套程式**產生有力矩臂梯度的整手並通過同一套契約。契約由規格生成;
契約閘門與 V3 重現差分進 `ci.sh --real`。

## Context to read

1. [`../hand-framework/README.md`](../hand-framework/README.md) — 導航
2. [`../hand-framework/00-context.md`](../hand-framework/00-context.md) — 為什麼、不做什麼、使用者已裁決的三件事
3. [`../hand-framework/02-requirements.md`](../hand-framework/02-requirements.md) — 追溯矩陣(全 `TODO_` 直到建好)
4. [`../hand-framework/v7-matrix.md`](../hand-framework/v7-matrix.md) — 哪裡還有洞

## Specification

規格 → 規劃 → 執行三層,見 `01-boundaries`。里程碑 M0–M6 與每片先紅的測試在 `C:\Users\BearWang\.claude\plans\indexed-marinating-flame.md`(核准版),摘要:

| M | 先紅 | 然後 | 版號 |
|---|---|---|---|
| 0 | 樹守衛在空目錄上紅 | 21 檔樹、矩陣全 `TODO_`、任務狀態、DEFERRAL D-004…D-008 | V01.0P.002 |
| 1 | CI 釘住測試、差分腳本不存在 | `package_reproduction.py` + CLI + 夾具;`--real` 三條閘門;計時 | .003 |
| 2 | 生成器 ≠ 簽入 JSON | 規劃層 + `NamingPolicy` + `contract_builder`;兩份 V3 契約重生相等;ES-6 | .004 |
| 3 | 差分無產生器可跑 | 執行層 + 閘門 + shim;Mac 差分綠;刪舊產生器與死碼 | .005 |
| 4 | 凸出拇指被拒等 | 掌盤五條不變式 + `opposition.py` 切分 + 取樣推導 | .006 |
| 5 | 梯度 → N 零件號 | 每相異臂一份 datablock;`expected_shared_mesh_count` | .007 |
| 6 | 一致性套件對 compact 紅 | 掃拇指擺位;生成契約;真機跑;登錄不發布 | V01.0Q.000 |

## Acceptance checks

- `tests/unit/core/test_docs_dcc.py`、`test_docs_hand_framework_figures.py` 綠;`trace_check.py` R1–R6 綠。
- 每片:`scripts/ci.sh` 綠、checkpoint C1–C5 綠、`models/hand-v3/` 零位元組變動、V1/V2/V6 包測試綠。
- M3:三條差分指令綠(`v6-scripts`)。
- M6:`hand_compact*.json` 真機全 PASS;`TODO_` ref 歸零。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- M0:樹守衛先紅後綠;M1:差分 + 三條 `--real` 閘門(7 s + 1 s + 0.2 s);M2:契約由規劃生成,ES-6 首跑抓到 5 個沒重載的模組。
- **M3:新產生器(`scripts/hand_*.py` 讀規劃)在真機重現 V3:差分 4/4(3434/2686/10302/54196,STL 時戳在同一次跑內),
  契約 20/14,`ci.sh --real` 全綠;三張渲染圖親眼看過(手立在地板上、圖說在旁、佈局三節加掌盤)。**
- 舊產生器三個模組與 `finger_mount_frames` 已刪;`test_script_primitive_ssot` 綠;ES-5 字面值掃描綠。
- 第一次真機跑抓到一個真缺陷:按名字認主體在第二條鏈起落單(Blender `.001`),已改按位置並記入 LESSONS。
- 親驗:`palm_v3.py` 372/380 行(M4 要切 `opposition.py`)。

### Open failures

- 沒有機器檢查在失敗。矩陣剩 8 個 `TODO_` ref:PS-1、VOC-4(M6)、PS-2 契約欄位(M5)、PS-3、ES-1、ES-2、DS-2(M4)、ES-3。
- D-004 已 `due`:V1/V2/V6 七份契約接進 `--real`——先在真機各跑一次確認仍過,再接。

### Next step

- D-004(小片):Mac 上逐一跑 `biaxial_hinge*.json`(5)、`octopus_hand*.json`(2)與 V2 的契約;全過就在 `ci.sh` 加 `_run hard`,
  CI-pin 測試擴成列出全部;記秒數到 `30-verification`。
- 然後 M4:先寫 `test_palm_v3` 的紅案例(拇指凸出 23 被拒、三指列窄一節距、推導預設 = 22.0、取樣跟著上限),
  再切 `opposition.py`、加五條不變式。
