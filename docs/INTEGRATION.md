# Blender MCP Studio — Tailnet 整合文件

> 語言：繁體中文
> 最後更新：2026-04-06

---

## 1. 專案概述

**Blender MCP Studio** 是一套透過對話驅動 3D 建模的工作站工具，整合了：

- **LLM**（Claude / OpenAI / Ollama）作為意圖解析層
- **MCP 協定**（Model Context Protocol）作為 Blender 控制介面
- **Blender TCP Server**（blender-mcp addon）作為場景執行器

### 架構圖

```
使用者瀏覽器
    │
    ▼ HTTPS
Tailscale Funnel (bearmacminimac-mini.tail56c751.ts.net)
    │
    ▼ HTTP (port 8443)
MacHomeHub（reverse proxy）
    │
    ├── /blender/*  ──────────► Vite Dev Server  (127.0.0.1:19147)
    │                                │
    │                    ┌───────────┴────────────┐
    │                    │ Vite proxy (dev server) │
    │                    └───────────┬────────────┘
    │                                │
    │                    ┌───────────┴──────────────┐
    │                    │  /blender/api/*  ──────► FastAPI (127.0.0.1:17823)
    │                    │  /blender/ws/*   ──────► FastAPI WebSocket
    │                    └──────────────────────────┘
    │
    └── /blender/api/health  ─────► FastAPI health endpoint

FastAPI (17823)
    │
    └── TCP 9876  ──────────────► Blender (手動啟動)
                                        │
                                  blender-mcp addon
```

---

## 2. 服務清單

| 服務 | Port | 協定 | 說明 |
|------|------|------|------|
| Vite Dev Server（Web UI） | 19147 | HTTP | React + Vite 前端，含 API proxy |
| FastAPI（API Server） | 17823 | HTTP / WebSocket | 後端 API，`/api/*` 和 `/ws/chat` |
| Blender TCP Server | 9876 | TCP | Blender blender-mcp addon 監聽 |

---

## 3. 整合需求

### 3.1 Tailscale sub-path

Tailscale Funnel 根路徑 `/` 由 MacHomeHub 接管，Blender MCP Studio 使用：

```
https://bearmacminimac-mini.tail56c751.ts.net/blender/
```

MacHomeHub 以預設的 `strip_prefix: true` 模式將 `/blender/*` 轉發至 Vite（port 19147），
前綴 `/blender` 在轉發前被剝除，Vite 接收到的路徑不含前綴。

路徑轉換示例：
- `/blender/` → Vite 收到 `/`
- `/blender/api/health` → Vite 收到 `/api/health` → proxy 到 FastAPI
- `/blender/ws/chat` → Vite 收到 `/ws/chat` → proxy 到 FastAPI WebSocket
- `/blender/assets/main.js` → Vite 收到 `/assets/main.js`（靜態檔案）

### 3.2 vite.config.ts 修改

```typescript
export default defineConfig({
  base: '/blender',            // ← 加入 base path（讓靜態資源路徑含前綴）
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/ws': { target: 'ws://localhost:17823', ws: true },
      '/api': { target: 'http://localhost:17823' },
    },
  },
})
```

**說明**：
- `base: '/blender'` 讓 HTML 中的資源路徑含 `/blender/` 前綴，符合瀏覽器的完整 URL
- MHH 在轉發前已剝除 `/blender`，Vite 收到的是 `/ws/*` 和 `/api/*`
- proxy 規則保持最簡單，不需要 rewrite
- 後端不需感知任何前綴

### 3.3 WebSocket URL 修改（useWebSocket.ts）

原本硬編碼的 `WS_URL = '/ws/chat'` 需改為動態推導：

```typescript
const base = import.meta.env.BASE_URL.replace(/\/$/, '') // e.g. '/blender'
const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${proto}//${location.host}${base}/ws/chat`
```

這樣：
- 直接開 `http://localhost:19147/blender/` 時：`ws://localhost:19147/blender/ws/chat` → Vite proxy → 後端
- 透過 Tailscale 開 `https://host/blender/` 時：`wss://host/blender/ws/chat` → MHH → Vite proxy → 後端

### 3.4 launchd plist（兩個服務）

#### `deploy/com.blender-mcp.api.plist`
- Label：`com.blender-mcp.api`
- 啟動 FastAPI uvicorn，port 17823
- WorkingDirectory：Blender MCP 專案根目錄
- 環境變數：`CORS_ORIGINS` 含 Tailscale URL

#### `deploy/com.blender-mcp.web.plist`
- Label：`com.blender-mcp.web`
- 啟動 Vite dev server，port 19147
- WorkingDirectory：`web/` 子目錄

安裝至 `~/Library/LaunchAgents/`，用 `launchctl load` 啟用。

### 3.5 MHH services.yaml 設定

