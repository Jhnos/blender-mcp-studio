# 對話能產出可印的零件

**Status:** ACTIVE

## Goal

讓對話路徑能呼叫本專案自己的產生器:說「做一隻夾爪」就拿得到真的印製包。
順帶把**從來沒被引用過**的對話驗證器接進 `ci.sh --real`——先有閘門再加能力。

## Context to read

1. `src/core/use_cases/conversational_modeling.py` — `_BLENDER_TOOLS` 是**手寫**的工具清單,
   與公開的九項 MCP 目錄是兩回事;動它不碰 `docs/01-architecture.md:177` 那條安全邊界
2. `src/core/use_cases/mechanical_generation.py` — 上一輪蓋好的產生能力,對話目前看不到它
3. `scripts/verify/mcp_verify_chat.py` — 修好 import 後首跑 4/5(2026-09-09)

## Specification

### 能力

- 對話工具清單新增兩項:列出已註冊實例、產生一個已註冊實例。
- 這兩項**不經 `BlenderPort`**,走 `MechanicalGenerationService`;use case 要能分辨
  哪些工具名該路由到哪裡,而且分辨方式不能是「試試看哪個不炸」。
- 輸入仍只有 slug。對話**不得**成為繞過登錄表的第二條路。
- 公開的九項 MCP 目錄**不動**。

### 閘門(先做這半)

- `scripts/verify/mcp_verify_chat.py` 進 `ci.sh --real`,並由架構測試釘住。
- H6(前端場景清單只回 10 個物件)**本任務不修**——上限在上游 addon,
  已記在 `CHANGELOG` V01.0R.010。要修是另一個任務。

## Acceptance checks

先寫會紅的那一個:對話送出「列出可用的實例」時,回覆包含三個以上已註冊的 slug——
今天工具清單裡沒有這項,必紅。

- `scripts/ci.sh` 全綠;`--real` 全綠且含對話驗證器。
- 守衛:對話工具清單裡的產生類工具,接受的 slug 集合 == `HAND_INSTANCES.keys()`。
- 守衛:公開 MCP 目錄仍是九項(should-fire:加第十項要紅)。
- Human acceptance is required before moving this file to `archive/`。

## Hand-off

### Verified facts

- `_BLENDER_TOOLS` 是 use case 裡的手寫清單,與公開目錄無關(2026-09-09 實查)。
- 對話目前能做的極限是方塊/曲線/燈/相機/位移/材質——**沒有一句話能產出可印零件**。
- 對話驗證器修好 import 後首跑 4/5,H6 失敗且原因在上游。
- LLM 供應者是本機 Ollama。

### Open failures

- None yet(尚未動工)。

### Next step

- 寫那個會紅的測試,再把 `MechanicalGenerationService` 注進 use case。
