# docs — 導航

Blender MCP Studio 的文件樹。**一檔一主題，互相 `[[wikilink]]` 指向。**
接手時不要全部讀完——照「何時該讀」欄位只載入你這一步需要的那幾個檔。

## 導航表

| 檔案 | 主題 | 何時該讀 |
|---|---|---|
| [[tasks/00_INDEX]] | 任務狀態（**進度唯一真相源**） | **每次接手的第一件事** |
| [[00-context]] | 專案目的、範圍、不在範圍 | 第一次接觸這個專案 |
| [[01-architecture]] | 核心不變式、分層、ADR、安全邊界 | 動任何 `src/`、`api/`、`web/src/` 之前 |
| [[10-runtime-ssot]] | **埠、路由、canonical URL、環境變數** | 需要任何埠號或位址時（別處都不寫這些） |
| [[11-mcp-clients]] | MCP 連線契約、九項工具、各 host 設定 | 接 MCP client 或改工具目錄 |
| [[12-deployment]] | LaunchAgent 部署、identity、prefix 契約 | 部署或改服務設定 |
| [[20-conventions]] | 程式碼風格、命名、DI、commit 慣例 | 寫 code 之前 |
| [[30-verification]] | **CI 分層、驗證指令、什麼不算證據** | 宣告「完成」之前 |
| [[LESSONS_LEARNED]] | 失效 class（新的在上） | **除錯動工前**，查同類教訓 |
| [[DEFERRALS]] | 刻意延後的抽象化 + 觸發條件 | 覺得「這裡明明可以再抽象」時 |
| [[KNOWLEDGE]] | 知識放置規則與 5S 預算 | 要新增／搬移文件時 |

## 子目錄

| 目錄 | 內容 | 何時該讀 |
|---|---|---|
| `tasks/` | 進行中與待驗收的任務；`archive/` 放已驗收 | 每次接手 |
| `verification/` | 產出物 contract 流程與各版本視覺驗收 rubric | 產生或驗證機械模型時 |
| `archive/` | 已完成的 campaign 與被取代的文件 | **僅供追溯歷史，不得據以推斷現況** |

## 兩條硬規則

1. **進度只寫在 [[tasks/00_INDEX]]**。任何其他檔案都不記進度、狀態或完成度——
   同一件事寫兩處必然漂移。
2. **事實只寫在它的 SSOT 檔**。埠號與位址只在 [[10-runtime-ssot]]，驗證指令只在
   [[30-verification]]。其他地方要用就指過去。

這兩條由 `tests/unit/core/test_docs_dcc.py` 機器強制，不是靠自律。

## 接手 SOP

1. 讀 [[tasks/00_INDEX]] 找到 ACTIVE 或 AWAITING-ACCEPTANCE 的任務。
2. 讀該任務檔的 hand-off 段，然後 `git log --oneline -5`。
3. 除錯前先查 [[LESSONS_LEARNED]] 有無同 class 教訓。
4. 依上表只載入這一步需要的檔；**不要重新掃描整個 repo** 去重建已完成的工作。
