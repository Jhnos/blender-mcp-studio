# 01 — 架構：不變式、分層、決策

> 回導航 [[README]] · 相關 [[10-runtime-ssot]]、[[11-mcp-clients]]、[[20-conventions]]
>
> 架構圖的單一真相源是可互動的 [architecture.html](architecture.html)。其內嵌 JSON
> model 同時驅動畫面與 AI 結構化欄位；`test_architecture_ssot.py` 以 AST 驗證
> model node 與真實 class/function anchor，避免圖與程式漂移。
>
> **埠號、位址與環境變數不寫在本檔**，一律見 [[10-runtime-ssot]]。

## 目錄

- [核心不變式](#核心不變式)
- [分層與責任](#分層與責任)
- [Inbound adapters](#inbound-adapters)
- [Domain/application 契約](#domainapplication-契約)
- [Shared runtime](#shared-runtime)
- [架構決策](#架構決策)
- [安全邊界](#安全邊界)

## 核心不變式

所有 inbound transport 都匯入同一個 `AppRuntime`：

`HTTP MCP / stdio proxy / REST / WebSocket → application services → Blender adapters → BlenderSocketClient → Blender addon socket`

- FastAPI、REST、WebSocket 與 MCP 共用同一 `BlenderPort` instance。
- API lifespan 只 connect/disconnect 一次；stdio proxy 不擁有 backend。
- MCP 是 inbound adapter，只依賴 `SceneQueryPort` / `SceneCommandPort` / `PrintReadinessQueryPort`。
- REST 與 MCP 注入同一個 `PrintReadinessService`；它依賴窄化的 `PrintReadinessPort`，不併入 scene commands。
- WebUI 的批次變形經獨立 `BatchTransformService` 與 `SceneBatchCommandPort`；REST 只是 delivery adapter，沒有把 HTTP 概念放進 use case。
- WebUI 指令面板只依賴純 `CommandDefinition` registry 與注入 callbacks；它不 import REST action、Zustand store 或 Blender 名稱。
- `operationStore` 是 UI 操作 lifecycle SSOT，最多保留五筆；retry callback 只有來源明確宣告安全時才存在，批次變形與 Undo/Redo 永不自動重試。
- `SceneOperationsService` 使用不可變 domain value，並在 Blender JSON 邊界嚴格 narrowing。
- `BlenderMCPAdapter` 是高階操作到 addon dialect 的唯一翻譯 chokepoint。
- 共享 `BlenderSocketClient._lock` 序列化 socket request/response；MCP 不建立第二把 transport lock。

## 分層與責任

| 層 | 主要構件 | 責任 |
|---|---|---|
| Presentation | FastAPI routers、FastMCP server | HTTP/WS/MCP framing、schema、error mapping |
| Application | `AppRuntime`、`SceneOperationsService`、`PrintReadinessService`、`BatchTransformService` | composition、lifecycle、use-case orchestration |
| Domain | scene/print-readiness/batch-transform immutable values、窄 ports | Client-neutral language 與 inward dependency contract |
| Adapter | `BlenderMCPAdapter`、`BlenderPrintReadinessAdapter`、`BlenderBatchTransformAdapter`、`BlenderSocketClient` | addon translation、inspection、single-Undo batch mutation、locking、TCP |
| Engine | Blender + addon | 執行 `bpy` 並保存 3D scene state |

### Web frontend 模組邊界

```text
CommandPalette -> CommandRegistry -> injected Studio callbacks
                                      |-> PreviewStage actions
                                      |-> ExportPanel readiness handle
                                      `-> BatchSelectionStore

Preview / history / export / batch -> OperationStore -> OperationStatusCenter
ObjectList -> MDR dispatch -> REST batch endpoint -> BatchTransformService
```

- `web/src/commands/registry.ts` 是純 TypeScript registry，負責唯一 id、availability 與搜尋排序；新增指令以註冊擴充，不修改 palette conditional。
- `web/src/commands/studioCommands.ts` 只組合九個 curated 前端指令，所有副作用都由 `StudioCommandActions` 注入。
- `web/src/hooks/useGlobalShortcuts.ts` 是鍵盤入口，`input`、`textarea`、`select` 與 `contenteditable` 一律 fail closed，不攔截文字編輯。
- `web/src/stores/batchSelectionStore.ts` 保存前端批次目標與最後已知物件名；勾選不改 Blender active selection。
- `ExportPanelHandle` 只暴露 `open()` 與 `rerunInspection()` 兩個意圖，不讓指令層讀寫元件內部 report state。

Dependency rule：外層依賴內層；domain/application 不 import FastAPI、FastMCP 或 `bpy`。

## Inbound adapters

- Web UI 使用 `/api/*` 與 `/ws/chat`。
- MCP host 使用標準 Streamable HTTP `/mcp`；對外 canonical URL 見 [[10-runtime-ssot]]。
- stdio-only host 啟動 `scripts/run_mcp_stdio_proxy.py`，它只把 stdio 轉成
  Streamable HTTP，不 import project Blender adapter。

詳細 client 設定見 [[11-mcp-clients]]。

## Domain/application 契約

`SceneQueryPort` 定義 `status()`、`get_scene_info()`、`get_object_info(name)`、
`get_viewport_screenshot(max_size)`。

`SceneCommandPort` 定義 `create_object(spec)`、`modify_object(spec)`、
`delete_object(name)`、`apply_material(spec)`。

`SceneOperationsService` 同時實作這兩個 incoming port，且**只**依賴 `BlenderPort`。
Domain record 一律是 frozen/slots dataclass。外部 Blender JSON 逐欄窄化，
不做隱性的 `str`／`int`／`bool` 強制轉型。

`PrintReadinessQueryPort.check(spec)` 由共用的 `PrintReadinessService` 實作；
它獨立的 outgoing `PrintReadinessPort.inspect` 由 `BlenderPrintReadinessAdapter` 實作。
報告一律用毫米，分析上限為 20,000 三角面／5,000 交集。

`BatchTransformService` 依賴窄化的 `SceneBatchCommandPort`。它在變異前先驗證所有目標，
再委派**一次** Blender operator 呼叫，使單次 Undo 能還原整批。REST 只是 delivery
adapter；Web 的選取狀態不等於 Blender 的 selection。

## Shared runtime

`api/runtime.py` 是 composition root。一個 `AppRuntime` 內含唯一一份：

- `BlenderPort`
- `SceneOperationsService`
- `PrintReadinessService`
- `BatchTransformService`
- event bus 與 adapter factory
- security、prompt、persistence、vision、asset、text-3D ports

FastAPI 在 `app.state` 上發布相容別名，但它們的物件 identity 與 runtime 欄位相同。
FastAPI 的 lifespan 擁有 Blender 的 connect/disconnect；組合後的 FastMCP lifespan
只擁有 MCP 協定資源。

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
- 理由：不同 host 共用同一 remote endpoint，避免每個 client 各開一條 addon socket connection。

### ADR-005：批次變形是獨立 transaction boundary

- 決策：`POST /api/scene/batch-transform` 呼叫 `BatchTransformService`，再透過窄 `SceneBatchCommandPort` 進入一個帶 `UNDO`、並以 `('EXEC_DEFAULT', True)` 明確啟用 undo 的 Blender operator。
- 理由：逐物件 fan-out 會產生部分成功與多筆 Undo；任意 Python endpoint 則破壞 typed client-neutral boundary。
- 後果：最多 100 個目標先完整 preflight，再一次套用；一次 `/api/undo` 必須復原全部目標，並由真 Blender nonce fixture 證明。

### ADR-006：前端生產力工具採 registry + lifecycle store

- 決策：快捷指令由純 registry 排序與過濾；最近操作由專用 Zustand store 管理，不由每個 component 建立 toast timer。
- 理由：palette 不應成為任意 backend action console；操作結果也不應散落為互不一致、無法追溯的區域提示。
- 後果：公開指令固定為九個 curated callbacks；操作記錄上限五筆，只有明確 idempotent 的刷新可顯示重試。

完整決策脈絡與 rejected alternatives 見
[archived MCP layer ADR](archive/2026-07-client-neutral-mcp/development/MCP_LAYER_ADR.md)。

## 安全邊界

| 控制項 | 強制的行為 |
|---|---|
| Tailnet identity | 除 `/api/health` 外的所有 HTTP；`/mcp` 缺 identity → 401 |
| Host/Origin guard | 由 loopback 與 `CORS_ORIGINS` 推導的嚴格 allowlist |
| Protocol version | 不支援的 `MCP-Protocol-Version` → HTTP 400 |
| Tool surface | 恰好九項工具的相等性檢查；`execute_code` 不存在 |
| Error mapping | 可復原的 domain error 轉成可行動的 `ToolError`／HTTP 422 |
| Error masking | 非預期的 MCP 內部錯誤不把 traceback 洩漏給 client |
| Socket serialization | `BlenderSocketClient` 內的單一 `asyncio.Lock` |

- `/api/health` 是**唯一**的 identity exemption，存在理由是讓 watchdog 探測 process。
- MCP public catalog 固定九項 curated tools，刻意不含 `execute_code`；第九項
  `check_print_readiness` 是唯讀、冪等且 30 秒 timeout。
- annotations 是 host UX hint，**不是** authorization；identity middleware 與
  registry 才是實際強制的邊界。
- `clientInfo.name` 可被觀測作協定遙測，但不參與 authorization、catalog 或
  capability branching。
- 公網 multi-user connector 不在本版範圍；需要獨立 OAuth 2.1/CIMD、audit、
  rate limit 與 privacy design。
