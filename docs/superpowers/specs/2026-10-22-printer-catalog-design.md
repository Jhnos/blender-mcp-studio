# 印表機目錄：廠商解耦、不預設機器、可選印表機（設計）

> 狀態：使用者 2026-10-22 核准。上游：`2026-10-21-mcp-complete-pipeline-design.md`（階段 1，V01.0S.000 已部署）。
> 研究證據：[[superpowers/specs/2026-10-22-orcaslicer-research]]，摘要見 §6。實作計畫：[[superpowers/plans/2026-10-22-printer-catalog]]。

## 1. 意圖

使用者原話：「創維也要支援」，以及「兩家廠商都解耦合，不要預設機器，而是讓機器可選」。

意思是：Bambu Lab 和 Creality（創想三維）兩家都要能印。印表機不寫死在程式裡，ModelSpec 也不再有預設機器；LLM 或使用者從「這台主機實際能切片的印表機」裡挑一台。

## 2. 目標、非目標、反目標

**目標**
- 印表機是資料：每台一個 YAML 條目，寫明廠商、切片器、設定檔名、床板類型與列印覆寫。新增一台印表機只要加一筆資料，不必改程式。
- `print_target.printer` 必填，沒有預設值。缺少或不認得時，錯誤訊息要列出可用的印表機。
- 新增 MCP 工具 `list_printers`：只列出切片器確實裝在本機的印表機，每台附廠商、型號、噴嘴、可用材料與床板。
- 一個「Orca 家族 CLI」轉接器同時驅動 Bambu Studio 與 OrcaSlicer。兩者的差異（二進位、設定檔根目錄、結束碼、`result.json` 位置）由切片器設定資料描述。
- 首批印表機：Bambu Lab P2S（沿用 v80 驗收過的覆寫）、Creality K1C、K1、K1 Max、K2 Plus、Ender-3 V3、Ender-3 V3 KE，噴嘴一律 0.4、材料 PLA。

**非目標**
- 多色或 AMS／CFS 配料、非 PLA 材料的驗收（目錄格式會支援，但這一階段不驗收）。
- 直接傳檔到印表機或遠端列印。只產出切片後的 3MF 與 G-code。
- 替 Creality 調參數。只用 Orca 內建的官方設定檔，加上明確寫在資料裡的覆寫。

**反目標（做到也算失敗）**
- 程式裡任何地方出現印表機或廠商的預設值。
- 列出一台本機切不了的印表機，或者靜默改用另一台。
- 材料或製程與機器不相容時，仍然靜默切片。必須用設定檔的 `compatible_printers` 擋下並報錯。
- 只有 Bambu 的真機閘門。兩家廠商各要有一道真機切片閘門。

## 3. 約束

- 設定檔在執行時從安裝的 app 讀取，不複製進 repo（沿用階段 1 §5.2 #6）。名稱以 JSON 的 `name` 為準，不是檔名。
- AGPL：OrcaSlicer 與 Bambu Studio 都以子行程呼叫；manifest 記下實際使用的切片器名稱、版本與授權。
- 逾時從實測推導：OrcaSlicer 的 `SLOWEST_SLICE_MEASURED_S` 用 v78 的 69 件實際量。
- 主機與路徑解耦沿用階段 1：二進位路徑寫在 `config/tools.yaml`，可用環境變數覆寫。

## 4. 我決定的部分

- **目錄格式**：`config/printers/<vendor>/<id>.yaml`。
  - 欄位：`id`、`vendor`、`model`、`nozzle_mm`、`slicer`（`bambu-studio` 或 `orcaslicer`）、`profile_vendor_dir`、`machine`、`process`（依層高對照）、`filaments`（依材料對照）、`bed_type`、`overrides`。
  - `overrides` 指向覆寫 JSON 檔，例如 P2S 的 `p2s-pla-overrides.json`。
- **id 格式**：`<vendor>-<model>-<nozzle>`，例如 `bambu-p2s-0.4`、`creality-k1c-0.4`。這是 spec v2 的破壞性變更（必填欄位、id 格式），所以 `spec_version` 升為 `"2"`。v1 照舊能解析，但 v1 一律對應到 `bambu-p2s-0.4`，並在報告標示「v1 legacy default」。
- **切片器設定**：`config/slicers.yaml` 列出每個切片器的二進位設定鍵、app bundle 內設定檔的相對路徑，以及結束碼表。
  - Orca 是負數碼，經 shell 會 mod 256；Bambu 用正數碼。
  - 共用轉接器 `OrcaFamilyCli` 取代 `BambuStudioCli`，Bambu 走同一個類別、不同資料。
- **相容性檢查**：送出 spec 時就檢查，不等到切片階段。
  - 檢查項目：材料是否在該機的 `filaments` 對照裡；製程與材料的 `compatible_printers` 是否包含該機的 machine 名稱。
  - 研究已發現的陷阱：K1 與 K1 Max 不能用 `Creality Generic PLA @K1-all`，要用 `Creality HF Generic PLA`。目錄裡寫死正確名稱，再由相容性檢查守住。

## 5. 留給建造者

- `list_printers` 的輸出欄位命名，以及它跟 `describe_model_spec` 怎麼互相連結。
- Ender-3 V3 系列的床板類型：先在真機確認 Orca 的預設，再寫進資料。

## 6. 研究摘要（OrcaSlicer v2.4.2）

| 項目 | 結論 | 狀態 |
|---|---|---|
| 版本與授權 | v2.4.2（2026-07-07），AGPL-3.0；macOS 只有 universal 版 DMG，246,088,803 B | 已查（GitHub API） |
| 簽章與公證 | 官方 CI 有 codesign、notarytool、staple 步驟 | 實際檔案**未驗**，下載後用 `spctl` 確認 |
| CLI 旗標 | 現有 Bambu 轉接器用的每個旗標在 Orca 都同名存在 | 已查（原始碼 @v2.4.2） |
| `inherits` | CLI 不會展開，現有的展平步驟要保留 | 已查 |
| 結束碼 | 負數（−100 切片錯誤，−50 沒有可切物件，−13 匯出失敗）；失敗時不寫 3MF | 讀碼確認，未實跑 |
| `result.json` | v2.4.2 只在 Linux 寫出 | macOS **未驗** |
| Creality 設定檔 | 廠商目錄 `Creality`；六個型號的機器、製程、PLA 名稱已列表 | app 內路徑**未驗** |
| 先例 | AFKFelix/orca-slicer-api（78 stars）包 Orca CLI 做服務；可對照它的 CLI 用法，不整包引入 | 已查 |

## 7. 驗收（Lane A，機器全包）

- 單元：
  - 目錄 schema
  - 沒填印表機、印表機未知、材料不相容，各自被拒絕
  - `list_printers` 只列已安裝的切片器
  - Orca 結束碼對照
- 真機閘門，各一道：
  - v78 的 69 件 × `bambu-p2s-0.4`（既有閘門改為明確指定機器）
  - v78 的 69 件 × `creality-k1c-0.4`（新增）
  - 兩道都要 1 盤、manifest 記下實際使用的切片器與版本，並附負向對照：不相容的材料要在送出時被拒絕。
- 整輪 `scripts/ci.sh --real` 必須不中斷地跑完。
