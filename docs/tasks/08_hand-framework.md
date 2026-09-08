# 靈巧手框架 — 把「換連桿」變成參數

**Status:** AWAITING-ACCEPTANCE

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

- M0–M5:文件樹與守衛;差分與全部契約在 `--real`;契約由規劃生成;執行層讀規劃並逐面重現 V3;
  掌盤四欄位五不變式;零件號數是宣告值(夾具真機 20/14)。
- **M6:`hand-compact` 已註冊(精簡連桿、力矩臂 5.5/3.6、兩個零件號、`HK_COMPACT_`),契約由規劃生成並在真機
  20/14 全過;整手 110 × 30 × 234.5,佈局 191 × 90.5。第一次擺位真機 19/20——直伸拇指擦過 F3——
  加了靜止淨距不變式 I6 重掃後全過(淨距 3.48 mm,V3 2.49)。三張渲染圖親眼看過並交使用者。**
- 追溯矩陣 19 列 `TODO_` 歸零;`ci.sh --real` 跑 17 份契約 + 差分,約 2.5 分鐘,全綠。
- 收尾 V01.0Q.001:圖表守衛改讀註冊表;`ci.sh` 全綠、trace 19/19、checkpoint C1–C5 綠(2026-09-09)。

### Open failures

- 沒有機器檢查在失敗。
- checkpoint C1 會報「沒有 ACTIVE 任務」:這是真實狀態——機器側全部完成,剩下的每一步都在使用者手上
  (Lane B 三題、印試片、台架)。不為了讓檢查器綠而捏造一個進行中的任務。

### Next step(使用者)

- **Lane B 三題**(看 `tmp/hand-compact/` 三張圖,或本對話附的檔案):像不像手?握姿順不順?針筒好不好推?
  通過 → `python3 scripts/publish_print_package.py hand-compact`(D-008),包進 `models/hand-compact/`,
  再把 `regenerated_package_matches_shipped.py --package hand-compact` 接進 `--real`。
- 印 `models/hand-v3/phalanx_mm.stl` 試片(`07_hand-v3-coupon.md`,C1–C7)——所有實體判斷都從它反推。
