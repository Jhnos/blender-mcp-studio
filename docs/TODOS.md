# 待辦事項（Todos）

> 詳細追蹤由 SQL 資料庫管理，此文件為人工可讀摘要。

## Phase 0 — 骨架
- [ ] 建立 `docs/` 全套文件
- [ ] 建立 `environment.yml` + conda 環境 `blender-mcp`
- [ ] 建立完整目錄骨架與所有 `__init__.py`
- [ ] 建立 `pyproject.toml`
- [ ] 建立 `.env.example`

## Phase 1 — Core Domain（TDD 順序）
- [ ] 撰寫 `Scene` domain 模型測試 → 實作
- [ ] 撰寫 `Command` value object 測試 → 實作
- [ ] 撰寫 `Session` entity 測試 → 實作
- [ ] 定義 `LLMPort` ABC（含測試合約）
- [ ] 定義 `MCPPort` ABC
- [ ] 定義 `BlenderPort` ABC
- [ ] 撰寫 `ConversationalModelingUseCase` 測試（mock ports）→ 實作

## Phase 2 — Adapters + API + Web UI
- [ ] 撰寫 `AnthropicAdapter` 測試（mock）→ 實作
- [ ] 撰寫 `OpenAIAdapter` 測試 → 實作（stub）
- [ ] 撰寫 `BlenderMCPAdapter` 測試 → 實作
- [ ] 建立 FastAPI app + WebSocket `/ws/chat` 端點
- [ ] 建立 REST `/api/scene` 端點
- [ ] 初始化 React + TypeScript + Vite 前端（`web/`）
- [ ] 實作 `ChatPanel` 元件 + WebSocket hook
- [ ] 實作 `SceneView` 元件

## Phase 3 — Workflow Engine
- [ ] 撰寫 `WorkflowEngine` 測試 → 實作
- [ ] 撰寫 `conversational_modeling.yaml` workflow 腳本
- [ ] E2E 整合測試

## Phase 4 — 文件與收尾
- [ ] 完善 `KNOWLEDGE.md`
- [ ] 撰寫 `README.md`（含安裝、使用說明）
