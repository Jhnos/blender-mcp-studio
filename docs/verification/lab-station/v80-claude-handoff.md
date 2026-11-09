# Claude Code 與 MCP 的工作站交付契約

版本由應用服務選擇，不由 Claude Code、文件入口或檔名選擇。宣告與規則見 [工作站](../../../models/lab-station/README.md)，任務結果只讀 [索引](../../tasks/00_INDEX.md)。

## 使用

1. Claude Code 連接專案的同一個正式 MCP 服務，設定方式見 [客戶端](../../11-mcp-clients.md)。它不是另一份 Blender 或另一套模型目錄。
2. 要驗證目前模型，呼叫 `run_design_pipeline`，不帶 `spec`。服務從唯一宣告解析輸入，保存新工作的 `spec.json`；再用 `get_job_status`／`get_run_report` 讀新證據。
3. `list_artifacts` 與 `describe_model_spec` 由同一個應用目錄提供目前選擇；缺失或錯誤必須回報，不改用歷史版本。只有明確要求歷史／自訂模型時才提供 spec。
4. 核心 MCP、模型與切片的腳本和判準只有 [驗證 SSOT](../../30-verification.md) 一份；所有客戶端共用，無 Claude 專用驗證管線。

## 原件與證據

原交付件、歷史版本及 ZIP 均保留。舊版 ModelSpec 副本封存於 `docs/archive/` 作追溯，不作目前選擇。正式交付的 SHA256 清單可獨立核對；舊模型檔名保留幾何來源版本，不能用它反推目前切片版本。

每次管線都建立新 run，不覆寫原交付證據。spec v1 的機構階段是 `not_applicable`；能讀取／重切片通過，不等於物理黏附與負載已驗證。不得啟動列印。
