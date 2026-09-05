# 12 — 部署：LaunchAgent、identity、plist SSOT

> 回導航 [[README]] · 相關 [[10-runtime-ssot]]、[[30-verification]]、[[01-architecture]]
>
> **埠、路由、canonical URL、prefix 契約、環境變數見 [[10-runtime-ssot]]**；
> 驗證指令與判準見 [[30-verification]]。本檔只講「怎麼部署、誰擁有什麼」。

## 目錄

- [Lifecycle 與擁有權](#lifecycle-與擁有權)
- [Tailnet identity 與 Origin 保護](#tailnet-identity-與-origin-保護)
- [LaunchAgent 安裝](#launchagent-安裝)
- [launchd plist SSOT（八條規則）](#launchd-plist-ssot八條規則)
- [明確的非目標](#明確的非目標)

## Lifecycle 與擁有權

API process 建立**一個** `AppRuntime`。REST、WebSocket 與 FastMCP 拿到的是同一個
`SceneOperationsService` 與 `BlenderPort` 的別名。啟動時開一條 addon 連線，
關閉時關一次。選用的 stdio process 只轉發到 HTTP 端點，**永不**自己連 addon socket。

這件事之所以重要：addon 協定與 scene state 並不是每個 MCP host 各一份。
Codex、Claude、Cursor、VS Code 與 Web UI 必須匯聚到同一個序列化的 socket owner。

## Tailnet identity 與 Origin 保護

Production 設 `REQUIRE_TAILNET_IDENTITY=1`。MacHomeHub 在 Tailnet 認證後注入可信的
`x-mes-identity` header，並移除 client 偽造的值。`/api/health` 是唯一的 HTTP
exemption，好讓 watchdog 探測 process；`/mcp` 受保護。

FastMCP 的嚴格 Host/Origin 保護只允許 loopback 與設定過的 CORS hostname。
這是私有 Tailnet 服務，不是啟用 OAuth 的公開 connector。

## LaunchAgent 安裝

`deploy/launchd/` 下的模板是 SSOT。`~/Library/LaunchAgents/` 裡安裝好的檔案是**衍生狀態**。

```bash
bash deploy/launchd/install.sh all
```

`all` 會安裝三個服務：`api`、`web`、`blender`（也可個別指定其中一個當 target）。

安裝後**驗證實際載入的狀態**，而不是相信 plist 的文字內容——指令見 [[10-runtime-ssot]]
的「驗證載入狀態」一節。

## launchd plist SSOT（八條規則）

任何為本專案安裝到維護者機器上的 macOS `launchd` plist，其來源**必須**在本 repo 版控中。

1. **位置**：模板住在 `deploy/launchd/`，一個服務一份 `*.plist`，與 `install.sh`、
   `uninstall.sh` 並存。
2. **模板內不得有絕對路徑**：使用 `install.sh` 在安裝時代換的佔位符。現有佔位符為
   `__PROJECT_ROOT__`、`__HOME__`、`__CONDA_PYTHON__`、`__NODE_BIN__`。
   只在確有需要時新增，保持表面積小。
3. **install.sh 必須冪等**：安裝前用 `plutil -lint` 檢查算繪後的 plist；先
   `launchctl bootout` 既有服務並吞掉良性錯誤（service not loaded、EIO、ENOENT）；
   原子式替換 `~/Library/LaunchAgents/` 裡的檔案；等舊 label 卸載完成後，
   以有上限的重試執行 `launchctl bootstrap`，再 `enable` + `kickstart -k` 新實例。
4. **uninstall.sh 只歸檔、不刪除**：把已安裝的 plist 移成
   `<name>.plist.deprecated.YYYYMMDD`（路徑已存在則加計數後綴），永遠保留一步回退。
5. **Production Web 先建置**：安裝 `web` 或 `all` 必須先跑前端 build 再 bootstrap。
   HMR 只屬於前景開發。
6. **相依服務依序就緒**：安裝 `all` 必須先 condition-wait 等到 Blender addon 的
   listener 就緒，才啟動 API。LaunchAgent 的 `running` 狀態**本身不是**就緒訊號。
7. **零漂移**：已安裝 plist 的 `plutil -convert xml1 -o -` 輸出與算繪後模板的
   diff 必須是乾淨的。這是契約。
8. **不得繞過 install.sh**：直接編輯 `~/Library/LaunchAgents/<label>.plist` 是禁止的——
   它會靜默地重新引入漂移。永遠改模板，然後重跑 `install.sh`。

用法見 [`../deploy/launchd/README.md`](../deploy/launchd/README.md)。

> **踩過的坑**：改了 plist 的 env 之後用 `kickstart` 重啟**不會生效**——kickstart
> 不 reload，載入的是另一份拷貝。另外 `launchctl bootout` 返回也不等於 job 已完全
> 離開 registry。詳見 [[LESSONS_LEARNED]]。

## 明確的非目標

- 不做公開網際網路的多使用者散布。
- 不提供 legacy SSE 端點。
- 不做 client 名稱專屬的行為。
- 不開放公開的任意 `execute_code` 工具。
- 不為 stdio 或某個特定 MCP host 開第二條 Blender 連線。
