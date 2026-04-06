# 程式設計風格（Coding Style）

## Python

### 型別
- **強制 Type Hints**：所有函式、方法、變數
- `mypy --strict` 模式通過為合格

```python
# ✅ Good
async def create_object(name: str, object_type: ObjectType) -> Scene:
    ...

# ❌ Bad
async def create_object(name, object_type):
    ...
```

### 命名規範
| 類型 | 規範 | 範例 |
|---|---|---|
| 類別 | `PascalCase` | `AnthropicAdapter` |
| 函式/方法 | `snake_case` | `create_object()` |
| 變數 | `snake_case` | `llm_response` |
| 常數 | `UPPER_CASE` | `DEFAULT_TIMEOUT` |
| 模組檔案 | `snake_case` | `llm_port.py` |
| 私有 | 底線前綴 | `_internal_state` |

### 非同步
- **Async First**：所有 I/O 操作用 `async/await`
- 禁止在 async 函式中呼叫阻塞 I/O

```python
# ✅ Good
async def fetch_response(prompt: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.post(...)
    return response.text

# ❌ Bad
def fetch_response(prompt: str) -> str:
    import requests
    return requests.post(...).text
```

### 依賴注入
- 禁止全域狀態
- 所有外部依賴由建構子注入

```python
# ✅ Good
class ConversationalModelingUseCase:
    def __init__(self, llm: LLMPort, blender: BlenderPort) -> None:
        self._llm = llm
        self._blender = blender

# ❌ Bad
from src.adapters.llm.anthropic_adapter import AnthropicAdapter
llm = AnthropicAdapter()  # 全域，硬依賴
```

### 錯誤處理
- 使用自定義 Exception（`src/core/domain/` 定義）
- 禁止裸 `except:`

```python
# ✅ Good
try:
    result = await self._llm.chat(messages)
except LLMConnectionError as e:
    raise SceneCreationError("LLM unavailable") from e

# ❌ Bad
try:
    result = llm.chat(messages)
except:
    pass
```

### 文件字串
- 只在複雜邏輯或公開 API 加
- 不加無意義的「This function does X」

### Formatter
- `ruff format`（black-compatible，行寬 100）
- Import 排序：stdlib → third-party → local（`ruff` 自動管理）

---

## TypeScript（前端）

### 型別
- 禁止 `any`
- 所有 API 回應定義 interface/type

### 命名
| 類型 | 規範 |
|---|---|
| 元件 | `PascalCase.tsx` |
| Hook | `camelCase`，`use` 前綴 |
| Store | `camelCase`，`Store` 後綴 |
| Type/Interface | `PascalCase` |

### 元件原則
- 單一職責：每個元件只做一件事
- 禁止直接呼叫 API，透過 hook 或 store

---

## Git 規範

### Commit 格式（Conventional Commits）
```
<type>(<scope>): <description>

feat(adapter): add OpenAI LLM adapter
fix(domain): correct Scene aggregate validation
test(usecase): add ConversationalModeling unit tests
docs(arch): update ADR-001
refactor(engine): extract workflow step executor
```

### 分支策略
- `main` — 穩定版本
- `feature/<name>` — 新功能
- `fix/<name>` — 修復
