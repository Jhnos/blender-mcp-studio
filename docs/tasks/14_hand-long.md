# 第五個實例:每指三關節的長指版

**Status:** TODO

## Goal

把 `joint_count` 第一次建在 2 以外的值上,驗「鏈長不是寫死的」。
與夾爪驗的是不同的軸:那件驗**幾根手指**,這件驗**幾節**。

## Context to read

1. `src/core/domain/hand_instances.py` — 三個實例的 `joint_count` 全是 2
2. `src/core/domain/palm_v3.py` — `strict=True` 的三道判準,尤其指掌比 0.7–1.4
3. `docs/tasks/archive/12_hand-gripper.md` — 上一個實例怎麼挑擺位(取鄰域穩健點,不取最佳點)

## Specification

- 每指三關節,其餘沿用 compact 連桿。
- 拇指擺位照 12 號任務的方法重掃:**先要求兩道判準各有餘裕,再取鄰域穩健點**;
  掃描結果若貼在格線邊界,擴格線之前先懷疑評分函數。
- 契約生成後簽入並進 `ci.sh --real`;決定性由探針量過並進紀錄檔。
- **走產品路徑建造**,不要跑腳本。
- 發布要等使用者對三張渲染圖裁決。

## Acceptance checks

- `scripts/ci.sh` 全綠;`--real` 全綠且含兩條新契約。
- 指掌比落在 `strict` 允許的 0.7–1.4 內——**這是本實例最可能踩到的一條**:
  多一節就是更長的手指,而掌盤沒有跟著長。
- 決定性紀錄含新實例。
- Human acceptance is required before moving this file to `archive/`。

## Hand-off

### Verified facts

- 三個既有實例的 `joint_count` 都是 2;這條軸從未被建在別的值上。
- V3 當初從四節降到三節,理由是手指追過了拇指——多一節會把同一個問題帶回來,
  所以指掌比那道判準是本實例的主要風險,不是形式檢查。

### Open failures

- None yet(尚未動工)。

### Next step

- 先只做規格側:建一個 `joint_count=3` 的候選 spec,看 `strict=True` 過不過,
  過不了就知道要掃哪些參數。
