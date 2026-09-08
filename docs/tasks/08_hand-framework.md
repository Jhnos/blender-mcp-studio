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

- M0–M4:文件樹與守衛;差分與全部契約在 `--real`;契約由規劃生成;執行層讀規劃並逐面重現 V3;
  掌盤四欄位五不變式,V3 逐位元組不變。
- **M5:契約欄位 `expected_shared_mesh_count`(預設 1)取代判準寫死的 1,should-fire 成對;
  `hand-v3-gradient` 驗證夾具(V3 連桿、力矩臂 7.1/6.1、`HG_V3G_`)註冊、生成契約、進 `--real`,
  真機 20/14,`shared_mesh` 觀測 2 = 宣告 2——零件號數是宣告值,不是產生器限制。
  每零件號一個 STL;`probe_soundness` 在規劃時拒絕量到空氣的探針。**
- import 掃描器修過一個洞:`from pkg import name` 要解析成子模組。

### Open failures

- 沒有機器檢查在失敗。矩陣剩 2 個 `TODO_` ref:PS-1(一致性套件)、VOC-4(`hand_compact` 契約)——都是 M6。

### Next step

- M6:先寫紅測試 `tests/unit/core/test_hand_instance_conformance.py`(對 `HAND_INSTANCES` 參數化:
  `strict=True` 重建掌盤不拒、前綴互異、`phalanx_stls` 數量對);再掃精簡實例的拇指擺位
  (`thumb_offset/drop/palmar ≤ 15/pinch ≤ 15`,照 `palm_v3.py` 註解的掃法),`strict=True` 下無解就停下回報;
  有解才註冊 `hand-compact`、建 `scripts/model_hand_compact.py`、生成契約、真機跑、登錄 `PACKAGES` 不發布。
