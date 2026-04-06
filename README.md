# Blender MCP Studio

> 對話驅動 3D 創作平台 — 用自然語言操控 Blender，由 LLM + MCP 驅動。

## 架構概覽

```
[React Web UI]
    ↕ WebSocket /ws/chat
[FastAPI 17823]
    ├── LLMChatPort → OllamaAdapter / AnthropicAdapter / ...
    └── BlenderPort → BlenderMCPAdapter
                          ↓ TCP :9876
                    [Blender + MCP Addon]
                          ↓ bpy
                    [Blender 3D Scene]
```

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

### 啟動 Blender（手動一次）

1. 開啟 Blender（Apple Silicon 版）
2. Edit > Preferences > Add-ons > Install... → 選 `blender_addon/` 目錄的 addon
3. 啟用 **Interface: Blender MCP**
4. 3D View 側欄 N-Panel > **BlenderMCP > Connect**

### 啟動服務

```bash
./scripts/start_services.sh
```

開啟瀏覽器：**http://localhost:19147**

> ⚠️ 本機有其他服務時，使用非常用 port（API=17823，Vite=19147）。
> 修改 `.env` 的 `BLENDER_HOST/PORT`，`vite.config.ts` 的 proxy target 需同步更新。

---

## LLM 設定

`.env` 中調整：

```env
# Ollama 本地/雲端（推薦）
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3-coder:30b          # 本地，需 ~17GB
# OLLAMA_MODEL=qwen3-coder:480b-cloud  # 雲端，零本機記憶體

# Anthropic Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### 新增 LLM 提供商（OCP 擴充點）

1. 實作 `src/core/ports/llm_port.py` 的 `LLMPort`
2. 在 `src/adapters/llm/factory.py` 用 `register_llm_provider()` 注冊：
   ```python
   from src.adapters.llm.factory import register_llm_provider
   register_llm_provider("my_llm", lambda: MyAdapter(...))
   ```
3. 先寫測試再實作 🎯

---

## 執行測試

```bash
conda activate blender-mcp
pytest tests/unit/          # 28 unit tests（不需 Blender）
pytest                      # 含 e2e（需 Blender 運行）
```

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
| [docs/TECH_SPEC.md](docs/TECH_SPEC.md) | 技術規格 |
| [docs/CODING_STYLE.md](docs/CODING_STYLE.md) | 程式設計風格 |
| [docs/PROGRESS.md](docs/PROGRESS.md) | 進度追蹤 |
| [docs/KNOWLEDGE.md](docs/KNOWLEDGE.md) | 踩坑經驗 + 架構決策脈絡 |
