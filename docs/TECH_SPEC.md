# 技術規格（Technical Specifications）

## 環境需求

| 項目 | 版本 | 說明 |
|---|---|---|
| 硬體 | Mac M4 (Apple Silicon arm64) | osx-arm64 native |
| macOS | 26.4+ | |
| Conda | 26.1.0+ | 環境管理 |
| Python | 3.11 (arm64 native) | conda env |
| Blender | 4.0+ | Apple Silicon 版 |
| Node.js | 20 LTS+ | 前端建構 |
| npm | 10+ | 前端套件管理 |

## Python 後端套件

| 套件 | 版本 | 用途 |
|---|---|---|
| `mcp` | latest | MCP SDK（官方 Python SDK） |
| `anthropic` | latest | Claude 適配器 |
| `openai` | latest | OpenAI 適配器 |
| `httpx` | latest | 非同步 HTTP（DeepSeek / Ollama） |
| `pydantic` | >=2.0 | 資料模型 + 驗證 |
| `pyyaml` | latest | YAML 設定載入 |
| `python-dotenv` | latest | .env 環境變數 |
| `fastapi` | latest | 後端 API Server |
| `uvicorn[standard]` | latest | ASGI Server（WebSocket） |
| `websockets` | latest | WebSocket 支援 |
| `pytest` | latest | TDD 測試框架 |
| `pytest-asyncio` | latest | 非同步測試 |
| `pytest-cov` | latest | 測試覆蓋率 |
| `ruff` | latest | Linting + Formatting |
| `mypy` | latest | 靜態型別檢查 |

## 前端套件

| 套件 | 用途 |
|---|---|
| `react` + `react-dom` | UI 框架 |
| `typescript` | 型別安全 |
| `vite` | 建構工具 |
| `zustand` | 輕量狀態管理 |
| `tailwindcss` | CSS 框架 |
| `@types/react` | TypeScript 定義 |

## 服務端口

| 服務 | 端口 | 說明 |
|---|---|---|
| Blender MCP Socket | 9876 | Blender addon 監聽 |
| FastAPI Backend | 8000 | API Server |
| Vite Dev Server | 5173 | 前端開發 |

## 環境變數（.env）

```bash
# LLM API Keys
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=

# Ollama（本地）
OLLAMA_BASE_URL=http://localhost:11434

# MCP / Blender
BLENDER_HOST=localhost
BLENDER_PORT=9876

# Server
API_HOST=0.0.0.0
API_PORT=8000

# Workflow
DEFAULT_WORKFLOW=conversational_modeling
DEFAULT_LLM_PROVIDER=anthropic
```

## LLM Port 介面規格

```python
class LLMPort(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...
```

## MCP Port 介面規格

```python
class MCPPort(ABC):
    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolResult: ...

    @abstractmethod
    async def list_tools(self) -> list[ToolDefinition]: ...
```

## WebSocket 訊息格式

### Client → Server
```json
{
  "type": "chat",
  "content": "幫我建立一個立方體",
  "session_id": "uuid"
}
```

### Server → Client
```json
{
  "type": "response",
  "content": "已在 Blender 中建立立方體...",
  "status": "streaming | done | error",
  "session_id": "uuid"
}
```

## 測試策略

| 層次 | 工具 | 說明 |
|---|---|---|
| Unit | `pytest` | Domain 模型、Use Cases（mock ports） |
| Integration | `pytest-asyncio` | Adapter 整合（mock API / Blender） |
| E2E | `pytest` | 完整流程（需 Blender 啟動） |
| Coverage | `pytest-cov` | 目標 > 80% |
