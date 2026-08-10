# Blender MCP Studio - Codex 設定

> 全域規則見 ~/.Codex/AGENTS.md — 適用於本專案。

Blender MCP Studio — 透過 MCP Server 控制 Blender 的工具，提供 3D 建模自動化能力。

**Ports:** API `19505`、Web `19504`、Blender addon socket `9876`。（SSOT＝`~/MacHomeHub/config/services.yaml` + `deploy/launchd/*.plist`；驗證：`launchctl list | grep com.blender-mcp` → `lsof -nP -p <PID> -iTCP -sTCP:LISTEN`。19147 是已廢舊埠。）
**Tailscale sub-path:** `/blender`（strip_prefix: false）
**Tailscale URL:** `https://bearmacminimac-mini.tail56c751.ts.net/blender`

如有開發文件，見專案根目錄。完整 Tailscale 路由表見 `~/.Codex/infrastructure.md`。

**機器 gate:** `scripts/ci.sh`（唯一 CI，無 GitHub Actions；`--real` 加真 Blender 驗證，需 addon 在 9876）。除錯先查 `docs/LESSONS_LEARNED.md`（同 class 教訓 SSOT）。
