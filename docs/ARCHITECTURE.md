# 架構決策（Architecture）

## 整體架構圖

```
┌─────────────────────────────────────────────────────────┐
│                      Web UI Layer                        │
│              React 18 + TypeScript + Vite               │
│         ChatPanel  │  SceneView  │  Zustand Store       │
└─────────────────────────┬───────────────────────────────┘
                          │ WebSocket / REST
┌─────────────────────────▼───────────────────────────────┐
│                    API Layer (FastAPI)                    │
│          /ws/chat  │  /api/scene  │  /api/health        │
└─────────────────────────┬───────────────────────────────┘
                          │ Python function call
┌─────────────────────────▼───────────────────────────────┐
│                  Application Layer                        │
│             ConversationalModelingUseCase                │
│              SceneManagementUseCase                      │
└──────────┬──────────────────────────┬───────────────────┘
           │ LLMPort                  │ BlenderPort
┌──────────▼────────┐     ┌───────────▼───────────────────┐
│   LLM Adapters    │     │    Blender MCP Adapter         │
│  AnthropicAdapter │     │  (wraps ahujasid/blender-mcp)  │
│  OpenAIAdapter    │     │  Socket → Blender Addon (9876) │
│  DeepSeekAdapter  │     └───────────────────────────────┘
│  OllamaAdapter    │                    │
└───────────────────┘             ┌──────▼──────┐
        │                         │   Blender   │
  [Claude/GPT/etc]                │  + addon.py │
                                  └─────────────┘
```

## 架構模式

### Hexagonal Architecture（六邊形架構）

- **Domain Core** (`src/core/`) — 零依賴，純 Python，可獨立測試
- **Ports** (`src/core/ports/`) — 抽象介面（ABC），定義合約
- **Adapters** (`src/adapters/`) — 實作具體的外部整合，可替換

### Domain-Driven Design（DDD）

| 概念 | 實作位置 | 說明 |
|---|---|---|
| Aggregate Root | `Scene` | Blender 場景的聚合根 |
| Entity | `Session` | 對話 session |
| Value Object | `Command` | 不可變的 Blender 指令 |
| Use Case | `use_cases/` | 應用層業務邏輯 |
| Port | `ports/` | 外部依賴抽象 |
| Adapter | `adapters/` | 具體實作 |

### Workflow Engine（腳本驅動）

每個 Workflow 由兩個檔案組成：
1. **YAML 定義**（`config/workflows/*.yaml`）：宣告式描述步驟、LLM 選擇、MCP 設定
2. **Python 腳本**（`src/workflows/scripts/*.py`）：具體的業務邏輯

**核心原則**：換腳本 = 換工作流程目標，引擎不變。

## ADR（Architecture Decision Records）

### ADR-001：選用 ahujasid/blender-mcp 作為 MCP 橋接
- **決策**：採用 ahujasid/blender-mcp（MIT 授權）
- **理由**：最成熟的開源實作、Claude 官方推薦、社群活躍
- **後果**：透過 `BlenderMCPAdapter` 包裝，保持可替換性

### ADR-002：多 LLM 抽象層
- **決策**：定義 `LLMPort` ABC，每個 LLM 提供商一個 Adapter
- **理由**：用戶希望可以互換 LLM，不鎖定單一提供商
- **後果**：初期以 Anthropic Claude 為主力，其他 adapter 逐步實作

### ADR-003：FastAPI + WebSocket
- **決策**：後端使用 FastAPI，前端透過 WebSocket 即時通訊
- **理由**：對話建模需要即時回饋（streaming），REST 不夠
- **後果**：前端實作 `useWebSocket` hook 管理連線狀態

### ADR-004：React + TypeScript + Vite
- **決策**：前端使用 React 18 + TypeScript，Vite 建構
- **理由**：現代化、可擴充、TypeScript 確保型別安全
- **後果**：需要 Node.js 環境（與 Python conda 環境並行）
