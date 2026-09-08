# 03 — 域規格:掌盤參數化與新不變式

> 回導航 [[hand-framework]] · 相關 [[hand-framework/01-boundaries]]、[[hand-v3/04-palm-thumb]]、[[hand-v3/03-finger]]

## 連桿介面

`FingerLinkSpec`(`src/core/domain/finger_link.py`)是結構型 Protocol,列出 V3 那一疊
真正讀到的每個連桿屬性。**成員數不寫在散文裡**——散文裡的計數是沒人驗的宣稱,
本輪已經抓到一次(docstring 說 19、實際 22);M4 把那句改掉。

兩個實作:`HingePhalanxSpec`(借來的,凍結,只允許加唯讀屬性)與 `CompactHingeLinkSpec`。
`has_bearing_seat` 是產生器**問**它拿到哪種關節的方式,不是從「座徑等於孔徑」去猜。

## 掌盤 M4 之前寫死了什麼(親驗,已改)

| 位置 | 寫死的 | 問題 |
|---|---|---|
| `:44-59` | `finger`/`thumb` 預設 = `HingePhalanxSpec(joint_count=2, offset=27.0)` + `(6.6, 6.6)` | 掌盤只認識一種連桿 |
| `:192-196` | `range(4)`、`3 * row_pitch` | 指列數是常數 |
| `:69`、`:85` | `thumb_base_palmar_mm=22.0`、`pinch_contact_mm=22.0` | 絕對值;註解說上限是掌盤厚度(`link.body_depth_mm`),**無不變式** |
| `:116` | `clearance = printed_radial_clearance_mm * 4` | 那個 4 沒有名字 |
| `:32` | `_SAMPLES_DEG = (0…50)` | 綁死 50°,換了上限的連桿會被靜默截斷 |
| `:99` | `strict=False` | 對生可達性與比例的拒絕預設關閉 |

## 五條不變式(M4 已建;全部加法式、對 V3 逐位元組中性——契約與差分未動)

| # | 不變式 | V3 值 | should-fire 夾具 |
|---|---|---|---|
| I1 | `thumb_base_palmar_mm <= finger.link.body_depth_mm` | 22 ≤ 22(在邊界上,與 `:74-75` 「坐在邊緣」一致) | 23 → 拒絕 |
| I2 | `pinch_contact_mm <= finger.link.body_depth_mm` | 22 ≤ 22 | 23 → 拒絕 |
| I3 | `row_finger_count: int = 4` 欄位 + `station_labels` 屬性 | 4 | 0 → 拒絕 |
| I4 | `thumb_boss_clearance_mm` 具名,預設 = 4 × 徑向間隙 | 1.0 | 小於連桿間隙 → 拒絕 |
| I5 | `_SAMPLES_DEG` 改為由 `maximum_articulation_deg` 每 10° 推導 | 同一個元組 | 上限 60 → 元組多一格 |
| I6(M6 加) | `strict` 下拇指**靜止**時與每根直伸的手指表面淨距 > 0(`opposition.thumb_rest_clearance_mm`) | 2.49 mm | 平行、只離指面 5 mm 的拇指 → 拒絕 |

`thumb_base_palmar_mm`、`pinch_contact_mm`、`thumb_boss_clearance_mm` 都是「0 = 由連桿推導」,沿用 `finger_v3.py`
裡 `wiring_bore_offset_mm` 的 sentinel 模式;V3 推出來剛好 22.0 / 22.0 / 1.0——ES-2 的測試斷言這件事,
而且 `AnthropomorphicPalmSpec() == AnthropomorphicPalmSpec(0, 0, 0)`。

## 為什麼要切一個檔(M4 已切,`palm_v3.py` 369 行)

`palm_v3.py` 目前 372 行,預算 380 行警告、400 行硬上限。任何新增不變式都會越線。
切法照 `bearing_seat_cuts` 的形:`_row_tip_world`、`_thumb_tip_world`、`thumb_index_tip_gap_mm`、
`_posture_grid`(`:222-224, 335-372`)搬到 `src/core/domain/opposition.py`,變成「拿掌盤當參數的函式」,
掌盤留三行委派。可達性的數字由既有三處測試釘住(`test_palm_v3`、`test_docs_hand_v3_figures`、
`test_hand_v3_print_package`),搬動若改了任何一個數就會紅。

## 精簡實例的掌盤要另外給的

`thumb_offset_mm`、`thumb_base_drop_mm`、`thumb_base_palmar_mm ≤ 15`、`pinch_contact_mm ≤ 15`
——這些是**輸入**,照 `palm_v3.py:72-73` 描述的掃法重掃,不是新規格。
掃出來若在 `strict=True` 下被拒,**那是發現,停下回報**;不做平放拇指的 fallback。

M6 結果:第一次只對可達性掃(2823/7168 合格),選出的擺位在真機被 `disjoint_groups` 抓到——直伸的拇指擦過第三指
(8 個面)。根在掌盤深度上時,兩個橢球的赤道在投影交叉處恰好相切;V3 沒撞是因為它唯一的交叉落在關節上。
於是加了 I6,第二次掃(879 個候選)選 offset 24、drop 22、對生 25°、tilt −10°:靜止淨距 3.48 mm,指尖 1.08 mm,比例 1.14;
真機 20/14 全過。
