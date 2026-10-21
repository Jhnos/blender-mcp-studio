# reuse-survey-queries.md — 每條查詢字串與回傳摘要（2026-10-21）

> 原始輸出逐檔保存在同目錄 `q/`（`cap*.txt`、`repo-meta-*.txt`、`releases-licenses.txt`、`pip-index.txt`、`pip-wheels.txt`、`pip-npm-extra.txt`、`final-lookups.txt`）。
> 工具：`gh search repos "<q>" --sort stars --limit N --json fullName,stargazersCount,pushedAt,license,description`（gh 已登入帳號 Jhnos）；`gh api repos/<o>/<n>`；`gh api repos/<o>/<n>/releases/latest`；`gh api repos/<o>/<n>/contents/<LICENSE>`；`pip index versions`；`pip download --no-deps --only-binary=:all: --dest scratchpad/wheels`；`npm view`；WebSearch；WebFetch。
> 註：第一輪 ~40 條 `gh search` 在 1 分鐘內打出去，觸發 search API 403 rate limit；改用 2.5 s 節流＋403 後等 65 s 重試（`ghsearch.py`），全部重跑成功。`gh search` 只做 repo 名稱／描述比對，字數多的描述性查詢常回 0 筆，屬查詢形式限制，不等於不存在——這類已另以 WebSearch 補查。

## 能力 1：概念→參數化幾何

| 查詢 | 回傳摘要（前幾筆＋一行判斷） |
|---|---|
| `gh search repos 'cadquery' --limit 8` | CadQuery/cadquery 5968★；gumyr/build123d 3475★；CQ-editor 1262★；**flowful-ai/cad-skill 689★**（LLM 技能，PolyForm NC → 不取）；partcad/partcad 508★ Apache-2.0；vscode-ocp-cad-viewer 418★。→ 主候選：cadquery、build123d、partcad |
| `gh search repos 'build123d' --limit 8` | gumyr/build123d 3475★；**Pan-Chera/Multi-Agent-CAD 1043★ MIT**（多代理 text-to-CAD）；partcad 508★；forgent3d 254★；**jdilla1277/agentcad 168★ Apache-2.0**（CLI+MCP）；**pzfreo/build123d-mcp 124★ Apache-2.0** |
| `gh search repos 'build123d mcp' --limit 8` | Svetlana-DAO-LLC/cad-agent 53★（PolyForm Small Business → 不取）；pzfreo/cadgenbench-build123d 6★；lightsong-agents/cad-design-skill 0★；superWorldSavior/engineering-toolchain 0★。→ 生態繞著 build123d-mcp 長 |
| `gh search repos 'cadquery mcp server' --limit 8` | rishigundakaram/cadquery-mcp-server 20★ NOLIC（2025-06 停）；naturecodec-stack 0★。→ CadQuery 專屬 MCP 無成熟品 |
| `gh search repos 'text2cad' --limit 8` | SadilKhan/Text2CAD 489★（NeurIPS'24；授權 CC BY-NC-SA → 不取）；MLYengineering/Text2CAD 7★ MIT（契約驅動、headless）；其餘 ≤13★ |
| `gh search repos 'cad-recode' --limit 8` | filaPro/cad-recode 272★（ICCV2025，點雲→CAD code，LICENSE 檔空 → 不取）；其餘 ≤3★ |
| `gh search repos 'text to cad llm' --limit 8` | **0 筆**（查詢形式限制；由 build123d／kittycad 查詢補） |
| `gh search repos 'llm cad generation parametric' --limit 8` | **0 筆** |
| `gh search repos 'zoo kittycad text-to-cad' --limit 8` | **0 筆**；改 `'zoo text-to-cad'` → KittyCAD/text-to-cad-ui 296★ MIT（**archived**）、rojosinalma/cad-render 1★ AGPL；`'kittycad'` → kittycad.py 30★ MIT、modeling-api 29★ |
| `gh search repos 'sverchok' --limit 8` | nortikin/sverchok 2531★ GPL-3.0；Irev-Dev/curated-code-cad 327★ MIT（code-CAD 清單）；sverchok-extra 65★ |
| `gh search repos 'openscad python' --limit 8` | 全部 ≤1★（jstebbins/openscad-python-wrapper GPL-2.0 等）；→ OpenSCAD 的 Python 路徑靠官方 nightly／PythonSCAD，不是 pip 套件 |
| `gh search repos 'openusd'`（順帶） | SpatiaOS/Procedura 410★ MIT「text prompt → editable parametric program」（OpenSCAD 後端，Linux x86_64 腳本） |
| WebSearch `Zoo KittyCAD Text-to-CAD API python SDK pricing open source` | docs.zoo.dev FAQ：40 分鐘/月免費後 $0.50/min；UI 開源、**模型不開源**；雲端服務 |
| WebSearch `OpenSCAD macOS Apple Silicon arm64 download nightly 2025 release command line headless` | openscad.org/downloads：development snapshot 為 macOS 11+ universal（Intel+Apple Silicon）dmg；stable 仍 2021.01 |
| WebSearch `OpenSCAD 2025 release Python support "pythonscad" ... macOS arm64` | 2025-05 郵件列表：Python 支援只在自編譯／AppImage／Flatpak 可用；PythonSCAD mac 安裝器有問題 |
| `pip index versions cadquery / build123d / partcad / agentcad / build123d-mcp / kittycad / solidpython2 / pyopenscad / openscad` | 2.8.0 / 0.13.0 / 0.8.232 / 0.7.0 / 0.3.91 / 1.8.0 / 2.1.3 / **無** / **無** |
| `pip download --only-binary=:all: cadquery-ocp build123d cadquery` | `cadquery_ocp-8.0.1.1.0-cp311-cp311-macosx_11_0_arm64.whl`（62.8 MB）、`build123d-0.13.0-py3-none-any.whl`、`cadquery-2.8.0-py3-none-any.whl` |

