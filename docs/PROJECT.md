# 專案目的（Project Purpose）

## 願景

打造一個「對話驅動 3D 創作」的可擴充平台。使用者透過自然語言與 AI 對話，AI 自動操控 Blender 完成 3D 建模、場景配置、材質設定等創作任務。

## 核心目標

1. **Phase 1 — 對話建模**：輸入文字描述 → LLM 理解意圖 → 透過 MCP 操控 Blender 建模
2. **Phase 2 — 場景生成**：複雜場景自動組合（物件、燈光、材質、相機）
3. **Phase 3 — 動畫創作**：互動式角色與動畫驅動
4. **Phase 4 — 程序化藝術**：Generative Art，數據驅動場景

## 設計哲學

> **換腳本 = 換目標**

工作流程由 YAML 腳本定義，核心引擎不變，只需更換腳本即可切換任意創作目標。這確保系統永遠保持彈性與可擴充性。

## 使用者體驗

1. 開啟 Web UI（瀏覽器）
2. 在對話框輸入創作描述（中英文皆可）
3. 系統即時回應操作進度與結果
4. Blender 視窗同步呈現 3D 成果

## 技術邊界（In Scope）

- Web UI 對話介面（React + TypeScript）
- FastAPI 後端（WebSocket 即時通訊）
- 多 LLM 支援（Claude / OpenAI / DeepSeek / Ollama）
- Blender MCP 橋接（ahujasid/blender-mcp）
- 腳本驅動 Workflow 引擎

## 不在範圍（Out of Scope）

- Blender 渲染農場
- 3D 模型資料庫管理
- 多人協作
- 商業授權管理
