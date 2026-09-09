# 碎片預算改由實測支撐,決定性探針涵蓋每一個布林零件

**Status:** AWAITING-ACCEPTANCE

## Goal

現在的碎片預算 `SLIVER_TRIANGLES_PER_PART = 2` 是**從規劃推導**的,沒有任何一次實測
支撐它。把它變成有量測背書的數字,並讓決定性探針從「單指的零件」擴到**每一個**
會做布林的零件。

## Context to read

1. `scripts/verify/build_determinism_probe.py` — 現有探針;目前只跑 `hand_plan(...).loose_finger.parts`
2. `src/verification/package_reproduction.py:43` — `SLIVER_TRIANGLES_PER_PART = 2` 與 `sliver_budgets()`
3. `src/core/planning/hand_plan.py:42` — `HandPlan` 有 `chains`(每個站一條)與 `palm`,都不在探針涵蓋內
4. `docs/LESSONS_LEARNED.md` 兩條同族:「精確相等的閘門是用一個實例的運氣校準的」、
   「拿一個自己就不穩定的東西當基準,『有差異』不帶任何資訊」

## Specification

### 涵蓋

探針改跑該實例**所有**站的 `chains`,加上 `palm`。目前只跑第一站的單指,
所以掌盤與其餘站的零件從來沒有被量過決定性。

### 量測落檔

探針新增 `--json <path>`,把每個零件跨 N 次重建的三角面數散布寫成紀錄檔;
簽入一份 `docs/hand-framework/determinism.json`,內容是最近一次實測的
「每個零件的最大面數差」。紀錄檔要帶量測日期與 runs 數——**沒有日期的量測快照
不能當現況**。

### 閘門

新增單元閘門:對每一個已登錄實例,`sliver_budgets()` 給的預算必須 **≥** 紀錄檔量到的
最大差。預算小於實測值就紅(那代表包差分隨時會假紅);預算遠大於實測值也要能看出來,
但**不擋**——寬鬆的預算是保守,不是錯誤。

`ci.sh --real` 新增一條低 N 的探針跑,判準是「沒有任何一步的面數差超過紀錄檔的值」。
N 與秒數在首跑後填回 `docs/30-verification.md` 的閘門表。

### 不做

- 不改任何幾何。本任務不碰產生器,`models/` 的位元組必須一個字元都不動。
- 不追求「讓布林變成確定性的」。輸出順序不定是 exact solver 的性質,
  本任務是要**量它、把預算釘在量到的值上**,不是消滅它。

## Acceptance checks

先寫會紅的那一個:對照紀錄檔的閘門,在紀錄檔還不存在時必紅。

- `scripts/ci.sh` 全綠。
- 探針涵蓋 `chains` 全部與 `palm`;一個新增的站或零件沒被涵蓋要能被閘門看見。
- 紀錄檔帶量測日期與 runs 數。
- `--real` 新增的探針閘門綠,且秒數已填回 `docs/30-verification.md`。
- `models/` 底下沒有任何檔案變動(`git diff --stat models/` 為空)。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- 探針存在且可跑(`V01.0R.005` 入庫),但只涵蓋第一站的單指零件,且不在 `ci.sh` 裡。
- `SLIVER_TRIANGLES_PER_PART = 2` 目前唯一的依據是規劃推導。
- 2026-09-09 實測到的一個數字:hand-compact 整手重生成是 48248 面,已發布的 manifest 記 48244,
  差 4,落在預算內——但「4」這個差是**觀察到的**,不是量測分布。
- 起點:`V01.0R.008`,`--real` 27 條全綠。

- **實測完成(2026-09-09,常駐 Blender,每個零件 4 次)**:三個實例、八個零件裡,
  只有 `HK_COMPACT_PHALANX_2` 的完成面數會動,差 **2**;其餘七個(含三個掌盤)全部 **0**。
  預算 `2` 從此是量到的上界,不是規劃推導。紀錄在 `docs/hand-framework/determinism.json`,
  帶量測日期與 runs 數。
- **頂點順序幾乎每一步都不同**——hand-compact 17 步、hand-v3 13 步、gradient 26 步。
  那是 exact solver 的性質不是缺陷,所以 CI 判準用「完成品面數差不超過預算」,
  不用「完全一致」;後者會讓閘門永遠紅,然後所有人學會忽略它。
- `--real` **28 條全綠**(2026-09-09),新閘門實測 18 s。
- `models/` 一個位元組都沒動(`git diff --stat models/` 為空)。

### Open failures

- 無。剩下的只有使用者驗收。

### Next step

- 使用者裁決是否歸檔;歸檔後照既定順序做第四個實例。
