# 待辦事項（Todos）

> 詳細追蹤由 SQL 資料庫管理，此文件為人工可讀摘要。

## V1 Phase 0–4 ✅ 全部完成

## V2（2026-04-06）✅ 全部完成（121/121 tests）

| ID | 功能 | 狀態 |
|---|---|---|
| a1 | LLM Structured Output（tool_use / function calling）| ✅ |
| a2 | 動態系統提示 + Blender API context | ✅ |
| a3 | exec() 沙箱 + Prompt Injection 防禦 | ✅ |
| b1 | VisionPort + GPT-4o / Claude Vision | ✅ |
| b2 | IterativeRefinementUseCase | ✅ |
| c1 | Hunyuan3D + Hyper3D 工具定義 | ✅ |
| c2 | ModelingPipelineUseCase（YAML 多步管線）| ✅ |
| d1 | 舊 MCP client adapter（已由 Streamable HTTP inbound adapter 取代）| ✅ superseded |
| d2 | SemanticToolRouter（keyword 語義路由）| ✅ |
| d3 | SQLiteSessionStore | ✅ |
| e1 | Live Viewport（WS push 截圖）| ✅ |
| e2 | RefinementPanel UI | ✅ |
| f1 | 本機唯一 CI `scripts/ci.sh`（GitHub Actions 已移除）| ✅ |
| f2 | E2E 測試（MockBlender + MockVision）| ✅ |

## V3（進行中）

| ID | 功能 | 優先 |
|---|---|---|
| v3-streaming | LLM 串流輸出（token-by-token WS push）| ✅ |
| v3-export | 3D 列印匯出（STL/OBJ/PLY）與 GLB/FBX 交換格式 | ✅ |
| v3-readiness | 匯出前健檢（REST + 第九個 MCP tool + WebUI + 真 Blender fixtures）| ✅ |
| v3-undo | 對話式 Undo/Redo（Cmd+Z）| ✅ |
| v3-polyhaven | Poly Haven 材質庫整合 | ✅ |
| v3-history | 場景快照歷史（可回溯）| ✅ |

## 下一階段

| ID | 功能 | 狀態 |
|---|---|---|
| v3-3mf | 3MF 匯出（明確單位、多物件、製造 metadata）| ⏳ 獨立階段 |
| v3-repair | 網格自動修復（補洞、布林、法線）| ⏳ 不納入健檢；需獨立破壞性 UX |
| v3-mcp-tasks | MCP Tasks 長任務 | ⏳ 等 host 能力協商與穩定 wire format |
