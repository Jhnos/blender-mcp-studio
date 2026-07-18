# 架構決策（Architecture）

> 架構單一真相源是可互動的 [architecture.html](architecture.html)。其內嵌 JSON
> model 同時驅動畫面與 AI 結構化欄位；`test_architecture_ssot.py` 以 AST 驗證
> model node 與真實 class/function anchor，避免圖與程式漂移。

## 核心不變式

所有 inbound transport 都匯入同一個 `AppRuntime`：

`HTTP MCP / stdio proxy / REST / WebSocket → SceneOperationsService → BlenderMCPAdapter → BlenderSocketClient → addon :9876`

- FastAPI、REST、WebSocket 與 MCP 共用同一 `BlenderPort` instance。
- API lifespan 只 connect/disconnect 一次；stdio proxy 不擁有 backend。
- MCP 是 inbound adapter，只依賴 `SceneQueryPort` / `SceneCommandPort`。
- `SceneOperationsService` 使用不可變 domain value，並在 Blender JSON 邊界嚴格 narrowing。
- `BlenderMCPAdapter` 是高階操作到 addon dialect 的唯一翻譯 chokepoint。
- 共享 `BlenderSocketClient._lock` 序列化 socket request/response；MCP 不建立第二把 transport lock。

## 分層與責任

| 層 | 主要構件 | 責任 |
|---|---|---|
| Presentation | FastAPI routers、FastMCP server | HTTP/WS/MCP framing、schema、error mapping |
| Application | `AppRuntime`、`SceneOperationsService` | composition、lifecycle、use-case orchestration |
| Domain | `scene_operations.py` value objects、ports | Client-neutral language 與 inward dependency contract |
| Adapter | `BlenderMCPAdapter`、`BlenderSocketClient` | addon translation、sandbox、locking、TCP |
| Engine | Blender + addon | 執行 `bpy` 並保存 3D scene state |

Dependency rule：外層依賴內層；domain/application 不 import FastAPI、FastMCP 或 `bpy`。

## Inbound adapters

- Web UI 使用 `/api/*` 與 `/ws/chat`。
- MCP host 使用標準 Streamable HTTP `/mcp`；外部 canonical URL 是
  `https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp`。
- stdio-only host 啟動 `scripts/run_mcp_stdio_proxy.py`，它只把 stdio 轉成
  Streamable HTTP，不 import project Blender adapter。

詳細 client 設定見 [MCP_CLIENTS.md](MCP_CLIENTS.md)。

## 架構決策

### ADR-001：保留 ahujasid/blender-mcp addon 作為 Blender execution boundary

- 決策：以 `BlenderMCPAdapter` 包裝 addon socket protocol。
- 理由：保留已驗證的 Blender 執行能力，同時阻止 addon dialect 洩漏至 domain。
- 後果：API process 是 socket owner；真機驗證可用 direct socket 作獨立 oracle。

### ADR-002：LLM provider 透過 ports 可替換

- 決策：LLM use cases 依賴 `LLMPort`，具體 provider 留在 adapters。
- 理由：MCP scene operations 不應依賴或等待特定 LLM。

### ADR-003：FastAPI process mount client-neutral FastMCP

- 決策：不啟動第二個 MCP backend process；FastMCP ASGI app mount 在 `/mcp`。
- 理由：REST/MCP 可共用 runtime、identity middleware、Origin guard 與 Blender socket。
- 後果：MCP lifecycle 與 FastAPI lifespan 組合，但只有 FastAPI lifespan 管 Blender connect。

### ADR-004：遠端以 Streamable HTTP 為主，stdio 只做 proxy

- 決策：不公開 legacy SSE；不建立 stdio-only Blender server。
- 理由：不同 host 共用同一 remote endpoint，避免每個 client 各開一條 9876 connection。

完整決策脈絡與 rejected alternatives 見
[development/MCP_LAYER_ADR.md](development/MCP_LAYER_ADR.md)。

## 安全邊界

- `/mcp` 受 Tailnet identity middleware 保護，唯一 exemption 是 `/api/health`。
- MCP public catalog 固定八項 curated tools，刻意不含 `execute_code`。
- annotations 是 host UX hint，不是 authorization。
- `clientInfo.name` 不參與 authorization、catalog 或 capability branching。
- 公網 multi-user connector 不在本版範圍；需要獨立 OAuth 2.1/CIMD、audit、rate limit 與 privacy design。
