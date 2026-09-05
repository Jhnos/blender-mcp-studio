# 30 — 驗證 SSOT：分層、指令、判準

> 回導航 [[README]] · 相關 [[10-runtime-ssot]]、[[12-deployment]]、[[LESSONS_LEARNED]]

**這個檔是「怎麼證明它真的能動」的唯一真相源。** 其他文件要提驗證指令時指回這裡。

## 目錄

- [唯一 CI 入口](#唯一-ci-入口)
- [驗證矩陣](#驗證矩陣)
- [不算證據的東西](#不算證據的東西)
- [Troubleshooting](#troubleshooting)

## 唯一 CI 入口

```bash
scripts/ci.sh          # T1 static + T2 unit/headless dummy run；commit 前必跑
scripts/ci.sh --real   # T3 REST/MCP/readiness/batch；需要 Blender addon 已就緒
```

本專案**沒有** GitHub Actions；`scripts/ci.sh` 是唯一 CI。新行為一律從一個
**有鑑別力的失敗測試**開始——測試要能在功能未實作時變紅，而不是靠實作細節通過。

### 閘門涵蓋範圍（每個都要能說出它讀了哪些樹）

| 閘門 | 涵蓋 | 排除 |
|---|---|---|
| ruff check／format | `src tests api scripts` | `scripts/archive` |
| mypy（strict） | `src api scripts` | `scripts/archive` |
| container-narrowing | `src api scripts` | `scripts/archive`、SSOT 模組自身 |
| pytest | `tests/unit tests/e2e` | — |
| eslint／tsc／vitest | `web/src` | `web/dist` |

排除清單三者一致是刻意的：**範圍不一致的閘門會產生沒人有權處理的發現**。
`scripts/` 在 2026-09-05 之前完全不在任何 Python 閘門的根目錄裡——包括
`check_container_narrowing.py` 自己的原始碼。

### 結構性閘門（不是 lint，是架構規則）

| 檔案 | 它擋什麼 |
|---|---|
| `test_rest_error_ssot.py` | router 自行把 domain error 譯成 HTTP status；並凍結 endpoint 自有的守衛清單 |
| `test_router_composition.py` | router 組裝 use case、內嵌 `bpy` 原始碼或觸碰 `execute_code` |
| `test_docs_dcc.py` | 斷掉的 wikilink、導航孤兒、埠號寫在 SSOT 之外 |
| `test_script_primitive_ssot.py` | 產生器重新定義共用 primitive |
| `test_file_budgets.py` | `api/`、`src/` 出現 god-file（400 行硬上限，380 行預警） |
| `errorMessage.gate.test.ts` | 前端手抄 `instanceof Error`（用真的 eslint 驗證規則有生效） |

**每一個都附 should-fire 與 should-pass fixture。** 只有前者的閘門，
與「永遠報錯」在外觀上完全相同。

## 驗證矩陣

| Tier | 真實元件 | 被替換的邊界 | 這一層能宣稱什麼 |
|---|---|---|---|
| Unit | Domain、service、tool registry | Fake Blender port | validation、routing、error 語意 |
| ASGI e2e | FastAPI、FastMCP framing、middleware | Fake Blender port | mount、identity、Origin、protocol、client 中立性 |
| Headless UI | React／MDR／Vite 測試 | Mock HTTP backend | 前端行為 |
| Real machine | 對外 Tailnet MCP + API + Blender | 無 | nonce 變異、列印夾具、單次 Undo 還原整批，並以獨立 socket oracle 佐證 |

Real tier 只變異帶 nonce 前綴的驗證物件，並在 `finally` 移除。它同時經 REST 與 MCP
下指令，再獨立地從 Blender addon socket 讀真實狀態當 oracle（埠見 [[10-runtime-ssot]]）。

## 不算證據的東西

這一節是判準，不是建議。以下任何一項都**不能**作為驗收證據：

| 看似通過 | 為何不算 |
|---|---|
| Real tier 印出 `SKIP` | addon 離線時會 SKIP；跳過不等於通過 |
| 對 MCP URL 發 GET 得到 HTTP 200 | Vite 的 HTML fallback 也回 200。必須跑真的 initialize + `tools/list` |
| `curl localhost` 通過 | 使用者走的是對外 FQDN；localhost 通過不代表對外可用（見 [[10-runtime-ssot]]） |
| `/api/health` 回 `status: ok` | 只證明 API process 活著。要看 `blender` 欄位是否 `connected` |
| LaunchAgent 狀態是 `running` | process 起來不等於它的相依服務已 ready |
| 型別檢查器全綠 | `Any` 是靜音區；零錯誤可能等於零檢查（見 `LESSONS_LEARNED.md:129`） |
| 某個 gate 綠燈 | 綠勾只涵蓋它實際跑到的子集；沒跑到的會靜默腐爛（`LESSONS_LEARNED.md:101`） |

最後兩條是本專案反覆踩到的類別。設計任何新閘門時，先問「它宣稱涵蓋的範圍，
和它實際比對的東西，是不是同一個集合」。

## Troubleshooting

| 症狀 | 檢查 |
|---|---|
| MCP 回 401 | 確認請求走已認證的 Tailnet／MHH，而非匿名 Funnel |
| MCP 回 403 | 比對請求的 Host/Origin 與 `CORS_ORIGINS`、允許的 host |
| MCP initialize 失敗 | 檢查回應 framing 與 `MCP-Protocol-Version`；不要用瀏覽器 GET |
| Health 顯示 `disconnected` | 啟動 Blender 與 addon（埠見 [[10-runtime-ssot]]），檢查 API 警告 log |
| Web 正常但 MCP URL 顯示 HTML | 確認 `/blender/mcp` 的 Vite proxy 排在 fallback route 之前 |
| stdio host 起得來但沒有工具 | 用絕對路徑跑 proxy，並確認 Tailnet 可達 |

## 產出物驗證

機械產出物（`.blend`／`.stl`／算圖）有自己的 contract 流程，見
[[verification/generated-artifacts]]。各版本的視覺驗收 rubric 也在 `verification/` 下。
