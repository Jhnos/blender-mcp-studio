# 目前交付件：需求與驗證對照

Population: 每次由共用 ArtifactCatalog 擷取的目前 ModelSpec、完整原件收據、原生模型、STL 集合與該次新產生的 3MF／G-code；排除歷史研究生成器、其他工作與測試替身。空集合、缺件、來源指紋不符皆拒絕，不能退回舊版。

需求來源只有 [任務16](../../tasks/16_lab-station.md#specification)。本表定義驗收必須接上的檢查，不指定版本、不記執行進度。歷史研究模型的 R1–R56 見 [研究矩陣](07-matrix.md)，不能替本表解除要求。實際結果與未解除項目只讀 [任務索引](../../tasks/00_INDEX.md)。

`Verified-by` 必須指向會對交付件做斷言的檢查。`—` 表示尚無足以解除整條要求的檢查；不能填入規劃中的檔名、局部觀察或研究模型的成功報告來讓追溯工具轉綠。

| ID | Requirement | Tier | User-visible | Kind | Verified-by |
|---|---|---|---|---|---|
| C01 | REST、MCP、schema 範例與本機唯一宣告取得同一目前交付件；缺失來源拒絕，不要求客戶端另選版本 | voc | yes | behavior | artifact:scripts/verify/native_pipeline_verify_real.py::verify |
| C02 | 原件不覆寫；修訂後原件身份完整、未修改件保持原 bytes、公開下載逐件吻合來源／輸出收據 | voc | yes | behavior | artifact:scripts/verify/native_pipeline_checks.py::check_product; artifact:scripts/verify/native_pipeline_checks.py::check_downloads |
| C03 | 兩頭獨立；上臂及下臂均為雙桿，上下臂以四點梯形板連接；上下與前後提供獨立可鎖定調整，探頭角度另調 | voc | yes | behavior | — |
| C04 | 全機可用姿態及退齒、轉動、就座、收折與維修路徑無非預期交叉、內含或斷接；碰撞反例會被拒絕 | product | yes | behavior | — |
| C05 | 三探頭共用250 mL容器、約200 mm可調伸距；抬出與換杯路徑保持另一頭固定，符合真實杯口及探頭尺寸 | voc | yes | behavior | — |
| C06 | 原件螢幕修訂的五階段控制保持剛體身份與原 local surfaces，螺栓隨動、退齒及目標角控制可保存重開 | engineering | yes | behavior | artifact:scripts/verify/native_revision_verify_factory.py::host; artifact:scripts/verify/native_revision_fixture.py::callback_reopen |
| C07 | 可調螢幕能收起；後蓋可開、頂部通風；實際開關、卡扣、鉸鍊、加強結構與手指／工具操作空間可用 | voc | yes | behavior | — |
| C08 | LCD與電路空間依實際板件／接頭／線材尺寸裝配，探頭夾持及幫浦／微壓／pH前端／供電接口可固定；佔位包絡不當成真實硬體 | product | yes | behavior | — |
| C09 | 全部同身份STL完成並通過幾何檢查後，才用同一組零件衍生3MF；保存全件擺位與有向表面，不跳過或替換零件 | voc | yes | behavior | artifact:scripts/verify/native_pipeline_verify_real.py::positive; artifact:scripts/verify/native_pipeline_checks.py::check_slice_inventory |
| C10 | 單盤新切片包含全部具名原件沉積及接床路徑、支撐與brim；含線寬及指向圓弧的完整沉積包絡不越界 | product | yes | behavior | artifact:scripts/verify/native_pipeline_checks.py::check_extrusion_receipt |
| C11 | 實際使用PLA、0.4 mm噴嘴及0.2 mm模型層高，設定穿過全部邊界並在新產物一致；不以支撐插入層誤判模型層高 | product | yes | behavior | — |
| C12 | 只拆支撐與brim即可裝配／活動／鎖定；不鑽孔、研磨或修整配合面，且支撐移除不破壞孔、齒面、插銷及止扣 | voc | yes | behavior | — |
| C13 | 探頭保持力、關節鎖定、臂件與鉸鍊強度、層向風險及抗傾倒以實際材料／負載證據驗證，不把水密或固定姿態當承載資格 | engineering | yes | behavior | — |

## 如何解讀局部觀察

- 控制欄位存在、driver有效或一個內部姿態的兩個位移方向獨立，只能支援C03的局部軟體觀察；還需要實際四點連接、可用範圍與鎖定的檢查。
- C06驗控制與原件保持，不能替C04／C07驗整機干涉及操作空間。C09／C10不認證物理黏附、支撐可移除或C12的直接配合。
- C11須讀取該次實際輸出設定並與擷取的列印條件及機器／噴嘴資料核對；命令參數或測試替身符合，不足以解除產物層要求。
- C05／C08／C12／C13的硬體、材料或量測未知值必須明示，不能由歷史假設或佔位模型默認成真實尺寸。驗收未齊時保留整體要求，不縮小為軟體流程成功。

追溯檢查方法見 [驗證SSOT](../../30-verification.md)。本表存在未接上的檢查時，追溯工具應拒絕完整追溯；這不是目前核心CI已認證所有機械要求的證據。
