# 設計：讓 MCP 完整——概念進、合規模型出

**狀態**：定稿（2026-10-21）。普查已回填（§5），reviewer 八題處置於 §5.2；使用者裁決：階段 1 第一個實例＝匯入既有交付件（§5.2 第 1 題選 A），切片器裝在這台 Mac、AGPL 以子行程呼叫並在 manifest 明標、不另送法務（§5.2 第 6 題）。
**對應任務**：`docs/tasks/17_mcp-complete-pipeline.md`。**實作計畫（階段 1）**：[[superpowers/plans/2026-10-21-mcp-complete-phase1]]。

## 1. 意圖與為什麼

使用者（Jhnos，原話）：「我透過 LLM 只負責想法與概念，MCP 可以支援到可 3D 列印或是虛擬世界模型，並讓整個物理、機械結構、定義等等都符合。」

今天這個專案已經有大半的零件——參數化產生器、產出物契約、列印就緒檢查、CGAL 獨立幾何守衛、關節動作掃掠、驗證套件、可重現的發布包——但它們只活在 CI 腳本與 REST 裡；MCP 只暴露 11 個基礎工具。結果是：任何 MCP host 上的 LLM 能建一個立方體，卻不能說「把這個夾具做到可以印、而且動得起來」。這份設計把現有能力升成一條**由 MCP 驅動、機器自驗、證據落檔**的管線。

## 2. 目標、非目標、反目標

**目標**
1. 任何 MCP host（Claude Desktop、Codex、本專案 Web chat）只用自然語言與工具呼叫，就能從概念走到「可送印的 STL／3MF 加驗證報告」；虛擬世界匯出（glTF 加碰撞體與關節定義）為第二階段。
2. 「符合」由機器判定（Lane A）：幾何（水密、流形、無自交、最小壁厚）、機構（關節極限、行程內零干涉、可達姿態、拆裝路徑）、列印（就緒問題為零、目標印表機切片成功、支撐與黏附量化）、可重現（manifest 與校驗和）。人只裁品味（Lane B）。
3. 每次執行留下證據目錄（報告 JSON、產出物、影像），CI 閘門與 MCP 工具跑的是**同一個應用服務**，不存在第二套實作。
4. 硬體解耦：應用層只依賴 runtime SSOT 與環境變數；主機名、家目錄、作業系統機制（launchd）只存在部署層與設定檔；換機器（macOS／Linux、x86／arm64）只換部署層與設定。
5. 先用現成資源：每個能力先查現成專案，能黑盒包裝就不自建；自建的部分在規格裡附 prior art 查詢紀錄。

**非目標**
- 不做通用 CAD、不取代 Blender；不做即時物理遊戲引擎。
- 不把 `execute_code` 開成公開 MCP 工具（安全邊界不變）。
- 不改既有公開 DTO 的相容性（新工具用新 DTO）。
- 第一階段不做負載／強度分析（FEA）；記為後續能力。

**反目標（做到也算失敗）**
- 工具在相依工具缺席時「靜默跳過」回綠燈。缺席＝明確失敗＋安裝指引。
- 報告裡有「通過」卻沒有可開啟的證據檔。
- 任何一步把正確性驗證丟給使用者。
- 為了讓閘門綠而放寬門檻（本專案 LESSONS 反覆踩過）。

## 3. 約束（來自專案與使用者）

