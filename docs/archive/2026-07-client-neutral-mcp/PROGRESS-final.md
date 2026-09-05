# 進度追蹤（Progress）

## 當前 Phase

**V3 本輪完成 — client-neutral MCP、切片健檢、批次場景變形與前端生產力工具已完成（2026-07-19）**

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
| 黑貓手機架 3D 腳本 | ✅（14 objects in Blender）|

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
| d1 | 舊 MCP client adapter（已由 client-neutral Streamable HTTP inbound adapter 取代）| ✅ superseded |
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
| f1 | 本機唯一 CI `scripts/ci.sh`（GitHub Actions 已移除）| ✅ |
| f2 | E2E 測試（MockBlender + MockVision，13 tests）| ✅ |

---

## V3：Client-neutral MCP + 切片準備 ✅（2026-07-19）

| 項目 | 狀態 |
|---|---|
| MCP Streamable HTTP 與 stdio proxy，共用單一 `AppRuntime` / socket | ✅ |
| 九項 curated MCP tools；不公開 `execute_code` | ✅ |
| STL/OBJ/PLY 毫米匯出與 GLB/FBX 交換格式 | ✅ |
| `PrintReadinessService`、REST `/api/print-readiness`、MCP `check_print_readiness` | ✅ |
| WebUI 自動健檢、stale state、review 確認、invalid 阻擋 | ✅ |
| 真 Blender nonce fixtures 與 addon socket 獨立 oracle | ✅ 9/9 |
| checkbox 多選目標與批次移動 mm／旋轉 °／縮放 % | ✅ |
| `BatchTransformService`、REST `/api/scene/batch-transform`、單一 Undo operator | ✅ |
| 五筆操作狀態中心；刷新可安全重試，Undo/Redo/批次變形不提供重試 | ✅ |
| 純 registry 的九項 curated 指令面板、Cmd/Ctrl+K 與 editable-target guard | ✅ |
| 鍵盤全選目標 → 批次變形 → 操作歷史的真元件 dummy-run | ✅ |

---

## 測試狀態（2026-07-19）

| 類型 | 數量 | 狀態 |
|---|---|---|
| Python unit + e2e | 358 | ✅ 全通過 |
| Web unit + dummy run | 83 | ✅ 全通過 |
| 真 Blender print-readiness evidence | 9 | ✅ 9/9 |
| 真 Blender batch-transform evidence | 2 | ✅ 2/2；一次 Undo 復原兩物件 |
| 靜態 gate | web build/eslint、ruff、strict mypy、container narrowing | ✅ |

---

## 服務端點

| 服務 | 位址 | 說明 |
|---|---|---|
| FastAPI | `http://localhost:19505` | 主 API + WebSocket |
| Vite UI | `http://localhost:19504` | React 前端 |
| Blender socket | `localhost:9876` | MCP addon（socket 模式）|
| MCP Streamable HTTP | `https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp` | 所有相容 host 共用；不提供 legacy SSE |
| Ollama | `http://localhost:11434` | LLM inference |

---

## REST / MCP 端點總覽

| Method | Path | 說明 |
|---|---|---|
| WS | `/ws/chat` | 對話 WebSocket |
| GET | `/api/health` | 健康檢查 |
| GET | `/api/scene` | 場景物件列表 |
| GET | `/api/preview` | Viewport 截圖（輪詢）|
| POST | `/api/print-readiness` | 唯讀 3D 列印就緒檢查 |
| POST | `/api/scene/batch-transform` | 多物件增量變形；單一 Undo transaction |
| POST | `/api/export` | STL/OBJ/PLY/GLB/FBX 匯出 |
| POST | `/api/refine` | Vision 迭代精煉 |
| POST | `/api/pipeline` | 執行 YAML pipeline |
| GET | `/api/pipelines` | 列出可用 pipelines |
| MCP | `/mcp`（外部 `/blender/mcp`）| 九項 client-neutral tools |

---

## 圖例
- ✅ 完成
- 🔄 進行中
- Deferred 延後產品決策（不屬於目前里程碑）
- ❌ 阻塞