## 能力 2：機構／運動學定義與驗證

| 查詢 | 回傳摘要 |
|---|---|
| `gh search repos 'yourdfpy' --limit 6` | clemense/yourdfpy 297★ MIT；conda-forge feedstock；Pyroki_MultiCapsuleFit（yourdfpy+trimesh 做碰撞膠囊） |
| `gh search repos 'urdfpy' --limit 6` | mmatl/urdfpy 318★ MIT（最後 push 2024-08，停維護，有人 fork 修 bug）→ 以 yourdfpy 取代 |
| `gh search repos 'phobos' --limit 6` | dfki-ric/phobos 909★ BSD-3（Blender addon，URDF/SDF/SMURF）；其餘同名無關 |
| `gh search repos 'phobos blender' --limit 6` | 只有 1 個教學 repo 0★ |
| `gh search repos 'onshape-to-robot' --limit 6` | Rhoban/onshape-to-robot 640★ MIT（需 Onshape 雲 API）；neurobionics/onshape-robotics-toolkit 308★ |
| `gh search repos 'ikpy' --limit 6` | Phylliade/ikpy 1038★ Apache-2.0 |
| `gh search repos 'pinocchio' --limit 6` | stack-of-tasks/pinocchio 3802★ BSD-2；pink 863★（IK）；roboplan 455★ MIT（motion planning on Pinocchio） |
| `gh search repos 'pinocchio robotics' --limit 6` | 只 ≤3★ 包裝 repo |
| `gh search repos 'odio_urdf' --limit 6` | hauptmech/odio_urdf 106★ **NOLIC**，2023-12 停 |
| `gh search repos 'urdf python' --limit 6` | 2 筆 0★ 作業 repo（查詢字太泛） |
| `gh search repos 'mjcf urdf converter'`、`'urdf blender import'`、`'joint limit reachability check python'`、`'robot description format converter'` | **各 0 筆** |
| `gh search repos 'urdf2any'` / `'sdformat mjcf'` | syundo0730/urdf2any 1★ Apache-2.0（URDF→USD/MJCF）；sdformat-mjcf 只見 conda-forge feedstock |
| WebSearch `URDF vs MJCF vs SDF robot description format single source of truth conversion tools 2025` | 共識：URDF 當作者 SSOT、往 MJCF/USD 轉；URDF 無閉鏈、SDF 有；urdf2any、sdformat-mjcf、mujoco_ros2_control 轉換工具皆標「近似／實驗性」 |
| WebSearch `Phobos Blender add-on Blender 4.x 5.x compatibility URDF export 2025 2026` | 只找到「tested with Blender v3.3 LTS」；無 4.x/5.x 相容聲明 |
| `pip index` / `pip download` | yourdfpy 0.0.60 pure wheel；ikpy 4.1.0 pure；**pin 4.1.0 cp311 arm64 wheel（7.1 MB）**；urdf2any 0.3.0；sdformat-mjcf 0.1.2；python-fcl 0.7.0.11 |

