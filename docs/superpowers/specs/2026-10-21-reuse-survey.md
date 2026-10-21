# reuse-survey.md — 可重用專案普查（Blender MCP Studio，2026-10-21）

> 目的：讓 MCP 從「概念」推到「可列印／虛擬世界模型，物理與機構合規」時，決定每個能力是黑盒包裝、白盒抽片、只借概念，還是自建。
> 標記：[實測]＝本機跑指令看到；[讀]＝讀到頁面／檔案；[推論]＝未驗證。星數／push 日／授權皆 2026-10-21 由 `gh api` 讀取（原始輸出在 `q/`）。
> 可裝性：`pip download --no-deps --only-binary=:all:` 到 scratchpad/wheels（**未安裝**）；wheel 檔名即證據。
> 查詢字串與逐條結果：`reuse-survey-queries.md`。

## 0. 本專案 port 現況（`src/core/ports/`，讀 docstring [讀]）

| Port 檔 | 職責（一行） | 與本普查的關係 |
|---|---|---|
| `blender_port.py` | `BlenderPort`：connect/execute/call_tool、scene_summary、object_details、viewport_screenshot | 所有 Blender 行程內能力的唯一出口 |
| `mcp_port.py` | `MCPPort`：對**另一個 MCP server** call_tool / list_tools / connect | **黑盒接入外部 MCP 子服務的現成 port**（問題 a 的關鍵） |
| `mechanical_generation_port.py` | `InstanceBuilderPort`（在有 bpy 處跑登錄產生器）＋`InstanceCatalogPort` | 參數化幾何若改用 build123d，是擴此 port 或新增 `ParametricCadPort` |
| `print_readiness_port.py` | `PrintReadinessPort.inspect`（Blender 量測）＋`PrintReadinessQueryPort.check` | 切片 CLI、3MF、壁厚守衛掛在這條線之外側 |
| `scene_export_port.py` | `SceneExportPort.export`：Blender 無關的產出物 | glTF/USD/URDF 匯出與驗證 |
| `verification_port.py` | `VerificationRunnerPort.run_suite`＋`VerificationQueryPort` | 機構掃掠、干涉、模擬驗收的登錄入口 |
| `code_sandbox_port.py` | 驗證要送進 Blender exec 的 Python | 外部 CAD 腳本若落地也要過同類閘門 |
| `text3d_port.py` | `Text3DGenerationPort.generate`（Hunyuan3D） | text-to-CAD 若接雲端，形狀與此 port 相同 |
| `llm_port.py` / `vision_port.py` / `prompt_builder_port.py` | LLM chat/tools/stream、影像分析、系統提示 | 多代理 CAD（MAC）概念落地時用 |
| 其餘（batch_transform、event_bus、input_sanitizer、polyhaven、session/snapshot store、adapter_factory） | 與本題無直接關係 | — |

## 1. 概念→參數化幾何（LLM 可驅動）

