# 核心邊界收債:port 回傳型別、外部服務的錯誤型別、lint 豁免

**Status:** ACTIVE

## Goal

把 `docs/DEFERRALS.md` 裡三條核心側的延後(D-001 port 回傳未型別化、D-002 外部服務的整包
`except Exception`、D-003 `PreviewStage` 的 lint 豁免)逐條收掉或以親驗證據確認仍該延後;
每一條都先有紅測試,每一片都過 `ci.sh --real` 與 checkpoint。

## Context to read

1. `docs/DEFERRALS.md` — 三條的根因、觸發條件、目前防護
2. `docs/01-architecture.md` — 「Domain/application 契約」與安全邊界
3. `docs/30-verification.md` — 閘門與什麼不算證據

## Specification

| 條 | 根因(親驗) | 正解 | 狀態 |
|---|---|---|---|
| D-001 | `BlenderPort` 回傳 `object`,use case 自己窄化 Blender 方言,與 adapter 重複 | port 回傳 typed DTO(`scene_summary`／`object_details`／`viewport_screenshot`),解碼在 `src/adapters/blender_scene_decoding.py`,截圖暫存檔在 `src/adapters/viewport_capture.py` | **done**(V01.0Q.004) |
| D-002 | `api/routers/{vision,pipelines,generate3d}.py` 整包 `except Exception → 500`,因為 LLM／text-3D／pipeline 沒有 domain error 型別 | `ExternalServiceError` 家族由 adapter 在邊界拋出,`api/main.py` 對映 502;router 不再自己翻譯;預算棘輪擋回流 | **done**(V01.0Q.005) |
| D-003 | `PreviewStage.tsx` 的 `react-hooks/refs` 定點豁免 | 三個觸發條件親驗皆未成立,維持並記錄日期;同類的 `ObjectListNode` 豁免補登為 D-009 | **評估完成**(維持) |
| 順手 | 截圖暫存檔的 dance 在 chat／snapshots／ws 迴圈／refinement 各一份 | 全部改走 `BlenderPort.viewport_screenshot()`,閘門擋住原始工具名回流 | **done** |
| 續 D-002 | LLM adapter 讓 httpx／SDK 例外直接逃出,use case 再整包包成 `LLMConnectionError("LLM chat failed")`,529 變 503、cause 丟失 | `LLMProviderError`(502)／`LLMConnectionError`(503)在 Anthropic 與 Ollama 三條路徑(chat／stream／tools)的邊界翻譯;use case 不再包;`chat.py` 預算 3 → 2 | **done**(V01.0Q.007) |
| 順手 | `src/workflows` 是初版留下的孤島:沒有任何 REST／MCP／UI 路徑到得了 | 刪除;`00-context` 的範圍改寫成真正在跑的 pipeline;`test_no_src_package_is_an_island` 擋下一個 | **done** |

## Acceptance checks

- 每條先紅後綠;`scripts/ci.sh --real` 全綠;checkpoint C1–C5 綠。
- D-001:`test_the_use_case_decodes_nothing` 綠;REST 與 MCP 真機閘門過(真 adapter 解碼)。
- D-002:三個 router 沒有 `except Exception`;`test_rest_error_contract` 的 422/503 極性不變。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- D-001 done(V01.0Q.004)、D-002 done(V01.0Q.005)、D-002 續:LLM adapter(V01.0Q.007);D-003 評估維持、D-009 補登;
  截圖 dance 收斂、`src/workflows` 孤島刪除(V01.0Q.006)。
- LLM 邊界翻譯的紅測試先抓到自己一個缺陷:串流回應未讀就取 `.text`,在 handler 裡再拋 `ResponseNotRead`——改用狀態行。
- 929 個單元測試綠,`ci.sh --real` 全綠(17 份契約 + 差分)。
- 2026-09-09 V01.0R.002:`hand-compact` 已發布、任務 08 歸檔;核心側本輪無變更,本檔仍是唯一待驗收的核心任務。
- router 裡剩的整包 except:`chat.py` 2(WS 錯誤幀)、`ws_manager.py` 2(背景迴圈守衛),預算只能往下。

### Open failures

- 沒有機器檢查在失敗。核心側登記在案的債全部處理完;機器側無待辦。

### Next step(使用者)

- 驗收核心邊界收債的方向(port 回傳 typed DTO、外部服務與 LLM provider → 502、孤島刪除);通過就把本檔移到 `archive/`。