## 能力 3：物理／動力學模擬

| 查詢 | 回傳摘要 |
|---|---|
| `gh search repos 'pybullet' --limit 6` | bulletphysics/bullet3 14804★（zlib）；其餘為 RL 環境 |
| `gh search repos 'mujoco' --limit 6` | google-deepmind/mujoco 15786★ Apache-2.0；dm_control 4715★；mujoco_menagerie 4232★ |
| `gh search repos 'genesis physics simulation' --limit 6` | 只 2 筆 1★ 衍生；主 repo 另以 `gh api repos/Genesis-Embodied-AI/Genesis` 讀：30098★ Apache-2.0 |
| `gh search repos 'isaac lab' --limit 6` | isaac-sim/IsaacLab 8398★；**mujocolab/mjlab 3235★ Apache-2.0**（Isaac Lab API on MuJoCo-Warp） |
| `gh search repos 'project chrono' --limit 6` | 全是同名無關專案；主 repo 另以 `gh api repos/projectchrono/chrono`：3101★ BSD-3 |
| `gh search repos 'mujoco mcp' --limit 6` | Rongxuan-Zhou/mujoco-mcp-server 8★ MIT；ros-claw/unitree-mujoco-mcp 6★；sandraschi/mujoco-mcp 3★ MIT；其餘 ≤2★ |
| `gh search repos 'pybullet mcp' --limit 6` | H-Freax/PybulletMCP 3★ NOLIC；M1ndSmith 0★ MIT |
| `gh search repos 'physics simulation mcp server'` / `'robot simulation mcp'` / `'assembly interference check python'` | 1★ / 0 / 0 |
| `gh search repos 'pybullet planning' --limit 6` | caelan/pybullet-planning 471★ MIT（2024-11 停）；yijiangh/pybullet_planning 138★ MIT |
| `pip download --only-binary=:all: pybullet` | **失敗：No matching distribution**（無 arm64 wheel，只有 sdist） |
| `pip download mujoco / genesis-world` | `mujoco-3.16.0-cp311-cp311-macosx_11_0_arm64.whl`（28 MB）；`genesis_world-1.4.4-py3-none-any.whl`（83.6 MB，另需 torch） |
| `pip index versions pychrono / mjlab / isaaclab` | 1.1.0 / 1.6.0 / **無** |
| WebFetch Genesis README | 未明示 macOS 支援；只在 torch 安裝註解提 Apple Silicon（Metal/MPS）；Apache-2.0 |

## 能力 4：網格驗證／修復

| 查詢 | 回傳摘要 |
|---|---|
| `gh search repos 'trimesh' --limit 6` | mikedh/trimesh 3704★ MIT；drlukeparry/pyslm 195★ LGPL-2.1（AM 用） |
| `gh search repos 'manifold3d' --limit 6` | 只見 wrapper／skill；主 repo `gh api repos/elalish/manifold`：2364★ Apache-2.0；Krateian/Sutura 12★（v0.2 起自訂授權） |
| `gh search repos 'pymeshlab' --limit 6` | cnr-isti-vclab/PyMeshLab 983★ GPL-3.0 |
| `gh search repos 'pymeshfix'` / `'meshfix'` | pyvista/pymeshfix 410★ GPL-3.0；MarcoAttene/MeshFix-V2.1 482★ NOLIC |
| `gh search repos 'open3d' --limit 6` | isl-org/Open3D 14110★ MIT |
| `gh search repos 'admesh' --limit 6` | admesh/admesh 257★ GPL-2.0；python-admesh 9★ GPL-2.0 |
| `gh search repos 'libigl python' --limit 6` | libigl/libigl-python-bindings 370★ GPL-3.0 |
| `gh search repos 'mesh wall thickness analysis'` / `'mesh repair watertight python'` | **各 0 筆** |
| WebSearch `trimesh wall thickness check minimum feature size 3D print python library thickness analysis` | 無專用 OSS 壁厚庫；二手文章用 trimesh 射線法（需 rtree/embreex）；Blender Print3D toolbox 有 thickness check |
| `pip download --only-binary` | trimesh 5.1.1 pure；manifold3d 3.5.4 cp311 arm64；pymeshlab 2025.7.post1 cp311 arm64（65 MB）；pymeshfix 0.18.1 cp311 arm64；open3d 0.20.0 cp311 arm64（54.5 MB） |
| `pip list`（正式 env 現況） | 已有 `cgal==6.0.1.post202410241521`、`numpy==2.4.6`；**無** trimesh/manifold3d |

