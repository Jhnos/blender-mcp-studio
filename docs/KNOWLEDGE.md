# 經驗傳承（Knowledge Transfer）

> 記錄踩坑、決策脈絡、最佳實踐。隨專案演進持續更新。

---

## Mac M4 arm64 注意事項

### Python 環境
- 必須使用 arm64 native Python（`conda` 在 osx-arm64 平台預設即是）
- 避免 Rosetta 2 模擬層（效能損耗約 20-30%）
- 確認：`python -c "import platform; print(platform.machine())"` 應輸出 `arm64`

### Blender 安裝
- 從 [blender.org](https://www.blender.org/download/) 下載 **Apple Silicon** 版（`.dmg`）
- 非 Intel 版，否則透過 Rosetta 執行效能差
- Blender 5.1 內建 Python 版本 3.11（與 conda env 對齊）

### Conda 環境
- 建立時指定 `python=3.11`（與 Blender 內建版本對齊）
- 所有套件安裝確認 arm64 wheel（`pip install` 在 arm64 conda env 下預設正確）

---

## Blender 5.1 踩坑

### Node 存取方式改變（CRITICAL）
```python
# ❌ 舊寫法（Blender 4.x）— Blender 5.1 會 KeyError
mat.node_tree.nodes["Principled BSDF"]

# ✅ 新寫法（Blender 5.1）— 用 type 屬性搜尋
node = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
if node:
    node.inputs["Base Color"].default_value = (r, g, b, 1.0)
```

### 多材質設定流程
```python
mat = bpy.data.materials.new(name="MyMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
# 必須先確認 bsdf 存在才能設定 inputs
```

---

## ahujasid/blender-mcp 架構理解

### 通訊協議（直接 socket，跳過 stdio MCP）
```
FastAPI + BlenderMCPAdapter
    ↓ TCP socket port 9876 (直連)
Blender Addon (__init__.py)
    ↓ bpy API
Blender 3D Scene
```

### 協議格式（ahujasid v1.5.5）
```json
// 發送（send_command）
{"type": "tool_name", "params": {...}}

// 成功回應
{"executed": true, "result": "..."}

// 失敗回應
{"status": "error", "message": "..."}
```

### 重要限制
- Blender Addon 在 Blender 啟動時才有效
- Socket server 預設 port 9876（設定 `BLENDER_PORT` 環境變數可覆蓋）
- 一次只能一個連線（不能 Claude Desktop + 我們的 server 同時連）
- `get_viewport_screenshot` 需要指定 `filepath`（本地絕對路徑）

### 我們的包裝策略
- `BlenderMCPAdapter` 直接透過 TCP socket 與 addon 溝通
- 不依賴 `uvx blender-mcp`（避免額外進程）
- 符合 Hexagonal Architecture：`BlenderPort`（業務介面）← `BlenderMCPAdapter`（實作）

---

## 解耦合架構決策

### 組合優於多重繼承（solid-03）
```python
# ❌ 多重繼承 — 違反 SRP，LSP 風險
class BlenderMCPAdapter(BlenderPort, MCPPort): ...

# ✅ 組合 — BlenderMCPClient(MCPPort) 被 BlenderMCPAdapter(BlenderPort) 使用
class BlenderMCPClient(MCPPort):   # 單一責任：MCP socket 協議
    def __init__(self, socket: BlenderSocketClient): ...

class BlenderMCPAdapter(BlenderPort):  # 單一責任：BlenderPort 業務介面
    def __init__(self, host: str, port: int):
        self._mcp = BlenderMCPClient(BlenderSocketClient(host, port))
```

### Provider Registry 取代 if/else（solid-02, OCP）
```python
# ❌ 每次新增 provider 都要改 factory 函式
if provider == "anthropic": ...
elif provider == "deepseek": ...

# ✅ Registry dict — 新增 provider 只需 register_llm_provider()
_PROVIDER_REGISTRY: dict[str, Callable[[], LLMPort]] = {
    "ollama": _build_ollama,
    "anthropic": _build_anthropic,
}
register_llm_provider("my_custom_llm", _build_my_custom)  # OCP extension point
```

### ISP — 依賴最小介面
```python
# ❌ Use case 依賴胖介面
class ConversationalModelingUseCase:
    def __init__(self, llm: LLMPort, ...):  # 包含 provider_name/model_name

# ✅ Use case 只依賴 chat()
class ConversationalModelingUseCase:
    def __init__(self, llm: LLMChatPort, ...):  # 最小介面
```

### Domain Events（ddd-04）
```python
# src/core/domain/events.py
@dataclass(frozen=True)
class CommandExecutedEvent(DomainEvent):
    session_id: str = ""
    tool_name: str = ""
    ...

# Use case publishes — entities stay pure
bus.subscribe(CommandExecutedEvent, my_audit_handler)
await use_case.execute(session)  # events published automatically
```
- Use case 是 publisher，不是 entity（entity 保持純粹）
- `InMemoryEventBus` 處理異常：bad handler 不會 crash 整個流程
- 想換 Redis Streams：實作 `EventBusPort` 即可，use case 無需更動

### AdapterFactoryPort（solid-05）
```python
# src/core/ports/adapter_factory_port.py — abstract
class AdapterFactoryPort(ABC):
    def build_llm_adapter(self, provider=None) -> LLMChatPort: ...
    def build_blender_adapter(self, host=None, port=None) -> BlenderPort: ...

# Test 時：inject MockFactory，不需要真實 Ollama/Blender
class MockFactory(AdapterFactoryPort):
    def build_llm_adapter(self, provider=None): return MockLLM()
```
- `app.state.adapter_factory` 在 lifespan 設定，router 只看 port 介面

### Tool Schema Validation（ddd-06）
```yaml
# config/tool_schemas.yaml
tools:
  - name: execute_code
    required: [code]
  - name: get_object_info
    required: [name]
```
- 未知 tool 直接放行（forward compatibility）
- Schema 違規只 warn，不 block（Blender 會給最終錯誤）
- `ToolSchemaRegistry.default()` 懶加載，`from_yaml()` 支援自定路徑
- `CommandParser._registry` 可在測試中 inject 自定 registry


### Adapter 不讀 os.environ（ddd-02）
```python
# ❌ Adapter 有隱性環境依賴，難以測試
class OllamaAdapter:
    def __init__(self):
        self._model = os.environ.get("OLLAMA_MODEL", "...")

# ✅ Factory 讀 env，Adapter 只收 constructor 參數
class OllamaAdapter:
    def __init__(self, model: str, base_url: str): ...

# In factory.py:
OllamaAdapter(model=os.environ.get("OLLAMA_MODEL", "..."))
```

---

## LLM 選型決策（Mac M4 32GB）

### 本地模型（Ollama）
| 模型 | VRAM | 特點 | 建議用途 |
|---|---|---|---|
| `gemma4:26b` | ~16GB | MoE 僅 4B active，極快 | 快速 bpy 草稿 |
| `qwen3-coder:30b` | ~17GB | 最強 local coding | 完整 bpy 腳本 |
| `deepseek-r1:32b` | ~18GB | 強推理 | 複雜幾何計算 |

### 雲端模型（零本機記憶體）
- `qwen3-coder:480b-cloud`：透過 Ollama 帳號路由到雲端，不佔本機記憶體
- 適合「本機在跑其他服務」的情境
- 設定：`OLLAMA_MODEL=qwen3-coder:480b-cloud`

### Port 管理（重要！）
這台設備掛了很多服務。**每次啟動前必須用 `lsof -i :PORT` 確認**。
- 專案使用：API=17823，Vite=19147，Blender socket=9876，Ollama=11434
- 禁止使用：8000, 8001, 5000, 5173, 3000（常見服務）

---

## 常見問題排查

### Blender addon 無法連線
1. 確認 Blender 已啟動且 addon 已啟用
2. N-Panel → BlenderMCP → 確認 "Connect" 已點
3. `lsof -i :9876` 確認 port 有在監聽

### API 啟動失敗（Blender 未連線）
- 正常：lifespan 會 catch exception，API 仍正常啟動
- Blender 相關功能（/api/scene, /api/preview）會回傳空值
- 先確認 Blender 啟動後再重啟 API

### LLM 呼叫失敗
1. `curl http://localhost:11434/api/ps`：確認 Ollama 在線
2. 雲端模型需要 Ollama 帳號登入
3. `.env` 中 `OLLAMA_MODEL` 是否正確

### React WebSocket 斷線
1. `curl http://localhost:17823/api/health`：確認 API 在線
2. `vite.config.ts` proxy target 需指向正確 port（17823）
3. WS URL 必須走 proxy（`/ws/chat`），不可直連

### Vite dev server 掉線（常見！）
- **原因**：detach async bash session 關閉時 Vite 一起死
- **解法**：用 `nohup ... < /dev/null > /tmp/vite.log 2>&1 & disown $!`
- **一鍵重啟**：`./scripts/start_services.sh`

---

## LLM 工具呼叫（V2 Structured Output）

### Claude tool_use 實作要點
```python
# AnthropicAdapter.chat_with_tools()
response = client.messages.create(
    model=self._model,
    max_tokens=4096,
    tools=[t.to_anthropic_dict() for t in tools],
    messages=[...],
)
# 回應中 tool_use block
for block in response.content:
    if block.type == "tool_use":
        tc = ToolCall(name=block.name, arguments=dict(block.input))
```

### Ollama OpenAI-compatible tools
```python
# OllamaAdapter — tools param 格式等同 OpenAI
payload = {
    "model": self._model,
    "tools": [t.to_openai_dict() for t in tools],
    "messages": [...],
}
# 解析 message.tool_calls[].function.{name, arguments}
```

### ISP 最佳實踐：`LLMToolChatPort extends LLMChatPort`
```python
# use case 用 isinstance 決定路徑
if isinstance(self._llm, LLMToolChatPort):
    return await self._chat_with_tools(session)
else:
    return await self._chat_with_regex_fallback(session)
```

---

## 安全沙箱（V2 Security）

### BlenderCodeSandbox 設計
- 18 個 regex pattern，以「黑名單 + 白名單思路」
- `os`, `subprocess`, `eval`, `exec(` (standalone), `__import__`, `socket`, `ctypes`, `pickle` 全封
- `bpy.*` 全放行
- 檔案**讀取**放行（資源載入需要）
- **決策**：pattern 存 list，新增 pattern 無需改 code

### PromptInjectionSanitizer 順序
1. Strip bidi override chars（\u202a-\u202e, \u2066-\u2069）— 隱藏 prompt 攻擊
2. NFC normalize — unicode 變體同一化
3. 7 個注入 pattern match（`ignore previous`, `system prompt`, etc.）
4. 回傳 `SanitizeResult(clean, sanitized_text)` — 永不回傳 None

---

## Vision 迭代精煉（V2 Vision Loop）

### IterativeRefinementUseCase 流程
```
1. capture_screenshot() → bytes
2. vision.analyze_image(bytes, prompt) → VisionAnalysis
3. _is_converged(vision_text)? → 任何 CONVERGENCE_KEYWORDS 出現即收斂
4. 否 → LLM chat_with_tools(refinement_prompt) → commands
5. blender.execute(commands)
6. repeat max_iterations 次
```

### 收斂關鍵詞（data-driven，可編輯 _CONVERGENCE_KEYWORDS）
```python
_CONVERGENCE_KEYWORDS = frozenset([
    "looks good", "complete", "done", "accurate", "matches",
    "符合", "完成", "準確", "正確", "很好", "很棒", "完美",
])
```

### Vision Adapter 選擇
- `OPENAI_API_KEY` 設定 → `GPT4oVisionAdapter`（OpenAI REST，httpx 直呼）
- `ANTHROPIC_API_KEY` 設定 → `ClaudeVisionAdapter`（anthropic SDK）
- 兩者都沒有 → `None`（/api/refine 回 503）
- `VISION_PROVIDER=anthropic` 可強制指定

---

## Semantic Tool Routing（V2 d2）

### SemanticToolRouter 設計
- 關鍵字 → tool_name 的倒排索引（`_KEYWORD_INDEX`）
- 用 `re.findall(r'\w+', message.lower())` tokenize
- 若無 match → fallback 全部 tools（安全）
- `min_tools=3` 確保至少傳 3 個 tools 給 LLM
- **升級路徑**：換 sentence-transformers 不需改介面

---

## Multi-step Pipeline（V2 c2）

### PipelineStage Placeholder 語法
```yaml
- name: create_base
  tool: create_object
  arguments:
    name: "{{ object_name }}"   # 從 context dict 解析
    type: "{{ object_type }}"
```

### 錯誤處理策略
| 情況 | 處理 |
|---|---|
| required stage 失敗 | 中止整個 pipeline |
| optional stage 失敗 | 標記 SKIPPED，繼續 |
| 執行例外（network/timeout）| 標記 FAILED，message 在 error 欄位 |
| validation_key 不在輸出 | 標記 FAILED |

---

## MCP SDK SSE 傳輸（V2 d1）

### 兩種 BlenderPort 實作
| 實作 | 設定 | 用途 |
|---|---|---|
| `BlenderMCPAdapter` | `BLENDER_TRANSPORT=socket`（預設）| ahujasid 原始 add-on |
| `MCPClientBlenderAdapter` | `BLENDER_TRANSPORT=mcp_sse` | FastMCP/標準 MCP SSE 伺服器 |

### MCPClientBlenderAdapter 注意事項
- 每次 tool call 都建立新的 SSE session（HTTP stateless）
- `connect()` 探測 `list_tools()`，失敗不拋例外
- 適合：任何實作 `tools/call` 的 MCP 相容伺服器

---

## Session 持久化（V2 d3）

### SQLiteSessionStore
```python
# data/sessions.db 自動建立（Path 可注入，方便測試 tmp_path）
store = SQLiteSessionStore(db_path=Path("data/sessions.db"))
session = await store.create()       # uuid4 id
session = session.add_message(...)   # 不可變 add
await store.save(session)            # upsert JSON
loaded = await store.get(session.id) # Pydantic model_validate_json
```

### Chat router fallback
```python
# session_store 存在 → SQLite；否則 → app.state._sessions (dict)
session_store = getattr(request.app.state, "session_store", None)
```

---

## 架構演進記錄（V2 追加）

| 日期 | 決策 | 理由 |
|---|---|---|
| 2026-04-06 | `LLMToolChatPort extends LLMChatPort`（ISP）| 向後相容；use case 用 isinstance 決定 path |
| 2026-04-06 | Vision adapter 回傳 `None` 而非拋例外 | router 用 503 告知客戶端，不 crash server |
| 2026-04-06 | `SemanticToolRouter` 以 keyword 而非 embedding | 零依賴、快速、可測；embedding 升級路徑保留 |
| 2026-04-06 | Pipeline stage optional flag | 3D printing 部分步驟（solidify, UV）可選 |
| 2026-04-06 | `MCPClientBlenderAdapter` 每次重建 session | MCP SSE stateless 設計，避免 connection leak |
| 2026-04-06 | `PipelineLoader` 用 `@lru_cache` | YAML 只讀一次；測試用 `tmp_path` 注入不同 config |
| 2026-04-06 | RefinementPanel 用 Zustand 獨立 store | 精煉狀態與對話狀態完全解耦，可獨立測試 |
