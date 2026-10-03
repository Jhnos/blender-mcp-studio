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
