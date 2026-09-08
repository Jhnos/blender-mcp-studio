# 靈巧手 V3 — 單自由度線驅動 + 雙層充氣夾層

**Status:** ACTIVE

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

- 文件樹 20 檔已寫,平鋪於 `docs/hand-v3/`(子目錄會超過導航兩跳而變孤兒)。
- 追溯矩陣 22 條需求全部有驗證器,R1–R6 綠。過程中 `trace_check.py` 抓到一個真缺口:
  PS-6 原本只有 differential 沒有 artifact,已補。
- InMoov 授權為 CC BY-NC 3.0,個人非商業可用須署名(親驗)。
- InMoov 每指**兩條**線,與 V3 的單腱前提不同,兩者腱力不可互比(親驗)。
- repo 內部已有單軸指節鏈 `HingePhalanxSpec`,活的且有測試;產生器在
  `scripts/archive/`,歸檔理由是零引用不是幾何缺陷。

### Open failures

- 覆蓋矩陣 [`../hand-v3/v7-matrix.md`](../hand-v3/v7-matrix.md) 上**每一列都是 TODO**。
  唯一可立即跑的是 V1／V2 的四份迴歸契約。
- 抓持力無法由現有管線驗證,只能實體台架量。台架一次都還沒跑,
  [`../hand-v3/v8-results.md`](../hand-v3/v8-results.md) 全部空白。

### Next step

- Track 1:依 [`../hand-v3/08-inmoov.md`](../hand-v3/08-inmoov.md) 下載並列印 InMoov 右手,
  同時採購兩隻外層手套與針筒。
- Track 2:寫 `tests/unit/core/test_finger_v3.py` 的第一個**會紅**的測試——
  腱路徑長變化超過致動器行程時必須 raise。