| 候選 | URL | ★ | 最後 push | 授權 | arm64/cp311 | 取用模式 | 對應 port | 代價 | 風險 |
|---|---|---|---|---|---|---|---|---|---|
| **build123d**（首選核心） | github.com/gumyr/build123d | 3475 | 2026-10-20 | Apache-2.0 | [實測] `build123d-0.13.0-py3-none-any.whl`＋`cadquery_ocp-8.0.1.1.0-cp311-cp311-macosx_11_0_arm64.whl`（62.8 MB） | 白盒／直接依賴（獨立行程，不進 Blender） | 新 `ParametricCadPort`（或擴 `mechanical_generation_port`） | M | OCP wheel 大；需與 Blender 行程分離（OCCT 不在 bpy 內）；LLM 產碼要過 sandbox |
| **CadQuery** | github.com/CadQuery/cadquery | 5968 | 2026-10-18 | Apache-2.0（LICENSE 檔 [讀]；GitHub 標 NOASSERTION） | [實測] `cadquery-2.8.0-py3-none-any.whl` 同 OCP | 白盒（與 build123d 同核心，二擇一） | 同上 | M | Assembly 約束求解器是本專案想要的「機構 DSL」雛形（見 §8） |
| **pzfreo/build123d-mcp** | github.com/pzfreo/build123d-mcp | 124 | 2026-10-15 | Apache-2.0 | [實測] PyPI 0.3.91；README 稱支援 Py 3.11–3.14 [讀] | **黑盒**（stdio 子行程，經 `MCPPort`） | `MCPPort` → 包成 `ParametricCadPort` adapter | S | 其 `execute` 跑任意 build123d 碼——**我方不得再公開**；HTTP 模式無驗證（README 警告）→ 只用 stdio |
| jdilla1277/agentcad | github.com/jdilla1277/agentcad | 168 | 2026-10-19 | Apache-2.0 | [實測] PyPI 0.7.0；README 稱 Py 3.10–3.12 [讀] | 只借概念（`check-spec` 對 spec.json、版本化 STEP、diff） | — | — | 自帶 viewer/review 系統，整包太重 |
| partcad/partcad | github.com/partcad/partcad | 508 | 2026-10-21 | Apache-2.0 | [實測] PyPI 0.8.232 | 只借概念／備選黑盒（`pc mcp`） | — | M | 它是「零件套件管理器」，有自己的 YAML 世界觀；抽片價值在組件 DSL（§8） |
| Pan-Chera/Multi-Agent-CAD | github.com/Pan-Chera/Multi-Agent-CAD | 1043 | 2026-10-17 | MIT | build123d 釘 <0.13 [讀] | 只借概念（plan/geometry/code/repair 分階段＋獨立 Judge＋視覺驗證） | `llm_port` 多代理編排 | — | 預設雲端 LLM；本地 Ollama 未文件化 [讀] |
| OpenSCAD（CLI） | github.com/openscad/openscad | 10477 | 2026-10-18 | GPL-2.0+（含 CGAL 例外）[讀 COPYING] | 本機未裝 [實測]；nightly macOS 11+ universal dmg [讀 openscad.org]；stable 仍 2021.01 [實測 release] | 不取為主引擎；備選黑盒 CLI（只為吃 BOSL2/MCAD 社群庫） | — | S | 第二套 CAD 引擎；09-references 已決定「不引入 OpenSCAD 相依」 |
| Zoo / KittyCAD Text-to-CAD | docs.zoo.dev | kittycad.py 30 | 2026-10-17 | MIT（SDK）；模型不開源 [讀] | [實測] PyPI kittycad 1.8.0 | 不取（雲端、計費 $0.50/min、不可重現）；若要接，形狀同 `text3d_port` | `text3d_port` 同型 | S | 離線／確定性需求不符；text-to-cad-ui 已 archived [實測] |
| Text2CAD / CAD-Recode | github.com/SadilKhan/Text2CAD, filaPro/cad-recode | 489 / 272 | 2025-05 / 2025-11 | CC BY-NC-SA 4.0 [讀] / LICENSE 空 [讀] | — | 不取（授權） | — | — | 研究碼、需 GPU 訓練 |
| Sverchok（Blender 側） | github.com/nortikin/sverchok | 2531 | 2026-10-14 | GPL-3.0 | Blender addon，非 pip | 不取（Blender 5.1 相容未證；我方已有 bpy 產生器鏈） | — | — | 把機構邏輯綁進 node tree，LLM 不好驅動 |
| Geometry Nodes（Blender 內建） | — | — | — | GPL（Blender） | 已在 Blender 5.1 | 只借概念 | `blender_port` | — | 同上 |
| SpatiaOS/Procedura | github.com/SpatiaOS/Procedura | 410 | 2026-10-20 | MIT | 設定腳本只 Linux x86_64 [讀] | 只借概念（一次一件＋檢查改善＋輸出 USD/URDF motion） | — | — | OpenSCAD 後端、Isaac Sim 物理 |
| flowful-ai/cad-skill | github.com/flowful-ai/cad-skill | 689 | 2026-07-14 | **PolyForm Noncommercial** [讀] | — | 不取（授權） | — | — | — |

**為什麼不自建**：OCCT 核心（布林、圓角、STEP）不是能自己寫的；build123d 是 Apache-2.0、純 Python 層、cp311 arm64 wheel 現成。

## 2. 機構／運動學定義與驗證

