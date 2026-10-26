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
scripts/ci.sh --real   # 核心 T1/T2/T3：模型、REST/MCP、機構、切片與包；不呼叫 Ollama
scripts/ci.sh --chat   # 獨立 T4 對話：Ollama 前置＋WS/REST＋Blender oracle，不重跑 T1/T2/T3
scripts/ci.sh --all    # 先核心、再對話；共用 Blender，不能並行
# 只重驗目前交付件：同一個核心閘門，不指定版本
$HOME/miniconda3/envs/blender-mcp/bin/python scripts/verify/design_pipeline_verify_real.py
```

核心與對話各自回報所選範圍；未選對話不代表對話通過。明確要求真機套件但 addon 未就緒時回傳失敗。對話前置探測會保留 HTTP 狀態／連線錯誤；超過預算只表示未取得成功回應，不能推定 Ollama 離線或飽和。

單次 `claude -p` 執行驗證時，使用原生環境選項 `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`，讓 Bash 在前景等待到終態；依驗證預算設定足夠的工具 timeout。父 CLI 回覆成功不等於子程序通過，必須保留實際命令、終態輸出及正反例報告。若父程序中止，先確認後端工作終態才可重跑。此選項僅控制 CLI 等待方式，見 [Claude Code 官方環境選項](https://code.claude.com/docs/en/env-vars)。

T1/T2仍彙整全部失敗；只要已有硬失敗，核心／完整模式在接觸Blender前終止，不能帶著已失敗的前置啟動T3。獨立對話模式維持獨立範圍。

真機階段任何 hard gate 失敗後立即停止，避免後續操作污染共享場景。逾時不代表 Blender 已停止；重跑前必須確認先前工作已排空。靜態與單元階段仍彙整失敗。

### T3 裡的產出物閘門（2026-09-08 起）

| 閘門 | 讀什麼 | 首跑秒數（Mac，2026-09-08） |
|---|---|---|
| hand-v3 contract | 在常駐 Blender 重建整手，20 項證據 | 7 |
| hand-v3 finger contract | 同一場景（`--skip-generate`），14 項 | 1 |
| regenerated package matches shipped | `tmp/<slug>/*.stl` 對 `models/<slug>/manifest.json`（hand-v3、hand-compact）：面數在規劃推導的**碎片預算**內（每個布林零件 ±2；exact solver 輸出順序不定）、尺寸 ±0.1，**不比 sha** | 0.2 |
| inset hinge ×3 | 生成、同場景 pins、讀取式 probe | 4 |
| biaxial hinge ×5 | 生成、同場景 PIP 與 split、兩份讀取式 probe | 6 |
| hollow side hinge | 生成 | 3 |
| octopus hand V1 ×2 | 生成、同場景 tips | 20 |
| octopus hand V2 ×2 | 生成、同場景 tips | 26 |
| generation delivery path | **清空** `tmp/hand-compact/`，走公開 REST endpoint 重建，比 API 回報的數字與磁碟上的位元組，再對 `models/hand-compact/manifest.json` 走同一份碎片預算 | 10 |
| build determinism within budget | 同一零件在常駐 Blender 重建 3 次，判準是**完成品的面數差不超過碎片預算**——頂點順序幾乎每一步都不同，那是 exact solver 的性質不是缺陷，拿它當紅燈的閘門會永遠紅 | 18 |
| design pipeline (current selection) | `scripts/verify/design_pipeline_verify_real.py scripts/verify/contracts/design_pipeline_current.json`：合約只宣告 `selection: current`；經公開 MCP 取得應用目錄的選定 ModelSpec，先拒絕不可用或 discovery／example 不一致，再提交驗證，輪詢到終態（預算＝切片逾時＋300 s），逐階段驗證據：import 69 件且 `import.json` 列 69 個 STL＋1 個 3MF（含 sha256）、geometry 69 件 0 失敗、mechanism `not_applicable`、print 1 盤、manifest 含合約列出的檔案與 AGPL 切片器條目、所有文件無主機路徑；再以截斷表頭的 STL 副本做反例，geometry 必須 FAILED 並點名該檔。交付物根目錄取 `config/tools.yaml` 的 `artifact_roots[0]`（`--artifact-root` 可覆寫）。前置（交付物、切片器、端點）缺一即 FAIL 附原因，不 SKIP；要在部署後跑 | 真切片約 3 分鐘 |

順序是硬的：手指契約重用手契約生成的場景；差分讀那次生成匯出的 STL；
交付路徑閘門**最後**跑，因為它會清空 `tmp/hand-compact/` 再自己重建——排在前面就會抽掉別人的輸入。三條由
`test_real_ci_gates_the_hand_contracts` 釘在 `ci.sh` 裡；`test_real_ci_runs_every_contract` 釘住 `contracts/` 下
**每一個**檔案都在 `--real`、走對的 checker、且場景重用有先生成（[[DEFERRALS]] D-004，2026-09-09 `done`）。
交付路徑那一條由 `test_real_ci_gates_the_hand_contracts` 一併釘住順序。整個 T3 約 85 s。

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
| `test_document_links.py` | 全部文件（含archive）的本地Markdown連結失效；搬移／封存須與DCC一起跑，僅修正相對指向，不重寫歷史事實 |
| `test_script_primitive_ssot.py` | 產生器重新定義共用 primitive |
| `test_contract_builder.py` | 簽入的手契約 ≠ 由規劃生成的契約(契約是生成產物,手改即紅) |
| `test_generator_imports.py` | 產生器可達的模組沒進契約 `reload_modules`(常駐 Blender 跑舊碼還綠) |
| `test_architecture_ssot.py::test_domain_and_planning_never_import_bpy` | 域層或規劃層匯入 bpy/mathutils |
| `test_file_budgets.py` | `api/`、`src/`、`scripts/`（`archive/` 除外）出現 god-file（400 行硬上限，380 行預警；`scripts/` 於 2026-09-09 納入） |
| `errorMessage.gate.test.ts` | 前端手抄 `instanceof Error`（用真的 eslint 驗證規則有生效） |

**每一個都附 should-fire 與 should-pass fixture。** 只有前者的閘門，
與「永遠報錯」在外觀上完全相同。

## 驗證矩陣

| Tier | 真實元件 | 被替換的邊界 | 這一層能宣稱什麼 |
|---|---|---|---|
| Unit | Domain、service、tool registry | Fake Blender port | validation、routing、error 語意 |
| ASGI e2e | FastAPI、FastMCP framing、middleware | Fake Blender port | mount、identity、Origin、protocol、client 中立性 |
| Headless UI | React／MDR／Vite 測試 | Mock HTTP backend | 前端行為 |
| Core real machine | 對外 Tailnet MCP + API + Blender + 切片器（不使用即時 LLM） | 無 | nonce 變異、列印夾具、單次 Undo 還原整批，並以獨立 socket oracle 佐證 |

對話 T4 另外透過 Ollama、公開 WS/REST 與獨立 Blender oracle 驗證自然語言建立物件、讀回與清理。核心 CI 中的 LLM 單元／ASGI 測試使用 fake，仍保留。

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
