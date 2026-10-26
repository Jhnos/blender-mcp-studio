# 工作站目前模型

唯一版本宣告：[model-spec.json](model-spec.json)。應用服務讀取並驗證這份資料；REST、MCP、範例與驗證腳本都使用服務解析結果，不各存一份版本設定。

- 驗證目前模型：MCP 呼叫 `run_design_pipeline` 不帶 `spec`；REST 提交空物件。使用者與客戶端不必記版本名稱或模型路徑。
- 查詢：`list_artifacts.default_spec` 與 `describe_model_spec.example` 由同一個應用目錄提供；REST 提供相同查詢。
- 宣告缺失或格式錯誤時明確失敗；不猜最新檔案、不退回歷史版本。`default_available=false` 表示選定交付件不可用，不能當成切換版本的理由。
- 只有刻意驗證歷史／自訂模型時才提供明確 `spec`。每次工作保存當次解析的 `spec.json`，不能拿舊報告當新結果。
- 版本升級只修改本宣告並發布對應交付件；程式與驗證合約不寫版本。新舊原模型均保留，修改另存新修訂。

目前交付資料及其限制以宣告指向的目錄 README、`SHA256.json` 為準。原生模型檔名可能保留幾何來源版本；檔名不是目前版本的判定依據。spec v1 的匯入管線不重驗保存模型的機構運動。

發布目錄內的 README、日誌與雜湊是當時的交付快照；其中「尚未整合／驗證」等敘述保留當時語境，不代表目前服務狀態。目前整合與驗證結果只讀 [任務索引](../../docs/tasks/00_INDEX.md)，不改寫原交付證據。

連線見 [MCP 客戶端](../../docs/11-mcp-clients.md)，執行與判準見 [驗證 SSOT](../../docs/30-verification.md)。
