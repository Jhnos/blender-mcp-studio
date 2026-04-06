# 進度追蹤（Progress）

## 當前 Phase

**V2 完成 — 121/121 tests passing | Commit `429c4b1`**

---

## Phase 0：文件與骨架 ✅

| 項目 | 狀態 |
|---|---|
| `docs/` 全套文件骨架 | ✅ |
| `environment.yml` + conda 環境 | ✅ |
| `pyproject.toml` | ✅ |
| `.env.example` | ✅ |

## Phase 1：Core Domain（TDD）✅

| 項目 | 狀態 |
|---|---|
| `Scene` / `Command` / `Session` 領域模型 + 測試 | ✅ |
| `LLMPort` / `MCPPort` / `BlenderPort` 介面 | ✅ |
| `ConversationalModelingUseCase` | ✅ |
| `CommandParser` 在 domain | ✅ |

## Phase 2：Adapters + API + Web UI ✅

| 項目 | 狀態 |
|---|---|
| `OllamaAdapter`（httpx async，strip think blocks） | ✅ |
| `AnthropicAdapter` | ✅ |
| `BlenderMCPAdapter`（組合模式，無多重繼承） | ✅ |
| LLM / Blender Factory（Provider Registry, OCP）| ✅ |
| FastAPI + WebSocket `/ws/chat` | ✅ |
| `/api/scene` + `/api/preview` REST endpoints | ✅ |
| React Web UI（對話 + 物件列表 + Viewport 預覽）| ✅ |

## Phase 3：Workflow Engine ✅

| 項目 | 狀態 |
|---|---|
| `WorkflowEngine`（YAML 驅動，env var 展開）| ✅ |
| `conversational_modeling.yaml` | ✅ |
| 黑貓手機架 3D 腳本 | ✅（10 objects in Blender）|

## Phase 4：解耦合審計 ✅

| 項目 | 狀態 |
|---|---|
| Tech debt 審計（19 issues 全修）| ✅ |
| DDD/SOLID 審計（13 issues 全修）| ✅ |

## V2：生成品質 + 安全 + Vision ✅（2026-04-06）

### Phase A — 生成品質基礎

| ID | 功能 | 狀態 |
|---|---|---|
| a1 | LLM Structured Output（Claude tool_use / OpenAI functions）| ✅ |
| a2 | 動態系統提示 + Blender API context（YAML 注入）| ✅ |
| a3 | exec() 沙箱（18 patterns）+ Prompt Injection 防禦（7 patterns）| ✅ |

### Phase B — Vision 視覺回饋

| ID | 功能 | 狀態 |
|---|---|---|
| b1 | VisionPort + GPT-4o / Claude Vision adapters | ✅ |
| b2 | IterativeRefinementUseCase（截圖→Vision→收斂→修正迴圈）| ✅ |

### Phase C — 3D 生成

| ID | 功能 | 狀態 |
|---|---|---|
| c1 | Hunyuan3D + Hyper3D Rodin 工具定義 | ✅ |
| c2 | ModelingPipelineUseCase（YAML 驅動多步建模）| ✅ |

### Phase D — 架構升級

| ID | 功能 | 狀態 |
|---|---|---|
| d1 | MCPClientBlenderAdapter（官方 MCP SDK v1.27 SSE 傳輸）| ✅ |
| d2 | SemanticToolRouter（keyword 語義工具預篩）| ✅ |
| d3 | SQLiteSessionStore（aiosqlite 會話持久化）| ✅ |

### Phase E — 即時預覽 UI

| ID | 功能 | 狀態 |
|---|---|---|
| e1 | Live Viewport（WS push base64 截圖 → SceneView 即時顯示）| ✅ |
| e2 | RefinementPanel（精煉迴圈 UI，迭代卡片 + Vision 分析）| ✅ |

### Phase F — CI/CD + E2E

| ID | 功能 | 狀態 |
|---|---|---|
| f1 | GitHub Actions CI（pytest + ruff + mypy）| ✅ |
| f2 | E2E 測試（MockBlender + MockVision，13 tests）| ✅ |

---

## 測試狀態（截至 V2 完成）

| 類型 | 數量 | 狀態 |
|---|---|---|
| Unit tests | 108 | ✅ 全通過 |
| E2E tests（Mock）| 13 | ✅ 全通過 |
| **合計** | **121** | **✅ 121/121** |
| Coverage | 76% | 核心 domain/ports 覆蓋率高 |

---

## 服務端點

| 服務 | 位址 | 說明 |
|---|---|---|
| FastAPI | `http://localhost:17823` | 主 API + WebSocket |
| Vite UI | `http://localhost:19147` | React 前端 |
| Blender socket | `localhost:9876` | MCP addon（socket 模式）|
| Blender MCP SSE | `http://localhost:8765/sse` | MCP SDK 模式（可選）|
| Ollama | `http://localhost:11434` | LLM inference |

---

## REST API 端點總覽（V2）

| Method | Path | 說明 |
|---|---|---|
| WS | `/ws/chat` | 對話 WebSocket |
| GET | `/api/health` | 健康檢查 |
| GET | `/api/scene` | 場景物件列表 |
| GET | `/api/preview` | Viewport 截圖（輪詢）|
| POST | `/api/refine` | Vision 迭代精煉 |
| POST | `/api/pipeline` | 執行 YAML pipeline |
| GET | `/api/pipelines` | 列出可用 pipelines |

---

## 圖例
- ✅ 完成
- 🔄 進行中
- ⏳ 待辦
- ❌ 阻塞

