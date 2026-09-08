# v9 — 來源

> 回導航 [[hand-framework/v0-INDEX]] · 相關 [[hand-v3/01-prior-art]]、[[hand-v3/v9-references]]

**只列親自存取過的來源。** 取不到就寫 not found。等級:`[親驗]` 本專案自己開頁面讀到的;`[轉引]` 未複核。

## 先例(建模組前的復用檢查,依使用者規則)

| 來源 | 用到的內容 | 等級 | 對本框架的意義 |
|---|---|---|---|
| kg398/100_fingers <https://github.com/kg398/100_fingers> | OpenSCAD 參數化手;**活動鉸鏈無銷**;人手比例範例;GPLv3 程式 / CC BY 4.0 模型 | `[親驗 2026-09-08]` | 銷不是必需品;參數化的**設計決策**可參考,程式碼(GPLv3)不能抄,格式進不了本管線 |
| Polymorph-Intelligence/RoninHand <https://github.com/Polymorph-Intelligence/RoninHand> | **半原地列印**,核心三件;Apache 2.0 / CC BY 4.0 | `[親驗 2026-09-08]` | 同上;組裝更少但間隙控制最難驗 |
| wengmister/BiDexHand <https://github.com/wengmister/BiDexHand> | 參數化 CAD(SolidWorks/STEP),MIT | `[轉引]` | 授權最寬;STEP 進不了規格驅動管線 |
| Yeah Robotic Hand(Hackaday.io 204373) | Blender **modifier** 參數化手,OSHWA | `[轉引 2026-09-08 網搜]` | 最接近「Blender 參數化」,但靠 modifier 堆疊不是規格驅動,無契約驗證 |

**查證結論**:沒有任何一個是 Python/bpy、規格驅動、契約驗證的手框架。可轉移的是設計結論,不是程式碼。
本框架的三層與契約生成在 repo 內建。無銷關節的先例已寫入 [[DEFERRALS]] D-005 的觸發條件。

## 本 repo 內的先例(親驗,不是外部)

| 來源 | 用到的模式 |
|---|---|
| `scripts/presentation_profile.py` + `scripts/archive/README.md` | 「把 fork 變成 profile 常數」——規劃層物件的既定樣式 |
| `src/core/domain/finger_link.py:bearing_seat_cuts` | 「幾何決策當資料放域層」——`PhalanxPlan` 的既定樣式 |
| `tests/unit/core/test_architecture_ssot.py:153-157` | CI 釘住測試的形 |
| `tests/unit/core/test_docs_hand_v3_figures.py` | 三個文件守衛的形,本樹逐一複製 |
| `docs/DEFERRALS.md` D-001…D-003 | 延後必寫觸發條件的格式 |

## 方法

| 來源 | 用到的內容 | 等級 |
|---|---|---|
| requirement-traceability 技能 `assets/trace_check.py` | R1–R6 | `[親驗]`,本輪跑過 |
| verification-plan-design 技能 | v0–v9 樹形、DFMEA、空母數守衛 | `[親驗]` |