| 候選 | URL | ★ | 最後 push | 授權 | arm64/cp311 | 取用模式 | 對應 port | 代價 | 風險 |
|---|---|---|---|---|---|---|---|---|---|
| **yourdfpy**（首選） | github.com/clemense/yourdfpy | 297 | 2026-05-10 | MIT | [實測] `yourdfpy-0.0.60-py3-none-any.whl` | 白盒／直接依賴（parse、validate、FK、trimesh 視覺化）[讀] | 新 `MechanismDefinitionPort`（URDF 讀寫） | S | 0.0.x 版號；關節極限處理未在 README 明示 [讀] |
| **pinocchio（pin）** | github.com/stack-of-tasks/pinocchio | 3802 | 2026-10-19 | BSD-2 | [實測] `pin-4.1.0-0-cp311-cp311-macosx_11_0_arm64.whl`（7.1 MB） | 白盒／直接依賴（FK/IK/動力學、關節極限、碰撞對） | `verification_port` 的 runner | M | C++ 綁定、相依 hpp-fcl/eigenpy；功能遠超目前需要 |
| ikpy | github.com/Phylliade/ikpy | 1038 | 2026-08-30 | Apache-2.0 | [實測] `ikpy-4.1.0-py3-none-any.whl` | 白盒（可達性／IK 簡單場景） | 同上 | S | 只做串鏈 IK，不做碰撞 |
| Phobos（Blender addon） | github.com/dfki-ric/phobos | 909 | 2026-07-14 | BSD-3 | 「tested with Blender v3.3 LTS」[讀]；本專案 Blender 5.1 | 只借概念（SMURF＝URDF＋附加 YAML 的分層） | — | — | 版本落差大，不裝 |
| onshape-to-robot | github.com/Rhoban/onshape-to-robot | 640 | 2026-08-26 | MIT | — | 不取（需 Onshape 雲 API）[讀] | — | — | — |
| odio_urdf | github.com/hauptmech/odio_urdf | 106 | 2023-12-15 | **無授權** | — | 不取 | — | — | — |
| urdf2any / sdformat-mjcf | github.com/syundo0730/urdf2any；PyPI sdformat-mjcf | 1 / — | 2026-10-10 | Apache-2.0 / — | [實測] PyPI 0.3.0 / 0.1.2 | 備選黑盒（URDF→USD/MJCF、SDF↔MJCF） | `scene_export_port` | S | 1★、轉換標「近似」[讀 search]；轉後要重驗質量／極限 |
| 本專案既有 FK＋BVH 掃掠＋拆裝碰撞 | repo `lab_electrode_*`、verification suites | — | — | — | 已在 | **保留為 SSOT**；外部格式只當匯出／交換 | `verification_port` | — | — |

**查無**：`'joint limit reachability check python'`、`'urdf blender import'`、`'mjcf urdf converter'` 各 0 筆（gh search）；可達性檢查無獨立套件，靠 pinocchio/ikpy＋自家掃掠。
**為什麼不自建**：URDF 解析／FK 是 commodity；yourdfpy MIT 純 Python，pinocchio 給動力學與極限檢查，省掉自寫數值核。

## 3. 物理／動力學模擬

| 候選 | URL | ★ | 最後 push | 授權 | arm64/cp311 | 取用模式 | 對應 port | 代價 | 風險 |
|---|---|---|---|---|---|---|---|---|---|
| **MuJoCo**（首選） | github.com/google-deepmind/mujoco | 15786 | 2026-10-20 | Apache-2.0 | [實測] `mujoco-3.16.0-cp311-cp311-macosx_11_0_arm64.whl` | 白盒／直接依賴（headless；吃 MJCF；URDF 載入能力 [推論]，需驗） | `verification_port` 新 runner（`SimulationPort`） | M | 接觸參數需調；列印件裝配干涉要自己把 URDF＋mesh 餵進去 |
| Blender rigid body（Bullet，行程內） | — | bullet3 14804 | 2026-10-09 | zlib [讀] | 已在 Blender 5.1 | 自建編排（經 `blender_port`） | `blender_port` | S | 非確定性、無 headless API 以外的控制；只適合粗驗 |
| PyBullet | github.com/bulletphysics/bullet3 | 14804 | 2026-10-09 | zlib | [實測] `--only-binary` **失敗**（無 arm64 wheel，只有 sdist） | 不取（要本機編譯） | — | L | pybullet-planning 2024-11 停更 |
| Genesis | github.com/Genesis-Embodied-AI/Genesis | 30098 | 2026-10-20 | Apache-2.0 | [實測] `genesis_world-1.4.4-py3-none-any.whl`（83.6 MB）＋需 torch；README 未明示 macOS [讀] | 不取（現階段）；只借概念 | — | L | 相依雪球（torch、Quadrants 編譯器） |
| Project Chrono | github.com/projectchrono/chrono | 3101 | 2026-10-21 | BSD-3 | [實測] PyPI pychrono 1.1.0 存在（未下載 wheel） | 備選（多體動力學、柔性體） | — | L | 學習曲線；我方需求 MuJoCo 已夠 |
| Isaac Lab / mjlab | github.com/isaac-sim/IsaacLab；mujocolab/mjlab | 8398 / 3235 | 2026-10-21 / 2026-10-18 | BSD-3＋Omniverse EULA [讀] / Apache-2.0 | isaaclab 無 PyPI [實測]；mjlab 1.6.0 但 MuJoCo-Warp GPU | 不取（NVIDIA GPU/Linux 取向） | — | — | — |
| python-fcl | github.com/BerkeleyAutomation/python-fcl | 271 | 2026-04-08 | BSD-3 | [實測] PyPI 0.7.0.11 | 備選白盒（連續碰撞；09-references 已研究） | `verification_port` | M | 預設 solver 與 C++ 不同（09-references 已記） |
| MuJoCo/PyBullet MCP servers | Rongxuan-Zhou/mujoco-mcp-server 8★ MIT；sandraschi/mujoco-mcp 3★；H-Freax/PybulletMCP 3★ NOLIC | ≤8 | 2026-03〜10 | MIT/無 | — | 不取（太新、無社群）；只借工具命名 | — | — | — |

