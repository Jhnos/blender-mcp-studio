# Client-neutral MCP implementation status

> 回 [README](README.md) · 現行架構 [architecture.html](../../../architecture.html) ·
> 執行清單 [implementation plan](../superpowers/plans/2026-07-18-client-neutral-mcp-layer.md)

本檔是此已完成 campaign 的凍結進度紀錄；不得用來判斷現行任務。

| Phase | 狀態 | Evidence |
|---|---|---|
| Domain values + ports | Done | `9cc924d` |
| Shared application service | Done | `9caa260` |
| Nine-tool FastMCP adapter | Done | `check_print_readiness` added without exposing `execute_code` |
| Shared runtime + `/mcp` mount | Done | `0b48f0f` |
| `/blender/mcp` + stdio proxy | Done | `0f10edd` |
| Protocol/client-neutral gates | Done | `d281e58` |
| Real verifier + CI hook | Done | `scripts/ci.sh --real` passed REST, MCP, readiness, and batch Undo gates |
| Client/architecture/integration docs | Done | `MCP_CLIENTS.md` + rendered/guarded `architecture.html` |
| Hermetic CI | Passing | `scripts/ci.sh` |
| Deployment / real Blender acceptance | Done | Production preview on `19504`; API health reported Blender connected |

## Archive closure

Campaign accepted and archived on 2026-08-11. Current architecture lives in
[`../../../ARCHITECTURE.md`](../../../ARCHITECTURE.md), current client setup in
[`../../../MCP_CLIENTS.md`](../../../MCP_CLIENTS.md), and active work in
[`../../../tasks/00_INDEX.md`](../../../tasks/00_INDEX.md).
