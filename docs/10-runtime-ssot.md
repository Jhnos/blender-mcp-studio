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

Socket 一般回覆期限為 30 秒；AppRuntime 僅為 registry 推導且完整相符的生成程式注入 `GENERATOR_TIMEOUT_S`（900 秒，來源 `src/adapters/generation/authorized_code.py`）。REST／對話共用此設定與同一序列化 socket。逾時回報傳輸失敗與完成未知，丟棄連線，不重播變更。驗證用 HTTP 呼叫保留額外 30 秒回應餘裕。

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
BAMBU_STUDIO_BIN=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
ORCASLICER_BIN=/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer
DESIGN_RUNS_DIR=data/runs
DESIGN_JOBS_DB=data/jobs.db
ARTIFACT_ROOTS=.:models
BLENDER_MCP_PUBLIC_BASE_URL=
```

`BAMBU_STUDIO_BIN`、`ORCASLICER_BIN`、`DESIGN_RUNS_DIR`、`DESIGN_JOBS_DB`（設計管線工作紀錄的 SQLite 檔）、
`ARTIFACT_ROOTS`（以 `os.pathsep` 分隔）覆寫 `config/tools.yaml` 的預設值
（`bambu_studio_bin`、`orcaslicer_bin`、`design_runs_dir`、`design_jobs_db`、`artifact_roots`）；相對路徑以 repo 根目錄解析。

**印表機與切片器目錄**：`config/slicers.yaml` 每個切片器一筆（id、`binary_key` 指向 `tools.yaml` 的鍵、
profiles 子目錄、授權、錯誤碼、安裝提示）；`config/printers/<vendor>/<id>.yaml` 每台印表機一個檔
（切片器、設定檔名稱、材料、床板、覆寫檔）。由 `load_printer_catalog()` 載入；id 重複或指向不存在的
切片器會載入失敗並指名檔案。程式碼裡沒有預設印表機，`printer` 一律必填。

**切片設定檔**：兩個切片器（Bambu Studio 切 Bambu、OrcaSlicer 切 Creality）都由同一個
`OrcaFamilyCli` 驅動，廠商設定檔都不放在 repo，而是每次切片時從各自已安裝的 app bundle 讀取：
`<App>.app/` 下 `slicers.yaml` 的 `profiles_subdir`，其中 `<App>.app` 由該切片器的二進位
（`BAMBU_STUDIO_BIN`／`ORCASLICER_BIN`）往上找到的 `.app` 推得（與讀 `Info.plist` 版本同一方法）。
要讀哪三個葉設定檔（machine、依層高的 process、依材料的 filament）寫在各印表機的
`config/printers/<vendor>/<id>.yaml`，依 JSON 的 `name` 欄位查找（不是檔名）；`inherits` 鏈先父後子攤平
（子鍵覆蓋，`include` 依序併入、移除，`inherits` 清空），語意同 v80 的 `prepare_profiles.py`
（`src/adapters/slicing/bundle_profiles.py`）。疊加順序：bundle 設定檔 → 該印表機 `overrides`
指名的覆寫檔（`config/slicer-profiles/` 下，我們自己的資料；目前只有 P2S 的
`p2s-pla-overrides.json`，Creality 沒有；檔案不存在時目錄載入就失敗）→ 由工作推導的鍵
（`slice_job.job_process_keys`，每個廠商同一套）：`layer_height`；單一材料所以關掉 prime tower；
有支撐時 `normal(auto)` + `snug`；brim 寬度與 `brim_type` 都來自工作（`brim_mm` > 0 為
`outer_only`，否則 `no_brim`）。啟動切片器之前先做 plate-fit 預檢（`plate_extent.plate_fit`）：
3MF 的排版超出 machine 設定檔的可列印區域，或量不出來，就直接 failed 並說明，不啟動切片器。
app 內沒有 profiles 目錄或設定檔讀不到時，切片結果是 failed，訊息與「切片器不可用」同一類；
`list_printers` 把這種印表機列在 `unavailable`，`describe_model_spec` 的 enum 也不列它。

**刀路檢查**：`slicers.yaml` 每個切片器必填 `toolpath_inspection: true|false`（只收 YAML 布林）。
為 true 時，切片成功後在同一個 adapter 內讀新 3MF 的 plate G-code，寫 `print/extrusion.json`，
檢查不過就讓這次切片 failed；每次切片前先刪舊的 `extrusion.json`；工作鍵另加
`enable_arc_fitting: "0"`；port 期限＝切片指令逾時＋`TOOLPATH_INSPECTION_TIMEOUT_S`（子行程本身仍只拿指令逾時）。
目前 Bambu Studio 為 true、OrcaSlicer 為 false（它的 G-code 是另一套註解格式，原因與實測數字在
`config/slicers.yaml` 註解）。切片器以輸出目錄為工作目錄、所有路徑先 resolve，副產物不會落在 job 外。

`BLENDER_MCP_PUBLIC_BASE_URL` 是這個部署對外的公開基底網址（例如 `https://<host>/blender`；
留空則由 `tailscale status --self --json` 取得）。它不改變 API 自己監聽的位址，只用來推導：
API 的 CORS 預設 origin（`CORS_ORIGINS` 未設時）、驗證腳本與 stdio proxy 連線的 MCP／REST URL、
Tailscale Serve 註冊的主機名，以及 api plist 的 `__PUBLIC_ORIGIN__`。同一個解析器（`src/infrastructure/public_base_url.py`）
供 API 的 CORS 預設（`CORS_ORIGINS` 未設時）、驗證腳本、stdio proxy、`tailscale-serve-register.sh`
與 `deploy/launchd/install.sh`（填 api plist 的 `__PUBLIC_ORIGIN__`，由
`BLENDER_MCP_PUBLIC_BASE_URL` 或 tailscale 推導）使用；程式碼與部署來源不得寫死主機名或家目錄
（`tests/unit/core/test_no_hardcoded_hosts.py` 擋）。`BLENDER_BIN` 指定 Blender 執行檔
（`scripts/run_blender.sh`、`install.sh`）。

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
