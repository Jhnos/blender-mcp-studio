#!/usr/bin/env bash
# run_workflow.sh — 執行指定 workflow（CLI 模式）
set -euo pipefail

WORKFLOW="${1:-conversational_modeling}"
echo "▶️  執行 workflow: $WORKFLOW"
conda run -n blender-mcp python -m src.workflows.engine "$WORKFLOW"
