# Client-neutral MCP layer TDD 與驗證規範

> 狀態：Target test strategy。本文是 [MCP_LAYER_DEVELOPMENT.md](MCP_LAYER_DEVELOPMENT.md) 的驗證 SSOT；逐檔步驟見 [implementation plan](../superpowers/plans/2026-07-18-client-neutral-mcp-layer.md)。

## 1. TDD iron law

```text
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

每個 behavior change 必須完成：

1. **RED**：寫一個只描述單一行為的 test。
2. **Verify RED**：執行並確認它因缺少該行為而失敗，不是 import typo、fixture 壞掉或環境缺 dependency。
3. **GREEN**：只寫足以通過該 test 的 production code。
4. **Verify GREEN**：focused test 與既有 regression tests 全綠，無 warning/error noise。
5. **REFACTOR**：只改善名稱、責任或 duplication，不加新 behavior。
6. **Verify GREEN again**：refactor 後重跑同一 gate。

如果 production code 先出現：刪除該段，回到 failing test。不得把先寫的 code 留著當「參考」。

## 2. 測試主張層級

不同 test 能證明的事不同。禁止用低層測試替高層主張背書。

| Tier | 使用的真實元件 | 可證明 | 不可證明 |
|---|---|---|---|
| Unit/domain | domain values、service、port contract | invariants、mapping、error semantics | MCP framing、FastAPI mount、真 Blender |
| In-memory MCP | 真 FastMCP server/tool registry + fake scene port | catalog、schema、annotations、structured result、ToolError | HTTP middleware、Origin、Tailnet、socket |
| ASGI integration | 真 FastAPI + 真 mounted FastMCP + fake BlenderPort | lifecycle、route、identity、Origin、protocol negotiation、shared assembly | Blender真的變更 |
| Headless protocol smoke | 真 HTTP server + MCP client + fake Blender backend | process/HTTP framing與proxy | `bpy`執行 |
| T3 real machine | 真 MCP endpoint + 真 API + 真 adapter + 真 addon + Blender | end-to-end scene mutation | 公網/OAuth/其他機器環境 |

一個 test 若把被測層替換掉，就不能宣稱該層正常。例如：Fake `SceneOperationsService` 的 MCP test不能證明 high-level command 會經 adapter翻譯成 `execute_code`。

## 3. Test double policy

### 3.1 允許的替身

| Boundary | Preferred double | 理由 |
|---|---|---|
| `BlenderPort` in application unit tests | hand-written fake | 外部 socket昂貴；fake保留完整 Port behavior與recording |
| `SceneQueryPort` / `SceneCommandPort` in MCP registry tests | hand-written fake implementing both contracts | 只隔離 application；FastMCP與tool function保持真實 |
| External identity in ASGI tests | explicit trusted header fixture | 測 middleware contract，不 mock middleware |
| Time/random nonce | injected deterministic value | 讓 failure可重現 |
| Real Blender gate cleanup | test utility/function | cleanup不污染 production API |

### 3.2 禁止的替身

- 不 mock `FastMCP.tool` decorator、`tools/list` 或 `call_tool`，因為這些正是被測 protocol behavior。
- 不 mock `create_app` 或 middleware後再宣稱 endpoint可連。
- 不 assert `MagicMock.called` 作為主要成功條件；主要 assertion看 domain result、MCP result或真 Blender state。
- 不新增 production `reset_for_test()`、`destroy_for_test()` 或 public socket getter。
- 不建立缺欄位的 partial addon response，除非 test正是在驗證缺欄位被拒絕。
- 不 mock high-level method而讓 test依賴其被 mock 掉的 side effect。

### 3.3 Complete fake requirement

Port fake 必須實作完整 Protocol，可被同一 contract suite重用。Addon response fixture要鏡像真實 shape：

```json
{
  "name": "Scene",
  "object_count": 1,
  "materials_count": 0,
  "objects": [
    {"name": "Cube", "type": "MESH", "location": [0.0, 0.0, 0.0]}
  ]
}
```

缺欄位 fixture另命名 `invalid_scene_missing_objects`，不得讓它看起來像正常 response。

## 4. TDD evidence record

每個 task的工作紀錄至少保存：

```text
Behavior: <one observable behavior>
RED command: <exact command>
RED reason: <expected assertion failure>
GREEN command: <exact command>
Regression command: <exact broader command>
Refactor: <none or named responsibility change>
Mechanical claim protected: <test/sentinel name>
```

不要求 commit message塞入完整紀錄，但 PR/task summary必須能回答「你親眼看到哪個 test先紅？」。

## 5. Vertical slice order

實作順序以可獨立交付的 vertical slices為單位。每個 slice都必須先完成 RED；不可一次先建完全部 production modules再補 tests。

### Slice 1: Immutable scene vocabulary

**Behavior:** domain values immutable；Query/Command Protocol可由 structural substitute滿足。

**RED tests:**

- import `CreateObjectSpec`應先因 module不存在失敗。
- 對 frozen field賦值應 raise `FrozenInstanceError`。
- complete fake同時是 `SceneQueryPort`與`SceneCommandPort`。

**Expected RED:** `ModuleNotFoundError`只在第一步可接受；建立 module後，真正 behavior test必須以 mutation未被阻止或 Protocol不匹配而紅。

**GREEN:** stdlib `@dataclass(frozen=True, slots=True)` + `@runtime_checkable Protocol`。

**REFACTOR boundary:** 不建立 base DTO class、repository或serialization framework。

**Focused gate:**

```bash
~/miniconda3/envs/blender-mcp/bin/python -m pytest \
  tests/unit/core/test_scene_operation_contracts.py -q --no-cov