**查無**：`'assembly interference check python'`、`'physics simulation mcp server'`（1★）、`'robot simulation mcp'` 0 筆。裝配干涉模擬無現成「列印件」專用品；由 URDF＋MuJoCo 或既有 BVH 掃掠自建情境。
**為什麼不自建**：接觸動力學求解器是 MuJoCo 的本業；Apache-2.0、arm64 wheel、headless，無理由重寫。

## 4. 網格驗證／修復

| 候選 | URL | ★ | 最後 push | 授權 | arm64/cp311 | 取用模式 | 對應 port | 代價 | 風險 |
|---|---|---|---|---|---|---|---|---|---|
| **trimesh**（首選） | github.com/mikedh/trimesh | 3704 | 2026-10-20 | MIT | [實測] `trimesh-5.1.1-py3-none-any.whl` | 白盒／直接依賴（watertight、winding、volume、proximity、射線壁厚） | `print_readiness_port` 外側獨立 oracle | S | 壁厚射線法需 rtree/embreex（二手來源 [weak]） |
| **manifold3d** | github.com/elalish/manifold | 2364 | 2026-10-21 | Apache-2.0 | [實測] `manifold3d-3.5.4-cp311-cp311-macosx_11_0_arm64.whl` | 白盒／直接依賴（保證流形的布林；Blender 4.5+ 內建同核心 [讀 09-references]） | 新 `MeshRepairPort` | S | 輸入必須先是流形；與 Blender 內建 Manifold solver 行為要對照 |
| CGAL（已在 env） | github.com/CGAL/cgal | 6084 | 2026-10-17 | 混合 GPL/LGPL [讀] | [實測] env 已有 `cgal==6.0.1.post202410241521` | 保留現況（自交／拓樸守衛） | 既有 `mesh_integrity` | — | SWIG 警告（09-references 已記） |
| Open3D | github.com/isl-org/Open3D | 14110 | 2026-09-30 | MIT [讀] | [實測] `open3d-0.20.0-cp311-...arm64.whl`（54.5 MB） | 備選（與 trimesh 重疊；大） | — | M | 體積大、相依多 |
| pymeshfix | github.com/pyvista/pymeshfix | 410 | 2026-10-06 | **GPL-3.0** | [實測] `pymeshfix-0.18.1-cp311-...arm64.whl` | 黑盒 subprocess（只在需要補洞時） | `MeshRepairPort` | S | GPL → 必須隔行程、明標 |
| PyMeshLab | github.com/cnr-isti-vclab/PyMeshLab | 983 | 2026-02-03 | **GPL-3.0** | [實測] `pymeshlab-2025.7.post1-cp311-...arm64.whl`（65 MB） | 黑盒 subprocess（備選） | 同上 | S | GPL、65 MB |
| admesh / python-admesh | github.com/admesh/admesh | 257 / 9 | 2026-02-20 | GPL-2.0 | CLI 需 brew | 不取（trimesh 已覆蓋 STL 修復） | — | — | — |
| libigl-python-bindings | github.com/libigl/libigl-python-bindings | 370 | 2026-09-04 | GPL-3.0 | — | 不取 | — | — | — |
| lib3mf | 見 §5 | — | — | BSD-2 | universal2 wheel | 3MF 層級驗證 | — | — | — |

