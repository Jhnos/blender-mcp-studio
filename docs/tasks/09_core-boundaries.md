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
| D-003 | `PreviewStage.tsx` 的 `react-hooks/refs` 定點豁免 | 觸發條件未成立時維持;若 D-002 之後仍有餘裕,評估把 ref 讀取移出 render 期 | 待評估 |

## Acceptance checks

- 每條先紅後綠;`scripts/ci.sh --real` 全綠;checkpoint C1–C5 綠。
- D-001:`test_the_use_case_decodes_nothing` 綠;REST 與 MCP 真機閘門過(真 adapter 解碼)。
- D-002:三個 router 沒有 `except Exception`;`test_rest_error_contract` 的 422/503 極性不變。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- D-001 done:port 三個 typed 查詢、兩個 adapter 各自解碼、422 訊息逐字保留;真機 REST／MCP 閘門走真 adapter 的解碼。
- D-002 done:`ExternalServiceError`／`VisionAnalysisError`／`TextTo3DError`;vision 與 text-3D adapter 在邊界把外部失敗翻成
  domain error(cause 串起來);`api/main.py` 一處對映 502;四個整包 `except Exception` 刪除。REST 契約測試新增:
  provider 失敗 → 502、pipeline 內 Blender 斷線 → 503(原本是 500)。928 個單元測試綠,`ci.sh --real` 全綠。
- 凍結的 endpoint 守衛清單少了四個手做的 500;上傳圖片的 provider 失敗改成 502。

### Open failures

- 沒有機器檢查在失敗。`chat.py`(4)、`snapshots.py`(1)、`ws_manager.py`(2)仍有整包 except,列在預算裡只能往下;
  它們攔的是 LLM 串流與快照 I/O,尚無對應的 domain error 型別。

### Next step

- D-003:讀觸發條件,親驗 `PreviewStage.tsx` 的 `react-hooks/refs` 豁免是否仍成立;成立則維持並記錄日期,
  否則把 ref 讀取移出 render 期。之後評估 `chat.py` 的四處整包 except 是否能用 `LLMConnectionError`／`ExternalServiceError` 收掉。
