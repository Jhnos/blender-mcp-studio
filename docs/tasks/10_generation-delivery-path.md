# 參數化產生器接上交付路徑

**Status:** ACTIVE

## Goal

讓「產生一個已註冊的機械實例」成為 **port + use case + REST endpoint**，走既有的
`AppRuntime` 與同一條序列化 Blender socket——而不是只有 `scripts/verify/*.py` 這條
CI 專用路徑。做完之後，第四個實例可以用產品做出來，不必再跑腳本。

範圍限一種產生器家族（手實例，`HAND_INSTANCES` 三個 slug）。章魚手與鉸鏈的產生器
在這條縫證明站得住之後才接。

## Context to read

1. `docs/01-architecture.md` — 分層表、ADR-003、安全邊界（**九項 MCP catalog 是刻意固定的**）
2. `src/core/domain/hand_instances.py` — 實例登錄表，本任務唯一的合法輸入來源
3. `src/verification/generated_artifact_bootstrap.py` — 現有的「讓常駐 Blender 重跑產生器」程式碼組裝
4. `scripts/verify/generated_artifact_verify_real.py` — 現行 CI 路徑怎麼把它送進 Blender
5. `docs/LESSONS_LEARNED.md:33` — 常駐程序的 reload 清單手打就會靜默跑舊碼
6. `docs/LESSONS_LEARNED.md:89` — 產生器不是位元組可重現的，回歸判準用面數＋尺寸＋契約

## Specification

### 新增

| 層 | 檔案 | 內容 |
|---|---|---|
| Domain | `src/core/domain/mechanical_generation.py` | `InstanceBuildRequest(slug)`、`InstanceBuildResult(slug, parts, face_counts, dimensions_mm, artifact_paths)`、`UnknownInstanceError` |
| Port | `src/core/ports/mechanical_generation_port.py` | `MechanicalGenerationPort.build_instance()`，回傳 typed DTO（不是 `object`——D-001 的教訓） |
| Use case | `src/core/use_cases/mechanical_generation.py` | 以 `HAND_INSTANCES` 驗 slug；未登錄 → `UnknownInstanceError`；不做任何 narrowing |
| Adapter | `src/adapters/mechanical_generation.py` | 組裝產生器程式碼、經**共用** `BlenderPort` 送出、在邊界翻成 domain error |
| Presentation | `api/routers/generation.py` | `GET /api/instances`、`POST /api/instances/{slug}/build` |

### 約束

- **MCP catalog 不動**。九項是 `docs/01-architecture.md:177` 的明文決策；本任務不碰、不加工具、不改 ADR。
- 不開第二條 socket、不開第二把 lock（ADR-003）。
- `src/core/**` 仍然不 import `src.core` 以外的東西。
- 輸入只有 slug。**request body 不得有任何欄位參與產生器程式碼的組裝**——這是把
  `execute_code` 擋在外面的那道牆，不是慣例。
- reload 清單沿用契約推導出來的那一份，**不得手打第二份**。

### 錯誤對映

| 情況 | HTTP |
|---|---|
| slug 不在登錄表 | 404 |
| Blender 連不上 | 503 |
| 產生器在 Blender 裡拋錯 | 502 |

## Acceptance checks

先寫會紅的那一個：`POST /api/instances/hand-compact/build` 回傳的 `parts` 對得上
`HAND_INSTANCES["hand-compact"]` 的宣稱——今天沒有這條路由，必紅。

- `scripts/ci.sh` 全綠（T1 + T2）。
- 新增守衛 `tests/unit/adapters/test_generation_code_is_registry_derived.py`：
  餵敵意 slug 與多餘的 body 欄位，斷言送進 Blender 的程式碼字串**逐字**只由登錄表推導；
  附一個 should-fire（植入一個會被夾帶的欄位）證明它真的會咬。
- 新增守衛：路由接受的 slug 集合 == `HAND_INSTANCES.keys()`，多一個少一個都紅。
- 新增守衛：adapter 用的 reload 清單 is 契約推導的那一份（同一個物件，不是等值的拷貝）。
- `scripts/ci.sh --real` 新增一條：**同一個實例走 REST 路徑產出的面數與尺寸，
  和走腳本路徑的結果落在同一個 sliver 預算內**。兩條路徑產出不同幾何就紅。
- 雜湊不當判準（LESSONS:89）。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- 域與規劃層**已經在六角形裡**：`src/core/domain/hand_instances.py`、`src/core/planning/hand_plan.py`。
  住在 `scripts/` 的是碰 `bpy` 的組裝、閘門與匯出——分層本身沒錯，缺的是交付路徑。
- 現行唯一的產生入口是 `scripts/verify/generated_artifact_verify_real.py`，
  經 addon 的 `execute_code` 送 `build_generator_code()` 組出來的字串。
- REST 有 13 個 router，MCP 有 9 個工具；不對等是刻意的，不是債。
- 起點：`V01.0R.005` / `4436e5d`，工作區乾淨。

### Open failures

- None yet（尚未動工）。

### Next step

- 寫那個會紅的測試：`tests/integration/api/test_generation_routes.py`，
  斷言 `POST /api/instances/hand-compact/build` 的 `parts` 對得上登錄表的宣稱。