## 能力 5：列印就緒與切片

| 查詢 | 回傳摘要 |
|---|---|
| `gh search repos 'bambustudio' --limit 6` | bambulab/BambuStudio 5137★ AGPL-3.0；DMontgomery40/bambu-printer-mcp 217★ GPL-2.0 |
| `gh search repos 'orcaslicer' --limit 6` | OrcaSlicer/OrcaSlicer 16047★ AGPL-3.0；FULU-Foundation/OrcaSlicer-bambulab 7193★ |
| `gh search repos 'prusaslicer' --limit 6` | prusa3d/PrusaSlicer 9421★ AGPL-3.0 |
| `gh search repos 'curaengine' --limit 6` | Ultimaker/CuraEngine 1858★ AGPL-3.0 |
| `gh search repos 'lib3mf' --limit 6` | 3MFConsortium/lib3mf 314★ BSD-2；lib3mf_python 4★ BSD-3 |
| `gh search repos 'tweaker-3 orientation'` / `'3d print overhang analysis python'` / `'slicer cli automation python'` / `'3mf validator'` / `'3d printing mcp server slicer'` | **各 0 筆**；Tweaker-3 改以 `gh api repos/ChristophSchranz/Tweaker-3`：110★ GPL-3.0 |
| `gh api releases/latest` | BambuStudio v02.08.02.61（2026-08-21）`Bambu_Studio_mac-*.dmg`；OrcaSlicer v2.4.2（2026-07-07）`OrcaSlicer_Mac_universal_V2.4.2.dmg`；PrusaSlicer 2.9.6（2026-06-25）`PrusaSlicer-2.9.6.dmg`；CuraEngine 最後 release 2.7.0（**2017**）；lib3mf 2.5.0 `lib3mf-2.5.0-py3-none-macosx_10_9_universal2.whl` |
| WebFetch BambuStudio wiki Command-Line-Usage | `--slice`、`--export-3mf`、`--export-settings`、`--export-slicedata`、`--outputdir`、`--load-settings`（≤1 machine+1 process）、`--load-filaments`、`--orient`、`--arrange`、`--info`、`--pipe`、`--debug`；未提 macOS |
| WebFetch OrcaSlicer wiki cli_mode / cli_misc | `--load-settings`、`--load-filaments`、`--arrange 1`、`--slice 0`、`--export-3mf`、`--outputdir`、`--export-statistics`、`--datadir`；43 個保留鍵不可覆寫；未給 mac 路徑 |
| WebFetch help.prusa3d.com command-line article | **404** |
| WebSearch `PrusaSlicer macOS command line ".app/Contents/MacOS/PrusaSlicer" --export-gcode headless` | 論壇（弱）：`/Applications/.../PrusaSlicer.app/Contents/MacOS/PrusaSlicer --export-gcode --load x.ini`；有 segfault 與 FFF/SLA 混設定報錯案例 |
| 本機 `which` / `ls /Applications` | openscad、prusa-slicer、orca-slicer、BambuStudio、CuraEngine、gltf_validator、gltf-transform **皆未安裝**；/Applications 只有 Blender.app；node/npm 在 /opt/homebrew/bin |
| 本 repo `雙上臂四點梯形-v80-單盤切片檢查/README.md` | 已用 Bambu Studio 02.08.02.61 官方 CLI 離線切 69 件、`--info` 重讀成功、return_code 0；DMG SHA256 對過官方 release API |
| `pip index versions tweaker3` | **無** |

## 能力 6：虛擬世界模型匯出與驗證

