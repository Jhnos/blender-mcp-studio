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

## 架構演進記錄

| 日期 | 決策 | 理由 |
|---|---|---|
| 2026-04-06 | 採用 ahujasid/blender-mcp | 最成熟開源實作，MIT 授權 |
| 2026-04-06 | 加入 FastAPI + WebSocket | 對話建模需要即時回饋 |
| 2026-04-06 | 選用 React + TypeScript | 可擴充、型別安全 |
| 2026-04-06 | LLM 多 adapter 抽象 | 不鎖定單一 LLM 提供商 |
| 2026-04-06 | 直連 Blender socket（跳過 stdio MCP） | 減少進程，架構更乾淨 |
| 2026-04-06 | Blender singleton（app.state） | 避免每 request 重建 TCP 連線 |
| 2026-04-06 | Port 17823/19147（非常用 port） | 設備掛很多服務，避免衝突 |
| 2026-04-06 | qwen3-coder:480b-cloud | 本機記憶體被佔用時的零成本選擇 |
| 2026-04-06 | Provider registry（OCP） | 新增 LLM 不需修改 factory 核心 |
| 2026-04-06 | BlenderMCPAdapter 組合模式 | 移除多重繼承，SRP 更清晰 |
| 2026-04-06 | CommandParser 在 domain | 解析命令是業務邏輯，不屬於 use case |
| 2026-04-06 | GetScenePreviewUseCase | 將截圖 I/O 從 router 解耦 |