**查無**：`'mesh wall thickness analysis'`、`'mesh repair watertight python'` 0 筆（gh）；WebSearch 無專用 OSS 壁厚庫 → 壁厚／最小特徵仍**自建**（Blender BVH 射線或 trimesh 射線），以本專案 mm 判準為 SSOT。
**為什麼不自建**：流形布林（manifold）與基本水密／體積檢查是成熟演算法，Apache/MIT wheel 現成；自建只做本專案特有判準。

## 5. 列印就緒與切片（CLI）

| 候選 | URL | ★ | 最後 push | 授權 | macOS arm64 | 取用模式 | 對應 port | 代價 | 風險 |
|---|---|---|---|---|---|---|---|---|---|
| **Bambu Studio CLI**（首選） | github.com/bambulab/BambuStudio | 5137 | 2026-10-13 | **AGPL-3.0** | [實測] release v02.08.02.61 `Bambu_Studio_mac-*.dmg`；本 repo v80 已在本機跑過官方 CLI（return_code 0、`--info` 重讀）[讀]；**目前 /Applications 未裝** [實測] | **黑盒 subprocess**（AGPL 隔行程、明標、不連結） | 新 `SlicerPort`（`print_readiness_port` 外側） | S | 原廠 P2S 設定只在它；`--load-settings` 限 1 machine+1 process；T65535 結尾訊息（v80 已記）；App 路徑 [推論] `BambuStudio.app/Contents/MacOS/BambuStudio` |
| **OrcaSlicer CLI**（備選） | github.com/OrcaSlicer/OrcaSlicer | 16047 | 2026-10-21 | AGPL-3.0 | [實測] v2.4.2 `OrcaSlicer_Mac_universal_V2.4.2.dmg`；wiki 文件化 `--slice/--export-3mf/--outputdir/--export-statistics` [讀] | 黑盒 subprocess | `SlicerPort` 第二實作 | S | 同 AGPL；P2S 設定需自行維護 |
| PrusaSlicer CLI | github.com/prusa3d/PrusaSlicer | 9421 | 2026-09-21 | AGPL-3.0 | [實測] 2.9.6 dmg；mac 路徑與旗標只有論壇來源 [weak]；官方 help 文章 404 [實測] | 備選黑盒 | 同上 | S | 無 Bambu 機型原生設定 |
| CuraEngine | github.com/Ultimaker/CuraEngine | 1858 | 2026-10-20 | AGPL-3.0 | 最後 GitHub release **2017** [實測]；無 mac 單獨二進位 | 不取 | — | — | — |
| **lib3mf** | github.com/3MFConsortium/lib3mf | 314 | 2026-10-19 | BSD-2 | [實測] `lib3mf-2.5.0-py3-none-macosx_10_9_universal2.whl` | 白盒／直接依賴（讀寫 3MF、驗 metadata） | `SlicerPort` 產出物驗證 | S | 無現成「3MF validator」（查無），驗證邏輯自建於 lib3mf 之上 |
| Tweaker-3（方向） | github.com/ChristophSchranz/Tweaker-3 | 110 | 2026-03-24 | GPL-3.0 | **不在 PyPI** [實測]（git install） | 只借概念／備選黑盒；Bambu/Orca 自帶 `--orient` | — | S | GPL |
| DMontgomery40/bambu-printer-mcp | github.com/DMontgomery40/bambu-printer-mcp | 217 | 2026-10-20 | GPL-2.0 | Node 24；呼叫 Bambu/Orca CLI [讀] | 只借概念（slice template 流程、CLI 旗標組合） | — | — | GPL-2.0、Node、含印表機控制（本專案範圍外） |

**查無**：`'3d print overhang analysis python'`、`'slicer cli automation python'`、`'3mf validator'`、`'3d printing mcp server slicer'` 0 筆。懸垂／支撐分析用切片器 `--export-statistics`／`--export-slicedata` 讀回，不另找庫。
**為什麼不自建**：切片器是數十萬行的 AGPL 專案，且 P2S 原廠設定只有 Bambu Studio 有；隔行程黑盒是唯一合理路徑（v80 已證明可行）。

## 6. 虛擬世界模型匯出與驗證

