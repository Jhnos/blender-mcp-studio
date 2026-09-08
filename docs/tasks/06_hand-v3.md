# 靈巧手 V3 — 單自由度線驅動 + 雙層充氣夾層

**Status:** AWAITING-ACCEPTANCE

## Goal

交出 V3 的文件樹:設計文件、需求追溯矩陣、驗證計畫。文件先行,幾何後行。
本階段**不寫任何幾何程式**,但要讓使用者能立刻開始 Track 1 的實體列印。

## Context to read

1. [`../hand-v3/README.md`](../hand-v3/README.md) — V3 導航
2. [`../hand-v3/00-context.md`](../hand-v3/00-context.md) — 範圍與不做什麼
3. [`../hand-v3/02-requirements.md`](../hand-v3/02-requirements.md) — 追溯矩陣
4. [`../verification/generated-artifacts.md`](../verification/generated-artifacts.md) — 新增模型的六步

## Specification

一隻擬人手:四指一排加對生拇指,每指三個指節由一條腱連動閉合(欠致動),
外面套兩層手套,手指閉合後用針筒往夾層打氣以加強抓持。

兩條軌並行:Track 1 直接印 InMoov 當實體試驗台回答「充氣有沒有用」;
Track 2 從 repo 既有的 `HingePhalanxSpec` 發展 V3 自己的生成式幾何。

V1／V2／V6 是凍結交付物,一個位元組都不動。

## Acceptance checks

- `pytest tests/unit/core/test_docs_dcc.py` 三條全綠(無斷鏈、無孤兒、埠號未外洩)
- `trace_check.py docs/hand-v3/02-requirements.md` 回 0
- `NOTICE` 列出每個外部來源與其授權
- 使用者可依 [`../hand-v3/08-inmoov.md`](../hand-v3/08-inmoov.md) 直接開始採購與列印
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- `SingleTendonFingerSpec` 已交(`src/core/domain/finger_v3.py`),10 條測試綠。
  實測腱行程需求 14.40 mm vs 致動器行程 30.0 mm。
- **兩份真機契約 11/11 全 PASS,印製包 `models/hand-v3/` 已發布(revision `hand-V3`)。**
- 列印佈局已交:五件一盤,182.5 × 100.5 mm,相鄰重疊 0,放得進 256 mm 床身。
- **整手組裝已交**:1 掌盤 + 19 指節,零非流形邊、指間零靜止干涉。
- 掌盤幾何已交:一個殼、零非流形邊、五條腱道真的貫通、進氣口貫通、袖口夾槽已切。
  過程中修掉「拇指根浮在空中」與「射線在空氣裡回報通了」兩個缺陷。
- 手指契約 `hand_v3_finger.json` **真機 12/12 全 PASS**。
- `AnthropomorphicPalmSpec` 已交,對指可達性 20.7 mm < 22.0 接觸判準(拇指不轉為 26.1)。
  拇指根站在掌面前方,是量測推翻假設後的結果;鏈長則在整手降到三節後與手指相同,
  對生角與掌前凸台才是它成為拇指的原因。
- oracle 新增 `center_channel_expected_open`:不是每個重複件都是空心觸手。手指沒有中央
  通道,而且不能有——那會切穿銷孔。做成**契約宣告期望值**而不是跳過檢查,因為本專案的
  規則是「量不到就是失敗,不是跳過」;而且「軸上是實心的」本身就是一條斷言。
- **修掉一個繼承來的缺陷**:借來的連桿在靜止姿態就讓相鄰件穿透 2.5 mm(實測 303 個面),
  而那個產生器被歸檔時從未被契約驗過。關節中心 24 → 27 mm,重建後靜止與 ±50° 掃掠零重疊。
- 手指最終形態:**四件共用一個網格 = 一個零件編號**,整指 229 mm,腱孔 4/4 位置正確,
  零非流形邊。三張渲染圖 + 平鋪列印佈局已產生。
- 手指產生器已交,四節共面指節建得出來:零非流形邊、四個獨立網格、腱孔中心與力矩臂
  4/4 相符。過程中修掉三個「逐件檢查全綠但東西是壞的」缺陷,詳見 CHANGELOG V01.09.000。
- **實測結論**:力矩臂的可用窗只有 1.15 mm 寬,比值 1.16,**排不動三個關節的順序**;
  順序必須交給彈簧勁度梯度。
- `PresentationProfile` 已交,`setup_render` 改讀 profile。行為未變的證明:場景讀回 16 項
  全相符、四個 STL 位元組相同。**PNG 不能當 oracle**——同一份程式跑兩次雜湊就全不同。
- **實測推翻了文件的一個說法**:`HingePhalanxSpec` 單軸的是**連桿**,它的串接規則
  `assembly_rotations_deg` 是 `(0, 90, 0, 90)`——交替軸。兩份文件已改寫。

- 文件樹 20 檔已寫,平鋪於 `docs/hand-v3/`(子目錄會超過導航兩跳而變孤兒)。
- 追溯矩陣 22 條需求全部有驗證器,R1–R6 綠。過程中 `trace_check.py` 抓到一個真缺口:
  PS-6 原本只有 differential 沒有 artifact,已補。
- InMoov 授權為 CC BY-NC 3.0,個人非商業可用須署名(親驗)。
- InMoov 每指**兩條**線,與 V3 的單腱前提不同,兩者腱力不可互比(親驗)。
- repo 內部已有單軸指節鏈 `HingePhalanxSpec`,活的且有測試;產生器在
  `scripts/archive/`,歸檔理由是零引用不是幾何缺陷。

### Open failures

- 覆蓋矩陣 [`../hand-v3/v7-matrix.md`](../hand-v3/v7-matrix.md):域規格那四列已 PASS,
  **其餘每一列仍是 TODO**。幾何尚未產生。
- 抓持力無法由現有管線驗證,只能實體台架量。台架一次都還沒跑,
  [`../hand-v3/v8-results.md`](../hand-v3/v8-results.md) 全部空白。

### Next step

- Track 1:依 [`../hand-v3/08-inmoov.md`](../hand-v3/08-inmoov.md) 下載並列印 InMoov 右手,
  同時採購兩隻外層手套與針筒。**使用者執行。**
- Track 2 下一片:整手契約 `hand_v3.json` 在真機跑,然後發布印製包 `models/hand-v3/`。
