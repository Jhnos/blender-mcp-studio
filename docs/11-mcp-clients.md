# 11 — MCP clients：連線契約、工具目錄、host 設定

> 回導航 [[README]] · 相關 [[10-runtime-ssot]]、[[01-architecture]]、[[30-verification]]
>
> 埠與環境變數見 [[10-runtime-ssot]]；安全邊界的完整說明見 [[01-architecture]]；
> 驗證判準見 [[30-verification]]。本檔只講「client 怎麼接、接到什麼」。

## Contents

- [Transport](#transport)
- [Connection contract](#connection-contract)
- [Tool catalog](#tool-catalog)
- [Client configuration examples](#codex-configuration-example)

## Transport

- 協定：MCP Streamable HTTP，經 initialize 協商。
- Server 模式：stateless HTTP。
- Legacy SSE：**不對外開放**。
- 相容路徑：`scripts/run_mcp_stdio_proxy.py` 使用 FastMCP `create_proxy` 與
  `transport="stdio"`。
- 結果型別：typed result 用 structured text/JSON；PNG 用 MCP image content。

Blender MCP Studio exposes standard MCP Streamable HTTP at:

`https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp`

The server does not detect or special-case the MCP host. Any client that supports
MCP Streamable HTTP can use the URL while authenticated to the Tailnet.

For a client that only launches stdio servers, run:

`~/miniconda3/envs/blender-mcp/bin/python scripts/run_mcp_stdio_proxy.py`

The stdio process proxies the HTTP MCP endpoint; it does not open another Blender
socket and can coexist with the Web UI and REST API.

## Connection contract

| Capability | Contract |
|---|---|
| Primary transport | MCP Streamable HTTP at the canonical URL above |
| Compatibility transport | Local stdio-to-HTTP proxy; set `BLENDER_MCP_URL` to override its upstream |
| Network boundary | Tailnet membership and the gateway-injected identity are required |
| Structured output | Read tools and mutations return typed MCP `structuredContent` where applicable |
| Screenshots | `get_viewport_screenshot` returns MCP image content with MIME type `image/png` |
| Destructive confirmation | Tool annotations identify destructive operations; the host decides whether to prompt |
| Backend ownership | REST, WebSocket, HTTP MCP, and stdio MCP share one API runtime and one addon socket |

The canonical URL is the server contract. Client configuration filenames and UI
labels can change between host releases; treat the examples below as host setup
examples, not server requirements.

## Tool catalog

| Tool | Kind | Purpose |
|---|---|---|
| `blender_status` | Read | Report whether the shared Blender connection is available |
| `get_scene_info` | Read | Return scene counts and object summaries |
| `get_object_info` | Read | Return transforms, visibility, and materials for one object |
| `get_viewport_screenshot` | Read | Return a bounded PNG viewport capture |
| `check_print_readiness` | Read | Inspect visible meshes for slicing risks and millimetre metrics without changing the scene |
| `list_verification_suites` | Read | List registered tests, scope and expected case coverage |
| `run_verification_suite` | Temporary mutation | Run a registered suite on the current model and restore its poses and selection |
| `create_object` | Write | Create a mesh cube, curve, light, or camera |
| `modify_object` | Destructive write | Change transforms or visibility |
| `delete_object` | Destructive write | Permanently remove one object |
| `apply_material` | Destructive write | Create/update and assign a Principled BSDF material |
| `run_design_pipeline` | Write | Submit the current model, a registered native revision, or an explicit historical/custom ModelSpec; returns a queued job |
| `describe_model_spec` | Read | ModelSpec v1 JSON Schema, defaults, supported printers/materials and a worked example |
| `list_artifacts` | Read | Deliverable directories usable as `source.root_dir` (STL count per subdirectory, 3MF names) |
| `get_job_status` | Read | Poll a design job by `job_id` |
| `get_run_report` | Read | Per-stage verdicts, metrics, evidence and the overall `passed` flag of one run |
| `check_mesh_integrity` | Read | Closed / non-self-intersecting check for STLs under an artifact root |
| `slice_for_print` | Write | Slice a 3MF with the Bambu Studio CLI into a new run directory |
| `list_instances` | Read | Registered parametric instances and the part files each build must produce |
| `build_instance` | Destructive write | Build one registered instance in Blender and overwrite its declared STLs |
| `tool_status` | Read | Availability and version of the external tools the pipeline needs |

`execute_code` is intentionally not public. The internal Blender adapter may use
it after translating a curated domain operation, but no MCP client can submit
arbitrary Python.

### 工具契約（註記與逾時）

| Tool | Read-only | Destructive | Idempotent | Max timeout |
|---|---:|---:|---:|---:|
| `blender_status` | yes | no | yes | 5 s |
| `get_scene_info` | yes | no | yes | 10 s |
| `get_object_info` | yes | no | yes | 10 s |
| `get_viewport_screenshot` | yes | no | yes | 30 s |
| `check_print_readiness` | yes | no | yes | 30 s |
| `list_verification_suites` | yes | no | yes | 5 s |
| `run_verification_suite` | no | no | yes | 330 s |
| `create_object` | no | no | no | 30 s |
| `modify_object` | no | yes | yes | 30 s |
| `delete_object` | no | yes | no | 30 s |
| `apply_material` | no | yes | no | 30 s |
| `run_design_pipeline` | no | no | no | 30 s |
| `describe_model_spec` | yes | no | yes | 10 s |
| `list_artifacts` | yes | no | yes | 10 s |
| `get_job_status` | yes | no | yes | 10 s |
| `get_run_report` | yes | no | yes | 10 s |
| `check_mesh_integrity` | yes | no | yes | 47.5 s（由 `max_total_stl_bytes` 推導） |
| `slice_for_print` | no | no | no | 切片埠的 `timeout_s`（Bambu：`SLICE_TIMEOUT_S`）+ 30 s |
| `list_instances` | yes | no | yes | 10 s |
| `build_instance` | no | yes | no | `GENERATOR_TIMEOUT_S` + 30 s |
| `tool_status` | yes | no | yes | 10 s |

所有工具都設 `openWorldHint=false`。名稱有長度上限，向量恰好三個有限數字，
顏色是 `[0,1]` 的 RGBA，變異類 schema 拒絕額外屬性。
**Tool annotation 只是建議性的**——實際邊界由 identity middleware 與 registry 強制。

### 設計管線（ModelSpec → 可列印包）

驗證目前模型時，直接呼叫 `run_design_pipeline`，不提供 `spec`。應用服務從唯一宣告選版，
立即回傳 `job_id`／`run_id` → `get_job_status` 輪詢 → `get_run_report` 讀逐階段證據。
`describe_model_spec` 與 `list_artifacts` 可查詢服務所選模型；只有明確要求歷史／自訂模型時，
才提供自己的 spec。客戶端不必先找路徑、選版本或複製範例。
`check_mesh_integrity` 與 `slice_for_print` 可單獨使用，也接受 ModelSpec 以外的檔案。

原件修訂仍使用同一個工具：`run_design_pipeline` 傳入
`{"revision":{"recipe_id":"screen-clamp","target_angle_deg":30}}`，REST 的相同參數傳給
`POST /api/design/runs`。修訂時省略 `spec`；目標角僅接受 0、15、30、45、60 度。
服務在排隊前固定目前選版與列印條件，另存完整 STL，再由同一批零件衍生 3MF，沿用原有
幾何、切片與封裝階段。原檔與目前選版不會自動改變；同一工作只提供正式產物、報告與切片證據，
來源副本、執行程式及內部收據不提供下載或封裝。完成待確認的工作保持隔離；晚到收據驗證後，
若資格流程未繼續，工作會明示中斷，不自動重送修改。工具可用性以當前已載入版本為準。


- **路徑規則**：`stl_paths`、`input_3mf` 一律是允許的 artifact root 底下的**相對路徑**，
  與 ModelSpec 同一道關卡（無 `..`、無隱藏段、副檔名須為 `.stl`／`.3mf`、符號連結不得逃出 root），
  並受同一組檔案數與大小上限。任何輸出都不含主機絕對路徑。
- **證據檔**：`slice_for_print` 的 `output_3mf`／`settings_json`／`log_path` 是
  `run://{run_id}/print/<name>` 資源 URI；以 MCP 資源 `run://{run_id}/{name}` 讀取
  （`.json`／`.log` 回文字，其餘回二進位），超出 run 目錄的名稱會被拒絕。
- **未設定**：伺服器沒有接上對應服務時，工具仍在目錄內，呼叫會得到
  「not configured on this server」的工具錯誤。
- 匯入階段忽略的檔案（隱藏路徑段**或**副檔名不是 `.stl` 的符合項）記在 `skipped` 指標，
  名單（最多 20 筆）在該 run 的 `import.json`。
- **每個 PASSED 階段都有可開的證據**：`evidence` 只放相對 run 目錄的路徑，都能用
  `run://{run_id}/{name}` 讀取。`import.json` 列出每個 STL 與專案 3MF 的相對路徑、sha256 與位元組數；
  `geometry.json` 列出逐檔判定。兩者都進 manifest，所以來源檔也被 checksum 釘住。
- **規格 v1 的限制**：`mechanism.suites` 必須為空（非空會在送出時被拒）；mechanism 階段固定為
  `not_applicable`，訊息「mechanism not evaluated in Phase 1 (import path)」。不支援的印表機或材料
  在送出時就被拒絕，不會建立工作。未知鍵的錯誤會列出允許的鍵。
- **Blender 忙碌**：設計 run 的階段持有 Blender lease 時，`create_object`、`modify_object`、
  `delete_object`、`apply_material`、`check_print_readiness`、`run_verification_suite`、
  `build_instance` 立即回工具錯誤「Blender is busy with design run stage <stage>; retry later」，
  不排隊；`run_verification_suite` 與 `build_instance` 執行時也持有 lease，之後到的 run 會等它。

### 登錄測試

先呼叫 `list_verification_suites`，再將回傳的 `suite_id` 傳給 `run_verification_suite`。目前有 `cable-contact-controls`（10個實體／自接觸／跨段、7個線對線正反例）、`electrode-head-routes`（4個獨立探頭端走線姿態）、`electrode-head-bundle`（三線共同工作／各自抬高姿態與一個阻擋反例）、`electrode-full-chains`（三條底座至探頭完整線的工作與各自抬高姿態），以及 `electrode-cable-motion`（以同一組保存參數重驗62個升降／抬高後前後伸縮／混合取樣姿態，另驗升降端點安全但中途受阻的反例）。另有 `electrode-wrist-service`（兩頭各32個退齒／旋轉／復位取樣與障礙反例）及 `electrode-clamp-service`（286個拆件移動取樣、12個止擋，工作位及障礙反例）。新增 `electrode-transfer-capillary` 與 `electrode-transfer-pH_temp`，各驗一頭由已鎖緊工作位經鬆鎖、退齒、轉位、復位至已鎖緊維修位的188個取樣，以及獨立中途線路障礙反例；另一頭保持鎖緊。另有 `electrode-cycle-capillary` 與 `electrode-cycle-pH_temp`，在已就座維修位依序退出兩螺栓、夾蓋組及探頭組，再反向重裝（208／260取樣）；所有移出零件保留在場景碰撞檢查中，含九段線路與指定障礙反例。十個探頭套件要求目前開啟已生成的工作站電極臂模型；工具不載入、建立或覆寫使用者模型。測試會暫時建立配件或調整臂姿態，完成後恢復姿態、肩肘及腕部退齒屬性（包含原本未建立的屬性）、選取與active object；無法恢復即回報執行錯誤。

本工作站走線套件的通過基準使用 `cable-clearance` 配置；可在Blender開啟 `tmp/lab-station-route-engine/motion-lift-pH_temp-+000-000.blend` 後執行。其他配置仍依實際量測回傳結果，不會因同樣是電極臂模型就自動通過。

回傳包含 `suite_id`、`passed`、逐項 `checks`（name／expected／observed／passed／detail）、`scope` 和 `scene_restored`。`passed=false` 表示有測試未通過；未知測試、缺少模型、缺漏證據或Blender不可用則是工具錯誤。測試名稱是封閉登錄集合，不能傳程式碼、檔案路徑或自訂預期值。REST的 `/api/verification/suites` 與 `/api/verification/suites/{suite_id}/run` 使用同一服務。

## Codex configuration example

Add this to `~/.codex/config.toml` for a personal connection, or to the trusted
project's `.codex/config.toml` for a project-scoped connection:

```toml
[mcp_servers.blender_mcp_studio]
url = "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
required = true
startup_timeout_sec = 20
tool_timeout_sec = 360
```

Restart or open a new Codex task, then inspect `/mcp`. Codex's current config
schema also supports stdio servers through `command`, `args`, and `env`.

目前模型由共享應用服務解析：`run_design_pipeline` 省略 `spec` 即提交目前模型，REST `POST /api/design/runs` 可提交 `{}`。明確 spec 只用於歷史／自訂驗證。REST 的 `GET /api/design/spec`、`GET /api/design/artifacts` 與 MCP `describe_model_spec`、`list_artifacts` 共用同一目錄服務；客戶端沒有版本設定副本。

## Claude Code configuration example

Claude Code supports remote HTTP MCP directly:

```bash
claude mcp add --transport http blender-mcp-studio \
  https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
```

Use `claude mcp list` or `/mcp` to inspect the connection. This syntax follows
the [Claude Code MCP documentation](https://docs.anthropic.com/en/docs/claude-code/mcp).

## VS Code configuration example

Create `.vscode/mcp.json` or use **MCP: Open User Configuration**:

```json
{
  "servers": {
    "blender-mcp-studio": {
      "type": "http",
      "url": "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
    }
  }
}
```

VS Code documents `type: "http"` as the Streamable HTTP connection and asks the
user to trust a newly configured server. See the
[VS Code MCP server guide](https://code.visualstudio.com/docs/agent-customization/mcp-servers).

## Cursor configuration example

Cursor's MCP settings support Streamable HTTP. Add a custom MCP server in
**Settings → Tools & MCP** and use the canonical URL. If configuring JSON, follow
the schema shown by the installed Cursor version rather than copying another
host's top-level keys. See the [Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol).

## Generic stdio JSON example

Use this shape for a host that only accepts a local command. Paths are absolute
because GUI-launched clients do not reliably inherit the shell working directory:

```json
{
  "mcpServers": {
    "blender-mcp-studio": {
      "command": "/Users/bearmacmini/miniconda3/envs/blender-mcp/bin/python",
      "args": [
        "/Users/bearmacmini/Blender_MCP_drawer/scripts/run_mcp_stdio_proxy.py"
      ],
      "env": {
        "BLENDER_MCP_URL": "https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp"
      }
    }
  }
}
```

## 接上之後

**安全邊界**（identity、Host/Origin、protocol version、二十一項工具相等性、公網散布的
前提）完整說明見 [[01-architecture]] 的安全邊界一節。這裡只提醒 client 開發者三件事：

- `/mcp` **不是** identity exemption。缺少可信 Tailnet identity 的請求會收到 HTTP 401。
- `clientInfo.name` 不改變 authorization、capabilities、schema 或工具目錄。
- 這是私有 Tailnet 部署，不是公開 connector。

**驗證**：對 MCP URL 發 GET 得到 HTTP 200 **不算證據**——前端 fallback 也會回 200。
必須跑真正的 initialize 與 `tools/list`。完整判準與指令見 [[30-verification]]。


`list_artifacts` 的選版來源已設定原生檔檢查時，`default_native` 會提供同一選版快照的root-relative原生檔名、SHA256、完整列印件指紋與來源清單指紋。`available=false`會附拒絕原因，不改讀歷史資料夾；未提供原生來源檢查的服務可省略此欄位。`scope=file_identity_only`只表示檔案身分核對，不代表原生檔可開啟、機構可動或已通過列印驗收。真正修訂前仍須暫存來源並重新核對；客戶端不要從檔名中的舊版號推斷目前模型。