| 候選 | URL | ★ | 最後 push | 授權 | arm64/cp311 | 取用模式 | 對應 port | 代價 | 風險 |
|---|---|---|---|---|---|---|---|---|---|
| Blender glTF 匯出（內建） | github.com/KhronosGroup/glTF-Blender-IO | 1665 | 2026-10-17 | Apache-2.0 | 已在 Blender 5.1 | 經 `blender_port` 呼叫（既有 export 路徑） | `scene_export_port` | S | — |
| **glTF-Validator** | github.com/KhronosGroup/glTF-Validator | 475 | 2026-10-06 | Apache-2.0 | [實測] 2.0.0-dev.3.10（2024-10-22，prerelease）資產只有 `macos64`（x86_64 → Rosetta）；**npm `gltf-validator` 2.0.0-dev.3.10 Apache-2.0** [實測]；本機有 node [實測] | 黑盒（`npx gltf-validator` 子行程） | `scene_export_port` 驗證 | S | 兩年無新版；dev 標籤 |
| **gltf-transform CLI** | github.com/donmccurdy/glTF-Transform | 1988 | 2026-10-20 | MIT | [實測] npm `@gltf-transform/cli` 4.5.1 | 黑盒（inspect/validate/optimize） | 同上 | S | Node 相依 |
| pygltflib | PyPI | — | — | — | [實測] `pygltflib-1.16.5-py3-none-any.whl` | 白盒（讀寫 glTF JSON、extras 標註碰撞體） | 同上 | S | — |
| **OpenUSD（usd-core）** | github.com/PixarAnimationStudios/OpenUSD | 7550 | 2026-10-20 | TOST（Apache 修改版）[讀] | [實測] `usd_core-26.8-cp311-none-macosx_10_15_universal2.whl` | 白盒／直接依賴（UsdPhysics schema 標碰撞體／剛體；Blender USD 匯出 [推論] 可用） | `scene_export_port` | M | 40 MB；USD 匯出在 Blender 5.1 的 physics 欄位覆蓋度未驗 |
| KHR_physics_rigid_bodies（glTF 物理擴充） | github.com/eoineoineoin/glTF_Physics；Blender exporter | 57 / 36 | 2026-04 / 2026-03 | 無 / GPL-3.0 | 規格「proposed」未合入 Khronos [讀]；exporter 未註明 Blender 版本 [讀] | 只借概念（等批准）；短期用 glTF `extras` 自標 | — | — | 擴充改名風險（Babylon 文件提醒）[讀] |

**查無**：`'usd python blender'`、`'gltf physics extension collision'`、`'KHR_physics_rigid_bodies'`、`'usd physics schema export blender'` 0 筆（gh）。
**為什麼不自建**：glTF/USD 讀寫與驗證都有一方標準工具；自建只做「碰撞體與物理屬性標註」這層契約。

## 7. 既有 CAD／模擬／列印 MCP server

| 候選 | URL | ★ | 最後 push | 授權 | 判斷 | 取用模式 |
|---|---|---|---|---|---|---|
| **pzfreo/build123d-mcp** | github.com/pzfreo/build123d-mcp | 124 | 2026-10-15 | Apache-2.0 | headless、PyPI、Py 3.11 OK、自帶 measure/validate/printability/export [讀] | **黑盒子服務（唯一值得直接接的）** |
| jdilla1277/agentcad（MCP 模式） | github.com/jdilla1277/agentcad | 168 | 2026-10-19 | Apache-2.0 | CLI 為主、MCP 為輔；check-spec 好 | 只借概念 |
| partcad `pc mcp` | github.com/partcad/partcad | 508 | 2026-10-21 | Apache-2.0 | 有 `execute` 工具；世界觀重 | 備選黑盒 |
| neka-nat/freecad-mcp | github.com/neka-nat/freecad-mcp | 2982 | 2026-10-13 | MIT（FreeCAD LGPL-2.1） | 需 FreeCAD GUI 開 RPC；可跑任意 Python [讀] | 不取（GUI 相依、等同 execute_code） |
| Fusion 360 MCP（faust-machines 等） | github.com/faust-machines/fusion360-mcp-server | 127 | 2026-10-06 | MIT | 綁專有 Fusion GUI | 不取 |
| Onshape MCP（jarvis 174★ / hedless 154★） | github.com/hedless/onshape-mcp | 154 | 2026-09-10 | 無 / other | 雲端 | 不取 |
| jhacksman/OpenSCAD-MCP-Server | github.com/jhacksman/OpenSCAD-MCP-Server | 208 | 2026-09-07 | MIT | 需 OpenSCAD 二進位 | 備選（若要吃 SCAD 庫） |
| ahujasid/blender-mcp 與分支 | github.com/ahujasid/blender-mcp；seehiong/blender-mcp-bridge 78★ MIT；bpy-dev 98★ GPL-3.0；sandraschi 62★ MIT | 31813 | 2026-10-20 | MIT | 本專案 ADR-001 已包其 addon；分支多是加工具數 | 只借概念（工具目錄），不換 |
| MuJoCo / PyBullet MCP | 見 §3 | ≤8 | — | MIT/無 | 太新 | 不取 |
| DMontgomery40/bambu-printer-mcp | 見 §5 | 217 | 2026-10-20 | GPL-2.0 | Node、印表機控制 | 只借概念 |
| gNucleus/text-to-cad-mcp | github.com/gNucleus/text-to-cad-mcp | 18 | 2025-07-30 | MIT | 雲端服務包裝 | 不取 |

