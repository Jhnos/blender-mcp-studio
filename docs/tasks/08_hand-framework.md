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

- M0:樹守衛先在空目錄上紅,文件寫完綠;第一稿被守衛抓到四件事。
- M1:差分對舊產生器 4/4 PASS;`--real` 三條新閘門 7 s + 1 s + 0.2 s;should-fire 親驗 exit 1。
- M2:規劃層 83 個測試綠;兩份契約由規劃生成並簽入,真機仍 20/14;ES-6 首跑抓到 5 個從未重載的模組;
  佈局算法離線算出 242.0 × 103.5 = 真機量到的數。DS-1 現在有真守衛。
- 親驗:`finger_mount_frames` 零呼叫者;`palm_v3.py` 372/380 行;`build_finger` 等臂守衛在 `:221-225`。

### Open failures

- 沒有機器檢查在失敗。矩陣剩 10 個 `TODO_` ref(M3–M6),每個都有名字。
- D-004 已 `due`:V1/V2/V6 七份契約排進 M3 一起接進 `--real`。

### Next step

- M3:先寫 `tests/unit/planning/test_phalanx_plan.py` 與 `test_route_plan.py`(紅:模組不存在)釘住
  `04-plans` 帳本 P-1…P-6、R-1;再寫 `tests/unit/scripts/test_bpy_modules_read_plans_only`(ES-5)。
  然後建 `scripts/hand_{geometry,presentation,gates,generator}.py`,`model_finger_v3.py` 縮成 shim,
  Mac 上跑 `v6-scripts` 的三條差分指令;綠了才刪 `finger_v3_geometry.py`、`palm_v3_geometry.py`、
  `finger_v3_presentation.py` 與 `finger_mount_frames`。
