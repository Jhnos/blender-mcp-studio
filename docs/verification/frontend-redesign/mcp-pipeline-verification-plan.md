# MCP→Blender 管線 鑑別性驗證計畫（T4 真機）

> 設計依據：`verification-plan-design`（FICE 迴圈 + DFMEA + 空母體防呆）＋ `academic-rigor`（鑑別性證據、不 overclaim、雙手交叉）＋ `dummy-run-ladder`（軸 M/軸 Q 分離、proxy 不當真實）。
> 狀態：**設計中**，通道細節待管線測繪回填（標 `⟨待管線圖⟩`）。

## 0. 為什麼需要這份計畫（問題陳述）

T3 dummy-run 用 MSW fixture 讓前端畫出一個 cube——這**只證了前端機制（軸 M）**。一個方塊證明不了 MCP→Blender 管線在作用：**一個壞掉、斷線、甚至完全假的後端，也能讓前端畫出一個方塊**。

本計畫的唯一目的：設計**只有真 MCP→Blender 管線在跑才可能通過**的斷言，並證明**重構後的前端忠實反映真實 Blender 狀態**。

## 1. 第一性原理：鑑別性（Falsifiability）

每個測試在納入前必須通過這一問：

> **「如果 MCP 沒在作用（stub / 快取 / 假資料 / Blender 斷線），這個測試還會過嗎？」**
> 會過 → 廢測試，剔除（那個 cube 就是廢測試）。
> 只有真管線在跑才會過 → 保留。

三個讓測試有鑑別力的機制（缺一不可）：

1. **Nonce（隨機唯一值）**：每次跑用隨機生成的物件名/座標/參數。快取或 fixture 不可能預先知道這輪的 nonce → 破解「回傳寫死資料」的假後端。
2. **獨立 Oracle（第二證人）**：用一條**繞過前端自己 API 資料路徑**的通道去讀 Blender 真值，與前端顯示交叉比對。**共同證人＝共模失明**：若唯一證人就是 `/api/scene`，那 `/api/scene` 被假造時前端與「驗證」會一起被騙。→ 見 §4。
3. **差分（Differential over time）**：狀態必須隨真實變異（建立→+1、刪除→-1、undo→回復）。靜態 fixture 過不了 delta。

## 2. 待驗假設（可否證，P0 為核心鑑別）

> **H0 是你的問題的正面回答**，且有真實理由懷疑它可能失敗：`[親驗 addon.py:206-216]` addon handlers **無 `create_object`/`modify_object`/`delete_object`**；LLM（`conversational_modeling.py`）卻定義了 `create_object` 等工具。若 chat 真的送 `create_object` → `handlers.get()`→None → `Unknown command type`。**唯一能改場景的真實路徑＝LLM 選 `execute_code`。** H0 就是要 live 確認 chat 到底有沒有真的改到 Blender，以及走哪條路。

| ID | 假設（可否證斷言） | 為何有鑑別力（假後端為何會失敗） | 優先 |
|---|---|---|---|
| **H0** | 從**前端 chat** 發自然語言「建立一個名為 `⟨NONCE⟩` 的立方體」，事後**獨立 oracle** 查到 Blender 真的多了 `⟨NONCE⟩` 物件 | 這是端對端「MCP 從 chat 有沒有在作用」的正面測試。若 create_object 路徑斷（handler 缺）且 LLM 未改走 execute_code → 物件不會出現 → **抓到「看起來回覆了、其實沒改場景」** | **P0（最高）** |
| **H1** | 前端 REST（非 chat）建立名為 `⟨NONCE⟩` 的物件後，**獨立 oracle** 查到 Blender 真實 `bpy.data.objects` 含 `⟨NONCE⟩` | 假後端不知這輪 nonce，回傳的物件名不會等於 `⟨NONCE⟩` | P0 |
| **H2** | 建立「icosphere subdivisions=2」，oracle 讀回**頂點數 == 42、面數 == 80** | 只有真 Blender 幾何會產出這組確切拓撲數字；mock 猜不到 | P0 |
| **H3** | 「把物件移到 (1.5, 2.5, -0.5)」後 oracle 讀回 `object.location ≈ (1.5,2.5,-0.5)`（浮點容差 1e-4） | 真 Blender 變換數學；假後端無法憑空產生正確座標 | P0 |
| **H4** | 差分：baseline N → 建立→ N+1 → 刪 nonce → N → undo → N+1，每步 oracle 計數吻合 | 靜態資料過不了連續 delta | P0 |
| **H5** | 建立指定紅色材質的 cube；`/api/preview` 截圖在該物件區域**有紅色像素** 且 oracle 查到材質為紅 | 假 preview（靜態圖）不含本輪指令特定的紅；兩獨立證人須一致 | P1 |
| **H6** | 上述變異後，**重構前端 Inspector 顯示的物件清單**（使用者所見）== 獨立 oracle 的真實場景 | 證重構前端**忠實反映真值**，非顯示快取/舊值 | P0 |
| **H7** | 刪真物件→oracle 確認消失；undo→oracle 確認復原 | 證 undo action 真的打到 Blender，非只改 UI | P1 |

