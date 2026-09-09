# 第四個實例:三站夾爪(兩指＋對位拇指)

**Status:** AWAITING-ACCEPTANCE

## Goal

用既有框架生出第四個實例,把 `row_finger_count` 第一次建在 4 以外的值上,
並且**走產品路徑**(`POST /api/instances/{slug}/build`)而不是跑腳本。

## Context to read

1. `src/core/domain/hand_instances.py` — `HAND_INSTANCES["hand-gripper"]` 與擺位怎麼選的
2. `src/core/domain/palm_v3.py` — `row_finger_count` 的註解與 `strict=True` 的三道判準
3. `docs/hand-framework/v8-results.md` — 每個實例過了哪些檢查

## Specification

- 兩根手指加一根對位拇指,三站九節,走 compact 連桿(與 hand-compact 同一組零件幾何)。
- 拇指擺位由 `strict=True` 下的掃描決定,**取鄰域穩健點而不是最佳點**。
- 契約由 `build_hand_contracts.py` 生成後簽入,並進 `ci.sh --real`。
- 決定性由探針量過,進 `docs/hand-framework/determinism.json`。
- **發布要等使用者對三張渲染圖 Lane B 通過**,與 V3、compact 同規則。

## Acceptance checks

- `scripts/ci.sh` 全綠;`scripts/ci.sh --real` 全綠且含兩條新契約。
- `POST /api/instances/hand-gripper/build` 產出五個網格,數字與契約跑一致。
- 每個零件單一實體;跨站不干涉;關節掃角全程不干涉。
- 決定性紀錄含 `hand-gripper`,且預算涵蓋實測。
- Human acceptance is required before moving this file to `archive/`。

## Hand-off

### Verified facts

- **這個實例第一次就踩到它存在的理由**:hand-compact 的 24 mm 拇指外偏在兩指列的
  40 mm 掌盤上會懸空出去,`thenar_overhang` 的無條件檢查直接擋下。四指下成立的擺位,
  兩指下不成立。
- 擺位掃描做了三輪。前兩輪照「餘裕最大」排序,**最佳解全部貼在掃描範圍的前傾角邊界**——
  目標函數看不到更外面壞掉的東西。第三輪改成先要求兩道判準各有 3 mm 以上餘裕,
  再挑鄰域整片都成立的點:`offset=16, drop=16, opp=25, tilt=-30`,四個參數同時
  各動兩格(±4 mm、±4 mm、±10°、±10°)仍然通過。5411/11440 個候選通過,
  radius 2 的**只有這一個**。
- 靜止淨距 3.04 mm(V3 是 2.49,compact 是 3.48);指尖最近接近 1.78 mm,
  接觸判準 15.0 mm;指掌比 1.22。
- **真機首建即全過**:整手契約 20 項、單指契約 14 項,零 FAIL。關節掃角 11 個角度
  全部零干涉。跨站三對全部零重疊。十四個物件每個都是單一實體。
- 尺寸:掌盤 56 × 30 × 80.5 mm,整手 82 × 30 × 224.5 mm,
  印製佈局 137 × 80.5 mm(床身 256 mm,寬鬆)。
- **走產品路徑建成**:清空 `tmp/hand-gripper/` 後 `POST /api/instances/hand-gripper/build`
  回五個網格,面數與尺寸與契約跑逐項一致。這是任務 10 第一次被用在新東西上。
- 決定性與 hand-compact 同型:`PHALANX_2` 差 2,其餘 0。同一條連桿、同一個遠端零件在動,
  預算 `2` 由第二個實例獨立確認一次。
- `--real` 30 條全綠。

### Open failures

- 無機器面的失敗。
- **紀律上的一筆**:本任務檔是**動工之後**才建的。使用者給形態後應該先開任務檔再動手,
  這次順序反了;內容是事後補寫,不是事前規劃。

### Next step

- 使用者對三張渲染圖 Lane B 裁決。通過才登錄 `PACKAGES` 並發布 `models/hand-gripper/`。
