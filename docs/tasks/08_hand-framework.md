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

- M0:樹守衛先在空目錄上紅(6 failed),文件寫完綠;第一稿被守衛抓到四件事。
- M1:重現差分對**舊產生器** 4/4 PASS(3434/2686/10302/54196 面,尺寸全在 ±0.1 內);
  `ci.sh --real` 三條新閘門全 PASS,首跑 7 s + 1 s + 0.2 s;整支 `--real` 約 35 s。
- 差分的 should-fire 親驗:`--source` 指向空目錄 → 4 個 `missing` FAIL、exit 1。
- 親驗過的三個決定計畫形狀的事實在 `00-context`;`finger_mount_frames` 零呼叫者;`palm_v3.py` 372/380 行。

### Open failures

- 沒有機器檢查在失敗。矩陣剩 14 個 `TODO_` ref(M2–M6),每個都有名字。
- D-004 已 `due`(觸發:手契約閘門 < 10 分鐘):V1/V2/V6 七份契約排進 M3 一起接。

### Next step

- M2:先寫 `tests/unit/verification/test_contract_builder.py`——對 `hand-v3` 生成,與簽入的兩份 JSON
  `json.loads` 後相等(紅:模組不存在);再建 `src/core/planning/` 七個規劃物件與 `NamingPolicy`,
  `src/verification/contract_builder.py`,`scripts/verify/build_hand_contracts.py`;ES-6 reload 測試。
