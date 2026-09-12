# 已查閱來源與沿用決策（2026-09-12）

- https://github.com/billism1/3d-print-pcb-holder-extension ：MIT、OpenSCAD、滑軌鎖銷與五金保持。沿用機構概念；其尺寸適用 PCB 夾架，未複製程式或 STL。
- https://github.com/0x23/MicroManipulator ：微位移 XYZ 平台。需求是整根探頭約 100 mm 提升，不直接套用微位移行程。
- https://build.openflexure.org/openflexure-delta-stage/v1.2.3/pages/stage_geometry_notes.html ：柔性機構高度不等於可用位移，不以 100 mm 高度誤認 100 mm 行程。
- 本地沿用：`blender_mesh_primitives`、`blender_artifact_export`、`blender_generator_runner`、`lab_station_rig` 與既有 real contract oracle；不新造輸出／MCP 通道。

V4 搜尋（2026-09-12）：`openscad/MCAD` 的 nuts_and_bolts、`JohK/nutsnbolts`、`brhubbar/Screw-Boss-OpenSCAD` 提供標準螺絲／螺母孔與可拆螺母捕捉概念。沿用既有 Blender primitive 的圓孔／六角孔，不引入第二個 CAD 執行器，也不複製外部程式。尺寸與工具空間由本模型的實際幾何查核。

滑座鎖定前置搜尋（2026-09-12）：[EasyPrintedStages](https://github.com/SGTHANKI/EasyPrintedStages) 使用鎖定螺栓固定平台；[16motion](https://github.com/mosomate/16motion) 使用多片夾合與標準五金建立滑座。兩者導向與行程配置不同，不能直接套用目前雙 Ø8 導桿。先沿用本專案既有滑座／五金產生器，後續比較摩擦鎖定與正向止擋；搜尋不是保持力合格證據。

腕部前置搜尋（2026-09-12）：[OpenSCAD_Linkages_Library](https://github.com/machineree/OpenSCAD_Linkages_Library)、[OpenSCAD_connectors](https://github.com/adgaudio/OpenSCAD_connectors) 與既有 MCAD。未複製程式；本地已有圓柱、布林、螺母捕捉及姿態檢查，沿用這些底層。腕部需要按現有背架空間設計叉耳／轉動件，通用庫不能直接證明此處的裝配與承重。
