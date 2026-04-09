# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ 第一原則：使用者角度驗證

### 🚨 Health Check 必須走 Tailscale URL，不是 localhost

MHH 的 health check 必須經由 Tailscale URL（https://bearmacminimac-mini.tail56c751.ts.net/xxx）檢查服務，不是 localhost:port。

localhost 正常 ≠ 使用者能用。Tailscale URL 正常 = 使用者能用。

這條規則沒有例外。多幾毫秒延遲遠比花兩小時除錯重要。

**所有修改都必須從使用者角度驗證，不是開發者角度。**

1. 修完功能後，用瀏覽器走完整使用者流程，不是只跑 curl
2. 用 Tailscale URL 測試，不是 localhost（sub-path routing 行為不同）
3. 測試前清掉 cookie/cache，模擬第一次訪問的使用者
4. 如果有表單，實際 submit 一次看 redirect 有沒有到正確 URL
5. 不要只看 HTTP status code，要看頁面內容是不是使用者預期的
6. worktree 分支的改動必須 merge 到 main 並重啟服務才算完成
7. 沒測試的東西不要回報「修好了」

**反覆出現的問題：**
- worktree 分支改了但沒 merge 到 main → 服務跑的是舊 code
- Tailscale sub-path stripping 導致前端 URL 不正確
- curl 測 localhost 過了但瀏覽器經 Tailscale 不過
- launchd plist 缺少必要的環境變數（BASE_PATH、TOKEN 等）
- 前端表單 action URL 沒有加 sub-path 前綴

### 🧹 Worktree 清理是每個 task 的收尾責任

每個 code task 結束前必須：
1. 把改動 merge/cherry-pick 到 main（不是只 commit 到 worktree 分支）
2. git worktree remove 清掉自己建的 worktree
3. git branch -D 刪掉 claude/* 分支
4. rm -rf .claude/worktrees/ 如果目錄存在

**絕對禁止**：
- 留下 worktree 讓下一個 task 或用戶清理
- 回報「已 commit」但實際上 commit 在 worktree 分支不在 main
- 跑 git worktree prune 就當作清理完畢（prune 只清已刪除的引用，不會真正刪除 worktree 目錄）

**歷史教訓**：
- 今天（2026-04-07）用戶親自手動清理了所有專案的 worktree，因為多次要求清理都沒真正執行
- worktree 累積到每個專案 10-20 個，浪費磁碟空間，造成混亂
- worktree 分支的 code 沒 merge 到 main 是今天 SHB auth gate 反覆失敗的主因

---

## 跨專案開發規範

**⚠️ 強制規則：** 每次 session 開始時，必須 `Read` [`~/DEVELOPMENT_STYLE_GUIDE.md`](/Users/bearmacmini/DEVELOPMENT_STYLE_GUIDE.md)。此檔定義所有專案共用的開發律令（TDD / DDD / SOLID / 模組化 / 事件驅動 / 零技術債 / UEEDVP / Token 節省 / 錯誤學習機制）。違反此檔規範視為品質缺陷。
