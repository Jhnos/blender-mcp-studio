# Blender MCP Studio

> 對話驅動 3D 創作平台；Web UI 與任何標準 MCP host 共用同一 Blender runtime。

## 架構概覽

```text
Web REST/WS ─┐
HTTP MCP ────┼→ FastAPI :19505 → one AppRuntime → BlenderMCPAdapter → TCP :9876
stdio proxy ─┘                                                     → Blender
```

可互動、可供 AI 讀取且有 AST 防漂移 gate 的架構 SSOT：
[docs/architecture.html](docs/architecture.html)。

**設計原則**：Hexagonal Architecture · TDD · SOLID · DDD · 全解耦合

## 快速開始

### 環境需求

- Mac M4 Apple Silicon（測試環境，其他平台應可執行）
- [Blender 5.1 Apple Silicon 版](https://www.blender.org/download/)
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)（osx-arm64）
- Node.js 20 LTS+
- [Ollama](https://ollama.com/)（本地 LLM 推薦）

### 安裝

```bash
# 1. 複製環境變數範本並填入設定
cp .env.example .env
vim .env   # 設定 LLM_PROVIDER, OLLAMA_MODEL 等

# 2. 建立 conda 環境
conda env create -f environment.yml
conda activate blender-mcp

# 3. 安裝前端依賴
cd web && npm install && cd ..
```

### 啟動 Blender（launchd 管理，開機自啟）

Blender + addon（socket 9876）是 launchd 服務 `com.blender-mcp.blender`，登入時自動啟動、
關掉不會被強制拉回（GUI 友善）。安裝／重啟：

```bash
bash deploy/launchd/install.sh blender     # 或 all（blender + api + web）
launchctl kickstart -k gui/$(id -u)/com.blender-mcp.blender   # 手動重啟
```

就緒判別（**`/api/health` 的 `status:ok` 不代表 Blender 在線**，要看 `blender` 欄）：

```bash
lsof -iTCP:9876 -sTCP:LISTEN          # addon socket
curl -s localhost:19505/api/health    # → {"status":"ok","blender":"connected"}
```

> 首次需先安裝 addon 到 Blender：`bash scripts/install_blender_addon.sh`。
> 手動前景啟動（除錯用）：`bash scripts/run_blender.sh`。

### 啟動正式服務

```bash
./scripts/start_services.sh  # build + install/restart three LaunchAgents + verify listeners
```

開啟瀏覽器：**http://localhost:19504/blender/**

正式 Web 服務使用 production build + `vite preview`，不載入 HMR client。前景開發另用：

```bash
bash scripts/run_dev.sh  # API 19505 + Vite dev 5173；埠已占用時會 fail loud
```

> 修改服務埠時，先改 `~/MacHomeHub/config/services.yaml` 與 `deploy/launchd/*.plist`，
> 再同步 Vite proxy；不要直接編輯已安裝的 LaunchAgent。

### 連接 MCP client

支援 MCP Streamable HTTP 的 Codex、Claude Code、Cursor、VS Code 或其他 host
可直接使用：

```text
https://bearmacminimac-mini.tail56c751.ts.net/blender/mcp
```

只支援 stdio 的 host 使用：

```bash
~/miniconda3/envs/blender-mcp/bin/python scripts/run_mcp_stdio_proxy.py
```

完整 client 設定、九項工具與安全邊界見
[docs/MCP_CLIENTS.md](docs/MCP_CLIENTS.md)。MCP server 不辨識或特判 host 名稱。

### 匯出 3D 列印模型

WebUI 預覽區的「準備切片」可匯出：

| 用途 | 格式 | 單位契約 |
|---|---|---|
| 切片／3D 列印 | STL、OBJ、PLY | Blender 公尺自動轉為毫米，可匯入 Cura、PrusaSlicer、OrcaSlicer |
| DCC 交換／網頁預覽 | FBX、GLB | 保留 Blender 場景單位 |

點「準備切片」會先執行唯讀健檢，顯示毫米尺寸、三角面數、估算體積、表面積，以及非流形、
退化面、交疊、薄壁與懸空等問題。`ready` 可直接下載；`review` 需明確確認；沒有可分析網格的
`invalid` 會停用下載。修改門檻或場景後只標記「需要重新檢查」，不持續占用 Blender socket。

匯出面板支援「僅選取物件」、「套用修改器」與「三角化網格」。HTTP client 可呼叫
`POST /api/print-readiness` 與 `POST /api/export`；兩者由 application service 與 Blender adapter
負責，WebUI 不依賴 Blender operator 細節，也不會自動修補使用者模型。

參數化機構模型可使用[共用產物驗證流程](docs/verification/generated-artifacts.md)：一份 JSON
契約串接模型生成、STL 匯出、Blender 幾何 oracle 與公開 MCP 健檢，不需為每個版本重寫驗證器。

---

## LLM 設定

**模型是 `config/llm_providers.yaml`（SSOT）**；`.env` 只放機器專屬覆寫與金鑰。

```yaml
# config/llm_providers.yaml
providers:
  ollama:
    model: hf.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive:Q4_K_M   # 本地，預設
    # 雲端替代（需 ollama signin，零本機記憶體）。實測有效 2026-07-15：
    #   gemma4:cloud（32.7B / 256K）、gemma4:31b-cloud
```

```env
# .env — provider 選擇與金鑰
LLM_PROVIDER=ollama          # 預設；可選 anthropic / openai / deepseek
OLLAMA_BASE_URL=http://localhost:11434
# ANTHROPIC_API_KEY=sk-ant-...
```

> ⚠️ **雲端 tag 會被 Ollama 退役**（`qwen3-coder:480b-cloud` 於 2026-07-15 退役，症狀是 chat 回
> 「LLM chat failed」）。換雲端模型前先實測：
> `curl -s localhost:11434/api/chat -d '{"model":"gemma4:cloud","messages":[{"role":"user","content":"hi"}],"stream":false}'`

### 新增 LLM 提供商（OCP 擴充點）

1. 實作 `src/core/ports/llm_port.py` 的 `LLMPort`
2. 在 `src/adapters/llm/factory.py` 用 `register_llm_provider()` 注冊：
   ```python
   from src.adapters.llm.factory import register_llm_provider
   register_llm_provider("my_llm", lambda: MyAdapter(...))
   ```
3. 先寫測試再實作 🎯

---

## 測試與本地 CI

本專案用**本地 CI**，不用 GitHub Actions：真正會壞的東西需要真 Blender（socket 9876）、
真 Ollama 與 MHH 管理的服務——hosted runner 只能 lint 與 unit test，證不了管線是否真的在作用。

```bash
./scripts/ci.sh          # T1 靜態 + T2 單元（含 headless dummy run）。無副作用
./scripts/ci.sh --real   # 加跑 T3 真機 MCP 驗證（需 Blender；會建/刪 verify_* 物件）
```

| Tier | 內容 | 硬 gate |
|---|---|---|
| T1 靜態 | web build、eslint、ruff、strict mypy、container narrowing | ✅ |
| T2 單元 | pytest unit/e2e（含真 MCP framing + fake Blender）；vitest dummy run | ✅ |
| T3 真機 | REST/MCP nonce mutation + 列印健檢 fixtures；addon socket 獨立 oracle | ✅（Blender 沒開＝顯式 SKIP，不當 pass）|

**pre-push hook**（擋掉壞掉的 push）：

```bash
git config core.hooksPath .githooks    # 啟用（每個 clone 各做一次）
# 緊急繞過：git push --no-verify
```

個別執行：

```bash
pytest tests/unit/                     # python 單元
cd web && npx vitest run               # 前端單元 + dummy run
python scripts/verify/mcp_verify_chat.py   # chat 端對端（需 Blender + LLM）
```

目前的前端 dummy-run 規則見
[`docs/verification/frontend-redesign/dummy-run-plan.md`](docs/verification/frontend-redesign/dummy-run-plan.md)；
已完成的 MCP 鑑別性驗證計畫保存在 campaign archive。

---

## 新增 Workflow

1. 在 `config/workflows/` 新增 YAML 定義
2. 在 `src/workflows/scripts/` 新增 Python 腳本
3. `WorkflowEngine("my_workflow").build_llm_adapter()` 取得對應 LLM

---

## 文件

| 文件 | 說明 |
|---|---|
| [docs/PROJECT.md](docs/PROJECT.md) | 專案目的與願景 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 架構決策（Hexagonal Architecture）|
| [docs/architecture.html](docs/architecture.html) | 人類視覺 + AI 結構化欄位共用的架構 SSOT |
| [docs/MCP_CLIENTS.md](docs/MCP_CLIENTS.md) | Codex/Claude/Cursor/VS Code/stdio 設定與安全契約 |
| [docs/tasks/00_INDEX.md](docs/tasks/00_INDEX.md) | 唯一任務狀態與跨對話接手入口 |
| [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md) | 現行知識導航與 5S 放置規則 |
| [docs/archive/2026-07-client-neutral-mcp/](docs/archive/2026-07-client-neutral-mcp/) | 已完成 MCP／列印健檢／批次前端 campaign 證據 |
| [docs/TECH_SPEC.md](docs/TECH_SPEC.md) | 技術規格 |
| [docs/CODING_STYLE.md](docs/CODING_STYLE.md) | 程式設計風格 |
