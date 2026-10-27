# 雙探頭量測工作站外殼

**Status:** ACTIVE

導航：[目標](#goal) · [規格](#specification) · [驗收](#acceptance-checks) · [現行接手](#hand-off) · [歷史驗證](../archive/2026-10-27-lab-station-handoff-history.md)

## Goal

以 Blender MCP 專案設計動態氣泡表面張力計與 pH／溫度計共用的可列印外殼。

## Specification

- 使用者確定：拓竹 P2S；250 mL 燒杯或廣口瓶；三探頭共用一杯；約 20 cm 可調伸距。
- 共用桌面底座、LCD 可調與折平、兩組分節旋鈕鎖定臂；一組毛細管，一組 E201-C 與防水 DS18B20。
- 毛細管與 pH／溫度兩頭各自獨立活動、可鎖定；前後伸縮與上下升降可分別調整，探頭角度另行手調。
- 沿用原零件演進：上臂也採兩臂結構並可獨立上下抬升，上下臂交界為四點梯形板，分別連接兩支上臂與兩支下臂；不能換成新的單自由度機構來通過測試。
- 電路空間需後開蓋，上方留通風口；開關、卡扣、鉸鍊、關節加強及可折收螢幕都屬整機操作範圍。
- 完整 STL 先交付，再整理 3MF；修正後以同一組原零件列印，不另外創造替代零件。原檔保留、另存修訂。
- 優先單次列印工作、盡量單盤，可接受立放與支撐；手臂可各自作為列印組件，但不直接預組在盒體上，也不做大量預組裝。
- 初始以 PLA、0.4 mm 噴嘴及 0.2 mm 層高設計；實際配合、支撐移除與免後加工要求須分開驗收，不能只憑排版或切片成功宣稱達成。
- hatch-pet 是誤選，不做動畫或寵物造型。
- 幫浦、微壓感測器、pH 前端、供電板未定案；不得把佔位模型當真實安裝尺寸。
- 第一階段交付尺寸化配置模型與外殼試配 STL；關節鎖定、探頭夾持、LCD 固定與走線需後續工程驗證。

## Acceptance checks

- 官方觸控 LCD 圖為 127.70 × 87.45 mm 玻璃，與頁面摘要尺寸分開。
- 兩節臂解析長度、可達性與每件 P2S 包絡由單元測試守衛。
- Blender 真模型、獨立 STL mm 尺寸與水密檢查；實際畫面檢視。
- 使用者確認列印後可拆除支撐與 brim；不可鑽孔、研磨或修整配合面。孔、插銷、齒面、卡扣與螺母口袋須按列印公差直接裝配、活動及鎖定；支撐安排與移除不得迫使修面，實體配合仍須量化驗證。
- 干涉判定需區分表面交叉、邊界接觸與實體內含；離線內含沿用共用CGAL分類器，先驗證封閉／自交與轉換保真，不用單方向射線奇偶判斷替代獨立資格。齒槽關節須覆蓋退齒、旋轉與重新就座的完整操作。
- 機構、干涉與列印操作驗收必須綁定共用服務目前選定的交付模型與零件身份；研究生成器或歷史模型通過，不得移用為目前交付件的資格。
- 完整制造交付前：安裝孔、螺絲工具空間、探頭玻璃軟夾、防滑鎖定、連續姿態風險、抗傾倒與實體試片。
- Human acceptance is required before moving this file to `archive/`.

## Source Boolean contract (2026-10-27)

- LCD 鉸鍊耳片須在每個正式布林步驟後保持封閉、零退化／薄片與零非相鄰自交；不能靠末端合點掩蓋同孔重切的缺陷。
- 沿用 `serrated_joint_verify_real` 的逐步觀測及獨立 CGAL；新增實際後殼輸入與雙側鉸鍊耳片案例，原相切 bore 反例保留。沿用既有生成、三角化、二進位讀取與驗證模組，無新模組／依賴；保存的 v80 模型、STL、3MF 不改。
- 除來源階段外，實際列印原點／毫米匯出的二進位 STL 必須獨立讀回並通過拓樸與 CGAL；只允許完全相同座標去重，不得合併鄰近頂點或修補後再驗。
- 配對接觸齒面共用週期三角分割規劃；修訂前須辨識完整雙環、唯一角點及一致方向，修訂後所有原頂點／非接觸面保留。以實際匯出幾何做就座前行程、不同對角線與過行程控制；此規劃不等於螺紋／保持力驗收。
- 保留鉸鍊軸心、孔徑及齒面位置；共用孔在耳片及齒盤合併後一次貫穿。需重驗螢幕活動／齒面與全核心 CI，不以來源階段通過冒稱整機資格。

## Hand-off

### Verified facts

目前進度、實際驗證與執行中工作只記在 [任務索引](00_INDEX.md)。
目前模型由 [共用應用服務](../../models/lab-station/README.md) 決定；不得由歷史檔名推斷版本。
原逐輪交接已搬到 [歷史快照](../archive/2026-10-27-lab-station-handoff-history.md)，僅修正搬移後的相對連結，只在追溯指定事件時載入。

### Open failures

完整驗收仍須覆蓋本檔 Acceptance checks 與 [範圍規格](../verification/lab-station/01-scope.md)；單件網格、固定姿態與切片通過，均不能取代整機動作、實際接口、材料及負載證據。具體未解除項目見任務索引。

### Next step

接續任務索引指定的同一個工作及其實際 handle；若真機程序仍在執行，不得並行操作 Blender、修改其驗證來源或重啟驗證；確認終態後才進行同輪公開讀回、恢復選定原生模型與checkpoint。原模型／STL／3MF 保留，後續修改另存修訂。

## Screen clamp control contract (2026-10-27)

- Shared immutable clamp values own pitch, axial seating, target tooth angle and passive-pin float. Reuse the existing five-phase motion; do not duplicate its ramps in Blender bindings.
- Existing fold behavior defaults to a zero-degree target. An explicit target is finite and within the starting angle; physical clamp endpoints must lie on the joint's indexed tooth angles.
- Active screw follows body rotation and subtracts screw lead; passive pin and retainer follow body rotation and the same axial float. Preserve all five original rigid identities and mesh data.
- BDD: given each indexed target from 0 through 60 degrees, forward/reverse numerical and evaluated-driver poses agree, including after save/reload; removing rotation-follow or retainer-float must fail. Invalid geometry roles or binding state are rejected before mutation.
- This contract is a dependency of the shared native-revision service. Control fixtures do not qualify full model collisions, complete hardware tolerances, printing or holding force; no public revision capability is claimed before its adapter and delivery paths are integrated.

## Native revision service contract

- Input is a registered recipe identifier and validated mechanical parameters. No caller-supplied Python, native path, output path or client-specific version selector. The shared application catalog resolves the current selection; a narrow artifact port resolves its unique native file from the verified checksum manifest and returns typed provenance.
- One injected application service orchestrates the existing Blender lease and socket adapter for every client. An isolated factory process used for research is not a second public runtime or acceptance path.
- Source hash mismatch, unknown recipe, ambiguous native source or invalid parameters fail before Blender mutation. No fallback to an older directory. Revisions use exclusive new output directories; source files and the selected delivery are not overwritten or promoted automatically.
- Any required input triangulation or coordinate rebase is an explicit registered preparation step with named owners and preservation evidence. Invalid source surfaces cannot be silently repaired or relabelled as validated geometry.
- After each source operation, validate the affected surface independently. Save/reopen checks include original object identities, descendants, all rigid controls, external-library absence and unchanged unrelated surfaces. Actual binary STL bytes must pass topology and strict geometry checks.
- Complete the same-identity STL set before deriving a new 3MF. Unchanged parts retain source bytes; changed parts carry source/native/export provenance. Reuse the existing slicing and packaging services for single-plate qualification; a successful imported-v80 run does not qualify a revised candidate.
- BDD rejection cases: missing/malformed selection; stale source hash; multiple native candidates; unknown recipe; pre-existing destination; failed intermediate geometry; missing/extra/replaced part identity; unsaved driver mismatch; failed source restoration. Each failure retains diagnostic evidence and cannot publish a successful result or update the current selection.

### Verified native source boundary

- The current catalog supplies a parsed ModelSpec once. A narrow async source port resolves the single `.blend` explicitly listed by that selected root's SHA256.json; unlisted historical native files never become fallback candidates.
- Every manifest entry has a canonical relative path and a valid SHA256. All listed files are checked; the selected STL glob must have a nonempty, capped set of files with manifest entries. Symlinked entries, escapes, duplicate keys, stale/missing files, ambiguous listed natives and incomplete part provenance fail before any Blender call.
- The result is immutable typed provenance with root-relative paths, native and selected-part fingerprints, manifest fingerprint, verified-file count and aggregate byte budget. It certifies identity at read time, not native format, geometry or printability. The execution adapter must stage and recheck these fingerprints before editing.
- BDD positives include nested/Unicode parts, an unlisted historical native, and a changed current selection. Rejections include invalid manifest paths/digests/types, missing/stale assets, duplicate listed natives, missing/extra STL identities, empty selection and import caps. No error exposes host paths or silently selects an archive.

- Existing list_artifacts adds optional default_native from that exact validated discovery snapshot. An identity error is explicit native unavailability; it does not change selected input artifacts or imply imported-STL failure. Source lookup must not re-query the mutable selection provider during one discovery response.
- The production composition root injects the filesystem source port into the same ArtifactCatalog used by DesignPipeline. Both REST and MCP serialize its common result; no native operation or readiness claim is added by discovery.

### Source snapshot contract

- Before any native modification, resolve the captured ModelSpec again through the same source port and require the complete immutable receipt to match. Never re-query the selection provider during preparation.
- Stage all manifest-declared assets and the exact manifest bytes under an exclusive job-relative directory. File bytes are bounded by the verified aggregate size and each staged digest must match; reject pre-existing destinations, symlinks, invalid job identifiers, source changes during copying and incomplete copies.
- Return a typed job-relative snapshot receipt only after the copied set and original source recheck pass. Retain failed diagnostics without a successful receipt; never overwrite the source, current selection or another job. Cancellation must drain any started file worker before returning, including repeated cancellation.
- BDD: a successful snapshot is independent of later original-file edits. Rejection controls cover stale receipts, tampering during copy, source-manifest changes, existing outputs, missing/extra files and cancellation while the worker is live. Snapshot identity alone is not native geometry or print qualification.

### Native scene lifetime contract

- Within the existing serialized Blender request, isolate original local IDs by temporary names, append the verified source's single scene and all declared object identities, and run operations under an explicit temporary scene/view-layer context. The user window's scene and original file path must remain unchanged.
- The executor operates on staged handles only. Reject linked original data, non-object modes, unexpected source identity, multiple input scenes, cross-boundary dependencies, pre-existing outputs and source overwrite. No public arbitrary script or path input is introduced.
- The subset writer must include all staged objects, preserve their names and dependencies, and fail before writing if a staged object references an original ID. A separately reopened output must contain the complete active scene, correct parent/driver relations and no external library references.
- Cleanup always exits the override, removes newly created IDs and restores original names. Before/after snapshots verify original ID identities, object transforms, raw mesh topology/coordinates, parenting, custom properties and their editable UI metadata, driver definitions, selection, visibility and active context. Any failed cleanup or original-state mismatch is a restoration error, never successful qualification. Desktop UI layout is outside this snapshot contract and must not be claimed preserved.
- Pending native output is published exclusively only after cleanup and the original-state check pass. A late output collision preserves that existing file; an exception after writing pending bytes removes only the owned temporary file. A malformed native with a correct fingerprint still fails as a typed native-scene error after restoring original state.
- BDD controls cover success, raised operation failure, source mismatch, multi-scene source, original-name collision, planted original-mesh reference, new-ID cleanup and existing-output refusal. A factory fixture is isolated evidence only; the production shared-runtime gate is still required before public delivery.

### Internal execution authorization contract

- Only the internally derived complete program may receive a temporary sandbox exemption and its finite positive deadline. The same callback supplies both decisions; static registered generator/verification exemptions remain unchanged. Neither code, paths nor grant issuers are exposed as request parameters.
- A grant belongs to the issuing asyncio task and lexical scope. Concurrent requests, inherited child tasks and copied thread contexts cannot borrow it. Exiting the scope revokes all copied contexts, including a copy later re-entered by the original task. Nested scopes restore the outer grant; errors and cancellation revoke the completed scope.
- The production native runner must create the grant inside the actual worker held by the existing Blender lease; creating it in a parent before spawning that worker is invalid. Repeated cancellation must drain that worker before releasing the lease. A socket observation timeout does not prove the Blender callback completed or that original state was restored.
- BDD controls independently exercise cross-task replay, copied-context resurrection, exact-code mismatch, nested failure, cancellation, invalid deadlines and a real loopback socket with a shorter default timeout. An unsupported transport must reject an explicitly requested scoped policy rather than silently discard it. These adapter contracts do not establish public native revision or manufacturing qualification.

### Closed screen geometry and STL contract

- The registered screen-clamp request accepts only its recipe identifier and a valid indexed target. Geometry planning lives in `screen_revision_plan`; no source path, output path, code or arbitrary Boolean operation is a request field. Binding the validated target to a complete native job remains part of executor integration.
- Source preparation names every owner: three existing fastener meshes use vertex-preserving CDT; the two screen print owners and the pH wrist bind to their current, receipt-verified canonical STLs. Explicit fixed-axis registration must satisfy bidirectional point discrepancy and physical handedness before rebasing; it is not proof of bijective topology equivalence. Unrelated rigid frames remain within the declared numerical registration band.
- Geometry changes only the original back shell and lid. Every source step uses the existing independent closedness／self-intersection checker; material witnesses additionally prove the bore removed material and the integrated stop added it while adjacent controls retain material. Missing or ambiguous canonical identities and changed canonical bytes fail before mutation. Skipping either Boolean must fail specifically for missing material change.
- Temporary-scene operations use explicit collection／depsgraph data APIs; a scene/view-layer override does not authorize window-dependent operators. The original window remains on its original scene. Save/reopen compares all object identities, raw geometry, frames, parents and driver relations, with zero external libraries.
- Build the complete original-identity STL set before deriving any 3MF. Unchanged parts retain exact source bytes; changed parts use canonical print coordinates and actual binary output is independently checked. Reject extra/missing identities, stale source/native receipts, empty/incorrect geometry verdicts, existing destinations, mid-validation output tampering and extra files. Only final set/hash verification may write the output receipt and checksum manifest. Cancellation drains workers and never removes another job's receipts.
