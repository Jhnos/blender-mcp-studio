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
| D-002 | `api/routers/{vision,pipelines,generate3d}.py` 整包 `except Exception → 500`,因為 LLM／text-3D／pipeline 沒有 domain error 型別 | 為 `LLMPort`／`Text3DGenerationPort`／pipeline 定義 domain error,照 `BlenderConnectionError` 註冊到 `api/main.py` 的 handler,router 不再自己翻譯 | 下一步 |
| D-003 | `PreviewStage.tsx` 的 `react-hooks/refs` 定點豁免 | 觸發條件未成立時維持;若 D-002 之後仍有餘裕,評估把 ref 讀取移出 render 期 | 待評估 |

## Acceptance checks

- 每條先紅後綠;`scripts/ci.sh --real` 全綠;checkpoint C1–C5 綠。
- D-001:`test_the_use_case_decodes_nothing` 綠;REST 與 MCP 真機閘門過(真 adapter 解碼)。
- D-002:三個 router 沒有 `except Exception`;`test_rest_error_contract` 的 422/503 極性不變。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- D-001 done:port 三個 typed 查詢、兩個 adapter 各自解碼、422 訊息逐字保留;921 個單元測試綠,
  `ci.sh --real` 全綠(REST／MCP 閘門走真 adapter 的解碼)。非 mapping 的場景回覆從「警告 + 空 dict」改成錯誤。
- 六個手寫 fake 補上三個 typed 方法;mock 的三個 REST 測試改成 mock typed 方法並證明 422 路徑。

### Open failures

- 沒有機器檢查在失敗。

### Next step

- D-002:先寫紅測試——`api/routers/vision.py` 等三處不得有 `except Exception`(靜態掃描),
  且 `LLMPort` 拋出的 domain error 經 `api/main.py` handler 變 502/503(依 `test_rest_error_contract` 的極性表);
  再在 `src/core/domain/exceptions.py` 加 `ExternalServiceError` 系列,adapter 把 provider 例外翻成它。
