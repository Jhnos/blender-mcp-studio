# 10 — Runtime SSOT：埠、路由、環境變數

> 回導航 [[README]] · 相關 [[01-architecture]]、[[12-deployment]]、[[11-mcp-clients]]

**這個檔是埠號、監聽位址、對外路由、canonical URL 與環境變數的唯一真相源。**
其他文件需要這些值時一律指回這裡，不得複寫——複寫過的版本會各自腐爛。

## 目錄

- [Runtime baseline](#runtime-baseline)
- [服務與路由](#服務與路由)
- [Canonical URLs](#canonical-urls)
- [Prefix contract](#prefix-contract)
- [環境變數](#環境變數)
- [驗證載入狀態](#驗證載入狀態)

## Runtime baseline

| 項目 | 版本／值 | 說明 |
|---|---|---|
| Python | 3.11 | Conda env `blender-mcp` |
| FastMCP | `>=3.4,<4` | MCP server、in-memory client、stdio proxy |
| Pydantic | `>=2.0` | Strict MCP input schemas |
| FastAPI | installed env | REST、WebSocket、ASGI mount |
| Node.js | 20+ | Vite/React frontend |
| Blender | 5.1 | validated addon execution engine |

相依宣告的 SSOT 是 `pyproject.toml` 與 `environment.yml`。

## 服務與路由

| 服務 | 監聽 | 對外路徑 | Owner | 用途 |
|---|---|---|---|---|
| Vite production preview | `127.0.0.1:19504` | `/blender/` | Web LaunchAgent | React UI |
| FastAPI | `127.0.0.1:19505` | `/blender/api/*`、`/blender/ws/*`、`/blender/mcp` | API LaunchAgent | REST／WebSocket／MCP |
| Blender addon | `127.0.0.1:9876` | 無（API 獨佔的 raw TCP） | Blender LaunchAgent | Scene execution |

開發模式的 Web 走 `5173`（`scripts/run_dev.sh`），**不是** production 埠。埠 `19147` 已退役。

跨專案的服務登錄在 `~/MacHomeHub/config/services.yaml`；本專案的 LaunchAgent 來源在
`deploy/launchd/*.plist`（安裝後的副本是衍生狀態，見 [[12-deployment]]）。

## Canonical URLs

```text
Web UI: https://bearmacminimac-mini.tail56c751.ts.net/blender/
MCP:    https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
Health: https://bearmacminimac-mini.tail56c751.ts.net/blender/api/health
```

MCP 的內部端點是 `http://127.0.0.1:19505/mcp`。驗證一律走上面的對外 FQDN——
`localhost` 通過不代表使用者能用。

## Prefix contract

MacHomeHub 設定 `strip_prefix: false`，因此 Vite 收到完整的 `/blender/...` 路徑，
再套用明確的 proxy rewrite：

```text
/blender/mcp        → rewrite /mcp        → API :19505
/blender/api/scene  → rewrite /api/scene  → API :19505
/blender/ws/chat    → rewrite /ws/chat    → API :19505
```

MCP 的 proxy 條目必須排在 `/blender/api` **之前**，並保留 HTTP method、`Accept`、
`MCP-Protocol-Version` 與 `MCP-Session-Id`。它不緩衝串流，也不取代 Host/Origin 的
identity 語意。

## 環境變數

```bash
BLENDER_HOST=localhost
BLENDER_PORT=9876
BLENDER_TRANSPORT=socket
API_HOST=127.0.0.1
API_PORT=19505
CORS_ORIGINS=https://bearmacminimac-mini.tail56c751.ts.net
REQUIRE_TAILNET_IDENTITY=1
BLENDER_MCP_URL=https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
```

`BLENDER_MCP_URL` **只**設定選用的 stdio proxy 的上游；它不會改變 API runtime 的
Blender adapter 或 socket 端點。

## 驗證載入狀態

檢查實際載入的狀態，而不是原始檔的內容：

```bash
launchctl print gui/$(id -u)/com.blender-mcp.web
lsof -nP -iTCP:19504 -iTCP:19505 -iTCP:9876 -sTCP:LISTEN
curl -fsS http://127.0.0.1:19505/api/health
```

`status: "ok"` 只證明 API process 活著；`blender` 欄位必須是 `connected`，
scene 工具才可能成功。完整的驗證分層見 [[30-verification]]。
