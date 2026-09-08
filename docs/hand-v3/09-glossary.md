# 09 — 名詞與單位

> 回導航 [[hand-v3]]

## 代號

讀到裸代號先查這裡。這張表只解釋**在 V3 這棵樹裡**的用法。

| 代號 | 全名 | 在這裡的意思 |
|---|---|---|
| **DCC** | doc-centric campaign tree | 一檔一主題 + 導航表 + 互相指向的文件樹。本 repo 已有一棵,由 `tests/unit/core/test_docs_dcc.py` 機器強制:斷鏈、孤兒、事實重複三條都會紅 |
| **Lane A** | — | 機器可量化的正確性。**全部由自動化包辦,不丟給使用者**。少數項目由人執行,但判準仍是數字 |
| **Lane B** | — | 品味與體感。只有交使用者裁決才有意義的東西 |
| **IDD** | Interface-Driven Development | 介面先定死,實作只能透過它說話。V3 的用法見 [[hand-v3/07-interfaces]] |
| **VOC** | Voice of Customer | 需求展開的最上層:使用者看得到、驗得到的東西 |
| **DFMEA** | Design FMEA | 先列「它會怎麼壞」,每個失效模式各配一個夾具與一條斷言。見 [[hand-v3/v3-failure-modes]] |
| **YCB** | Yale-CMU-Berkeley object set | 抓取研究的標準家用物體集,用來讓不同人的量測可比 |
| **欠致動** | underactuated | 自由度多於致動器。V3 每指三個關節、一條腱,所以是欠致動 |
| **MDR** | Metadata-Driven Rendering | 宣告式 schema 驅動渲染。**V3 沒有新 UI,本案不適用**,列在這裡是為了說明它為何不出現 |

## 單位

- 幾何一律 **mm**,與 repo 其餘部分一致。STL 沒有單位中繼資料,切片時保持 mm、100%。
- 壓力一律 **kPa**(大氣壓約 101 kPa)。針筒推的是**錶壓**,不是絕對壓。
- 力一律 **N**。廚房磅秤讀到的是質量,乘 9.81 才是牛頓——記錄時兩個都寫。
- 角度一律**度**,關節角以完全伸直為 0。

## 命名

- V3 的 Blender 物件前綴 `HH_V3_`,與 V1 的 `HH_OCT_`、V2 的 `HH_OCT2_` 區隔。
- 印製包 slug `hand-v3`,manifest revision `hand-V3`。