- DDD＋六角：domain／application 不 import bpy、FastAPI、FastMCP；外部能力經 port 注入；REST、MCP、stdio proxy 共用一個 `AppRuntime` 與一條序列化的 Blender socket。
- 本機 CI 是唯一 CI；新行為先有會紅的測試；真機層共用一個 Blender 場景、依序執行；長工具的逾時由量測推導（見 `VERIFICATION_TIMEOUT_S`）。
- 檔案 400 行預算（95% 警戒）；新模組在規格裡要有 `## Prior art`。
- 已發布包（models/*/manifest.json）釘住幾何；升級共用 primitive 須明確參數保留舊路徑（LESSONS 2026-10-21）。
- 共用主機：Blender 單執行緒、Ollama 與其他工作負載共用 CPU；長工作要能背景化並回報進度。
- 使用者已決定：第一個端到端例子是**可列印機構**（P2S 在、實驗室工作站進行中）；虛擬世界匯出第二。手部三個已發布包維持現狀。

## 4. 已決定的「怎麼做」

### 4.1 管線與階段（應用服務 `DesignPipeline`）

```
概念（LLM）→ 規格（ModelSpec，機器可讀）→ 建構（產生器）→ 驗證四類 → 打包 → 報告
                                              ├ 幾何：契約＋CGAL 獨立守衛
                                              ├ 機構：動作掃掠、干涉、拆裝
                                              ├ 列印：就緒＋目標機切片＋支撐量化
                                              └ 重現：manifest、校驗和、確定性探針
```

每個階段是一個 use case，輸入輸出是 typed DTO，證據寫到 `runs/<run_id>/`。CI 的真機閘門改為呼叫同一批 use case（逐步搬遷，不一次重寫）。

### 4.2 規格 SSOT：`ModelSpec`

- 一份宣告式、版本化的定義，LLM 可以寫、可以改：零件與參數、關節（型式、軸、極限、間隙）、材料與配合、列印目標（機型、材料、層高）、虛擬目標（引擎、單位、碰撞體策略）。
- 本專案的領域計畫（hand plans、lab station spec）已是 Python dataclass；`ModelSpec` 是它們的機器可讀外殼，不重寫產生器。
- 機構定義是否直接採 URDF／MJCF／SDF 當 SSOT，或以 `ModelSpec` 為 SSOT 再投影成 URDF／MJCF／glTF：**待普查問題 (b) 的證據**。目前傾向「自有 SSOT＋投影」，因為列印公差與配合間隙不是那些格式的一等公民。

### 4.3 Port（新增或擴充）

| Port | 職責 | 第一個 adapter | 後續 adapter（黑盒） |
|---|---|---|---|
| `MechanicalGenerationPort`（既有） | 由規格建構零件與場景 | Blender 產生器 | — |
| `VerificationPort`（既有） | 登錄套件與契約 | 既有 | — |
| `MeshIntegrityPort`（新） | 水密、流形、自交、壁厚 | host 端 CGAL（既有 `mesh_integrity`） | 待普查（trimesh／manifold3d） |
| `MechanismSimulationPort`（新） | 關節行程掃掠、干涉、拆裝、可達 | Blender BVH（既有動作檢查搬入） | PyBullet／MuJoCo（待普查） |
| `SlicingPort`（新） | 目標機切片、支撐／黏附量化、3MF | 切片器 CLI 黑盒（待普查決定首選） | — |
| `PackagingPort`（新） | manifest、校驗和、3MF／glTF、重現比對 | 既有 package_reproduction 搬入 | glTF 驗證器（待普查） |
| `JobPort`（新） | 長工作背景化、進度、取消 | SQLite（沿用 session／snapshot store 模式） | — |

### 4.4 MCP 工具目錄（新增，與 REST 共用服務）

`list_instances`、`build_instance`（從對話工具升為公開 MCP）、`verify_artifact_contract`、`check_mesh_integrity`、`simulate_mechanism`、`slice_for_print`、`package_model`、`export_virtual_model`（第二階段）、`run_design_pipeline`（一次跑完）、`get_job_status`／`get_run_report`。

長工作一律「提交→job id→查詢」，不靠單一超長逾時；`run_verification_suite` 維持相容，另提供 job 版本。

### 4.5 硬體解耦

- 所有主機名、埠、路徑從 `config/`＋環境變數解析；Tailscale 網域以 `tailscale status --self --json` 動態取得或由環境變數提供；禁止在 `src/`、`api/`、`scripts/verify/` 寫死（現況 7 處要清）。
- 外部工具（切片器、模擬引擎）以 CLI／subprocess／服務黑盒接入，位置由設定提供；`tool_status` 工具回報每個能力的可用性與版本。
- 部署層可替換：launchd（現有）、systemd 單元、容器；應用層與閘門不呼叫 `launchctl`。閘門用跨平台手段（埠監聽、行程啟動時間）。
- 普查的可裝性以 macOS arm64 與 Linux x86_64／arm64 兩軸評估。

### 4.6 證據與驗收

- 每個 run 一個目錄：`report.json`（各階段 PASS／FAIL＋數字＋檔案路徑）、產出物、影像。
- 真機閘門沿用 Lane A：契約、CGAL、動作掃掠、切片成功；人只看渲染圖裁外觀。
- 新工具各有：單元測試（DTO 與服務）、離線 dummy run、真機契約；缺席工具的負對照（故意移除路徑→明確失敗）。

### 4.7 分階段

1. **階段 1 可列印機構**：`ModelSpec` 最小版、`MeshIntegrityPort`、`MechanismSimulationPort`（Blender BVH）、`SlicingPort`（首選 CLI）、`PackagingPort`、`JobPort`、MCP 工具目錄、主機名清理；以實驗室工作站為第一個實例跑通。
2. **階段 2 虛擬世界**：glTF 匯出加碰撞體與關節中繼資料、驗證器；`export_virtual_model`。
3. **階段 3 外部物理引擎**：`MechanismSimulationPort` 的第二個 adapter；負載／強度留待後續。

## 5. 重用決策（依 2026-10-21 普查，附錄 [[superpowers/specs/2026-10-21-reuse-survey]]、查詢紀錄 [[superpowers/specs/2026-10-21-reuse-survey-queries]]）

| 能力 | 首選（授權） | 模式 | 對應 port | 為什麼不自建／備註 |
|---|---|---|---|---|
| 概念→參數化幾何 | 既有 bpy 產生器優先；build123d（Apache-2.0）＋ pzfreo/build123d-mcp（Apache-2.0，stdio） | 白盒依賴＋黑盒子服務（經既有 `MCPPort`，只暴露量測／驗證／匯出三個 curated 用例，不暴露其 `execute`） | `MechanicalGenerationPort` 擴充或新 `ParametricCadPort` | OCCT 核心寫不出來；Zoo 雲端計費、Text2CAD 類授權非商用，不取 |
| 機構定義格式 | URDF 當交換 SSOT（yourdfpy，MIT）；本專案 domain spec 當作者層；pinocchio（BSD-2）做極限與動力學 | 白盒依賴；自建 spec→URDF 發射器 | 新 `MechanismDefinitionPort`；既有 FK／BVH 掃掠保留為驗證 SSOT | 公差與配合不是 URDF 一等公民，用旁掛 YAML（SMURF 概念） |
| 物理模擬 | MuJoCo（Apache-2.0，arm64 wheel） | 白盒依賴，自建 runner；Blender Bullet 只粗驗 | `MechanismSimulationPort` 第二 adapter（第三階段） | PyBullet 無 arm64 wheel；Genesis／Isaac 不符 headless 或授權。MuJoCo 讀 URDF 為 [推論]，接入前實測 |
| 網格驗證 | CGAL（既有）＋ trimesh（MIT）＋ manifold3d（Apache-2.0） | 白盒依賴；pymeshfix／pymeshlab（GPL）只在補洞時隔行程 | `MeshIntegrityPort` | 壁厚／最小特徵查無現成庫，自建判準 |
| 切片 | Bambu Studio CLI（AGPL-3.0，本專案 v80 已實跑）；備選 OrcaSlicer CLI | 黑盒 subprocess，manifest 明標 AGPL；lib3mf（BSD-2）讀寫 3MF | `SlicingPort` | 切片器是數十萬行 AGPL；P2S 原廠設定只在 Bambu。缺口：本機目前未裝切片器，二進位路徑要進 config SSOT |
| 虛擬匯出 | Blender glTF 匯出（內建）＋ glTF-Validator／gltf-transform（npm）＋ pygltflib；usd-core（universal2） | 黑盒 CLI＋白盒依賴 | `PackagingPort`／`SceneExportPort`（第二階段） | 物理擴充 KHR_physics_rigid_bodies 仍是 proposed，先用 extras 自標 |
| 既有 CAD／模擬 MCP server | 只有 build123d-mcp 值得黑盒接入 | 黑盒（stdio） | `MCPPort` | FreeCAD／Fusion／Onshape 綁 GUI 或雲端；模擬類 MCP 全 ≤8 星 |
| 規格／公差 | 自建：PLA 配合表（以自家試片為 SSOT）、ISO 286 小表、公差疊加用 numpy | 自建 | domain | 查無資料庫；這層是專案領域知識，要能被驗證套件引用 |

### 5.1 部署形態：分層容器化（使用者 2026-10-21 要求評估容器化）

實測事實：`blender -b` 背景模式下 `bpy.app.timers` 不觸發（註冊 3 次、等 2 秒、0 次），而現行 addon 把每條指令排進 timer 執行；Workbench 離屏渲染在背景模式可出圖（此機 Metal）；專案渲染只用 Workbench；`get_viewport_screenshot` 依賴視窗區域；API 連 Blender 的主機與埠已由環境變數決定；本機有 Docker（Colima，Ubuntu aarch64）；GX10 是 Linux ARM 加 GPU 主機；MHH 服務登錄表每服務有 `machine` 欄。

| 選項 | 優點 | 代價 | 決定 |
|---|---|---|---|
| A 全容器化（含 Blender 無視窗） | 一份 compose 走天下 | 先要無視窗執行器；Linux 容器 Mesa 渲染待驗；macOS 容器無 GPU；切片 CLI 容器化待驗 | 第二步 |
| **B 分層容器化** | 應用層與閘門立刻跨平台；Blender 引擎主機可插拔（原生 GUI 或無視窗容器） | 維護兩種部署描述；兩個 dummy run 當採用閘門 | **採用** |
| C 只做可攜安裝腳本 | 改動最少 | 無隔離、環境漂移靠人 | 不採 |

B 的內容：①無視窗 Blender 執行器（主執行緒輪詢佇列執行指令；GUI 模式維持 timer），`get_viewport_screenshot` 在無視窗模式改離屏渲染（DTO 不變）；②API＋web＋host 端驗證工具（CGAL、trimesh、切片 CLI）進 compose；③Blender 引擎主機兩種 adapter，由 `BLENDER_HOST`／`BLENDER_PORT` 選擇，MHH 登錄 `machine` 欄跟著走；④採用閘門：Colima 容器內 Workbench 渲染 dummy run、無視窗 socket 指令往返 dummy run，兩者綠才把容器 Blender 當正式 adapter。

## 5.2 Reviewer（builder check，2026-10-21）八題的處置

| # | 問題 | 處置 | 決定（我的，除非標「使用者」） |
|---|---|---|---|
| 1 | 第一個實例是哪個物件：登錄 V10 產生器，還是把使用者交付的 v78 `.blend`／STL 當建構產物餵進驗證→切片→打包？ | **使用者裁決**（見交付訊息的選項表） | 建議：先走「匯入既有產物」路徑（管線加 `import_artifact` 階段，`build` 可跳過），因為那是真正要印的東西，且不被產生器債擋；V10 產生器登錄為第二個實例。 |
| 2 | LLM 寫的 `ModelSpec` 怎麼進產生器又不破壞「只收 slug、程式碼逐字來自登錄表」的安全邊界？ | 我決定 | **資料通道，不是程式碼通道**：`ModelSpec` 是純資料（pydantic schema、版本化），只能選登錄實例並覆寫該實例**宣告過範圍**的參數；產生器程式碼仍逐字來自登錄表，sandbox 豁免不變；builder port 簽章擴成「實例＋參數覆寫」，附反向測試（超範圍、未宣告鍵、夾帶程式碼一律拒絕）。LLM 永遠寫不到程式碼。 |
| 3 | 實驗室工作站是閉鏈，URDF 不支援閉鏈；Lane A 判官是 BVH 掃掠還是 pinocchio？ | 我決定 | 機構 SSOT 是自有 `ModelSpec`（允許閉鏈、配合與公差）；URDF／MJCF 只是**投影**：URDF 給樹狀子鏈與交換，MJCF（帶 equality 約束）給 MuJoCo。階段 1 的 Lane A 判官＝既有 Blender BVH 掃掠與拆裝碰撞，不需要 URDF；pinocchio 到有模擬需求的階段才進。 |
| 4 | §5 重用表哪些屬於階段 1？ | 我決定 | 階段 1 只用：既有 bpy 產生器、CGAL、trimesh＋manifold3d、Bambu Studio CLI、lib3mf。build123d／build123d-mcp 是階段 1b（LLM 要新零件時的參數化幾何，獨立任務）；yourdfpy／pinocchio／MuJoCo 階段 3。 |
| 5 | 分層容器化（無視窗執行器）是阻斷、平行還是之後？ | 我決定 | **平行軌，不阻斷階段 1**。階段 1 只做應用層解耦（主機名清理、設定 SSOT）＋ API／web／host 工具的 compose；無視窗執行器是獨立任務，先 dummy run 再決定；它會改 vendored addon 的派工方式，須新 ADR 取代 ADR-001「原樣保留」。 |
| 6 | 切片器誰裝、裝哪台、P2S 設定從哪來、AGPL 要不要法務確認？ | 部分**使用者裁決** | 技術面我定：二進位路徑進 config SSOT（環境變數覆寫），`install.sh`／前置閘門檢查存在與版本；P2S 設定檔在執行時從安裝的 app 讀取（路徑在設定），不複製進 repo；缺席＝明確失敗。要你答：切片器裝在這台 Mac（GUI app）還是 GX10（Linux AppImage）；AGPL 以子行程呼叫是否需要你方法務確認。 |
| 7 | 遠端 MCP host 怎麼開啟證據檔？ | 我決定 | 階段 1 就做：報告 JSON 與影像經既有身分閘門的 REST 路由下載（`/api/runs/{id}/...`），MCP 以 resource 暴露同一路徑；不新增未受身分保護的入口。 |
| 8 | 長工作與單一序列化 Blender socket 的併存、cancel 語意？ | 我決定 | 每個 job 階段持有「Blender 獨占租約」，其他場景工具在租約期間回 busy（不排隊、不交錯）；階段之間釋放；cancel＝停在下一階段邊界，正在 Blender 內執行的步驟不可中斷，報告如實標示。 |

## 6. 留給建造者

- DTO 的欄位命名與 `ModelSpec` 的 schema 版本策略（在約束內自訂）。
- `JobPort` 的儲存細節與清理策略。
- 真機閘門搬遷到 use case 的順序（先新工具、再逐個契約）。
- 第一個實例的最小 `ModelSpec` 內容。

## 7. Prior art

普查紀錄：`reuse-survey.md`／`reuse-survey-queries.md`（scratchpad，定稿時搬入 `docs/verification/` 或本檔附錄）。專案先前查過的參考列於 `docs/verification/lab-station/09-references.md`。
