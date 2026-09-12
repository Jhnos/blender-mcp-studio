# 分段電極臂與三角平台概念

從 [12-simple-concept](12-simple-concept.md) 延伸：保留上臂鉸鍊，前臂改為平行雙桿與三角末端平台。位置調整由肩部與前臂共同提供，探頭角度仍手動校正。這不是上臂固定後仍有兩個位置自由度的五連桿，也不是自動直線導引。

## 參考與取捨

- [Agilent 3200EA 官方手冊](https://www.agilent.com/Library/usermanuals/Public/5973-1782.pdf)：兩組雙搖桿可保持電極平台水平。本概念借用分段電極臂用途與雙桿形式，但只將前臂做成平行四連桿，不宣稱具備該產品的整臂自動水平功能。
- [ELMETRON EH-10](https://elmetron.com.pl/electrode-holder-eh-10.html)：20 cm ABS 臂、不鏽鋼軸與多電極／溫度支援，作尺寸與用途參考，不引用其材料強度作列印資格。
- [GOnDO EH-10](https://www.gondo.com.tw/products_detail/46.htm)：ABS 主體、高度調整與旋轉，作簡潔配置參考；與 ELMETRON 同名而非同產品。
- 沿用本地 link、Boolean、渲染與 oracle，不複製商品幾何。生成入口為 `scripts/model_lab_platform.py`。早前 GitHub 查找的旋鈕案例沿用 [12-simple-concept](12-simple-concept.md) 的來源紀錄，不引入新 CAD 引擎。

原廠照片另見 [GOnDO 裝探頭照片](https://www.gondo.com.tw/upload/201806251037398boya1.JPG)。採近距平行桿與小型端盤的比例；照片遮蔽的內部連動、鎖緊與走線結構沒有被宣稱還原。

## 幾何與五金範圍

上臂 150 mm，兩支前臂各 150 mm；平行四連桿兩側軸距 24 mm，三角板探頭角點偏置 28 mm。關節錯層 8.4 mm、臂厚 8 mm、梁寬 12 mm、臂端盤 Ø22 mm（底座維持原尺寸）。新增第二根前臂放到外側避讓 HMI，夾座接頸與夾座一體，兩頭在工作姿態維持原共杯位置。

調整機構：12 支名義螺絲、12 顆螺母、4 個列印被動軸包絡；無獨立軸套／墊片。不是整機 BOM，不含後續探頭夾緊與板件固定。列印被動軸尚無防脫設計，不能用此包絡當製造軸。

## 驗證邊界

- `ElectrodeArmSpec` 與領域測試：九個位置目標的固定桿長、平行閉合、三角板角點、超距拒絕。
- 實際網格：每頭 21 個升降取樣（0–100 mm，每 5 mm），清杯後前後各 20 mm，合計 46 個單頭位置；另一頭保持不動。
- 每個位置查五組共同軸線與孔周圍材料、六個結構件全配對表面交叉、雙頭／HMI／外殼交叉及探頭／杯壁交叉。
- 雙頭抬高後，HMI 16 個收折角度；這不代表所有臂姿態下皆可折屏。
- `scripts/verify/lab_simple_verify_real.py` 依序重建 simple 與本概念，再移動 follower 材料，必須拒絕且還原後通過。這個入口由完整 real CI 執行。
- 未驗連續掃掠、全部五金互碰、線材、實體列印、軸防脫、齒槽離合、負載與固定力。自碰檢查只涵蓋列出的六個結構件，不能宣稱全機零干涉。

輸出：`tmp/lab-station-electrode-compact/electrode-concept.blend`、`working.png`、`raised.png`、`extended.png`、`screen_folded.png`、`verification.json`、`red-disconnection.json`。無製造 STL 發布。