## 8. 規格／約束定義與公差

| 候選 | URL | ★ | 最後 push | 授權 | 可裝性 | 取用模式 | 對應 port | 代價 | 風險 |
|---|---|---|---|---|---|---|---|---|---|
| **URDF（經 yourdfpy）當機構 SSOT** | 見 §2 | — | — | MIT | 純 Python | 白盒；由本專案 domain spec 生成 | `MechanismDefinitionPort` | M | 無閉鏈 [讀]；公差欄位要用 extras/自訂 YAML（SMURF 概念） |
| CadQuery `Assembly.constrain` | cadquery.readthedocs.io classreference | 5968 | 2026-10-18 | Apache-2.0 | 同 §1 | 白盒（Plane/Point/Axis/PointInPlane/Fixed*/PointOnLine/FixedRotation 約束＋`solve()`）[讀] | `ParametricCadPort` | S | 約束種類隨版本變；只做剛性裝配，不做公差 |
| PartCAD YAML 組件（URDF-style joints） | github.com/partcad/partcad | 508 | 2026-10-21 | Apache-2.0 | PyPI | 只借概念（零件/介面/mating 分層） | — | — | — |
| stackcore（公差疊加 Monte Carlo） | pypi.org/project/stackcore | — | — | 不明 [讀] | [實測] PyPI 0.3.3 | 不取；worst-case/RSS/MC 用 numpy 自建十行 | — | S | 授權與維護不明 |
| PLA 配合間隙資料庫 | （查無） | — | — | — | — | **自建**：以本專案試片（3 mm 距離、M3 五金、v6b coupon）為 SSOT；外部只有單機經驗值 0.1–0.3 mm [weak] | `print_readiness` 判準表 | S | 外部值不可當合格證據 |
| ISO 286 配合計算 | （查無 Python 套件） | — | — | — | — | 自建（表格小） | — | S | — |

**查無**（gh search 9 條全 0）：`'tolerance analysis python'`、`'3d printing tolerance clearance database'`、`'mechanism definition dsl'`、`'GD&T python'`、`'3d print fit tolerance test pla'`、`'parametric assembly constraints python'`、`'fits and clearances calculator'`、`'tolerance stack-up monte carlo'`、`'ISO 286 fits python'`。
**為什麼自建**：這一層是本專案的領域知識（PLA、P2S、M3）；沒有現成資料庫，且公差規則要能被驗證套件引用，放在自家 domain 才對。

## 三個特別問題

### (a) 有沒有一個 CAD／模擬 MCP server 值得直接黑盒接進來？

**有，一個：pzfreo/build123d-mcp**（Apache-2.0、PyPI 0.3.91、stdio、Py 3.11–3.14 [讀]；工具含 measure／validate／printability／export STEP+STL [讀]）。接法：本專案已有 `MCPPort`（call_tool/list_tools）[讀 src/core/ports/mcp_port.py]，寫一個 adapter 把它包成 `ParametricCadPort`，只暴露「由登錄規格建模→量測→匯出」三個 curated 用例；**其 `execute`（任意 build123d 碼）不得透出成公開 MCP 工具**，與本專案「不開 execute_code」一致。只用 stdio（README 自述 HTTP 模式無驗證、單 session [讀]）。
模擬類 MCP（MuJoCo/PyBullet）全 ≤8★、2026 年才出現 [實測]，不值得接；直接用 `mujoco` wheel 自建 runner。CAD 類 FreeCAD/Fusion/Onshape MCP 都綁 GUI 或雲端 [讀]，不符 headless。
[推論] 第二階段若 MCP hop 延遲或 session 狀態成問題，改為白盒抽其 measure/validate 函式（Apache-2.0 可改寫）進我方 adapter；黑盒先行是為了用最低成本驗證「LLM→build123d→量測」迴圈值不值。

