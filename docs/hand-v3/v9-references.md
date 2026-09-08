# v9 — 來源

> 回導航 [[hand-v3/v0-INDEX]] · 相關 [[hand-v3/01-prior-art]]、[[hand-v3/06-softlayer]]

**只列親自存取過的來源。** 取不到就寫 not found——DOI、arXiv 編號與 repo 名稱
是最容易被憑空生成的東西,寧可空著。

等級標記:`[親驗]` 是本專案自己開頁面讀到的;`[轉引]` 是研究代理回報而未複核的。

## 充氣／可調摩擦夾爪

| 來源 | 用到的內容 | 等級 |
|---|---|---|
| arXiv 2510.27184《Hybrid Gripper Finger Enabling In-Grasp Friction Modulation Using Inflatable Silicone Pockets》(Ly 等) | 摘要原文:提高內壓使**等效摩擦係數成比例上升**;能在不加大夾持力下抓起又重又滑的物體 | `[親驗摘要]` |
| arXiv 2502.00926《Structured Pneumatic Fingerpads for Actively Tunable Grip Friction》(Allison、Kelly、Hatton) | 摘要原文:摩擦力最多可差 **2.8 倍**;材料成本 < 1 美元 | `[親驗摘要]` |
| 上述兩篇的**壓力範圍與成功率數字** | 研究代理引為 0–125 kPa、成功率 0→100%,**摘要裡沒有這些數字** | **未證實,不要引用** |
| Becker 等,雙層氣囊 + 有孔約束外層,剪力 5 倍 | 二手轉引,原文未取得 | `[轉引]` |
| 顆粒夾緊(咖啡渣夾爪),PNAS 2010 | 抽真空鎖形狀的原理 | `[轉引]`,PNAS 頁面 403 未取得 |

## 機構

| 來源 | 用到的內容 | 等級 |
|---|---|---|
| inmoov.fr/hand-and-forarm/ | STL 免費下載;一手+前臂約 16 件、750 g、15–20 歐元 ABS;每指**兩條**線(上下側各一);彈簧只做手腕轉動的線長補償;伺服 HK15298 / MG996R;編織釣魚線 200 lb | `[親驗]` |
| InMoov 授權 = CC BY-NC 3.0 | 個人非商業可用,須署名 | `[親驗,經 web 搜尋確認來源為 inmoov.fr]` |
| Birglen & Gosselin 2006, J. Mech. Des. 128(2):356 | 欠致動三節指的抓取穩定性理論 | `[轉引]` |
| Yale OpenHand(grablab) | 浮動滑輪樹差動;CC BY-NC | `[轉引]` |
| RUKA-v2 | MIT 授權,商業化時的替代路線 | `[轉引]` |
| Hayward 等 2011, Scand J Rheumatol 40(5) | 手壓針筒壓力:20 mL 約 220 kPa、60 mL 約 131 kPa | `[轉引,PubMed 21469942 摘要]` |

## 量測方法

| 來源 | 用到的內容 | 等級 |
|---|---|---|
| YCB object and model set(Calli 等,arXiv 1502.03143) | 標準家用物體集,讓不同人的量測可比 | `[轉引]` |
| NIST 夾爪指標(抓取強度、單指強度、抗滑) | 一個人加一台廚房磅秤就能跑的三項 | `[轉引]` |
| ASTM WK83863 抓取強度試驗法(草案) | 存在但付費;未取得內容 | **not found** |

## 明確查不到的

- 熱塑性聚氨酯薄膜、丁腈手套的**爆破壓**。
- 列印 TPU 的氣密性。
- 任何把「腱驅動手」與「充氣夾層」做在一起的開源專案。

**這幾項不要用猜的數字設計。** 需要就自己量,量到就填回 [[hand-v3/v8-results]]。
