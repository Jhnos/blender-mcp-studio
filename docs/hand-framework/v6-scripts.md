# v6 — 可執行腳本與指令

> 回導航 [[hand-framework/v0-INDEX]] · 相關 [[hand-framework/v4-scenarios]]、[[hand-framework/07-contracts]]、[[30-verification]]

手動點一遍不算驗證。這一頁列的是**腳本與指令**,每條帶狀態;狀態欄是唯一會變的東西。

## 機器腳本

| 場景 | 腳本 | 狀態 |
|---|---|---|
| SF-15, SF-16, SF-9 | `tests/unit/core/test_docs_hand_framework_figures.py` | **已建**(M0) |
| SF-1 | `tests/unit/verification/test_contract_builder.py` | 待建(M2) |
| SF-2, SF-3, SF-5 | `tests/unit/planning/test_*.py` | 待建(M2) |
| SF-4 | `tests/unit/core/test_palm_v3.py` 新增案例 | 待建(M4) |
| SF-6 | `tests/unit/core/test_every_reachable_module_is_reloaded` | 待建(M2) |
| SF-7 | `tests/unit/scripts/test_bpy_modules_read_plans_only` | 待建(M3) |
| SF-8 | `tests/unit/core/test_hand_instance_conformance.py` | 待建(M6) |
| SF-10 | `scripts/verify/regenerated_package_matches_shipped.py --package hand-v3` | **已建**(M1);對舊產生器 4/4 PASS;M3 換新產生器後重跑 |
| SF-11 | `scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/hand_v3.json`(+ `hand_v3_finger.json --skip-generate`) | **既有**;M1 起在 `--real` 裡 |
| SF-12 | 同上,`hand_compact*.json` | 待建(M6) |
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

三條都綠 = HF-1 成立 = 舊產生器可以刪。
