# v6 — 可執行腳本與指令

> 回導航 [[hand-framework/v0-INDEX]] · 相關 [[hand-framework/v4-scenarios]]、[[hand-framework/07-contracts]]、[[30-verification]]

手動點一遍不算驗證。這一頁列的是**腳本與指令**,每條帶狀態;狀態欄是唯一會變的東西。

## 機器腳本

| 場景 | 腳本 | 狀態 |
|---|---|---|
| SF-15, SF-16, SF-9 | `tests/unit/core/test_docs_hand_framework_figures.py` | **已建**(M0) |
| SF-1 | `tests/unit/verification/test_contract_builder.py` | **已建**(M2):生成 == 簽入,兩份 |
| SF-2 | `tests/unit/planning/test_layout_plan.py` | **已建**(M2):四件 242.0 × 103.5 離線算出 |
| SF-3 | `tests/unit/planning/test_expected_counts.py`、`test_palm_v3.py` | **已建**(M4):三指列窄一節距、站台 F1–F3 + T |
| SF-5 | `tests/unit/planning/test_phalanx_plan.py`;真機 `hand_v3_gradient*.json` | **PASS**(M5):夾具實例在真機以 `expected_shared_mesh_count: 2` 過 20/14 |
| SF-4 | `tests/unit/core/test_palm_v3.py` 新增八個案例 | **已建**(M4):23 拒、22 不變、推導預設相等、取樣跟上限 |
| SF-6 | `tests/unit/verification/test_generator_imports.py` | **已建**(M2):首跑抓到 5 個沒重載的模組 |
| SF-7 | `tests/unit/scripts/test_hand_execution_reads_plans_only.py` | **已建**(M3):浮點白名單 + 名字型字串,附植入夾具 |
| SF-8 | `tests/unit/core/test_hand_instance_conformance.py` | **已建**(M6):對註冊表參數化,`strict=True` 重建、前綴互異、佈局進床 |
| SF-10 | `scripts/verify/regenerated_package_matches_shipped.py --package hand-v3` | **PASS**(M3):新產生器 4/4,面數逐一相等 |
| SF-11 | `scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3.json`(+ `hand_v3_finger.json --skip-generate`) | **既有**;M3 起驗的是新產生器(20/14) |
| SF-12 | 同上,`hand_compact*.json` | **PASS**(M6):真機 20/14;第一次 19/20(拇指擦過 F3),重掃後全過 |
| SF-13 | `scripts/ci.sh --real` 首跑計時 | **已量**(M1):三條閘門合計 8 s,見 [[hand-framework/v8-results]] |
| SF-17 | `checkpoint_check.sh .` | **既有** |

## 每片收尾的固定順序(Mac)

```bash
# 推到 Mac,清場再跑(stash -u 是本輪被咬過的紀律)
git push blendermac main:synced-main --force
ssh blendermac 'cd ~/Blender_MCP_drawer && git stash -u -q; git reset --hard synced-main -q && scripts/ci.sh'

# M1 起:契約 + 差分在 --real 裡(Blender 沒開 → SKIP,絕不假綠)
ssh blendermac 'cd ~/Blender_MCP_drawer && scripts/ci.sh --real'

# checkpoint
ssh blendermac 'cd ~/Blender_MCP_drawer && bash "$HOME/.codex/skills/milestone-checkpoint/scripts/checkpoint_check.sh" .'
```

## 文件閘門(本機即可)

```bash
python3 -m pytest tests/unit/core/test_docs_dcc.py tests/unit/core/test_docs_hand_framework_figures.py -q
python3 <requirement-traceability skill>/assets/trace_check.py docs/hand-framework/02-requirements.md
```

## 差分的決定性指令(M3)

```bash
ssh blendermac 'cd ~/Blender_MCP_drawer && P=$HOME/miniconda3/envs/blender-mcp/bin/python && \
  $P scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3.json && \
  $P scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3_finger.json --skip-generate && \
  $P scripts/verify/regenerated_package_matches_shipped.py --package hand-v3'
```

三條都綠 = HF-1 成立 = 舊產生器可以刪。**2026-09-09 三條綠,三個舊模組已刪。**