```yaml
  - name: "Blender MCP Studio"
    icon: "🎨"
    description: "Blender AI 建模工作室（React + FastAPI）"
    primary:
      port: 19147
      funnel_path: "/blender/"
      open_url: "https://bearmacminimac-mini.tail56c751.ts.net/blender/"
      strip_prefix: false
      health_endpoints:
        - path: "/blender/api/health"
          url: "https://bearmacminimac-mini.tail56c751.ts.net/blender/api/health"
      auto_intervene: false
      expected_process: "node"
    internal:
      - name: "Blender MCP API"
        port: 17823
        expected_process: "python3"
```

**重點**：
- `strip_prefix: false`：MHH 不剝除 `/blender` 前綴，原路轉發
- `health_endpoints[].url`：必須走 Tailscale URL（CLAUDE.md 全域規則）
- `internal` 欄位讓 MHH 同時監控 API process

### 3.6 Health Check URL

> ⚠️ 遵循 CLAUDE.md 全域規則：Health check 走 Tailscale URL，不走 localhost。

```
https://bearmacminimac-mini.tail56c751.ts.net/blender/api/health
```

預期回應：`{"status": "ok"}`

---

## 4. 依賴條件

| 依賴 | 狀態 | 說明 |
|------|------|------|
| Blender | **手動啟動** | 需在 Blender 中載入並啟用 blender-mcp addon，TCP server 監聽 9876 |
| Ollama | 建議啟動 | 若使用本機 LLM（`config/llm_providers.yaml` 設為 ollama）需確認 Ollama 正在跑 |
| conda env `blender-mcp` | 必須 | FastAPI 在此環境執行 |
| Node.js | 必須 | Vite dev server 需要 |
| MacHomeHub | 必須 | 負責 Tailnet sub-path routing |

**啟動順序建議**：
1. 啟動 MacHomeHub（已自動啟動，確認健康即可）
2. 啟動 FastAPI：`launchctl start com.blender-mcp.api`
3. 啟動 Vite：`launchctl start com.blender-mcp.web`
4. 開啟 Blender，在 Blender 中啟用 addon 並啟動 TCP server
5. 訪問 `https://bearmacminimac-mini.tail56c751.ts.net/blender/`

---

## 5. 整合腳本說明

`scripts/integrate_tailnet.sh` 一鍵完成以下步驟：

1. **修改 `web/vite.config.ts`**：加入 `base: '/blender'`，更新 proxy 路徑和 rewrite 規則
2. **修改 `web/src/hooks/useWebSocket.ts`**：WebSocket URL 改為動態推導
3. **建立 launchd plist**：在 `deploy/` 目錄生成兩個 plist 檔案
4. **安裝 plist**：複製到 `~/Library/LaunchAgents/` 並 load
5. **更新 MHH services.yaml**：在 `~/MacHomeHub/config/services.yaml` 追加 Blender MCP Studio 項目

執行方式：
```bash
cd /Users/bearmacmini/Desktop/Blender_MCP_drawer
bash scripts/integrate_tailnet.sh
```

腳本具有冪等性（idempotent）：重複執行不會重複修改，若設定已存在會跳過。

---

## 6. 驗證清單（Phase 4）

> 全部使用 Tailscale URL，不用 localhost

- [ ] `curl -sf https://bearmacminimac-mini.tail56c751.ts.net/blender/` → 回傳 HTML（含 `<div id="root">`）
- [ ] `curl -sf https://bearmacminimac-mini.tail56c751.ts.net/blender/api/health` → `{"status":"ok"}`
- [ ] MHH 儀表板（`https://bearmacminimac-mini.tail56c751.ts.net/`）顯示 Blender MCP Studio 綠燈
- [ ] 瀏覽器開啟 `https://bearmacminimac-mini.tail56c751.ts.net/blender/`，聊天介面正常載入
- [ ] WebSocket 連線成功（介面顯示「連線中...」消失，輸入框可用）
- [ ] 送出測試訊息，AI 有回應（不需 Blender 連線，API 會 graceful 處理）

---

## 7. 已知問題與注意事項

- **Blender 不會自動啟動**：blender-mcp TCP server 必須手動在 Blender 內啟用，launchd 無法自動管理 Blender GUI。
- **Vite dev server 的 HMR**：透過 Tailscale 訪問時，HMR（熱更新）WebSocket 可能連不上，但不影響正常使用，僅影響開發體驗。如需 HMR，改用 `vite preview` 或 build 後服務。
- **CORS**：FastAPI 的 `CORS_ORIGINS` 必須包含 Tailscale URL，plist 已設定，如手動啟動需注意。
- **MHH strip_prefix**：若 MHH 版本不支援 `strip_prefix: false`，需改用 Tailscale serve 直接路由（見腳本中備用方案）。