## 3. DFMEA — 失敗模式（每條配一個上面的斷言去抓）

| 失敗模式（管線會怎麼假裝成功） | 抓它的斷言 |
|---|---|
| 前端顯示物件，但其實是快取/fixture、非真 Blender | H1（nonce）+ H6（獨立 oracle 交叉） |
| api 收到指令回 200，但 Blender addon 斷線、場景實際沒變 | H4 差分計數不變 → 抓到 |
| LLM 產出錯的 Blender code，物件建了但參數錯 | H2（頂點數）、H3（座標）確切值不符 → 抓到 |
| `/api/preview` 回傳快取/舊截圖，不反映當前場景 | H5 跨證人一致性 |
| **空母體假綠**：場景本來就空，查詢回空被誤判「pass」 | 先驗 baseline 計數，斷言的是**變異量（+1/-1）非絕對值**；母體<必要前置一律標 vacuous 不計 pass |
| **共模失明**：前端與「oracle」其實讀同一條資料路徑，一起被騙 | §4 必須確認 oracle 與 `/api/scene` 是**物理獨立**通道 |
| 前一輪殘留物件污染這輪 | 每輪 teardown 刪除本輪 nonce 前綴物件；nonce 帶 `verify_` 前綴，只碰前綴內 |

## 4. 獨立 Oracle 通道（已由管線圖確認，`[親驗]`）

**黃金 oracle＝`execute_code` 直連 socket 9876**（addon.py:421-436：`print()` 的 stdout 被擷取回傳）。與前端 `/api/scene` 是不同的 addon handler，可取任意 bpy 真值：

```
# 直連 Blender addon（繞過前端 API 與 sandbox）：TCP localhost:9876，送單行 JSON（無換行）
{"type":"execute_code","params":{"code":"import bpy\nprint(len(bpy.data.objects))"}}
# 回： {"status":"success","result":{"executed":true,"result":"<stdout>\n"}}
```

真值查詢範例（給各假設）：
- 物件存在/計數：`print([o.name for o in bpy.data.objects])`、`print(len(bpy.data.objects))`
- 座標（H3）：`print(list(bpy.data.objects['⟨NONCE⟩'].location))`
- 幾何頂點數（H2）：`print(len(bpy.data.objects['⟨NONCE⟩'].data.vertices))`
- 亦可用 `get_object_info`（addon.py:327-362）取 verts/edges/polys/AABB/materials

**獨立性論證**：oracle 走 `execute_code`+`bpy` 直讀；前端 Inspector 走 `get_scene_info`（且**限前 10 物件** addon.py:284-285）。兩者不同 handler、不同資料整形 → 非共模。H6 正是拿「前端 get_scene_info 顯示」對「oracle execute_code 真值」，若前端造假/快取會被抓。

> **視覺備援 oracle**：VNC 看 Blender 真實 outliner 出現 `⟨NONCE⟩`（見 `~/.claude/infrastructure.md`）——與所有 JSON 路徑完全獨立，用於最終人眼確證。

## 5. 執行協定（腳本化、非手動）　⟨待管線圖回填確切 endpoint/socket⟩

走 **Tailscale URL**（硬規則 #1）：`https://bearmacminimac-mini.tail56c751.ts.net/blender`（localhost 通過≠使用者能用）。

FICE 迴圈，每輪：
1. **Fixture**：`clean`（刪所有 `verify_*` 前綴物件）→ 記錄 baseline 計數（oracle）。
2. **Interact**：透過**前端路徑**（chat WS / REST）發一個受控指令（帶本輪 nonce）。
3. **Compare**：前端顯示（Witness A）＋ 獨立 oracle（Witness B）雙讀，對預定義斷言比較。
4. **Evidence**：記 `假設 × nonce × Witness A × Witness B × 判定 × Lane`。
5. **Teardown**：`clean` 前綴物件。

前端驅動層可用 Browser MCP（走 Tailscale URL 的真前端）＋ 對 oracle 通道的獨立查詢腳本。

## 6. 證據矩陣（範本）

