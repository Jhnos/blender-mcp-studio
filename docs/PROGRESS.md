# 進度追蹤（Progress）

## 當前 Phase

**Phase 4 — 文件完善（完成）**

---

## Phase 0：文件與骨架 ✅

| 項目 | 狀態 |
|---|---|
| `docs/` 全套文件骨架 | ✅ 完成 |
| `environment.yml` + conda 環境 | ✅ 完成 |
| 完整目錄骨架 | ✅ 完成 |
| `pyproject.toml` | ✅ 完成 |
| `.env.example` | ✅ 完成 |

## Phase 1：Core Domain（TDD）✅

| 項目 | 狀態 |
|---|---|
| `Scene` / `Command` / `Session` 模型 + 測試 | ✅ 完成 |
| Domain 模型實作 | ✅ 完成 |
| `LLMPort` / `MCPPort` / `BlenderPort` 介面 | ✅ 完成 |
| `ConversationalModelingUseCase` | ✅ 完成 |
| `CommandParser` 移入 domain | ✅ 完成 |

## Phase 2：Adapters + API + Web UI ✅

| 項目 | 狀態 |
|---|---|
| `OllamaAdapter`（httpx async，strip think blocks） | ✅ 完成 |
| `AnthropicAdapter` | ✅ 完成 |
| `BlenderMCPAdapter`（組合模式，無多重繼承） | ✅ 完成 |
| `LLM Factory`（Provider Registry，OCP） | ✅ 完成 |
| `Blender Factory` | ✅ 完成 |
| FastAPI Backend + WebSocket `/ws/chat` | ✅ 完成 |
| App factory `create_app()` + lifespan singleton | ✅ 完成 |
| `/api/scene` + `/api/preview` REST endpoints | ✅ 完成 |
| `GetScenePreviewUseCase` | ✅ 完成 |
| React Web UI（對話 + 物件列表 + Viewport 預覽） | ✅ 完成 |

## Phase 3：Workflow Engine ✅

| 項目 | 狀態 |
|---|---|
| `WorkflowEngine`（YAML 讀取，env var 展開） | ✅ 完成 |
| `conversational_modeling.yaml` | ✅ 完成 |
| WorkflowEngine TDD（11/11 tests） | ✅ 完成 |
| 黑貓手機架 3D 模型腳本 | ✅ 完成（10 objects in Blender）|

## Phase 4：解耦合審計 + 文件完善 ✅

| 項目 | 狀態 |
|---|---|
| Tech debt 審計（19 issues） | ✅ 完成 |
| DDD/SOLID 審計（13 issues） | ✅ 完成 |
| 高優先 HIGH issues 全部修復 | ✅ 完成 |
| `KNOWLEDGE.md` 完善 | ✅ 完成 |
| `README.md` 完善 | ✅ 完成 |

---

## 測試狀態

- **Unit tests**: 28/28 通過
- **Coverage**: ~55%（核心 domain/ports/use-cases 覆蓋率高）
- **E2E tests**: 需 Blender 運行，手動驗證 ✅（黑貓模型成功建立）

---

## 服務端點

| 服務 | 位址 | 說明 |
|---|---|---|
| FastAPI | `http://localhost:17823` | 主 API + WebSocket |
| Vite UI | `http://localhost:19147` | React 前端 |
| Blender socket | `localhost:9876` | MCP addon |
| Ollama | `http://localhost:11434` | LLM inference |

---

## 圖例
- ✅ 完成
- 🔄 進行中
- ⏳ 待辦
- ❌ 阻塞
