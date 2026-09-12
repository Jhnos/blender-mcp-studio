# 獨立四連桿升降概念

使用者提出以活動臂取代線性導桿滑座後的候選。兩頭仍共杯、各自活動；此階段只有運動與空間概念，沒有列印發布或承重資格。V10 滑座模型僅供共用外殼／螢幕基線，不是新機構的驗收依據。

## 看與操作

產出位於 `tmp/lab-station-rotary/`：

- `working.png`：兩頭量測位置。
- `left-raised.png`：只抬起毛細管。
- `both-raised.png`：兩頭各抬起 100 mm。
- `rotary-concept.blend`：選取 `LR_CTRL_capillary` 或 `LR_CTRL_pH_temp`，調整自訂屬性 `lift_mm`（0..100）。
- `motion.json`：每頭 101 個位置，探頭／容器、桿端閉合、直立與另一頭不動的檢查。
- `assembly-motion.json`：每頭 21 個位置對其他固定網格的表面碰撞，以及固定支撐對既有外殼／HMI 的靜態碰撞。只豁免底面位於 80 mm 的支座／上蓋名義接觸；不代表支座已固定。
- `red-broken-link.json`：使其中一根連桿停止轉動，閉合檢查必須拒絕。

## 尺寸與限制

平行桿中心距 130 mm、兩端垂直軸距 40 mm。從水平下方約 22.62° 抬至上方約 22.62°，得到 100 mm 升程；中途向前最大偏移 10 mm，並非直線。原三探頭在假設內徑 66 mm 的圓筒中保持空間餘量；容量 250 mL 不能代替實際瓶口內徑。

機構安排在螢幕兩側；末端架相對探頭向外偏置 66 mm，以橋接件回接夾頭。這個橋接件與支撐臂尚未取得撓度、疲勞或承重資格。支撐件標為 `support_envelope`／`mount_envelope`；轉軸為名義金屬銷，螺母、預緊、防鬆、配重／彈簧、齒槽鎖定、止擋與底板承力尚未完成。

檢查不包含所有關節組合、雙頭同時運動、連續掃掠、所有移動件彼此碰撞、包含關係、線材與受力變形。沒有 STL；不得拿概念件直接代替可裝配製造件。

## 重跑

先依 [06-scripts](06-scripts.md) 生成 V10 共用機箱／螢幕基線，再執行：

```bash
$HOME/miniconda3/envs/blender-mcp/bin/python -m scripts.verify.lab_rotary_verify_real
```

此入口沿用既有 BlenderSocketOracle，執行受版本控制的本地生成器，並已接入 `scripts/ci.sh --real`；不是新公開 MCP 執行通道。解析規格為 `RotaryLiftSpec`，Blender 幾何、驅動與檢查為 `scripts/model_lab_rotary.py`。

參考與沿用決策見 [09-references](09-references.md)。完整需求追溯见 [07-matrix](07-matrix.md)。
