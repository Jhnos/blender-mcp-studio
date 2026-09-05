# 知識放置規則與 5S 預算

> 回導航 [[README]] · 相關 [[LESSONS_LEARNED]]、[[tasks/00_INDEX]]
>
> **導航表不在這裡**——要找「哪個檔講什麼」請看 [[README]]。本檔只回答一個問題：
> **我手上這條知識該寫到哪裡去？**

## 知識該放哪層

| 知識的種類 | 放哪裡 | 形狀 |
|---|---|---|
| 任務進度與狀態 | [[tasks/00_INDEX]] | **唯一進度源**；任務檔只放執行細節與 hand-off |
| 架構決策 | [[01-architecture]] 的 ADR 段 | 一個決策一節；已定案的不改寫，用新 ADR 取代 |
| 踩過的坑 | [[LESSONS_LEARNED]] | **新的在上**；根因鏈 + 為何沒被攔下 + **預防 class** |
| 埠、位址、環境變數 | [[10-runtime-ssot]] | 別處一律指過來，不複寫 |
| 驗證指令與判準 | [[30-verification]] | 同上 |
| 部署與 plist 規則 | [[12-deployment]] | 同上 |
| 產出物 contract 流程 | `verification/` | 一個模型版本一個 rubric 檔 |
| 已完成的 campaign | `archive/` | 整包移入，**不得據以推斷現況** |
| 跨專案通用的做法 | 全域 skill 或全域 agent 規則 | 不放本 repo |

判準：**與本專案耦合的 → 專案檔；換個專案仍成立的 → 全域。**

## 教訓的形狀（這條最常被寫壞）

`LESSONS_LEARNED.md` 不是事件 log。每一條必須是**抽象的失效 class**，
本專案的既有條目全部採「X 不等於 Y」的句式，照著寫：

- ✅「Process 已啟動不等於它的相依服務已 ready」——換個專案照樣成立，且附可執行的預防措施
- ❌「2026-09-05 我改了 foo.py 的第 42 行修好 bug」——那是 commit message，不是教訓

**寫完教訓不等於做完**。一條教訓的處方如果沒有變成 CI 裡會擋下來的閘門，
同一個洞會繼續長出新 bug——這件事本身已經是 `LESSONS_LEARNED.md` 裡的一條教訓。
所以收尾條件是：**教訓落檔 + 處方進 gate**，缺一不算完成。

## 目前不需要獨立的 memory 目錄

上表每一條存活的事實都已經有單一 SSOT。只有當某個跨 session 的事實無法被
架構、任務、教訓或維運文件表達時，才新增 memory 目錄；屆時採一檔一主題 + 索引。

## 5S 預算

| 對象 | 預算 |
|---|---|
| Agent 指示檔（`AGENTS.md`／`CLAUDE.md`） | ≤ 200 行 |
| 專案自撰 skill（`SKILL.md`） | 約 150 行；細節外移到 references |
| 現行任務目錄 | 只留 `TODO`／`ACTIVE`／`BLOCKED`／`AWAITING-ACCEPTANCE` |
| 供選擇性閱讀的檔案 | 超過 100 行要有目錄 |

**超標的唯一合法解是拆檔或歸檔，不是把句子壓短。** 壓縮語意會讓載重的指令
和裝飾性的句子一起模糊掉，比超標更糟。

## 節奏

- 每個 checkpoint 跑一次快速掃描；campaign 完成時跑完整一輪。
- 歸檔一律用**檔案搬移**，並在 commit 訊息裡點名搬了什麼——git history 是永久紀錄。
- **禁止靜默刪除**（無 commit 痕跡的移除），也**禁止改寫歷史**
  （`LESSONS_LEARNED` 與 `CHANGELOG` 的既有條目不動，要修就修現況）。
