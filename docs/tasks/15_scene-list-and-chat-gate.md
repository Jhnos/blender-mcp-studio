# 場景清單不再只有十個,對話路徑才能有閘門

**Status:** ACTIVE

## Goal

讓 `/api/scene` 回的物件清單反映真實場景,然後把對話驗證器接進 `ci.sh --real`。
順序是硬的:清單修好之前,那支驗證器一定紅,而明知會紅的閘門不該進 CI。

## Context to read

1. 上游 addon `__init__.py:283`:`# Collect minimal object information (limit to first 10 objects)`
2. `src/adapters/mcp/blender_mcp_adapter.py:292` — `scene_summary()` 直接用 addon 的 `get_scene_info`
3. `docs/01-architecture.md` ADR-001 — addon 是 execution boundary;
   **內部 adapter 允許在翻譯過的操作之後用 `execute_code`**,公開 client 不行
4. `scripts/verify/mcp_verify_chat.py` H6

## Specification

- `scene_summary()` 的物件清單改由 adapter 內部取得,不再吃 addon 那份截斷過的摘要。
  `object_count` 本來就是對的,不要動它。
- **要有上界**:一個沒有上界的清單只是把截斷從 10 換成無限;比照列印就緒檢查的取樣上限,
  選一個遠高於任何真實場景的值,並在超過時**明說被截斷**,不要靜默。
- H6 綠之後,`mcp_verify_chat.py` 進 `ci.sh --real`,並由架構測試釘住。

## Acceptance checks

- 先寫會紅的那一個:場景有超過 10 個物件時,`/api/scene` 的清單長度 > 10。
- 截斷發生時,回應**帶得出「被截斷了」這件事**;靜默截斷要紅。
- `mcp_verify_chat.py` 5/5,並在 `ci.sh --real` 裡。
- Human acceptance is required before moving this file to `archive/`。

## Hand-off

### Verified facts

- 上限在上游 addon,不在本專案碼裡(2026-09-09 在 Mac 上實查到那一行註解)。
- 對話驗證器修好 import 後首跑 4/5,只有 H6 紅。
- 現場場景有 209 個物件,`/api/scene` 只回 10 個。

### Open failures

- None yet(尚未動工)。

### Next step

- 寫那個會紅的測試,再改 `scene_summary()`。
