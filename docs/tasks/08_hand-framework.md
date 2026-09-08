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

- M0–M3:文件樹與守衛;差分與 `--real` 閘門;契約由規劃生成(ES-6 抓到 5 個沒重載的模組);
  執行層讀規劃並在真機逐面重現 V3(4/4、20/14),舊產生器已刪。D-004 done:全部 15 份契約在 `--real`。
- **M4:掌盤四個新欄位(`row_finger_count`、三個 0 = 由連桿推導的 sentinel)與五條不變式;
  V3 的 22.0 / 22.0 / 1.0 由連桿推導、逐位元組不變——契約只多一個 reload 模組,差分仍 4/4。
  `opposition.py` 切出,`palm_v3.py` 369 行。八個新案例先紅後綠。**

### Open failures

- 沒有機器檢查在失敗。矩陣剩 4 個 `TODO_` ref:PS-1、VOC-4(M6)、PS-2 契約欄位(M5)、ES-3。

### Next step

- M5:先寫紅測試——契約新欄位 `expected_shared_mesh_count`(預設 1;判準 `shared_mesh` 觀測 ≠ 宣告即 FAIL,
  附 should-fire)與 `build_finger` 對梯度手指建出 2 個 datablock(需真機);再讓 `contract_builder`
  對 `phalanx_part_count != 1` 的實例寫該欄位。V3 契約不寫 → 逐位元組不變。
- 然後 M6:掃精簡實例的拇指擺位(`strict=True`);註冊 `hand-compact`;生成契約;真機跑;登錄不發布。
