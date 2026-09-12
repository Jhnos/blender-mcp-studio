# 可重跑命令

- `python -m pytest tests/unit/core/test_lab_station.py tests/unit/core/test_lab_station_joints.py -q --no-cov`
- `python scripts/verify/generated_artifact_verify_real.py scripts/verify/contracts/lab_station.json`
- `scripts/ci.sh --real`
- `python /Users/bearmacmini/.codex/skills/requirement-traceability/assets/trace_check.py docs/verification/lab-station/07-matrix.md`

直上行程檢查將由同一產生器呼叫，失敗則不交付合格包；記錄 `probe-lift.json`。製造資格不因以上軟體命令通過而成立。