| 假設 | nonce | 指令（前端路徑） | Witness A（前端顯示） | Witness B（獨立 oracle） | 判定 | Lane |
|---|---|---|---|---|---|---|
| H1 | verify_a1b2 | 建立名為 verify_a1b2 的 cube | /api/scene 含? | bpy 查? | ⬜ | A |
| H2 | verify_… | icosphere subdiv=2 | — | verts==42? | ⬜ | A |
| … | | | | | | |

## 6b. 執行結果（2026-07-15，`[實測]`）

**前置**：修了 3 個阻塞 bug 才跑得動——WS handler 收 `Request`（每連線 crash）、api plist 埠 17823→19505、`/api/health` 硬回 ok→附 `blender` 欄。獨立 oracle（socket 9876 execute_code）live 確認可讀真值。

**REST 路徑：7/7 PASS**（`mcp_verify_rest.py`）——nonce 物件頂點數==8、Tailscale `/api/scene` 反映真值、REST 改名/刪除真的改到 Blender、差分 3→4→3。→ **api↔Blender 管線經前端 REST 已鑑別性證實為真**。

**H0 chat 路徑：FAIL（決定性發現）**——chat（本地 Gemma-4-E4B，Tailscale WSS）：LLM 回 `🔧 執行 create_object`，但 `blender_output: ❌ Unknown command type: create_object`，oracle 確認物件**未建立**。根因：LLM 被賦予 `create_object/delete_object/modify_object/apply_material` 工具（`conversational_modeling.py:52,57`），但 **Blender addon 只實作 `execute_code`**（`addon.py:206-216`，無這些 handler）。**chat「看起來執行了」但真實場景從未改變。** 唯一能改場景的路徑是 LLM 選 `execute_code`。

**修法選項**：(A) 在 use case 層把 create_object 等工具呼叫**翻譯成 execute_code**（bpy Python）再送 Blender；(B) 在 addon 補這些 handler；(C) 移除自訂工具、只留 execute_code 讓 LLM 直接寫 bpy。A/C 對齊標準 BlenderMCP 設計（LLM 寫 Python via execute_code）。

## 7. 誠實宣告（收尾必附，接 academic-rigor 紅線）

- **證到（軸 M+軸 Q 之機制面）**：`[待實測填]` 真 MCP→Blender 管線端對端在作用（nonce 物件真的進 Blender、幾何/座標真值吻合、前端忠實反映）。
- **未證 / 邊界**：真人主觀易用性（Lane B）；效能/負載；LLM 建模品質的廣度（本計畫證「管線通」與「特定指令正確」，非「AI 對任意需求都建得好」——那是另一個軸 Q，需更大樣本）。
- **紅線**：不得因為 H1–H7 通過就宣稱「AI 建模能力已驗證」。通過的是**管線真實性 + 特定指令正確性**，不是建模品質的一般性宣稱。

## 8. 前置檢查（跑之前，缺一則整份計畫 vacuous）

- **[阻塞中] Blender 正在運行且 BlenderMCP addon 在 `localhost:9876` 監聽**。判別（`[親驗]`）：
  - `lsof -nP -iTCP:9876 -sTCP:LISTEN` 有結果；或
  - `GET /api/preview` 回傳 PNG **size > 70 bytes**（70B 1×1 = 斷線 placeholder，scene.py:27-29）。
  - **現況 2026-07-15：9876 未監聽、無 Blender.app 程序 → 此刻無法執行**（缺「Blender 這個真實輸入」；dummy-run-ladder：機制已備妥，等輸入到位）。
- 服務經 **Tailscale URL** 可達（硬規則 #1，非只 localhost）：`https://bearmacminimac-mini.tail56c751.ts.net/blender`。
- 獨立 oracle（socket 9876 execute_code）確認可回值——**Blender 上線後第一件事就是 live 確認 §4 的 print oracle 真的回得了值**（管線圖標為 [未驗]：程式碼明載但未 live 跑過）。

## 9. 靜默退化警告（DFMEA 已納入，`[親驗]`）

管線多處**斷線時靜默退化、不報錯**——驗證絕不能被這些假綠騙：
- `/api/scene` 斷線 → `{"objects":[]}`，**與真的空場景不可辨** → 斷言一律用「非空 ground truth 的變異量」，先驗 baseline。
- `/api/preview` 斷線 → 1×1/70B placeholder → 用 size 當斷線判別。
- `/api/health` **硬回 `ok`**（main.py:122-124），**不代表 Blender 連上** → 不可拿 health 當 Blender 就緒證據。
- `get_scene_info` **限前 10 物件** → H4 計數用 oracle `len(bpy.data.objects)`，不用 /api/scene。
