# 01 — 模組邊界與層規則

> 回導航 [[hand-framework]] · 相關 [[hand-framework/04-plans]]、[[hand-framework/05-execution]]、[[01-architecture]]

## 三層,方向只有一個

```
規格(domain,純)  →  規劃(planning,純)  →  執行(bpy)
   算數字               把數字變成具名指令      只執行,不算術
```

- **domain** 不匯入 bpy、FastAPI、FastMCP(`test_architecture_ssot` 擋)。
- **planning** 是新層:純函式與凍結 dataclass,輸入規格、輸出「要建什麼、叫什麼、擺哪裡、量哪裡」。
  它存在的理由是**可以在沒有 Blender 的機器上測**——目前佈局換行、站台、探針點全困在 `import bpy` 後面。
- **execution** 只讀規劃:mm→m、呼叫 primitive、跑布林。**執行層裡出現算術就是違規**(ES-5)。

## 模組地圖

| 模組 | 層 | 狀態 | 職責 |
|---|---|---|---|
| `src/core/domain/finger_link.py` | domain | 既有 | `FingerLinkSpec` Protocol、`bearing_seat_cuts` |
| `src/core/domain/hinge_chain.py` | domain | 既有,凍結 | 借來的連桿;只允許**加法式**唯讀屬性 |
| `src/core/domain/compact_link.py` | domain | 既有 | 精簡連桿 |
| `src/core/domain/finger_v3.py` | domain | 既有 | 單腱手指:力矩臂、彈簧梯度、行程、夾層上界 |
| `src/core/domain/palm_v3.py` | domain | 已泛化(M4) | 見 [[hand-framework/03-domain-spec]];類名不變 |
| `src/core/domain/opposition.py` | domain | 已建(M4) | 對生可達性函式(從掌盤切出,因 372/380 行預算) |
| `src/core/domain/hand_instances.py` | domain | 已建(M2) | `HAND_INSTANCES` 註冊表——**唯一**命名實例的地方 |
| `src/core/planning/naming.py` | planning | 已建(M2) | `NamingPolicy`,見 [[hand-framework/06-naming]] |
| `src/core/planning/phalanx_plan.py` | planning | 已建(M3) | 每節的名字、孔、座、公母端尺寸 |
| `src/core/planning/station_plan.py` | planning | 已建(M2) | 站台原點、基底、鏈;拇指基底算一次 |
| `src/core/planning/route_plan.py` | planning | 已建(M3) | 站台 × 路徑 → 孔 |
| `src/core/planning/palm_plan.py` | planning | 已建(M3) | 板、拇指丘、根、進氣口、袖口夾的具名實體與順序 |
| `src/core/planning/csg.py` | planning | 已建(M3) | 規劃可要求的實體詞彙:Box、Cylinder、Ellipsoid、HollowBox |
| `src/core/planning/presentation_plan.py` | planning | 已建(M3) | 視角、框選、調色盤、圖說 |
| `src/core/planning/layout_plan.py` | planning | 已建(M2) | 換行擺盤算術 |
| `src/core/planning/expected_counts.py` | planning | 已建(M2) | 節數、單元數、佈局件數、站台清單 |
| `src/core/planning/probe_plan.py` | planning | 已建(M2) | 探針點、掃掠角、閉合軌跡參數 |
| `src/core/planning/hand_plan.py` | planning | 已建(M2) | 把以上組成一個 `HandPlan` |
| `src/verification/generator_imports.py` | verification | 已建(M2) | 讀原始碼推導產生器的 import 閉包(ES-6) |
| `src/verification/contract_builder.py` | verification | 已建(M2) | 規劃 → 契約 JSON,見 [[hand-framework/07-contracts]] |
| `src/verification/package_reproduction.py` | verification | 已建(M1) | 重現差分的純核心 |
| `scripts/hand_{geometry,presentation,gates,generator}.py` | execution | 已建(M3) | 只執行規劃;ES-5 掃描綠 |
| `scripts/model_finger_v3.py` | execution | 已縮成 shim(M3) | 契約、manifest、測試、regex 都指名它 |
| `scripts/model_hand_v3_gradient.py` | execution | 已建(M5) | 驗證夾具入口:V3 連桿、兩個零件號、`HG_` 命名空間 |
| `scripts/model_hand_compact.py` | execution | M6 | 精簡實例入口 |
| `scripts/finger_v3_geometry.py`、`palm_v3_geometry.py`、`finger_v3_presentation.py` | execution | **已刪除**(M3,差分綠後) | 不留兩套 |

## 必須重用、不得重造(親驗)

- `scripts/presentation_profile.py`:`PresentationProfile`、`StackedAssembly`、`FINGER_PROFILE`
- `scripts/hollow_hinge_render.py:setup_render`
- `scripts/blender_generator_runner.py:run_generator(build, prefix)`
- `scripts/blender_mesh_primitives.py`:`add_cylinder`、`add_ellipsoid`、`boolean`、`cleanup_mesh`
- `scripts/hollow_hinge_geometry.py:create_box`
- `src/verification/artifact_files.py:binary_stl_metrics`
- `tests/unit/scripts/test_script_primitive_ssot.py`:新 bpy 模組不得重打 primitive
- `docs/DEFERRALS.md` 的延後格式

## 三條層規則

1. **規劃層的每個物件都要能不開 Blender 就測**——測試放 `tests/unit/planning/`。
2. **執行層不出現字面尺寸、字面名字**——全部來自規劃與 `NamingPolicy`。
3. **凍結的東西只能加法式擴充**——`HingePhalanxSpec` 加唯讀屬性可以,改任何欄位不行。
