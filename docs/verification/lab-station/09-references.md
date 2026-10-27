# 已查閱來源與沿用決策（2026-09-12）

- https://github.com/billism1/3d-print-pcb-holder-extension ：MIT、OpenSCAD、滑軌鎖銷與五金保持。沿用機構概念；其尺寸適用 PCB 夾架，未複製程式或 STL。
- https://github.com/0x23/MicroManipulator ：微位移 XYZ 平台。需求是整根探頭約 100 mm 提升，不直接套用微位移行程。
- https://build.openflexure.org/openflexure-delta-stage/v1.2.3/pages/stage_geometry_notes.html ：柔性機構高度不等於可用位移，不以 100 mm 高度誤認 100 mm 行程。
- 本地沿用：`blender_mesh_primitives`、`blender_artifact_export`、`blender_generator_runner`、`lab_station_rig` 與既有 real contract oracle；不新造輸出／MCP 通道。

V4 搜尋（2026-09-12）：`openscad/MCAD` 的 nuts_and_bolts、`JohK/nutsnbolts`、`brhubbar/Screw-Boss-OpenSCAD` 提供標準螺絲／螺母孔與可拆螺母捕捉概念。沿用既有 Blender primitive 的圓孔／六角孔，不引入第二個 CAD 執行器，也不複製外部程式。尺寸與工具空間由本模型的實際幾何查核。

