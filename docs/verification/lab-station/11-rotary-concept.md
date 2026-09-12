# 獨立四連桿升降概念

使用者提出以活動臂取代線性導桿滑座後的候選。兩頭仍共杯、各自活動；此階段只有運動與空間概念，沒有列印發布或承重資格。V10 滑座模型僅供共用外殼／螢幕基線，不是新機構的驗收依據。

## 看與操作

產出位於 `tmp/lab-station-rotary/`：

- `working.png`：兩頭量測位置。
- `left-raised.png`：只抬起毛細管。
- `both-raised.png`：兩頭各抬起 100 mm。
- `rotary-concept.blend`：選取 `LR_CTRL_capillary` 或 `LR_CTRL_pH_temp`，調整自訂屬性 `lift_mm`（0..100）。另有 `base_yaw_deg`、`shoulder_deg`、`elbow_deg`、`wrist_deg`，各自控制底座、肩、肘與末端；角度欄位的 ±45° 是研究範圍，並非無碰撞保證。肩肘改角後需手動校正末端，四連桿只保持相對支座方向。
- `motion.json`：每頭 101 個位置，探頭／容器、桿端閉合、直立與另一頭不動的檢查。
- `assembly-motion.json`：每頭 21 個位置對其他固定網格的表面碰撞，以及固定支撐對既有外殼／HMI 的靜態碰撞。只豁免底面位於 80 mm 的支座／上蓋名義接觸；不代表支座已固定。
- `support-mesh.json`／`red-support-mesh.json`：四件肘部支撐各為單一連通體、零非流形邊與退化面；故意開面必須拒絕。另由左右兩份 `lab_rotary_support_*.json` readiness 契約檢查自交、法線與退化，禁止分析截斷；仍非承力／整機製造資格。
- `elbow-assembly.json`：先將 HMI 收折（`tilt_step=0`，先脫齒），再依序由外側裝入螺栓與墊片、內側墊片、螺母。兩側共 216 個 2 mm 步距取樣；組裝時需支撐臂件，未模擬螺紋旋入或預緊。
- `elbow-tools.json`／`red-elbow-drive.json`：收折 HMI 後的名義 4 mm 六角扳手直段與薄壁套筒就位；封住六角孔必須拒絕。只查直段表面碰撞，未含工具裝入掃掠、手柄擺幅、實際產品與施力。
- `elbow-detail.png`：支撐肘部齒盤與穿軸局部圖。
- `elbow-release.json`：每側五狀態，包含未脫齒轉半齒的必須干涉案例；`elbow_release_mm` 為 0..2 mm。僅查肘部成員與穿軸五金，不代表全臂任意姿態安全。
- `pivot-detail.png`：名義螺栓、墊片與軸套的局部視圖。
- `articulation.json`：每頭五個控制的實際移動／隔離，加上脫齒位移共 12 項。
- `coupled-motion.json`：同頭移動件表面配對與雙頭 121 高度組合。
- `screen-motion.json`：雙頭各三高度、螢幕 0..75° 每 5°，共 144 組表面檢查。
- `red-articulation.json`／`red-cross-head.json`：停用旋轉驅動／加入跨頭侵入網格必須被拒絕。
- `red-broken-link.json`：使其中一根連桿停止轉動，閉合檢查必須拒絕。

## 尺寸與限制

平行桿中心距 130 mm、兩端垂直軸距 40 mm。從水平下方約 22.62° 抬至上方約 22.62°，得到 100 mm 升程；中途向前最大偏移 10 mm，並非直線。原三探頭在假設內徑 66 mm 的圓筒中保持空間餘量；容量 250 mL 不能代替實際瓶口內徑。

機構安排在螢幕兩側；末端架相對探頭向外偏置 74 mm，以橋接件回接夾頭。這個橋接件與支撐臂尚未取得撓度、疲勞或承重資格。支撐件標為 `support_envelope`／`mount_envelope`；轉軸含名義 M5×35 螺栓、螺母、三片墊片與兩段金屬軸套包絡；預緊、防鬆、配重／彈簧、齒槽保持力、止擋與底板承力尚未完成。

升降檢查包含同頭移動件配對，以及兩頭各 11 個高度的 121 組配對。檢查不包含所有旋轉關節組合、連續掃掠、包含關係、線材與受力變形。只有四件肘部支撐的試配 STL，置於 `fit-prototypes/LR_CHECK_*_mm.stl`；其餘零件與整機製造包未發布，不得拿概念件直接代替可裝配製造件。

## 重跑

先依 [06-scripts](06-scripts.md) 生成 V10 共用機箱／螢幕基線，再執行：

```bash
$HOME/miniconda3/envs/blender-mcp/bin/python -m scripts.verify.lab_rotary_verify_real
```

此入口沿用既有 BlenderSocketOracle，執行受版本控制的本地生成器，並已接入 `scripts/ci.sh --real`；不是新公開 MCP 執行通道。解析規格為 `RotaryLiftSpec`，Blender 幾何、驅動與檢查為 `scripts/model_lab_rotary.py`。

參考與沿用決策見 [09-references](09-references.md)。完整需求追溯见 [07-matrix](07-matrix.md)。

肘部兩段支撐已整合齒盤；目前保留 `support_envelope` 名稱以免被當成已通過製造契約的零件。接回段繞過齒盤與升降連桿。肩部／腕部的實體可裝配介面，以及肘部工具手柄／裝入掃掠與預緊保持力仍未取得資格。

四件 STL 由独立副本在局部原點匯出，保留組裝模型姿態。驗證入口以二進位座標重算尺寸，與 Blender 世界頂點比較，差值限 0.02 mm。CI 在生成後依序執行左右兩份支撐契約，並檢查四件各自單連通、零副本間碰撞與檔案存在；支撐固定面、列印方向與載荷仍需評估。