| 查詢 | 回傳摘要 |
|---|---|
| `gh search repos 'gltf validator' --limit 6` | 只見 wrapper（KittyCAD/gltf-validator Rust 5★ 等）；主 repo `gh api repos/KhronosGroup/glTF-Validator`：475★ Apache-2.0 |
| `gh api repos/KhronosGroup/glTF-Validator/releases` | `latest` 404（全是 prerelease）；最新 2.0.0-dev.3.10（2024-10-22）資產：linux64 / **macos64** / web / win64 tar（無 arm64 原生） |
| `npm view gltf-validator` / `@gltf-transform/cli` | 2.0.0-dev.3.10 Apache-2.0 / 4.5.1 MIT |
| `gh search repos 'gltf-transform' --limit 6` | donmccurdy/glTF-Transform 1988★ MIT |
| `gh search repos 'openusd' --limit 6` | PixarAnimationStudios/OpenUSD 7550★（授權檔為 TOST 修改版 Apache）；awesome-openusd 678★；usdtweak 362★ |
| `gh search repos 'usd python blender'` / `'gltf physics extension collision'` / `'KHR_physics_rigid_bodies'` / `'usd physics schema export blender'` | **各 0 筆** |
| `gh search repos 'glTF blender exporter'` | 只 1 筆 2★；官方 `gh api repos/KhronosGroup/glTF-Blender-IO`：1665★ Apache-2.0 |
| `gh api repos/eoineoineoin/glTF_Physics` / `glTF_Physics_Blender_Exporter` | 57★ NOLIC（規格草案）/ 36★ GPL-3.0 |
| WebFetch eoineoineoin/glTF_Physics | KHR_physics_rigid_bodies、KHR_implicit_shapes 為「proposed」未合入 Khronos；實作：Blender 匯出入、Babylon.js、Godot、validator |
| WebFetch glTF_Physics_Blender_Exporter | 未註明 Blender 版本；GPL-3.0；用 glTF 匯出視窗的 Exporter Extensions 啟用 |
| WebSearch `Blender glTF exporter KHR_physics_rigid_bodies collision shapes export addon` | 同上；Babylon 文件提醒擴充仍在改名風險 |
| `pip download usd-core / pygltflib` | `usd_core-26.8-cp311-none-macosx_10_15_universal2.whl`（40.7 MB）；pygltflib 1.16.5 pure |

## 能力 7：既有 CAD／模擬／列印 MCP server

| 查詢 | 回傳摘要 |
|---|---|
| `gh search repos 'freecad mcp' --limit 8` | neka-nat/freecad-mcp 2982★ MIT（需 FreeCAD GUI 開 RPC addon，可跑 Python 腳本）；bonninr 227★；contextform 138★；blwfish 61★ LGPL；sandraschi 32★ MIT（headless 宣稱） |
| `gh search repos 'fusion 360 mcp' --limit 8` | faust-machines 127★ MIT；AuraFriday 127★ other；皆綁 Fusion GUI |
| `gh search repos 'onshape mcp' --limit 8` | jarvis-onshape-mcp 174★ other；hedless/onshape-mcp 154★ NOLIC；altendky 20★ Apache；皆走 Onshape 雲 |
| `gh search repos 'openscad mcp server' --limit 8` | jhacksman/OpenSCAD-MCP-Server 208★ MIT；fboldo 7★ MIT；suapapa/openscad-wasm-mcp 2★ MIT |
| `gh search repos 'blender mcp' --limit 8` | ahujasid/blender-mcp 31813★ MIT（本專案 ADR-001 已用其 addon）；seehiong/blender-mcp-bridge 78★ MIT（93 工具）；bpy-dev/blender-mcp 98★ GPL-3.0；sandraschi/blender-mcp 62★ MIT；ProfRino/Blender-MCP-Assembly-Skill 78★ NOLIC |
| `gh search repos 'cad mcp server' --limit 8` | KiCAD-MCP 2884★（PCB，不相干）；daobataotie/CAD-MCP 625★ MIT（2D CAD）；gNucleus/text-to-cad-mcp 18★ MIT（雲）；mattmohandiss/cad-mcp-server 6★ MIT（STEP 檢視） |
| WebFetch pzfreo/build123d-mcp README | 工具：execute（持久 session）、render PNG/SVG/DXF、measure（體積/面積/bbox/拓樸/質心）、hole/boss 偵測、printability check、fit/alignment compare、validate、export STEP/STL/DXF/SVG；`uv tool run --python 3.12 build123d-mcp@latest`，支援 3.11–3.14；HTTP 模式**無驗證、單 session**（README 警告）；Apache-2.0；CADGenBench 0.360→0.457 |
| WebFetch jdilla1277/agentcad README | build123d 預設（CadQuery 選配）；`run/inspect/measure/render/diff/check-spec(spec.json)/parts`；STEP 為正典輸出，STL/GLB/OBJ 可匯出；Python 3.10–3.12；Apache-2.0 |
| WebFetch partcad/partcad README | YAML 套件／組件 DSL；後端 CadQuery/build123d/Chili3D/OpenSCAD/SDF + STEP/STL/3MF/glTF 匯入；組件可用 URDF-style joints；`pc mcp`（stdio；list/inspect/render/test/export + `execute`）；Apache-2.0 |
| WebFetch Pan-Chera/Multi-Agent-CAD README | build123d（釘 <0.13）；需雲端 LLM key（OpenAI 相容端點，本地 Ollama「可能」但未文件化）；幾何＋視覺驗證迴圈＋獨立 Judge；組件輸出 STEP/STL/GLB + URDF；MIT |
| WebFetch neka-nat/freecad-mcp README | 兩段式（FreeCAD 內 addon + MCP server），主流程要 FreeCAD GUI 開 RPC；可跑 Python 腳本；MIT |
| WebFetch DMontgomery40/bambu-printer-mcp README | Node 24；呼叫 BambuStudio／Orca CLI 切片；FTPS/MQTT LAN 列印；STL 工具；GPL-2.0；README 自己建議 GUI 切片再匯出 |