### (b) 機構定義用哪個現成格式當 SSOT？

**URDF 當交換 SSOT，本專案 domain spec 當作者層**。理由：(1) 列印側要的是「連桿→網格檔＋關節軸／極限」，URDF 直接給 [讀 yourdfpy README]；(2) 模擬側 MuJoCo 可讀 URDF [推論，需在 runner 驗證]，另有 urdf2any（→USD/MJCF）與 sdformat-mjcf 轉換 [實測 PyPI 存在]；(3) 產業共識是「URDF 作者、往 MJCF/USD 轉」[讀 WebSearch]。不選 MJCF（MuJoCo 專屬，列印側無用）、不選 SDF（工具鏈少，但它有閉鏈——若本專案出現閉鏈機構（四連桿案）再升級成 SDF 或 SMURF 式 URDF＋YAML 附件）。公差／配合／材料欄位 URDF 沒有 → 用 SMURF 概念（Phobos）：URDF＋旁掛 YAML，由本專案 domain 定義 schema。
[讀 09-references] 既有 FK、BVH 掃掠、拆裝碰撞已是驗證 SSOT；URDF 是它們的**輸出契約**，不是取代。

### (c) 切片與列印就緒：哪個 CLI 在 macOS arm64 可無頭自動化且授權允許？

**Bambu Studio CLI，備選 OrcaSlicer。** 證據：本 repo v80 已在本機用官方 CLI 02.08.02.61 離線切 69 件、`--info` 重讀、return_code 0 [讀 v80 README]；每版附 mac dmg [實測 release 資產]；旗標 `--slice/--export-3mf/--export-slicedata/--load-settings/--load-filaments/--outputdir/--info/--orient/--arrange` 有官方 wiki [讀]。授權 AGPL-3.0 [實測]：**只能 subprocess 黑盒**（不連結、不改碼、manifest 明標 AGPL、記錄版本與 SHA256）；AGPL 的網路條款不觸發，因為我方不散布修改版且 CLI 不是對外服務的一部分 [推論，建議法務確認]。
OrcaSlicer v2.4.2 universal dmg [實測]、CLI 文件比 Bambu 完整 [讀]，但無 P2S 原廠設定；PrusaSlicer 可用但路徑只有論壇來源 [weak]；CuraEngine 2017 後無獨立 release [實測]。
現況缺口 [實測]：/Applications 現在沒有任何切片器——v80 用的 DMG 路徑未落在 repo 文件，接 `SlicerPort` 前要先把二進位位置與版本釘進 services/config SSOT。

## 建議整體整合形狀（供設計文件用）

| 模式 | 項目 |
|---|---|
| 黑盒（子行程／MCP） | Bambu Studio CLI（AGPL）、build123d-mcp（stdio）、`npx gltf-validator`＋`@gltf-transform/cli`、pymeshfix/pymeshlab（GPL，僅補洞時） |
| 白盒／直接依賴（寬鬆授權） | build123d＋cadquery-ocp、trimesh、manifold3d、lib3mf、yourdfpy、pinocchio（視需要）、mujoco、usd-core、pygltflib |
| 自建 | 各 port 與 adapter、domain spec→URDF 發射器、公差／配合表（自家試片）、壁厚／最小特徵判準、MCP curated 工具面 |
| 只借概念 | MAC 的分階段＋Judge、agentcad `check-spec`、Procedura 一次一件迴圈、bambu-printer-mcp 的切片模板流、CadQuery 約束種類、SMURF 分層 |
| 不取 | Zoo（雲、計費）、Text2CAD/CAD-Recode/cad-skill/cad-agent（授權）、Phobos（Blender 3.3）、onshape-to-robot（雲）、PyBullet（無 arm64 wheel）、Isaac Lab、FreeCAD/Fusion/Onshape MCP、Sverchok |

## 未覆蓋與限制

- 未安裝、未 import 任何候選；「可裝」只到 wheel 標籤層。build123d-mcp 的 3.11 相容只讀 README。
- 未檢索學術庫；論壇來源只用於 PrusaSlicer 路徑與 PLA 間隙，皆標 [weak]。
- MuJoCo 讀 URDF、Blender 5.1 USD physics 匯出、Bambu `.app` 內二進位路徑三項為 [推論]，接入前各需一次實測。
