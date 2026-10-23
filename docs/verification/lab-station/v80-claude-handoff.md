# Claude Code 與 MCP 的 v80 共用入口

先讀 [models/lab-station/README.md](../../../models/lab-station/README.md)，使用 [共用ModelSpec](../../../models/lab-station/model-spec.json)。任務進度只讀[索引](../../tasks/00_INDEX.md)。

## Claude Code

主專案為 `/Users/bearmacmini/Blender_MCP_drawer`。在此工作目錄重新讀CLAUDE.md後，使用 `models/lab-station/model-spec.json` 指定的 `models/lab-station-v80`，不要依檔名時間猜版本。正式目錄的69 STL、原生模型、切片檔及證據納入Git；另一份clone必須包含此修訂才會取得。

組裝模型檔名仍含v78，是v80沿用的原幾何；正式切片檔為 `P2S-PLA-69件單盤-已切片-v80.3mf`。原生模型中的44個參考物件不加入列印。

## MCP

1. 呼叫 `list_artifacts`，取 `default_spec` 並要求 `default_available=true`。預設root_dir必須為 `models/lab-station-v80`；缺失時報錯，不退回v78或tmp候選。
2. `describe_model_spec` 的example必須與共用ModelSpec相同。
3. 要重跑驗證時才呼叫 `run_design_pipeline`，將共用JSON放入spec引數；再用 `get_job_status`／`get_run_report`讀新run證據。這會重新切片，不能把舊交付報告當成新run結果。
4. spec v1的`mechanism.suites`留空，不會替保存的模型重驗運動機構。歷史機構證據留在原交付件，不等於新管線已執行機構驗證。

## 保留的原交付件

根目錄 `雙上臂四點梯形-v80-單盤切片檢查/` 及其ZIP，還有v78/v79原件皆保留，不作預設入口。正式版本從原SHA256清單明確列出的檔案逐位元複製；以 `models/lab-station-v80/SHA256.json`核對，任何修改另存修訂。

設定、支撐／brim、用料及尚未實印的限制以正式交付README為準；能存取或重切片通過，都不代表物理黏附／負載已驗證。不得啟動列印。