## 能力 8：規格／約束定義與公差

| 查詢 | 回傳摘要 |
|---|---|
| `gh search repos 'tolerance analysis python'` / `'3d printing tolerance clearance database'` / `'mechanism definition dsl'` / `'GD&T python'` / `'3d print fit tolerance test pla'` / `'parametric assembly constraints python'` / `'fits and clearances calculator'` / `'tolerance stack-up monte carlo'` / `'ISO 286 fits python'` | **全部 0 筆**（9 條） |
| WebSearch `tolerance stack-up analysis python open source library monte carlo worst case RSS` | PyPI **stackcore**（Monte Carlo + worst-case；授權／維護不明）；MoonBit tolerance（非 Python）；結論：無廣用 Python 庫 |
| WebSearch `3D printing PLA clearance tolerance database fit test hole shaft 0.2mm 0.3mm press fit slip fit guideline` | 無標準化資料庫；Fab Academy 試片、Prusa 論壇、UMD 指南：滑配 +0.2–0.3 mm、緊配 +0.1–0.15 mm（單機經驗，[weak]）；一篇用 ISO 286 做 FDM 配合實驗 |
| WebSearch `CadQuery assembly constraints solver "cq.Assembly" Plane Point Axis constraint documentation` | 官方 classreference：`constrain(kind=Plane/Point/Axis/PointInPlane/Fixed/FixedPoint/FixedAxis/PointOnLine/FixedRotation)`；`Assembly.solve()` |
| `pip index versions stackcore` | 0.3.3 |

## 授權補查（GitHub 回 NOASSERTION 者，讀 LICENSE 檔前三行）

openscad/COPYING → GPL（含 CGAL 連結例外）；CadQuery → Apache-2.0；bullet3 → zlib；Open3D → MIT；OpenUSD → 自訂「OpenUSD」條款（TOST）；IsaacLab → 「see README」＋版權聲明（BSD-3，另有 Omniverse EULA）；CGAL → 混合（GPL/LGPL，依模組）；fcl → BSD；flowful cad-skill → **PolyForm Noncommercial 1.0.0**；Text2CAD → **CC BY-NC-SA 4.0 社群授權**；cad-recode → LICENSE 檔**空白**；cad-agent → **PolyForm Small Business**；ros/urdfdom → BSD；Sutura → v0.2 起自訂。

## 未覆蓋的來源類別（誠實聲明）

- 學術庫（arXiv/Scholar）：未系統檢索；Text2CAD／CAD-Recode／CADGenBench 只以 GitHub 頁面與 README 為據。
- 論壇類只用於能力 5（PrusaSlicer mac 路徑）與能力 8（PLA 間隙），皆標 [weak]。
- 未實際執行任何候選套件（只下載 wheel 到 scratchpad，未安裝、未 import）；「可裝性」＝wheel 標籤符合 cp311/arm64，不等於能 import 成功。