```

### Slice 2: Application command routing

**Behavior:** typed commands轉成既有 high-level `Command`，不生成 `bpy`。

**RED tests:**

- `create_object`送出的 `tool_name`必須是 `create_object`。
- `modify_object`只包含非 `None`欄位。
- failed `ToolResult` raise `SceneOperationError`，不回 success receipt。

**Discriminating assertion:** 除了 command name，再 assert exact arguments。只 assert fake被呼叫一次不夠。

**GREEN:** `SceneOperationsService`接受 `BlenderPort` constructor injection。

**REFACTOR boundary:** common `_success()`可在兩個以上 command重複後抽出；不要先建 generic dispatcher。

### Slice 3: Application query narrowing

**Behavior:** raw addon response轉為 domain snapshots；wrong shape loud failure。

**RED tests:**

- 完整 scene fixture轉成 `SceneSummary`。
- missing `objects`、非 sequence location、non-string key各自 raise actionable error。
- screenshot回 bytes/width/height且 temporary file在成功與失敗時都清掉。

**GREEN:** rebuild containers與explicit required-field check。

**REFACTOR boundary:** narrowing helper不得 import infrastructure/HTTP/Pydantic；container check必須符合 project narrowing gate。

### Slice 4: Exact MCP catalog

**Behavior:** 真 FastMCP `tools/list`只回八個 tools，metadata正確。

**RED test:** server尚未註冊或catalog不相等；failure diff應顯示 missing/extra names。

**Primary assertion:**

```python
assert {tool.name for tool in tools} == EXPECTED_TOOLS
```

禁止：

```python
assert EXPECTED_TOOLS <= {tool.name for tool in tools}
```

Subset assertion抓不到危險的 `execute_code`意外暴露。

**GREEN:** dedicated decorators；每個 tool直接call incoming port。

**REFACTOR boundary:** decorator function不得長出 business logic或socket access。

### Slice 5: Schemas, structured output and errors

**Behavior:** host取得窄 input schema、typed output與recoverable error。

**RED tests:**

- color `2.0`在application call前被拒絕。
- unknown parameter被拒絕。
- scene query同時有 `structuredContent`與text fallback。
- screenshot是 `ImageContent`、MIME `image/png`。
- forced `SceneOperationError`產生 `isError=true`與actionable message。
- unexpected exception不洩漏 traceback。

**GREEN:** FastMCP/Pydantic boundary types、domain dataclass return annotation、controlled `ToolError`。

**REFACTOR boundary:** 不把 Pydantic model移入 domain以求schema方便。

### Slice 6: Shared runtime assembly

**Behavior:** FastAPI、REST與MCP共用一個 runtime/socket owner。

**RED tests:**

- initialize前 MCP lifespan未啟動時test應紅，證明combined lifespan必要。
- `connect_calls`不是1時紅。
- REST與MCP依賴的service/blender object identity不同時紅。
- shutdown `disconnect_calls`不是1時紅。

**GREEN:** `AppRuntime` composition root + combined lifespans。

**REFACTOR boundary:** concrete imports只留 composition root；不可用global mutable service locator。

### Slice 7: HTTP security and neutrality

**Behavior:** protocol在可信HTTP boundary運作且不依host品牌分支。

**RED tests:**

- 無 identity initialize = 401。
- identity present initialize = 200。
- invalid Origin rejected。
- unsupported protocol version = 400。
- `codex`、`claude-code`、`cursor`、`Visual Studio Code`、`unknown-host` catalog/policy完全相等。

**GREEN:** existing identity middleware + FastMCP transport protection；不寫 client name conditional。

**REFACTOR boundary:** client-name parameterized test留在一個contract suite，不複製五份測試。

### Slice 8: `/blender` route and stdio proxy

**Behavior:** 外部sub-path與stdio-only host都到同一 MCP endpoint。

**RED tests:**

- Vite proxy config未含 `/blender/mcp`時config test紅。
- stdio proxy沒有使用 `BLENDER_MCP_URL`或不是 `transport="stdio"`時紅。
- proxy source出現 `9876`、`BlenderMCPAdapter`或scene service import時sentinel紅。

**GREEN:** Vite streaming proxy + `fastmcp.server.create_proxy`。

**REFACTOR boundary:** stdio entrypoint保持單一 transport responsibility。

### Slice 9: Real Blender proof

**Behavior:** MCP command真的建立、移動、刪除 Blender object。

**Interaction path:** MCP Streamable HTTP。

**Independent oracle:** direct addon socket `execute_code`查 object existence、vertex count與location。

**RED requirement:** 在實作 MCP mutation前，real verifier至少一個 hypothesis必須FAIL；只有 Blender未啟動才可顯示明確SKIP。

**GREEN sequence:**

1. baseline清掉舊 `verify_mcp_`。
2. MCP `create_object`建立 nonce cube。
3. Oracle確認名稱存在且8 vertices。
4. MCP `modify_object`移到 `[1, 2, 3]`。
5. Oracle確認座標。
6. MCP `delete_object`。
7. Oracle確認消失。
8. `finally`再次cleanup。

Reply文字、fake call record或MCP success status都不是oracle。

## 6. Contract test suites

### 6.1 Scene query contract

同一 suite套用 hand-written fake與real `SceneOperationsService`：

- status回 `BlenderStatus`。
- scene/object result是immutable domain type。
- missing object failure語意一致。
- screenshot成功回PNG且不留下temp file。

### 6.2 Scene command contract

- create/modify/delete/material成功回 `OperationReceipt`。
- failure不回receipt。
- modify omitted fields不被寫入。
- command不自行connect/disconnect。

### 6.3 Transport equivalence contract

對 HTTP與stdio proxy各執行：

- initialize成功。
- `tools/list` canonicalized JSON hash相同。
- read-only sample結果shape相同。
- error的 `isError`與message class相同。

Transport可以在latency與connection lifecycle不同，但public contract不可不同。

## 7. Mechanical enforcement matrix

文件主張必須對應一個會紅的東西。

| Claim | Enforcement | Negative fixture / mutation |
|---|---|---|
| core沒有FastMCP/HTTP dependency | AST import sentinel | fixture module加入 `import fastmcp`，sentinel必須FAIL |
| 新MCP domain values是stdlib-only | AST domain-purity sentinel | fixture加入 `from pydantic import BaseModel`，sentinel FAIL |
| MCP adapter不碰socket | AST forbidden constructor/import | fixture呼叫 `BlenderSocketClient(...)`，sentinel FAIL |
| MCP adapter不生成bpy | scoped AST/string sentinel | fixture literal含 `import bpy`，sentinel FAIL |
| catalog只有八個tools | exact set equality | 暫時註冊 `execute_code`，test FAIL |
| 每個tool有正確annotations | exact policy table | flip `delete_object.destructiveHint`，test FAIL |
| schema拒絕extra fields | protocol call test | 加入 `code` param，call error且service calls=0 |
| runtime只connect一次 | assembly counter | 建第二個adapter，counter變2，test FAIL |
| component真的裝到production | initialize + `tools/list` through `create_app` | 只定義server但不mount，initialize FAIL |
| identity真的擋住MCP | middleware integration | 無header request得到401 |
| client-neutral | parameterized catalog hash | 加任一client branch，hash不同 FAIL |
| bad addon shape不silently fallback | narrowing unit test | missing key fixture raise error |
| 真 Blender被修改 | nonce + independent oracle | no-op fake response仍會被oracle抓到 FAIL |
| guard本身不是裝飾 | negative sentinel tests | 每個sentinel至少有一個故意違規fixture |

Sentinel只有存在不算完成；必須親眼看過negative fixture讓它失敗，再移除／隔離fixture後看它轉綠。

## 8. Structural sentinels

### 8.1 AST over regex

依賴方向、constructor exclusivity使用AST，避免comments/docstrings造成false positive後被迫放寬regex。Sentinel輸出完整檔案與line number，不只回hit count。

新domain檔的purity sentinel以空allowlist開始。若同一test也盤點既有Pydantic domain debt，既有檔使用明示ratchet allowlist，且必須測 stale entry會FAIL；不得把整個 `src/core/domain` 排除。

### 8.2 Exhaustive absence claims

宣稱「沒有 `execute_code`」時必須寫清範圍：

```text
Scope: MCP public adapter and catalog under src/adapters/mcp_server/**/*.py
Method A: AST tool registration inspection
Method B: runtime tools/list exact equality
Output: not truncated
```

`rg`沒有結果只能當輔助 evidence，不能單獨證明universal negative。

### 8.3 God-file gate

- `>350` lines：warning/review zone。
- `>550` lines：hard failure。
- 合法修正只有按responsibility拆分。
- Whitelist若存在，必須有理由、loud debt output與stale-entry ratchet。

本feature預期不需新增whitelist。

## 9. Error-path tests

至少覆蓋：

| Failure | Expected assertion |
|---|---|
| Blender offline | controlled tool error；status false；warning visible |
| object missing | actionable error含object name |
| malformed scene mapping | `SceneOperationError`，不是empty scene |
| vector length 2/4 | validation/narrowing error |
| NaN/Infinity | input rejected |
| screenshot metadata success but file absent | explicit error |
| screenshot tool failure | temp path removed |
| invalid protocol header | HTTP 400；service calls 0 |
| missing identity | HTTP 401；MCP initialize未執行 |
| unexpected exception | client看不到traceback；server error log存在 |
| cancellation during screenshot | temp path removed |

每個error test只驗證一個failure class。Test name出現多個「and」時優先拆分。

## 10. Concurrency tests

### 10.1 Hermetic ordering test

Fake socket transport用兩個barrier控制兩個concurrent calls：

1. Call A取得shared lock並停在barrier。
2. Call B開始但不得write。
3. Release A，收到A response。
4. B才write並收到B response。

Assertions看write/read event sequence，不只看lock object存在。

### 10.2 Shared ownership test

ASGI integration同時送REST query與MCP query，assert兩者record在同一 fake Blender instance。這證明assembly，不宣稱真socket concurrency。

### 10.3 Real concurrency scope

Version one真機gate以serial mutation為主，避免non-deterministic scene race。若未來宣稱multi-client concurrent mutation，必須新增專屬real test與scene ordering semantics ADR。

## 11. CI mapping

專案唯一CI仍是 `scripts/ci.sh`。

### T1 static

- Ruff check/format。
- mypy strict。
- container narrowing gate。
- layer-direction AST sentinel。
- socket-constructor exclusivity sentinel。
- god-file size sentinel（若納入本次實作）。

### T2 hermetic

- Domain/application unit tests。
- In-memory FastMCP contract tests。
- ASGI Streamable HTTP tests。
- stdio proxy unit/contract tests。
- Existing unit/e2e/frontend dummy run。

T2不需要Blender、Ollama或網路；如果需要，測試邊界設計錯誤。

### T3 real machine

- Existing REST verifier。
- New MCP verifier。
- Blender未listen `9876`時顯示explicit SKIP，不得印PASS。
- 任何hypothesis fail讓CI nonzero。

## 12. Required commands

Focused RED/GREEN command依slice使用implementation plan所列路徑。每個task結尾至少執行：

```bash
~/miniconda3/envs/blender-mcp/bin/python -m pytest <focused-test> -q --no-cov
```

完成hermetic implementation：

```bash
scripts/ci.sh
```

完成真機驗證：

```bash
scripts/ci.sh --real
```

依賴更新後額外確認：

```bash
~/miniconda3/envs/blender-mcp/bin/python -c \
  "import fastmcp; print(fastmcp.__version__)"
