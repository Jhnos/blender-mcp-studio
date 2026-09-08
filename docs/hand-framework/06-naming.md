# 06 — 命名策略與命名空間

> 回導航 [[hand-framework]] · 相關 [[hand-framework/04-plans]]、[[hand-framework/v5-fixtures]]、[[hand-v3/09-glossary]]

## 為什麼要一個物件管名字

V3 目前有**三套**站台標籤同時存在(親驗 `scripts/palm_v3_geometry.py`):

| 用法 | 標籤 | 位置 |
|---|---|---|
| 場景 metadata 與碰撞群組 | `F1`…`F4`、`T` | `:231-234`、`model_finger_v3.py:198` |
| 掌盤切孔 | `"1"`…`"4"`、`"THUMB"` | `:121-122` |
| 掛載框架 | `ARM_1`…、`THUMB` | `:199-203` |

三套各自正確,但同一個站台有三個名字,契約與文件對它的引用就有三種寫法。
`NamingPolicy` 讓每個角色只有一個名字。

## `NamingPolicy(namespace, family)`

| 方法 | 產出 | 目前對應的字面值 |
|---|---|---|
| `phalanx(index)` | `{ns}{family}_PHALANX_{index}` | `HJ_V3_PHALANX_{i}` |
| `hand_unit(station, index)` | `{ns}{family}_HAND_{station}_{index}` | `HJ_V3_HAND_F1_1` |
| `palm()` / `thenar()` / `root(station)` | `{ns}{family}_PALM` 等 | `HJ_V3_PALM`、`HJ_V3_THENAR`、`HJ_V3_ROOT_*` |
| `cut(kind, label)` | `{ns}CUT_{kind}_{label}` | `HJ_CUT_*`、`HJ_V3_CUT_*` |
| `layout_part(index)` | `{ns}{family}_LAYOUT_PART_{index}` | `HJ_V3_LAYOUT_PART_{i}` |
| `station_label(index)` | `F{index}`;拇指 `T` | 統一上表三套 |
| `scene_key(name)` | `{ns}{family}_{NAME}` | `HJ_V3_HAND_STATIONS` |
| `material(role)` / `collection(role)` | `{ns}{family}_{ROLE}` | `HJ_V3_BODY`、`HJ_V3_FINGER` |

## 命名空間:每個實例一個,可各自清場

`run_generator(build, prefix=...)` 用前綴清場。兩個實例若共用前綴,建第二個會清掉第一個。

| 實例 | `namespace` | `family` | 前綴 | 狀態 |
|---|---|---|---|---|
| `hand-v3` | `HJ_` | `V3` | `HJ_V3_` | 既有;**不可變**——契約、manifest、測試 regex 都釘著 |
| `hand-v3-gradient` | `HG_` | `V3G` | `HG_V3G_` | 驗證夾具(M5);有契約、無包 |
| `hand-compact` | `HK_` | `COMPACT` | `HK_COMPACT_` | 定案(M2);M6 註冊時使用 |

母數守衛(`test_docs_hand_framework_figures.py`)從 `scripts/model_finger_v3.py` 的
`run_generator(build, prefix="…")` 讀出前綴,再斷言本樹五份文件宣告的是 `HJ_V3_` 而且沒有別的 `H?_V3_` 變體
——V3 那棵樹曾五份文件宣告另一個 `H?_` 前綴而產生器用 `HJ_`,守衛就是那次之後加的。

## 與契約的關係

契約裡每個前綴、每個站台名都由 `NamingPolicy` 產生([[hand-framework/07-contracts]]),
所以「契約寫 `F1` 而場景寫 `ARM_1`」這種事在生成時就不可能發生。
