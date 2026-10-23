# 工作站共用入口

選定交付規格：[model-spec.json](model-spec.json)。Claude Code及MCP使用這份選擇；MCP的`describe_model_spec.example`與`list_artifacts.default_spec`由相同規格內容維持一致，測試禁止漂移。

模型與證據：[v80正式交付目錄](../lab-station-v80/README.md)。其中組裝原模型檔名包含v78，因v80沿用其幾何；已切片工作檔是v80，不能據原模型檔名選回舊切片。

1. 先讀本規格；MCP使用`list_artifacts`的`default_spec`，並要求`default_available=true`。
2. 選定交付件若缺失或校驗失敗，明確報錯，不依目錄順序／時間猜版本、不退回v78，也不選tmp失敗候選。
3. 重驗需要明確呼叫`run_design_pipeline`，會建立新run；不要把原交付證據寫成新run的證據。spec v1不重驗機構運動。
4. 原交付件及根目錄舊版本保留；修改另存新修訂，不覆寫。

正式目錄由原交付manifest明確列出的檔案逐位元複製，含69 STL、原生113模型、已切片3MF、首層圖與驗證資料。`SHA256.json`可獨立核對；本目錄與版本目錄納Git，避免其他clone只有程式碼卻沒有模型。製造與實印限制以交付README為準。