```

## 13. Stop conditions

遇到以下任一情況，停止寫production code並回到設計／RED：

- Test在production code前就通過。
- Test因import typo、fixture錯誤或dependency缺失而error，不是預期behavior failure。
- 為了test方便想在production class加method。
- Fake setup超過test本體且無法說明每個欄位。
- 需要mock FastMCP、FastAPI或application service本身才能測被聲稱的behavior。
- 想用coverage百分比取代discriminating assertion。
- 想以tool success reply證明Blender已變更。
- Static guard沒有negative fixture證明它會fire。
- 新tool沒有query/command分類、annotation或real oracle策略。

## 14. Refactor rules

只在GREEN後refactor：

- 抽出重複error mapping。
- 依responsibility拆分超長module。
- 改善domain name與Protocol segregation。
- 共用同一decision的schema constraint。

Refactor階段不得：

- 新增未測tool。
- 擴充input接受範圍。
- 改變error為fallback。
- 加入future provider framework。
- 把兩個只是長得相同、但reason to change不同的adapter硬合併。

## 15. Completion checklist

- [ ] 每個新增function/method都有先紅過的behavior test。
- [ ] 每個RED failure reason有紀錄且正確。
- [ ] Fakes實作完整port；assertion不以mock behavior為主。
- [ ] In-memory MCP tests使用真server registry與真protocol client。
- [ ] ASGI tests使用真mount、middleware、lifespan。
- [ ] 每個architecture/security claim都有mechanical gate。
- [ ] 每個sentinel有negative fixture證明會fire。
- [ ] Hermetic CI無warning/error noise。
- [ ] Real MCP verifier使用nonce與independent oracle。
- [ ] Cleanup在成功與失敗路徑都成立。
- [ ] `scripts/ci.sh`與`scripts/ci.sh --real`結果符合預期。

缺任何一項，不能把MCP layer標為完成。