滑座鎖定前置搜尋（2026-09-12）：[EasyPrintedStages](https://github.com/SGTHANKI/EasyPrintedStages) 使用鎖定螺栓固定平台；[16motion](https://github.com/mosomate/16motion) 使用多片夾合與標準五金建立滑座。兩者導向與行程配置不同，不能直接套用目前雙 Ø8 導桿。先沿用本專案既有滑座／五金產生器，後續比較摩擦鎖定與正向止擋；搜尋不是保持力合格證據。

腕部前置搜尋（2026-09-12）：[OpenSCAD_Linkages_Library](https://github.com/machineree/OpenSCAD_Linkages_Library)、[OpenSCAD_connectors](https://github.com/adgaudio/OpenSCAD_connectors) 與既有 MCAD。未複製程式；本地已有圓柱、布林、螺母捕捉及姿態檢查，沿用這些底層。腕部需要按現有背架空間設計叉耳／轉動件，通用庫不能直接證明此處的裝配與承重。

肘端前置查找（2026-09-12）：[agentscad](https://github.com/GillesBouissac/agentscad) 有 Hirth 接頭與五金工具；[BOSL2 joiners](https://github.com/BelfrySCAD/BOSL2/wiki/joiners.scad) 描述端面齒接合。沿用本地已驗證齒盤與布林，不複製外部程式；新增 arm 模組只負責把齒盤連到偏置頸部。


## 四連桿候選的前置查找

- [CMU planar linkages](https://www.cs.cmu.edu/~rapidproto/mechanisms/chpt5.html)：平行四連桿的耦合桿保持方向；不代表端點直線運動。
- [tangletron-3000](https://github.com/aav31/tangletron-3000)：列印平行連桿手臂及金屬螺絲關節的案例。
- [Armstrong-SCARA](https://github.com/ttsalo/Armstrong-SCARA)：列印臂與購買軸承／金屬軸的裝配案例；SCARA 拓撲不直接套用為本案升降。

查找在建立 rotary 概念與驗證入口前完成。沿用本專案 primitive、jaw、driver 與 BlenderSocketOracle；未複製上游程式或載入新 CAD 引擎，也不把他案承載說明當成本案證據。

## 底座固定的前置查找

建立 `lab_station_base` 前查閱 [ODRI actuator shell preparation](https://github.com/open-dynamic-robot-initiative/open_robot_actuator_hardware/blob/master/mechanics/actuator_module_v1/details/details_shell_preparation.md)、[PAROL6](https://github.com/Source-robotics/PAROL6-Desktop-robot-arm) 與 [Thor](https://github.com/AngelLM/Thor)。採用旋轉支座、軸套與金屬穿軸分工的配置思路；實際尺寸由本機箱空間決定，沒有複製程式或引用他案承載作為本案資格。

## 緊湊探頭夾座的前置查找（2026-10-02）

GitHub 查找 `electrode holder 3d print clamp pH probe` 與分片夾座，檢視 [ALPHUS](https://github.com/WeirongChen/ALPHUS) 原始儲存庫。其探頭匹配的左右夾片屬超音波探頭穩定架，並非本案圓柱電極的可直接替換夾座；未複製程式或 STL。NIH pH holder 搜尋結果未能讀取內容，不列為已驗證設計依據。

沿用本專案 `lab_station_clamp` 的分片軟襯、軸向止口與六角螺母孔，以及 `lab_station_clamp_check` 的裝入包絡原則。可換襯套與固定夾體分工，實際外形和孔位仍須按目前電極臂的雙探頭間距驗證；舊滑座夾具的通過結果不移植成新夾座的合格證據。

## 承壓鏈閉合檢查的前置查找（2026-10-03）

建立 `lab_electrode_closure` 前查找 GitHub 的 Blender assembly contact／clearance／preload。檢視 [JointForge](https://github.com/NatalieC001/JointForge)：其用途是分割列印件並加入插接鍵，未提供本案螺栓—旋鈕—齒面—螺母閉合驗證，未複製程式或採用其公差推薦。沿用本專案 BVH、世界座標射線與共面接觸微量分離方法；新增模組只編排特定承壓鏈的狀態和量測，不另造 CAD／力學引擎。

## 沿臂理線前置查找（2026-10-03）

- [NT7S ParametricCableComb](https://github.com/NT7S/ParametricCableComb)：可參數化的線梳，README 提醒梳齒列印方向影響抗折；適合作尺寸化通道的形式參考，頁面未顯示授權，未複製程式或網格。
- [Ed Nisley Cable Clips](https://gist.github.com/ednisley/52b8a6303fa130fe38858488b978874b)：線外徑、孔補償與列印線寬分開設定；僅參考參數分離，不採用其 USB 外徑當本機線徑。未複製程式。
- 沿用本專案圓柱／環差集與夾具工具；目前不引入 OpenSCAD 相依。氣管、pH 線與溫度線外徑已詢問，未取得實測前單路 Ø6 mm 僅作暫定包絡，不能據此發布固定孔或夾持資格。腕端收薄未新增模組；後續若新增理線模組，可由以上查找開始核對，但仍需實際安裝與完整動作驗證。

## 肩部完整轉位驗證拆分前查找（2026-10-03）

建立 `lab_electrode_motion` 與 `lab_electrode_readback_real` 前查阅 [Robotics Toolbox trajectory examples](https://github.com/petercorke/robotics-toolbox-python/blob/main/examples/README.md) 與 [PyBullet Planning](https://github.com/caelan/pybullet-planning/blob/master/README.md)、其 `examples/test_turtlebot_motion.py`。沿用關節空間取樣、隨行部件與障礙檢查的分工；不將端點直線插值當肩部圓弧。此專案已有 Blender 世界網格、儲存檔 oracle 與 FK，不引入第二個物理引擎，未複製外部程式。新模組分別承接原 main 的整段動作情境與原 real verifier 的 fresh-command 讀回，保持既有守衛與串行傳輸。

## 可換扣式導線夾模組前置查找（2026-10-03）

建立 lab_electrode_routes 前重新檢視 [Ed Nisley Cable Clips](https://gist.github.com/ednisley/52b8a6303fa130fe38858488b978874b) 與 [slide-n-snap](https://github.com/benjamin-edward-morgan/openscad-slide-n-snap/blob/master/slide-n-snap.scad)。參考線徑／製程間隙分離與可拆扣接形式；本案要扣住現有 8×12 mm 桿身，不直接套用外部尺寸。沿用本地 block／cylinder／Boolean、BVH 及真機 oracle，不引入 OpenSCAD 或複製程式。扣入力、材料疲勞及線材實際尺寸仍需試片；不能以剛體開口小於桿身當保持力證明。

## 跨肘線材路徑研究查找（2026-10-03）

查閱 [BlenderHarnessTools](https://github.com/PhilBladen/BlenderHarnessTools) 的線束與最小彎曲半徑可視化，以及 [beziers.py](https://github.com/simoncozens/beziers.py) 的曲線操作範圍。沿用 Blender 幾何與標準三次曲線解析式做可重現研究，未複製外部碼、安裝插件或新增生產模組；固定線長、端點切向、實體及線間距分開檢查。

[igus 彎曲半徑選型說明](https://www.igus.com/company/energy-chains-select-bend-radius-cable-carrier-ca) 要求遵循線材製造商的最小半徑。其頁面引用的舊版規範不當作本案現行合規判準；Ø6 mm 只是包絡，未取得各電纜／氣管的實際規格前，不以外徑倍率宣称可反覆彎折或寿命合格。

## 參數化模組復用（2026-10-03）

- [cqparts 文件](https://cqparts.github.io/cqparts/doc/)：參數化 Part／Assembly 分工；作接口與配置分離參考。
- [blender-cad](https://github.com/Fleynaro/blender-cad)：Blender 宣告式可重用零件建模；不引入另一個建模依賴。
- 本專案已有 hand instance registry、domain spec 與產生器鏈，電極臂沿用此分工；未複製上述專案程式碼。此輪是抽取既有邏輯，不新增一個 CAD 引擎或複製每版腳本。

## 曲線與走線共用化（2026-10-03）

- [dhermes/bezier](https://github.com/dhermes/bezier)、[官方Curve文件](https://bezier.readthedocs.io/en/stable/python/reference/bezier.curve.html)：比較既有曲線求值、細分及長度工具。沿用本專案研究中的三次曲線形式，抽成小型純Python領域運算與Blender檢查邊界；未複製第三方程式碼，未加入數值套件或二進位依賴。
- 搜尋結果只證明有既有工具，不構成此裝置的走線或材料資格；本地直線／圓弧、長度上下界、正反例與實體案例才是實作證據。

### 測試模組化來源

- [pytest-dev/pytest](https://github.com/pytest-dev/pytest)、[pytest參數化](https://docs.pytest.org/en/stable/how-to/parametrize.html)：沿用現有pytest執行純Python案例矩陣；Blender端使用同樣的案例／配件分離方式，重用本專案VerificationEvidence與VerificationSummary。未新增測試框架、第三方程式碼或依賴。

- [FastMCP官方工具文件原始碼](https://github.com/PrefectHQ/fastmcp/blob/main/docs/servers/tools.mdx)：沿用現有FastMCP typed output、ToolError與工具annotations；不引入新的MCP server或背景worker，透過同一AppRuntime及BlenderPort提供登錄測試。

- 線對線擴充前檢索GitHub [trimesh proximity](https://github.com/mikedh/trimesh/blob/main/trimesh/proximity.py)：提供網格與點鄰近查询；本案已有Blender KDTree與保守曲線取樣，沿用既有模組建立線包絡檢查，不新增網格依賴或另一套碰撞框架。

- 跨姿態模組前檢索GitHub [OMPL離散／連續碰撞比較](https://github.com/ompl/omplapp/blob/main/demos/SE3RigidBodyPlanning/CollisionCheckers.cpp) 與 [PyElastica](https://github.com/GazzolaLab/PyElastica)。前者明確分開姿態與動作檢查，後者提供細長柔性體力學模擬。本案先沿用既有定長曲線、Blender BVH/KDTree及Scenario，固定曲線分支並重播中間姿態；不引入缺乏材料輸入的力學模型，不將有限取樣標成連續碰撞證明。新增motion orchestrator／fixture只分離跨姿態選擇和合成反例，沒有複製幾何判準。

## 可重用維修情境與計算重用

- [MoveIt Task Constructor](https://github.com/moveit/moveit_task_constructor)：共用場景介面描述多階段操作。採用明確操作／移動件／已移除件的資料邊界，沿用Scenario與既有幾何檢查，沒有引入ROS或複製其程式。
- [trimesh caching](https://github.com/mikedh/trimesh/blob/main/trimesh/caching.py)：資料識別改變時使快取失效。本專案以完整不可變曲線、線徑及取樣界限作鍵，每次suite限定生命週期與容量；實體障礙仍逐姿態重建。

## 連續碰撞的運動模型與求解契約

- 2026-10-03查閱 [FCL](https://github.com/flexible-collision-library/fcl)：同一介面族提供網格碰撞、最短距離與連續碰撞；連續呼叫需要初始及目標變換。[ContinuousCollisionRequest原始碼](https://github.com/flexible-collision-library/fcl/blob/master/include/fcl/narrowphase/continuous_collision_request.h)列出平移、線性、螺旋與樣條運動，預設為CCDM_TRANS及CCDC_NAIVE，不能僅憑API名稱把結果當成任意機構路徑保證。
- [MoveIt Bullet CCD官方示例](https://moveit.picknik.ai/main/doc/examples/bullet_collision_checker/bullet_collision_checker.html)提供兩端離散姿態安全但途中穿過箱子的反例。採納這類辨識控制；實際連桿關節路徑與可變形線路須另證明符合所用運動模型。不能以端點剛體插值替代本案的實際關節／定長線路變化。
- 適用邊界：此為後續連續間隙方法的來源比較，尚未引入FCL／Bullet依賴，也不改變現有固定取樣的證據範圍。若採用現成求解器，須明確選擇運動及求解方式，驗證薄障礙、擦邊、旋轉與失敗／未收斂狀態，不能把不確定結果當作clear。

- [python-fcl](https://github.com/BerkeleyAutomation/python-fcl)與[請求類別原始碼](https://github.com/BerkeleyAutomation/python-fcl/blob/master/src/fcl/collision_data.py)：Python binding預設solver為CONSERVATIVE_ADVANCEMENT，與FCL C++預設不同。研究採隔離venv及顯式solver／運動類型；三角網格須用解析薄障礙、擦邊與clear對照測試驗證變換處理與接觸時間，不能把套件預設結果直接當作資格。

- [CGAL Polygon Mesh Processing](https://doc.cgal.org/latest/Polygon_mesh_processing/)與[官方SWIG綁定](https://github.com/CGAL/cgal-swig-bindings/blob/main/SWIG_CGAL/Polygon_mesh_processing/CGAL_Polygon_mesh_processing.i)：提供does_self_intersect／self_intersections；匯入前後頂點與面必須獨立核對，避免資料轉換改動掩蓋缺陷。

共用網格測試抽離前（2026-10-03）：查閱 [Blender bmesh triangulate](https://github.com/blender/blender/blob/main/source/blender/bmesh/tools/bmesh_triangulate.cc) 與上述CGAL官方SWIG自交介面。沿用Blender內建三角化、既有BlenderSocketOracle及CGAL獨立研究檢查；mesh_refinement_verify_real只是移出既有測試並補表面保留回歸，不另造幾何核心或MCP通道。

布林求解與永久自交守衛前置查找（2026-10-03）：[Blender 4.5 Manifold 說明](https://developer.blender.org/docs/release_notes/4.5/modeling/)、[官方Boolean原始碼](https://github.com/blender/blender/blob/main/source/blender/geometry/intern/mesh_boolean.cc)、[CGAL官方SWIG接口](https://github.com/CGAL/cgal-swig-bindings/blob/main/SWIG_CGAL/Polygon_mesh_processing/CGAL_Polygon_mesh_processing.i)。實測EXACT選項與MANIFOLD均不能解決重複孔壁，故保持原solver。永久mesh_integrity沿用CGAL，不重寫相交算法；新增自身拓樸及轉換保真守衛。

CGAL輪子載入警告：查閱[SWIG官方issue 2881](https://github.com/swig/swig/issues/2881)，問題在內建型別metadata、修復里程碑SWIG4.4；目前CGAL可安裝最新wheel仍帶舊生成碼，未以全域warning filter掩蓋其他警告。

## 原件資料座標重綁與保存驗證前置查找（2026-10-27）

檢視 [trimesh registration](https://github.com/mikedh/trimesh/blob/main/trimesh/registration.py) 的配準與反射參數，以及 [Blender FBX importer](https://github.com/blender/blender-addons/blob/main/io_scene_fbx/import_fbx.py) 的座標系轉換。原件與原STL已有保真讀取路徑，本案不導入ICP或第二套網格框架；`rebase_mesh` 只接受已驗證的表面與明確矩陣，保留原座標、補償從屬座標系，配準責任仍在呼叫端。未複製外部程式。

另參考 [Blender官方存取回歸測試](https://github.com/blender/blender/blob/main/tests/python/bl_blendfile_io.py) 的另存後重新載入方式；既有真機驗證器以libraries.write／append讀回自己的控制件，並逐姿態檢查實際驅動結果，不另起場景運算服務。原生修訂候選的完整輸出／驗證配方仍應透過專案腳本收斂，暫態研究腳本不屬於公開交付能力。

螢幕控制責任拆分前再查找GitHub，檢視 [Blender官方Rigify機構工具](https://github.com/blender/blender/blob/main/scripts/addons_core/rigify/utils/mechanism.py) 的驅動變數／屬性路徑分離方式。本案重用既有rig驅動器與領域時序；新增的 `lab_station_screen_control` 僅綁定現有零件，避免齒盤幾何模組超過職責／行數預算，不引入Rigify依賴或複製外部碼。

## 配對齒面重用與來源切削查找（2026-10-27）

- [BOSL2 Hirth 接合](https://github.com/BelfrySCAD/BOSL2/wiki/joiners.scad)、[trimesh triangulate_quads](https://github.com/mikedh/trimesh/blob/main/trimesh/geometry.py)：既有專案已提供齒形與固定對角線三角化；未複製程式。此處只補既有原件接觸雙環的完整登錄／覆蓋與一致拓樸規劃，不引入新CAD引擎、擬合或近點合併；下游沿用既有Blender座標重綁、STL匯出及CGAL驗證。
- [Blender Boolean API](https://docs.staging.blender.org/api/current/bpy.types.BooleanModifier.html)、[原生Manifold接合程式](https://github.com/blender/blender/blob/main/source/blender/geometry/intern/mesh_boolean_manifold.cc)：查找封閉來源的布林替代求解器。更換求解器本身不是精度／拓樸通過證據，仍須每步保真三角化及獨立閉合／自交檢查；未變更本專案共用求解器。

- [SPM原廠DIN931／ISO4014尺寸參考](https://spmetalparts.com/products/bolts/partially-threaded-hex-bolts/) 的M5名義頭高3.5／對邊8mm用於現有六角口袋方案；實際包絡採3.7mm，不推定已涵蓋全部公差。[norelem 07170_ST原廠表](https://www.norelem.fr/medias/07170-ST-Datasheet-19858-Hexagon-head-bolts-DIN-931-ISO-4014-steel-en.pdf?context=bWFzdGVyfHJvb3R8MTg1NTE4fGFwcGxpY2F0aW9uL3BkZnxoYjMvaDQxLzkwMDU3ODYzMDA0NDYvMDcxNzBfU1RfRGF0YXNoZWV0XzE5ODU4X0hleGFnb25faGVhZF9ib2x0c19ESU5fOTMxX0lTT180MDE0X3N0ZWVsLS1lbi5wZGZ8NTE1ZWNkNzc0N2VkYTVkNmIxMGZlNmNhZGRmZjFiYTRiNjcwMDkyMDQ5ZDY0ODI0MjVjYjg0NThlZWQzZGQwYQ) 明列07170-05X35的Ls最小15／Lg最大19mm、07170-05X40的20／24mm；光桿覆蓋與螺母完整牙段應分別驗證，不能用標稱總長減參考牙長代替保證尺寸。

## 共用原件修訂與控制介面前置查找（2026-10-27）

查閱 [Blender原廠存取回歸](https://github.com/blender/blender/blob/main/tests/python/bl_blendfile_io.py)、[BlenderProc](https://github.com/DLR-RM/BlenderProc) 的流程／檔案輸出邊界與 [Rigify父關係切換](https://github.com/blender/blender-addons/blob/main/rigify/utils/switch_parent.py) 的控制屬性／驅動變數分離。本案已有序列、矩陣、序列化socket與保存檢查器；沿用原件及既有工具，不引入第二套Blender執行框架。新增規格只描述本案主動螺紋導程與被動間隙，未複製外部碼。

另查 [Blender原廠evaluated ID範例](https://github.com/blender/blender/blob/main/doc/python_api/examples/bpy.types.Depsgraph.1.py)。原始ID欄位或單一動畫公式不能取代實際依賴圖讀回；五齒位fixture包含保存重載與中途角度，角度顯示由實際RNA轉角派生，不依賴重複的顯示時序。

五金公差後續核對：[NuFast ISO4014原廠生產圖](https://www.nufast.co.uk/uploads/ISO4014.pdf) 列M5頭高3.35..3.65mm、對邊7.78..8.00mm；既有3.7mm參考外包絡與±0.28mm樣本不能證明完整軸向間隙。頭高與口袋可用軸向位置必須耦合處理。[Böllhoff DIN986原廠表](https://eshop.boellhoff.de/out/media/pdf/DIN_986_Edelstahl_A2___en.pdf) 提供外形、六角與最小螺母高度，但未據此建立保證盲牙深度，因此尚未選定端部封帽方案。

原生來源查找：[Blender官方存取測試](https://github.com/blender/blender/blob/01c07a6f4aa9f8338c89e792583ebbf0a7138cb3/tests/python/bl_blendfile_io.py)及[CPython file_digest](https://github.com/python/cpython/blob/0e353134844fd50628f3730b9f704c3de1710e20/Lib/hashlib.py)。來源識別沿用既有路徑守衛及標準庫，未引入新資產框架；逐檔收據不能替代修改前的暫存重核。

隔離開發依賴查核：[npm audit官方行為](https://docs.npmjs.com/cli/v11/commands/npm-audit/)、[Vite通報](https://github.com/advisories/GHSA-rq7h-c2jc-7f22)、[Vitest mocker通報及4.1.12回補](https://github.com/advisories/GHSA-qxg6-89mg-rqv8)。採既有相容範圍內更新並同步Vitest／coverage-v8最低版，不使用force跨主要版本；audit與完整靜態回歸分別作證。


## 原場景保存的前置查找（2026-10-27）

GitHub查閱Blender官方固定commit `01c07a6f4aa9f8338c89e792583ebbf0a7138cb3` 的 [libraries.write範例](https://github.com/blender/blender/blob/01c07a6f4aa9f8338c89e792583ebbf0a7138cb3/doc/python_api/examples/bpy.types.BlendDataLibraries.write.0.py)、`bpy_rna_id_collection.cc` 的user_map及batch_remove。選擇直接包裝已安裝Blender公開API，不搬運GPL實作、不引入第二套Blender框架。另存依賴子集與原場景保留是兩份獨立契約；檔案可讀也須核對實際active scene membership，不能只看資料庫物件數。官方線上API頁回402，另以本機5.1.0 docstrings核對簽名；現階段仍是隔離生命週期研究，能力與進度只讀任務索引。


## 原生來源暫存前置查找（2026-10-27）

新增NativeStagingPort／filesystem暫存adapter／NativeRevisionService準備階段前，GitHub查詢 `copyfileobj file_digest`，repository `python/cpython`，回傳 [CPython emscripten下載驗證用法](https://github.com/python/cpython/blob/0e353134844fd50628f3730b9f704c3de1710e20/Platforms/emscripten/__main__.py)。沿用標準庫檔案IO及file_digest，並重用本地來源路徑守衛、指紋函式與工作排空器；copyfileobj本身無總位元組上限，故複製採小區塊讀取並扣除已驗總量，不引入另一套檔案框架或搬運CPython實作。來源選版仍只由既有ArtifactCatalog注入同一份快照，準備服務不另定版本政策，也沒有公開任意路徑／Python入口。

## 原生場景生命週期模組化查找（2026-10-27）

GitHub再查 `bpy.data.libraries.write` 與 `bl_blendfile_io.py`，檢視 [Blender官方子集寫入範例](https://github.com/blender/blender/blob/fa494ce9a0ada672f351d404dc6a1ce17c2e13a0/doc/python_api/examples/bpy.types.BlendDataLibraries.write.0.py)及[官方另存／重開測試](https://github.com/blender/blender/blob/3dba4a0c8e62ad64212f46778756825d4f6f67de/tests/python/bl_blendfile_io.py)。沿用 Blender 公開 libraries／user_map／batch_remove API 與標準庫排他檔案發布；不搬運上游程式、不新增 CAD 框架。原場景保存、輸出身份與獨立重開分開檢驗，不能從檔案寫出推論三者皆成功。

當次工作授權前查 GitHub `repo:python/cpython contextvars ContextVar Token reset asyncio`，讀取[CPython官方contextvars文件](https://github.com/python/cpython/blob/0e353134844fd50628f3730b9f704c3de1710e20/Doc/library/contextvars.rst)。使用標準庫ContextVar／token reset，不複製外部碼或增加依賴；本案另加owner檢查與scope撤銷，因context副本不等於授權轉移。Python最低3.11，不能使用3.14新增的Token context-manager簡寫。

## 原件封閉配方與STL輸出前置查找（2026-10-27）

先查BlenderProc的Boolean用法（未回傳匹配），再查[Blender官方modifier apply實作](https://github.com/blender/blender/blob/c9a38ad133166a5120c0e0ccec795784ab59ef84/source/blender/editors/object/object_modifier.cc)、[官方KDTree範例](https://github.com/blender/blender/blob/c9a38ad133166a5120c0e0ccec795784ab59ef84/doc/python_api/examples/mathutils.kdtree.0.py)及[trimesh binary STL輸出](https://github.com/mikedh/trimesh/blob/6c158cce226500fc64b12acd265af0cf01d1c212/trimesh/exchange/stl.py)。沿用現有Blender primitives、CDT、rebase與paired-contact planner；只增加明確collection／depsgraph的資料API路徑，不搬運GPL實作、不更換CAD核心。來源配準使用既有固定正交方向與雙向最近點誤差，不引入ICP或自動修補；STL writer使用現有trimesh、來源守衛與MeshIntegrityPort，未增加依賴。


## 原STL與3MF座標綁定前置查找（2026-10-27）

GitHub查閱[BambuStudio官方3MF匯入／匯出實作](https://github.com/bambulab/BambuStudio/blob/79df7ae309be398ed30c9f397c13c9911c2edc57/src/libslic3r/Format/bbs_3mf.cpp)及同commit CMakeLists。沿用既有ZIP／ElementTree與binary_stl_surface，不搬運上游程式、不引入新依賴。座標綁定只接受唯一正向換軸加平移，完整有向三角面多重集合須相同；尺寸或頂點接近不足以證明原表面相同。3MF來源必須是當次captured source receipt，舊Gcode／預覽不得用作新幾何資格。

3MF清理沿用同一BambuStudio固定commit原生匯入器；實際消費端對預設namespace序列化有相容要求，不能用通用XML parse成功代替。P2S官方安裝包的machine_end_gcode含T65535卸料哨兵，切片器預覽parser會記Invalid T command；保留原廠結尾並記錄原始log，不刪除該卸料命令以消除訊息。CLI副產物按job cwd隔離，原廠profile仍由既有bundle_profiles讀取，不另複製供機器執行。


## 共用場景所有權前置查找（2026-10-27）

新增共用port守衛前，GitHub查詢 `repo:python/cpython path:Lib/asyncio/locks.py Lock acquire` 未回傳匹配，改直接讀取[CPython官方asyncio Lock實作](https://github.com/python/cpython/blob/c59ea15111bef2b10bb456ea1881cc5bbcc99c6c/Lib/asyncio/locks.py)。保留既有asyncio.Lock與BlenderLease，不複製上游實作或新增鎖框架；標準Lock本身不限制task owner，因此共用lease另記實際owner。同task可重入，繼承context的子task不自動取得場景修改權。未知完成狀態與正常釋放分開；記憶體隔離票據本身不構成遠端終態或重啟恢復證據。


## 原件執行終態前置查找（2026-10-27）

新增job內收據與共享執行adapter前，GitHub查 `repo:blender/blender "os.replace" "json.dump"` 未回傳匹配；再查 `repo:python/cpython "fsync" "replace" "tempfile"`，讀取[CPython IDLE writefile的flush／fsync實作](https://github.com/python/cpython/blob/d9825d504ad738a5160d3c3ecd8cd575a1713e98/Lib/idlelib/iomenu.py)。沿用標準庫flush／fsync、專案既有的暫存後hard-link排他發布、唯一JSON key parser及現有job目錄，不搬運上游程式或引入另一個佇列／工作框架。載入已沿用generator_imports的實際import closure；未手抄reload清單。共享Blender與host-checker的來源SHA一併放入當次程式，遠端執行前重核，不能只指紋一段會匯入可變程式的bootstrap。
