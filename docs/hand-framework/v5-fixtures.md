# v5 — 夾具

> 回導航 [[hand-framework/v0-INDEX]] · 相關 [[hand-framework/v4-scenarios]]、[[hand-framework/06-naming]]、[[hand-v3/v5-fixtures]]

## 夾具是規格物件,不是資料庫紀錄

紀律與 [[hand-v3/v5-fixtures]] 相同:冪等、隔離、受控差異、不共用可變狀態。本框架多三條:

- **註冊表是唯一來源**:一致性套件對 `HAND_INSTANCES` 參數化,不在測試裡另建實例。
  測試裡另建的實例會漂——V3 樹的圖表守衛在註冊表存在前先用內建規格,註冊表一存在就改讀它。
- **每實例一個命名空間**:`hand-v3` 是 `HJ_V3_`;`hand-compact` 建議 `HK_COMPACT_`。
  兩個實例的物件不得共用前綴,否則 `run_generator` 清場會清掉另一個。
- **`tmp/<slug>/` 是產出目錄**,`models/<slug>/` 只讀。差分**讀** `models/`,**寫** `tmp/`,永遠不反過來。

## 受控差異的配對

| 場景 | 只差什麼 | 兩組 |
|---|---|---|
| SF-3 | `row_finger_count` | 4 vs 3 |
| SF-4 | `thumb_base_palmar_mm` | 22 vs 23 |
| SF-5 | `moment_arms_mm` | (6.6, 6.6) vs (5.5, 3.6) |
| SF-8 | `NamingPolicy.namespace` | `HJ_` vs `HK_` |
| SF-10 | 產生器(舊 vs 新) | 同一個規格 `hand-v3` |

## 參考母數

`models/hand-v3/manifest.json` 是 SF-10 的母數:它由 `publish_print_package.py` 寫入,
每個 STL 帶 `triangle_count` 與 `dimensions_mm`,而 `test_hand_v3_print_package.py` 已把它釘在
`EXPECTED` 表上——所以差分**不引入第二張期望值表**。

## 空母數守衛

差分若在 `tmp/hand-v3/` 找不到某個 STL:**exit 1 並印出路徑**,不 skip。
一致性套件若 `HAND_INSTANCES` 為空:FAIL——空註冊表上的「全部通過」是假綠。

## 兩機同步的夾具紀律

- 只走 git-over-SSH;`git reset --hard` 前一律 `git stash -u`。
- 絕不 scp `tmp/` 或 `models/`。
- 共用工作樹有另一個 session:只 stage 明確路徑,不用 `git add -A`。
