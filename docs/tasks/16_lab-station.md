# 雙探頭量測工作站外殼

**Status:** ACTIVE

導航：[目標](#goal) · [規格](#specification) · [驗收](#acceptance-checks) · [現行接手](#hand-off) · [歷史驗證](#歷史驗證紀錄)

## Goal

以 Blender MCP 專案設計動態氣泡表面張力計與 pH／溫度計共用的可列印外殼。

## Specification

- 使用者確定：拓竹 P2S；250 mL 燒杯或廣口瓶；三探頭共用一杯；約 20 cm 可調伸距。
- 共用桌面底座、LCD 可調與折平、兩組分節旋鈕鎖定臂；一組毛細管，一組 E201-C 與防水 DS18B20。
- hatch-pet 是誤選，不做動畫或寵物造型。
- 幫浦、微壓感測器、pH 前端、供電板未定案；不得把佔位模型當真實安裝尺寸。
- 第一階段交付尺寸化配置模型與外殼試配 STL；關節鎖定、探頭夾持、LCD 固定與走線需後續工程驗證。

## Acceptance checks

- 官方觸控 LCD 圖為 127.70 × 87.45 mm 玻璃，與頁面摘要尺寸分開。
- 兩節臂解析長度、可達性與每件 P2S 包絡由單元測試守衛。
- Blender 真模型、獨立 STL mm 尺寸與水密檢查；實際畫面檢視。
- 完整制造交付前：安裝孔、螺絲工具空間、探頭玻璃軟夾、防滑鎖定、連續姿態風險、抗傾倒與實體試片。
- Human acceptance is required before moving this file to `archive/`.

## Hand-off

### Verified facts

- V01.0R.02E封存準備：61711完整 `scripts/ci.sh --real` terminal exit0，`tmp/lab-station-route-engine/ci-cycle-complete.log` 全部hard gates green。離線與正式MCP十一套46案例逐項通過；各套scene_restored及五項全域控制全true。
- 完整CI後開回正式 `tmp/lab-station-electrode-guides-aligned/arm-seated.blend`，fresh oracle核對六就座鏈與四導線夾，`cycle-restored-formal.json`通過。無執行中的Blender工作。
- 同一不可變ClampStep資料驅動毛細管208／pH260步依序拆卸與反向重裝；移出件保持原位置並列入障礙，九段線路全程檢查。兩套MCP正式入口192.50／230.00秒；原始變換欄位的正常及callback中斷還原、指定障礙及故意遺留1mm反例均驗證。
- 兩張cycle-extracted PNG已實際檢視；維修移出件需手持支撐，非正常組裝懸浮。線長及Ø6mm仍為研究假設，不能作製造規格。
- 5S：研究細節移入歷史，沿用既有純資料／fixture／service邊界；無新增模組、依賴或公開工具。純資料238、維修fixture363、主fixture375行，未達380警戒。既有原始變換還原LESSON適用，不重複新增同義教訓。

### Open failures

- 固定取樣尚非連續掃掠、任意雙頭組合、螺紋／工具／手部空間、移出件支撐或材料／負載資格。
- 基座／LCD、電路與接口、載荷及實體試印未完成。幫浦／壓力／pH前端／供電板型號及線管外徑已詢問未答，不阻擋機構後續研究。
- Starlette TestClient偏好httpx2的警告待隔離環境相容性驗證；僅dry-run，尚未修改依賴。

### Next step

- 完成本輪02E提交、checkpoint、push、最終API部署及實際版本／十一套46案例讀回；全工作站保持ACTIVE。
- 接續連續間隙界限研究；GitHub FCL與MoveIt官方CCD來源已列09-references，需明確運動模型及薄障礙／擦邊／旋轉／不收斂控制，不能僅以API名稱稱連續資格。再推進基座／LCD、真實接口與物理資格。
- 依使用者持續推進要求，checkpoint後繼續，暫不要求清除對話。

## 歷史驗證紀錄

以下為逐輪證據與當時的下一步；接手只依上方現行段落與任務索引，不能將歷史下一步重新當成主線。

### V01.0R.02E 整合研究交接（封存前）

### Verified facts

- 61711完整 `scripts/ci.sh --real` terminal exit0，ci-cycle-complete.log 全部hard gates green。新正式MCP報告十一套46案例均passed、expected等於observed、每套scene_restored=true，五項全域控制全true；離線46案例此前已核對。完整CI後重新開回arm-seated，fresh oracle量測六就座鏈與四導線夾通過，cycle-restored-formal.json保存。尚未本輪升版／提交／最終部署。

- 55718兩張cycle-extracted預覽terminal exit0，六就座鏈與九段線路通過後出圖；兩張PNG已實際檢視，維修移出件需手持支撐，非正常組裝懸浮。26161完整靜態CI terminal exit0，T1／T2全部hard green，ci-cycle-static.log；T3待下列完整執行。74218 API預檢部署exit0，canonical MCP實讀11工具／11套46案例且health connected，cycle-preflight-catalog.json保存；版本仍02D，尚未本輪封存。5S：純資料238、共用維修fixture363、主fixture375，未達380；新控制加入既有MCP verifier，無新模組／依賴，沿用既有架構邊界。
- 9487正式登錄入口terminal exit0：毛細管192.50秒／pH230.00秒，各正常＋指定障礙兩案例passed、restored=true，均在300秒内；cycle-registered.json已讀。永久MCP verifier加入移動1mm後callback中斷的raw欄位還原檢查；52542正例通過，34323故意遺留1mm能被拒絕。研究注入初次清理因跨oracle命名空間變數不保留而失敗，60846由被注入函式globals恢復runpy並確認名稱run_path，正常控制重跑通過；cycle-restore-controls.json保存。沒有殘留patch。
- 78664 ordered-clamp-cables terminal exit0，298.37秒：兩頭208／260合計468列，機構與九段線路零hit，逐列已核對。所有移出實體持續列入障礙，研究結果ordered-clamp-cables.json。
- 既有純案例檔新增ClampStep／clamp_cycle_steps，完整絕對組位移描述兩螺栓、夾蓋組、各探頭組；反向重播同一資料。7項介面缺失先紅後29案例綠，登錄缺失KeyError紅後30綠；ruff與全mypy通過。新兩套cycle沿ServiceFixture／run_service_cases，來源目錄十一套46案例，公開工具不增；尚未部署。
- 36846共用拆裝執行器缺介面真機RED；47968GREEN，兩頭208／260樣本，正常／callback中斷都逐物件raw transform還原相等。重裝幾何包絡位移上界毛細管0.0000149012mm／pH0.0000149302mm，小於0.001mm；ordered-fixture-study.json記錄，取代先前無單位matrix殘差。helper不排除已拆件障礙，finally恢復原始欄位，尚需永久化此恢復正反例及正式全CI。
- 02D封存完成：5809ed4已推送；checkpoint74227、push81767、API部署98575及正式讀回全部exit0。transfer-deployed.json實讀02D、11工具、九套42案例，三服務監聽，工作樹封存後乾淨。
- 70517順序拆裝機構研究exit0：先兩螺栓−25mm，再夾蓋／螺母／外半襯＋25mm，再各探頭／內半襯＋25mm，隨後反向重裝；所有移出零件保留實際位置，不使用removed豁免。毛細管208、pH260合計468樣本零網格碰撞，ordered-clamp-study.json保存。83827初跑以1e-8矩陣殘差assert退出未產報告；70517用1e-6變換殘差門檻通過，但尚未記錄實測殘差，正式化時需記錄並以尺寸單位判定，不能稱精確還原。
- V01.0R.02D：完整 `scripts/ci.sh --real` session17505 terminal exit0；`tmp/lab-station-route-engine/ci-transfer-complete.log` 全部hard gates green。離線及正式MCP九套42案例逐項通過；MCP每套scene_restored與四項全域還原／非法輸入控制全true，已重讀新報告。
- 兩套單頭transfer各188取樣，14階段、13個相鄰邊界狀態一致：工作位鬆鎖、退齒、位移、轉腕、復位、維修位就座；另一頭全程保持鎖定。三關節干涉／已就座面隙與九段線路共用檢查，中途指定障礙反例各一列通過。終點採indexed_target(3,0)，前移4.637651516mm／抬高114.711320431mm。固定取樣不是連續運動資格。
- ServiceState／ServiceStep加入既有純資料檔，由同一ServiceFixture執行；MCP／離線共用入口，沒有新模組、依賴或公開工具（仍11項）。非有限、矛盾、陣列形狀／可變性、流程分派、障礙辨識均有先紅後綠證據，詳歷史。
- 完整CI後重新開啟正式arm-seated，再以fresh oracle量測六就座鏈與四導線夾通過，`transfer-restored-formal.json`保存。正式場景仍是`tmp/lab-station-electrode-guides-aligned/arm-seated.blend`；走線配置為`tmp/lab-station-module-configurations/cable-clearance.blend`。
- 兩張`transfer-seated-{head}.png`／blend由通過狀態重建，產圖前六就座鏈與九段線路再驗；圖片已實際檢視。線長與Ø6mm是研究假設，不能作裁線／製造規格。
- 5S：研究交接移至歷史；純案例201、配件250、主fixture375行，AGENTS75／CLAUDE7／project skill150。R55、MCP使用說明、機構文件與LESSON同步；架構仍使用既有資料／fixture／service邊界，沒有新增依賴方向。生成證據留tmp。

### Open failures

- 固定取樣不是連續掃掠、任意雙頭組合、材料／拉力或負載資格。新cycle已覆蓋保留移出件的完整依序拆卸／重裝取樣；螺紋、工具／手部空間與移出件支撐尚未資格化。
- 基座／LCD、電路與接口、載荷及實體試印未完成。幫浦／壓力／pH前端／供電板型號與線管外徑已詢問未答，不阻擋機構後續工作。
- Starlette TestClient偏好httpx2的警告仍待隔離環境相容性驗證；先前只有dry-run，未安裝或修改依賴。

### Next step

- 完整CI與正式場景讀回已通過，無進行中Blender工作。下一步整理交接／5S、升版／CHANGELOG／提交checkpoint／push／最終API部署及版本讀回；目前版本仍02D。
- 全工作站保持ACTIVE；延續共用資料／執行器，不重寫逐版測試。依使用者持續推進要求，checkpoint後繼續，暫不要求清除對話。



### V01.0R.02D 整合研究交接（封存前）

### Verified facts

- 95560 transfer-registered terminal exit0：兩套正式入口各兩案例全通過、restored=true；毛細管201.65秒／pH253.03秒，皆小於300秒，transfer-registered.json保存。82098兩張transfer-seated-{head}.png／blend產出前重新量六就座鏈及九段線路，已實際檢視，pH圖已展示。
- 86162 scripts/ci.sh terminal exit0，ci-transfer-static-final.log全部hard gates green。85563／41593先因container-narrowing守衛拒絕（formatter把說明移離呼叫），修正typed欄位不變式註記後獨立守衛及完整CI綠。關節三元组形狀／可變list反例先紅後38focused綠。沒有新模組；純案例202、配件250、主fixture375行；AGENTS75／CLAUDE7／skill150。
- 49447 API預檢部署exit0；啟動前約48秒尚未監聽，未重啟或改期限，live程序sample顯示事件迴圈，稍後health connected。43830 canonical MCP清單exit0，transfer-preflight-catalog.json實讀九套42案例。版本仍02C，這是完整CI前載入，不是本輪封存或完成資格。R55、MCP說明、機構文件及流程銜接LESSON已更新。
- 59180完整共用資料重播terminal exit0，376列全通過、416.89秒；另一頭保持三關節全鎖緊，indexed-full-transfer.json保存。新transfer兩套各一頭188取樣＋獨立中途障礙控制已登錄SERVICE_CASES（預期正式目錄九套42案例），沿用ServiceFixture／run_service_cases，不新增模組／依賴或公開工具。
- 轉移分派反例先紅（transfer-control-red.log，誤走verify_clamps）後59799真機綠；指定中途障礙被拒絕、只有一列控制觀察。控制辨識守衛擴含transfer，無關碰撞不得充當指定障礙。新登錄先KeyError紅→21案例資料測試綠；合計37focused與ruff／全mypy通過。順帶修正離線摘要被service_results覆寫而報錯單線案例數。尚未完整CI／部署／升版提交。
- 60782 indexed-closure-sequence terminal exit0，180列機構／九段線路零失敗（185.2秒）；工作位鬆鎖與維修位收緊各三關節，已就座關節逐列量面間隙。新ServiceState／ServiceStep及service_transfer_steps加入既有純案例模組，串為每頭188步；兩項測試先因缺介面紅後20綠，階段銜接、起終就座、移動全退齒及非有限／矛盾命令有守衛，ruff與全mypy通過。未接MCP／未完整CI／未升版提交。
- 6659 indexed-entry-sequence terminal exit0、360.87秒：196列機構／九段線路全通過，兩頭14個相鄰階段的六項姿態參數銜接一致；結果indexed-entry-sequence.json。路徑終點三關節已復位但未收隙，接續驗工作位鬆鎖與維修位收緊。總耗時超單套MCP300秒；整合需保留真實操作邊界與完整覆蓋，不能直接加長期限。
- 17872 indexed-service-study terminal exit0、34.66秒：indexed_target(3,0)及(1,1)兩候選、兩頭共四列通過；各頭三關節收隙取樣、全就座間隙、全場干涉、九段線路及134／164個別拆件樣本通過，indexed-service-study.json保存。選(3,0)前移4.637651516／抬高114.711320431mm進一步驗路徑；這只是終點研究，拆件時尚未同步線路觀察，不能稱完整流程通過。
- 02C封存完成：ab35ef0已推送；checkpoint23957、push80386、API部署15254、部署讀回36640皆terminal exit0。service-deployed.json讀回02C、11工具、七套38案例，API／Web／addon皆在監聽。
- 初始退齒研究：24774在抬高100mm卻強制腕部零角度咬合的起點出現六筆機構碰撞，wrist-raised-zero-release-rejected.json保存；零角度不是抬高後的可咬合齒位。85012改從工作位退腕齒，22取樣通過，wrist-working-release.json保存。
- 17432 terminal exit0，265.37秒：兩頭各依序退腕、退肘、退肩、抬高、轉腕、復位，共152取樣，機構與九段線路零失敗；十個相鄰階段邊界的五項姿態參數完全一致。service-entry-sequence.json與service-entry-sequence.log保存，host finally已開回正式arm-seated。這是研究，未接入正式MCP，肩肘最後仍退開2mm，亦未涵蓋承壓鏈初始鬆鎖。
- V01.0R.02C：完整scripts/ci.sh --real **88702 terminal exit0**，tmp/lab-station-route-engine/ci-service-complete.log所有hard gates green。正式MCP七套38案例、各套scene_restored與custom_property_oracle_controls／scene_preserved／exception_restores_scene／unknown_extra_code_missing_model_rejected全部true；mcp-verification.json已逐項重讀。無進行中程序。
- 878842 fresh開回arm-seated後，六承壓鏈與四導線夾讀回通過，service-restored-formal.json保存。正式場景仍是tmp/lab-station-electrode-guides-aligned/arm-seated.blend；走線通過配置是tmp/lab-station-module-configurations/cable-clearance.blend。
- ServiceProbe／WRIST_POINTS純資料與ServiceFixture分開，離線及MCP共用run_service_cases。兩頭腕部各32正常取樣；拆件130／156移動與4／8止擋；工作位兩個機構拒絕、兩個套件的線路障礙反例都通過。正式pH頭段family更新為412列研究通過值，其餘八段不變。
- ReplayCache僅重用完整不可變曲線／半徑／取樣資料，容量512、finally清理、回傳命中隔離；實體障礙照常重建。47486完整412列與未重用基準逐列相等，726.12→352.43秒；此為研究總耗時，不是单套MCP時間。正常取樣覆蓋未減；工作位反例直接驗機構前置條件。
- 反例辨識曾接受障礙尚未加入前的無關碰撞，34635真機紅→91886綠；永久守衛要求指定障礙已建立且被命中。31855工作位控制1.30秒，毛細管step12碰distal_pin、pH step21碰杯；service-working-final.json保留原因。案例資料缺模組、未知登錄、cache缺介面等紅綠詳見下方歷史。
- 可見預覽service-temperature-extracted-25.png／blend由同一通過family產生，另有本輪重建的motion-*圖；溫度探頭移出25mm圖已檢視並展示。線長與Ø6mm仍是研究假設，不能作裁線／製造規格。
- 5S：新增純案例78行、Blender維修配件182行；走線365、主fixture375、案例367，未達380警戒。AGENTS75／CLAUDE7／skill150。沒有新依賴／公開工具；GitHub MoveIt／trimesh來源、R54、LESSON、MCP與機構文件同步；既有研究交接移入下方歷史，生成證據留tmp。

### Open failures

- 固定取樣不是連續掃掠、任意雙頭組合、材料／拉力或負載資格。当前腕部案例涵蓋退開位置上的旋轉及復位，完整起始軸向退齒路徑仍需補入順序操作驗證。
- 個別拆卸路徑以removed前置條件檢查，尚非完整依序拆卸／重裝。基座／LCD、電路與接口、載荷及實體試印未完成。幫浦／壓力／pH前端／供電板型號與線管外徑已詢問未答，不阻擋機構後續工作。
- Starlette TestClient偏好httpx2的警告仍待隔離環境相容性驗證；先前只有dry-run，未安装或修改依賴，不以隱藏警告代替修復。

### Next step

- **目前live：17505完整scripts/ci.sh --real**，ci-transfer-complete.log；source／環境凍結，不啟動第二個Blender工作，輪詢同handle至terminal。靜態86162、兩套正式入口95560、預檢API49447與canonical目錄43830已terminal，不要重跑。完整CI通過後逐項讀engine-verification／mcp-verification九套42案例與恢復控制、開回正式arm-seated讀回六就座鏈，然後5S／升版CHANGELOG／提交checkpoint／推送／最終API部署與版本讀回。全工作站仍ACTIVE，完整順序拆裝未完成。
- 保留全工作站目標。下一工程項目是按真實先後次序的拆卸／重裝與初始軸向退齒取樣，再處理取樣間隙的保守界限及真實接口；沿用資料／共用執行器，不重寫逐版測試。


### V01.0R.02C 整合研究交接（封存前）


### Verified facts

- **目前live：完整scripts/ci.sh --real session88702**，日誌tmp/lab-station-route-engine/ci-service-complete.log；必須輪詢同handle至terminal。source／環境凍結，不啟動第二個Blender工作。70643 API預檢部署terminal exit0，health connected，正式MCP list_verification_suites已讀回七套38案例。版本仍02B，這是驗證前載入、不是完成封存；下一步待完整CI，若失敗先確認工作排空再修復。

- 新SERVICE_CASES／WRIST_POINTS與ServiceFixture已接共用run_service_cases、離線run及run_registered，目錄成為七套38案例，公開工具仍11項。資料矩陣先因缺模組紅後18綠；登錄先Unknown suite紅。43086兩套首次真機terminal exit0：腕部123.89秒／3案例、拆件274.98秒／5案例，均小於300秒；service-registered.json保存，正式MOTION_FAMILIES已換成完整412研究通過的新pH曲線，其他八段不變。
- 34635反例辨識先紅：注入障礙前的無關碰撞被誤當blocked通過。要求自己的blocker存在且被命中；91886同反例綠，共用run_service_cases永久先跑辨識守衛。工作位反例改直接verify_clamps機構阻擋，不跑該非法姿態上的額外走線；正常286移動／12止擋覆蓋不減。31855 terminal exit0、1.30秒，兩頭分別step12碰distal_pin、step21碰杯，service-working-final.json；整套最新時間仍待真機CI，不能以274.98秒宣稱最終版本時間。
- 2189 scripts/ci.sh terminal exit0，ci-service-static.log：T1／T2全部通過；41focused、全mypy與ruff通過。T3尚未跑，不作完整交付證據。新增兩模組依責任分為純案例資料與Blender維修配件，未增加外部依賴；建前重讀MoveIt GitHub，09-references記錄來源。LESSON／13使用規格／R54／11MCP文件同步，正式部署與完整CI待執行。

- 正式ReplayCache加入既有lab_cable_routes（365行），只保存完整不可變輸入的sample／chain／self／pair，有界512、每個context finally清除；candidate_hit回傳命中deepcopy，實體obstacles每姿態照常讀。validate_motion接受可選cache，舊呼叫預設不變。lab_cable_motion_checks共用真機入口新增參數／線徑／誤差敏感度、容量、正常／例外清理、跨context隔離與移動實體clear→blocked→clear控制；cache-controls-red.log先因缺介面紅，3253／31541／44981正反例exit0。55相關單元、全專案mypy、ruff通過，尚未完整CI。
- 47486正式介面完整重播terminal exit0：service-cable-cached.json的412列與原service-cable-study.json逐列完全相同，62motion／64wrist／286clamp、各頭結果相同；耗時352.43秒對726.12秒，減51.46%。service-cache-equivalence.json保存比較，仍超MCP300秒單套期限。後續須依實際操作邊界（既有motion、腕部調整、單頭拆件）建立可重用Scenario與各套完整負控制，不能減取樣或只增加期限。正式families尚未更換，MCP新增維修尚未接線；host finally已開回arm-seated，無進行中程序。

- 33443直接monotonic計時terminal exit0：8個九段拆蓋樣本11.19秒，sample_path72／sample_chain48／self72／pair216，只有9組boundary。13728同8樣本局部lru重用研究terminal exit0：4.44秒，純曲線取樣9／串接6／self9／pair27；實體first_hit仍72次、障礙重建8次，兩次全零hit。service-replay-timing.json與service-replay-reuse.json保留原始計數。快取僅在研究patch上下文內、有界512、完整參數key、回傳deepcopy；不是正式實作／完整412等價性／負控制證據，不能外推已符合300秒。host finally已開回正式場景，無進行中程序。下一步正式窄介面先驗key變動、負碰撞、作用域與回傳隔離，再重播完整412。

- 39677預覽terminal exit0：由通過的溫度探頭移出25mm資料重建姿態，重新求九段並驗證零hit後產出service-temperature-extracted-25.png／blend；PNG已實際檢視，主場景開回arm-seated。80882短段cProfile量測terminal exit0，8個完整九段樣本，service-replay-profile.prof／txt／log；可見重複sample_path／sample_chain及self／pair查詢，但含socket／thread活動與異常遞迴計數，不拿累積時間當精確耗時占比。後續用直接計數與monotonic計時確認，再做局部重用與等價性反例；無進行中程序。

- 62253九段整合研究terminal exit0，726.12秒：62動作＋64腕部＋286拆裝共412列，九段全經validate_motion，零碰撞／不可求解；service-cable-integrated.log及service-cable-study.json已核對完整數量、分段與四組passed。新pH family保持170mm，其餘八段不變；研究超過MCP300秒期限，不能直接接成一套或加長期限，須量測改善重複計算。正式MOTION_FAMILIES尚未更換。

- 5566細化搜尋terminal exit0，23.08秒：79個可定長候選經8個關鍵場景筛選，78個拒絕、1個保留；仍170mm，handles=(16.735425442991854,36.82519863370539,32.582306825290274,35.333156374931896)，side=1。43705針對變更線完整重播terminal exit0：62動作＋64腕部＋286拆裝共412列，零失敗，229.35秒；service-family-replay.json。這是變更線對完整prefix及所有其他線／實體的檢查，尚須九段整合。

- 57578候選研究terminal exit0：維持pH頭段170mm，搜尋前5個候選有2個端點碰撞、3個在抽出25mm處淨空且對85組既有／拆卸端點可求定長；service-family-discovery-first-rejected.json。這只證明端點碰撞與定長可行，尚非全姿態淨空，不改正式MOTION_FAMILIES。
- 83945候選重播terminal exit0但三組全被淘汰：候選0／1於pH升40／90mm碰溫度線，候選2通過62動作及64腕部取樣，但溫度探頭側移10mm碰pH線；共319列／201.41秒。service-family-replay-first-rejected.json保留三組完整參數、失敗姿態與距離；碰撞餘量未放寬，正式MOTION_FAMILIES未變。

- 維修觀察介面：verify_clamps增加可選observe(label, moving_names, removed_names, signed_step_mm)，使用不可變名稱tuple且在該步幾何通過後呼叫。79342先因缺observe紅，35473綠；78356永久單頭真機入口綠，核對130／156移動觀察共286，另12個止擋合計298；非法頭部與觀察者在step1拋錯後的完整變換還原均通過。ruff／mypy及21文件／預算守衛綠，check模組378行，後續擴充需按責任拆分，不能壓行。
- 線束耦合研究29864 terminal exit0但幾何資格未全過：毛細管130移動取樣通過；pH probe_-7側移19mm時pH_temp/0/head既有family不可求定長，總176樣本／288.82秒，service-cable-study-original-failure.json保留。只有退出碼不能作通過證據。每步仍使用同一fit_family／validate_motion與removed障礙排除，沒有放寬碰撞。

- 02B後續單頭維修：verify_clamps新增可選labels，保留無參數雙頭行為，空／重複／未知頭部拒絕。service-clamp-red.log先因缺labels失敗（66bba8）；24031研究綠，88220共用真機入口綠：capillary134、pH164，共298個裝配／止擋樣本，另一頭保持工作位且原始變換最後完全恢復。永久verify_single_head_service加入既有lab_electrode_readback_real，由配置驗證呼叫；沒有新模組／依賴，尚未完整CI／升版／提交或接入MCP維修套件。
- 研究中直接比較移回後matrix_world暴露至多1.49e-8的浮點差異（78745）；幾何恢復採1e-7矩陣容差，另一頭仍要求完全不變，外層preserve_current_scene後原始變換欄位要求完全相等。兩個正例通過；工作位capillary螺栓在step12撞distal_pin，pH探頭在step21撞杯，不能統稱杯內碰撞。single-head-service.json／single-head-service-gate.log保存實際原因。ruff／mypy及21項文件／預算守衛通過；無進行中程序，正式arm-seated已開回。
- 02B封存後確認：ecc434b已推送；checkpoint56771 C1–C5通過，API82377部署exit0，wrist-deployed.json確認02B、11工具、五套30案例與62姿態scope。

- 依賴警告只讀盤點：目前FastAPI0.135.3／Starlette1.3.1／httpx0.28.1，httpx2未安裝；官方https://starlette.dev/testclient/與https://github.com/pydantic/httpx2確認新TestClient偏好httpx2。31649 dry-run terminal exit0，httpx2-dry-run.json／log顯示候選2.13.1會安裝httpx2／httpcore2／truststore並更新idna到3.20，未實際安裝或修改pyproject。需本輪封存後在隔離環境驗證相容性，不以隱藏警告代替修復；目前回歸環境保持不變。

- V01.0R.02B：完整CI94709 terminal exit0，ci-wrist-state.log所有hard gates green；正式MCP五套30案例與custom_property_oracle_controls／scene_preserved／exception_restores_scene／三拒絕控制全true，mcp-verification.json已重讀。97012另以fresh命令開回正式arm-seated並讀回六承壓鏈與4導線夾通過，wrist-restored-formal.json留證；無進行中真機程序。
- 32 focused服務／MCP adapter／HTTP／DCC測試通過（64755）；附Starlette TestClient使用httpx的既有套件棄用警告，功能未失敗，後續相容性盤點仍需留意。97115維修預覽exit0，两頭service-wrist-{head}-final PNG／blend已產出，pH圖已實際檢視，正式arm-seated已重新開回。

- 02A後續維修研究發現既有場景恢復漏掉head.tip_release_mm，且原旁證也採同一窄清單。98487真機負對照exit1：0.321變成2.0，wrist-state-red.json／log；25592旁證敏感度負對照exit1，新增巢狀屬性未被偵測（property-oracle-red.json）。不能把02A舊旁證當完整自訂屬性恢復證據。
- preserve_current_scene補tip_release_mm；獨立SNAPSHOT改取所有物件自訂屬性，明確轉換群組／陣列，未知型別失敗。MCP驗證入口加入新增／巢狀變動的旁證控制、capillary非預設0.321與pH原本缺該屬性的情境，例外路徑也改腕部狀態。3271 exit0：0.321完整還原且新增／巢狀控制通過；ruff及兩檔mypy通過；完整CI及版本結果見上。
- 50610維修研究terminal exit0：單頭抬100mm，另一頭留工作位；各21個退齒旋轉位置＋11個軸向復位，共64姿態。沿用02A九段family，verify_pose與走線replay皆零碰撞，service-wrist-study.json／log，145.39秒；已恢復正式arm-seated。此研究尚未進MCP，也不涵蓋拆蓋／取探頭／重新鎖緊或连续掃掠。


- 5S：沿用恢復模組362行及獨立MCP檢查器159行，無新生產模組／依賴／公開工具；AGENTS75／CLAUDE7／skill150行。02A封存資料已移至下方歷史，修正現行交接的舊「無CI執行中」敘述；LESSON與MCP契約同步，生成證據留tmp；22140封存前文件／版本／預算22項守衛通過。

### Open failures

- 62離散姿態的完整三線已通過完整CI與正式MCP。取樣間連續掃掠、任意雙頭組合、實體接頭、材料／拉力未驗。Ø6mm、底座200／跨肘150／頭段220或170mm僅研究假設。
- 雙頭同抬拆蓋碰撞尚在；一次一頭維修研究需整合共用情境。基座／LCD、電路、載荷、物理試印未完成。已詢問幫浦、壓力感測器、pH／供電板型號及線管外徑，未答；不阻擋機構驗證。

### Next step

- 效能前置只讀查找：[trimesh caching.py](https://github.com/mikedh/trimesh/blob/main/trimesh/caching.py)以資料身份變化使快取失效。若412列整合超過既有MCP300秒期限，先量測sample_chain／nonlocal_self_hit／pair_hit的重複運算，評估每次suite限定生命週期、以完整不可變曲線／線徑／取樣資料作key的重用；實體場景碰撞不可只以物件名稱快取。尚未改演算法或引入依賴，須先紅綠敏感度與等價性證據，不能降低取樣或直接加長期限。

- 新維修模組前已查閱 [MoveIt Task Constructor](https://github.com/moveit/moveit_task_constructor)：共同場景介面串接相依階段。採用其明確階段狀態的思路，沿用本專案Scenario／幾何檢查，不新增ROS依賴。verify_clamps目前298個裝配／止擋取樣是兩頭合計；拆件的moving／removed集合需成為可重用資料，並驗證前置條件、單頭隔離與失敗恢復。此為設計接手，尚未實作或取得完整維修資格。

- 共用MCP維修登錄已接線；下一步API載入新目錄後完整scripts/ci.sh --real，核對七套38案例、每套300秒與正常／例外還原，接著更新VERSION／CHANGELOG並checkpoint提交部署；幾何單頭選擇、286個觀察及例外還原入口已通過focused。不要再用inspect.getsource改写函式。94709／97012／88220均已terminal，不重跑或輪詢舊handle；新完整CI待本輪功能整合。

- 下一工程項目為取樣間隙保守界限、單頭維修與真實接口；保留全工作站目標。關節退齒／調整／重新鎖定搭配線束亦需完整操作驗證；62線路姿態不代表這些操作已全部取得資格。
- 正式場景tmp/lab-station-electrode-guides-aligned/arm-seated.blend；重測走線開tmp/lab-station-route-engine/motion-lift-pH_temp-+000-000.blend。證據與六組動畫在tmp/lab-station-route-engine/。



### V01.0R.02A 封存接手

- V01.0R.02A：完整scripts/ci.sh --real（37008）terminal exit0，ci-motion-recipes.log所有hard gates green。T1／T2及全部真機回歸通過，包括正式MCP五套30案例、場景正常／例外恢復與非法輸入拒絕。無進行中CI。
- RouteFamily／fit_family加入既有純規劃模組，continue_route共用定長求解；MotionPoint與九段MOTION_FAMILIES加入既有情境資料。family與動作資料各先紅後綠（family-red.log、motion-points-red.log）；50focused及全專案mypy通過。
- 真機54828正反例通過但需290.29秒。重用既有「全配對碰撞檢查不等於每配對都要重建幾何」LESSON，96646計數負對照exit1，兩姿態單段取樣72次；區域快取後50962 exit0為18／18。每姿態重建、不跨姿態保留；完整同線自碰與異線配對不減少。計數守衛納入MotionFixture。
- 80234 terminal exit0，正反例降至208.51秒（motion-recipes-cached.log），原單套300秒期限不變。完整CI的engine-verification.json兩motion案例各62replay／558單段取樣；正例零hit，反例只拒絕pH lift(0,50)與mixed(10,50)。MCP重測新錨點，不讀tmp研究結果或舊通過旗標；family身份／尺寸不符拒絕。
- 62張motion-{path}-{head}-{forward}-{lift} PNG／blend由共用資料產生；兩頭mixed中間及pH raised-reach−20圖已目視檢查。46346編碼exit0，六组motion-{path}-{head}.gif完成；獨立framemd5核對lift／mixed11、raised-reach9個不同姿態，ffprobe確認800×680，63／51解碼幀，沒有物理補幀。
- 完整CI後21177 fresh開回arm-seated，再讀六承壓鏈與4導線夾通過，recipes-restored-formal.json保存。版本工具已升02A。
- 5S：沿用四個模組及兩單元檔，225／132／244／366行，均低於380警戒；無新增模組、公開工具或依賴。規格、MCP用法與R53同步；029與研究交接移下方歷史。生成證據留tmp，封存前22項文件／版本／預算守衛通過（83895 exit0）。

- 37008已terminal exit0，無進行中驗證。來源不變不需重跑完整CI；部署讀回的預期為02A、五套30命名案例，motion scope為62姿態。

### V01.0R.029與後續研究接手

### Verified facts

- 029後續研究：73058 terminal exit0，兩頭各raised-reach（抬100mm後前後−20到+20mm／5mm步距）及mixed（每步前2mm／升10mm），40姿態找到共用九段family，逐姿態replay零碰撞，mixed-discovery.json。69161 terminal exit0再合併原22純升降姿態，共62姿態搜尋及replay全通過；搜尋199.67秒、含replay311.10秒，combined-discovery.json。此為研究入口，尚未納入公開MCP情境或新完整CI；現有MCP仍029五套30案例。
- 18535 terminal exit0，用上述同一組控制點輸出combined-reach--20／+00／+20三張PNG與blend，+20圖已目視檢查，正式arm-seated已重新開回。研究無生產／測試來源變更；新資料暫留tmp/lab-station-route-engine。

- API52128部署exit0，正式MCP五套30案例讀回通過。
- V01.0R.029：重用candidates的定長求解為_fit_route，continue_route固定handle family／side且保持線名、長度、線徑和lead；新的單元先缺函式紅→綠，彎曲半徑約束先紅→綠。31focused通過，82599完整CI terminal exit0，ci-motion.log所有hard gates green；正式MCP五套30案例與場景正常／例外恢復、三拒絕控制均通過。
- 61476原工作位分支延續研究terminal exit0但有幾何失敗：毛細管11姿態通過；pH抬20／30mm異線包絡接近，40–100mm pH跨肘原family無解，continuation-discovery.json保留。不能改寫成通過。
- 新lab_cable_motion只負責跨姿態選擇，沿用lab_cable_routes.candidate_hit同一碰撞判準；68146共同分支22姿態search成功，89.1秒，motion-search.json含九段各姿態控制點及拒絕原因。還不是連續掃掠或材料證明。
- 新lab_cable_motion_checks提供資料式MotionFixture，正例與兩端清楚／中段固定方塊阻擋反例；MOTION_CASES與MCP第五套electrode-cable-motion已接線。新增模組前已查GitHub OMPL／PyElastica，無新依賴。55082 terminal exit0，正例22姿態通過，反例只在pH升50mm被方塊拒絕，端點距離35.46mm；217秒低於300秒既有套件期限。



- 完整CI後fresh開回arm-seated，六承壓鏈與4導線夾讀回通過，motion-restored-formal.json留證；mcp-verification.json重讀30案例。
- 22張motion-* PNG及blend由選定路徑直接產生，兩頭中間姿態已目視檢查。ffmpeg合成motion-capillary.gif及motion-pH_temp.gif，各800×680、6.1秒、61解碼幀／11不同姿態；52041編碼及獨立framemd5核對通過。沿用系統ffmpeg，沒有安裝Pillow或其他依賴。
- 5S：motion選擇169／fixture121／主fixture362／靜態走線334／純規劃208／案例271行，均未達380預警；指示75／7及skill150行。GitHub來源、MCP用法、R52與LESSON同步；028交接移入歷史。封存前22項文件／版本／預算守衛通過（30183 exit0）。

### Open failures

- 三條完整線已驗兩頭各11個升降取樣姿態並保持同一曲線分支；取樣之間的連續掃掠、前後伸縮／混合動作、實體接頭、材料／拉力仍未驗。Ø6mm是假設，每條底座200mm／跨肘150mm，加頭段220／170／170mm均僅研究長度。
- 候選配置雙頭同抬拆蓋仍有碰撞，一次一頭維修研究尚未進入共用情境。底座／LCD、電路、載荷與實體列印待完成。已向使用者詢問幫浦、壓力感測器、pH／供電板型號與線管外徑，未有回覆；可繼續機構驗證。

### Next step

- 本輪研究已全部terminal，無進行中Blender程序。將姿態抽象為含forward／lift／path的資料，沿用motion模組；不能只存lift而遺失前後位置。62姿態搜尋＋replay已超過單套300秒，下一步評估把離線選定family作可驗證參數資料，runtime只重驗全部姿態與負控制；不得直接加長期限或拆成各自重選不同family。尚未實作，先以TDD證明資料接線與完整覆蓋，再真機驗證。

- 82599已terminal exit0，無進行中真機程序。下一工程項目為前後伸縮／混合動作、取樣間隙的保守界限及單頭維修情境；不能只增加端點。部署讀回應為五套30案例。
- 後續以Scenario資料＋共用執行器＋可清理配件擴充姿態變形與單頭維修；MCP共用同一登錄，不複製逐版測試。走線仍用RouteCase／RouteSearchSpec。
- 正式場景tmp/lab-station-electrode-guides-aligned/arm-seated.blend，證據tmp/lab-station-route-engine/；完整工作站目標保持ACTIVE。



### V01.0R.028 封存接手

- API44157部署exit0；正式MCP目錄確認四套28案例。86288完整CI terminal exit0，ci-chain.log所有hard gates green；包含四套MCP28案例、正常／例外場景還原及三拒絕控制。
- V01.0R.028：擴充既有sample_chain／select_route.prefix，同線三段合併查接點、切向、半徑及非局部自碰；BundleFixture改讀配置路徑，異線全段納入occupied。無新模組或依賴；28focused通過，mypy／ruff格式通過（測試import排序曾失敗，已修正）。
- 研究45614因重載清單漏掉直接引用入口失敗，沒有執行幾何；改從研究入口推導closure，3544 exit0，九段各自淨空且各線串接無自碰。正式共用fixture 50657 exit0，10控制與三個九段姿態通過，chain-focused.json留證。
- sample_chain單元先缺函式紅→綠；CHAIN_CASES登錄先缺資料紅→綠；整批離線等待預算兩案例先紅→綠，按登錄套件數乘既有300秒，讀場景60秒及單一MCP期限不增。65792共用離線入口terminal exit0，chain-preview.log：10接觸、7線對線、4單段、4頭段組合、3完整鏈，共28案例通過。三張chain-*預覽已實際檢視，底座口仍是假定外部端點。



- 完整CI後fresh開回arm-seated並讀回六承壓鏈及4導線夾通過，chain-restored-formal.json留證。正式MCP量測報告重讀共28案例。
- 5S：走線326／配件346／規劃178／案例250行，指示75／7及skill150行，無新模組或依賴。R51、MCP目錄、走線說明與跨段LESSON同步；R50／R51表格斷行修正，027交接移入歷史保留。


### V01.0R.027 封存接手

- V01.0R.027：沿用lab_cable_routes加入雙線保守包絡／occupied候選排除；資料表新增7線對線案例與4三線組合情境，無新模組。GitHub查trimesh後保留既有KDTree。PairFixture先因缺pair_hit紅，補實作後通過；30focused測試、ruff及mypy通過。
- BundleFixture真機77405 exit1，bundle-suite.json保留：只抬pH/temp100mm時，pH150mm的43候選皆碰實體（下臂24／平台被動軸12／卡扣5／平台2）。86068固定170mm研究三姿態各三線通過，bundle-length-study.log／json留證；BUNDLE_ROUTES固定220／170／170mm，非裁線規格。
- 19560離線入口terminal exit0，bundle-final.log：8接觸、7線對線、4單線、4三線案例全通過；engine-verification.json保存量測。三線工作／分別抬高100mm三張PNG及blend已產出並目視檢查；放大保留線包絡反例須全因wire_contact拒絕。
- 部署API64673 exit0。15556正式MCP初始連線502、尚未進套件；健康檢查恢復後70943 terminal exit0，mcp-bundle-rechecked.log：三套23案例、場景完整還原、三拒絕控制及例外恢復通過。24112完整CI terminal exit0，ci-bundle.log所有hard gates green。


- 正式場景已開回arm-seated；一次讀回腳本誤用不存在的導線模組名後已修正，50652 exit0，六承壓鏈及4導線夾均通過，bundle-restored-formal.json留證。
- 5S：走線322、配件326、案例199行；指示檔75／7、專案skill150行，無新模組／依賴。來源、R50、MCP使用文件與研究範圍已同步，026交接移到歷史段落保留。封存前22項文件／版本／預算守衛通過。


### V01.0R.026 封存接手

- 測試模組化已於025封存。使用者明確更正為整合MCP（非MVP），授權公開目錄由九項擴至十一項；新增list_verification_suites／run_verification_suite。
- 新VerificationService經窄port取得typed量測，REST與MCP注入同一AppRuntime服務／序列化Blender port。目錄由同一案例表推導兩套：8接觸控制、4探頭走線；不接受任意程式或路徑。漏跑、重複、錯誤套件、偽造成功與未恢復場景均拒絕；真實檢查未通過則回passed=false報告。
- 公開驗證保留目前模型、原始transform欄位、關節屬性與選取，清除自己建立的物件和mesh。單獨正式MCP93114 exit0（mcp-final-rechecked.log）：12案例、未知名稱／多餘code／缺模型三拒絕、非預設姿態、例外恢復通過；獨立socket前後快照核對物件、網格、姿態、選取、目前檔案與render path。
- 矩陣指定恢復造成小數漂移，被獨立比較抓到；改保存原始變換欄位，未放寬容差。MCP重測51746曾在工具清單遇入口502，正式health恢復後93114通過；不是模型失敗。
- 完整CI5235排版失敗，T2時明確停止143，未進真機；格式修正後完整CI82324的chat讀回失敗即停。單獨3496回報0/1卻exit0，查明舊chat harness未判退出碼、WS90秒短於服務300秒。兩個負例先紅後綠，沿用VerificationSummary與固定五項涵蓋；先清理再量基線，WS360秒／oracle60秒。14 focused tests和mypy通過，97647真機5/5 exit0（chat-isolated-fixed.log）。
- 完整CI31824 exit1：T1/T2、REST／MCP／chat／readiness／batch通過，lab_station生成超過既有oracle180秒；日誌ci-mcp-complete.log。只讀barrier81472 exit0，確認背景生成完成。generator原採同一180秒oracle，現只對生成沿用正式GENERATOR_TIMEOUT_S=900，讀回／skip不變；新deadline測試先1紅1綠，修正後通過。V01.0R.026完整重跑30499 terminal exit0，ci-mcp-deadline.log所有hard gates green；包含新增MCP套件、完整chat五項與所有模型交付回歸。
- 正式arm-seated場景還原41822 exit0，六承壓鏈與required導線夾fresh重讀通過，mcp-restored-formal.json留證。34項文件／版本／架構／budget守衛通過。
- 5S：MCP adapter305、Blender配件212、新真機入口127行，指示檔75／7、專案skill150行；沿用Scenario／VerificationSummary與marker解碼，無外部依賴。架構SSOT／AST錨點、工具目錄、ADR007、R49、使用說明與兩條LESSONS守衛同步；HTML已實際渲染檢視，產物留tmp。


### V01.0R.025 封存接手

### Verified facts

- 測試已分層：`scenario_runner.py` 共用非空唯一案例／量測／必清理／完整涵蓋判定；`cable_route_cases.py` 8個接觸與4個實際姿態資料；`lab_cable_route_checks.py` Blender配件；原真機入口只保留連線、重載和finally開回正式檔。沿用VerificationEvidence／Summary，不新增測試框架。
- TDD：新執行器測試先因缺模組紅，再10項綠；案例矩陣與重載守衛後共21項通過。mypy及ruff通過。26793單獨真機terminal exit0，四路徑完整rows與024報告逐欄相等；`modular-equivalence.json`保留相等與8／4案例證據。V01.0R.025完整CI4762 terminal exit0、all hard gates green，日誌 `tmp/lab-station-route-engine/ci-modular-tests.log`。正式場景已fresh核對六承壓鏈與導線夾，`modular-restored.json`留證。
- 每例保存穩定名稱、expected、observed、detail及量測；量測例外不能被當成預期拒絕，清理失敗立即停，漏跑／重複／順序錯誤不可通過。六個表面案例各自建立並移除鏡射方塊；自接觸與正常直線都具名，不再手寫True表。host用finally還原場景，傳輸逾時仍須先排空。
- 5S：共用執行器88、案例93、Blender配件118、真機入口29行，均低於380预警；不新增外部依賴或公開工具。先查pytest GitHub／官方參數化文件並重用現有結果格式；13使用方式、R48與09來源同步。

### Open failures

- 模組化不擴大測試資格：四個走線案例仍各自獨立，整束線間距、跨段、中間變形與材料／拉力未驗。Ø6mm是假設；220／150mm不是裁線規格。
- 候選配置雙頭同抬拆蓋仍有碰撞，一次一頭的維修研究尚未進入共用情境。底座／LCD、電路、載荷與實體列印待完成。

### Next step

- **使用者最新要求：**測試也要模組化，並明確更正為整合到MCP（非MVP）。本輪先封存已驗證的共用測試，再提供固定目錄的list_verification_suites／run_verification_suite，經同一AppRuntime／序列化Blender port執行；不接受任意腳本。預計接觸控制與探頭端走線两套，測試後須恢復目前場景姿態／選取／臨時物件。此為明確授權擴充原九項公開工具契約，需同步schema／契約／真機測試與部署。

- CI4762已terminal exit0，無執行中的驗證。下一步實作上方使用者要求的MCP整合；真機仍串行，逾時先排空同一handle。
- 後續測試以Scenario資料＋共用執行器＋可清理配件擴充，不複製逐版測試腳本；走線仍走既有RouteCase／RouteSearchSpec。
- 正式場景 `tmp/lab-station-electrode-guides-aligned/arm-seated.blend`，研究／新證據 `tmp/lab-station-route-engine/`。下一工程項目仍為跨段／線間距與單頭維修情境。


### V01.0R.024 封存接手

### Verified facts

- 共用柔性走線入口已建立：`cable_paths.py` 純毫米曲線與保守細分、`cable_path_plan.py` 不可變邊界／搜尋配置與候選、`lab_cable_routes.py` Blender錨點量測／實體與自接觸檢查／呈現。後續變體只改 `RouteCase`／`RouteSearchSpec`，不複製生成器。
- V01.0R.024：18項曲線／規劃單元測試通過；單獨真機73888及完整CI28222均terminal exit0，all hard gates green；日誌 `tmp/lab-station-route-engine/ci-route-engine.log`。完整CI再次通過8個控制、4個單線單姿態案例與既有全部回歸。
- 毛細管頭段220mm研究長度，在工作／單頭抬高100mm的幾何候選分別拒絕39／19個候選後找到淨空線路；取樣最小曲率半徑約12.78／15.96mm。pH與溫度頭段150mm工作位亦找到候選。報告保存配置、錨點、控制點、長度上下界和拒絕原因。
- 曲線長度以弦長／控制多邊形長度夾住；碰撞半徑含取樣步距與曲線偏差餘量。終端只能接在實際外向表面，完全埋入、自接觸、穿透、半徑變大及鏡射網格有真機對照。保留全部有界候選，避免平順排序提前截斷可行路徑；新教訓与測試同步。
- 5S：現有023配置入口及69件讀回沿用；新模組142／157／276行，真機入口83行，低於380預警；無新依賴或公開工具。先查bezier GitHub與官方文件，來源見09-references；生成資料仍只在tmp。

### Open failures

- 以上四案例各自獨立，尚未證明整組線束、跨段線間距、中間變形、材料最小半徑、保持力與拉力。Ø6mm是假設；220／150mm不是裁線規格。
- cable-clearance仍是候選配置；雙頭同抬拆蓋有碰撞，研究的一次一頭298維修樣本尚未整合成共用操作情境。
- 整機底座／LCD、電路、載荷、材料及實體列印資格仍未完成，沒有可宣稱整機合格的製造STL。

### Next step

- 完整CI28222已terminal exit0，無正在執行的驗證。兩張毛細管預覽已檢視；正式場景重新開啟、fresh命令查六承壓鏈與導線夾，證據 `tmp/lab-station-route-engine/restored-formal.json`。Blender仍須串行，逾時先排空同一handle。
- 之後從同一走線入口擴充跨段／線對線與連續姿態檢查，另將單頭維修次序資料化。禁止複製逐版產生器或source字串替換。
- 正式場景仍為 `tmp/lab-station-electrode-guides-aligned/arm-seated.blend`；路徑研究在 `tmp/lab-station-route-engine/`，配置研究在 `tmp/lab-station-module-configurations/`。


### V01.0R.023 封存接手

### Verified facts

- V01.0R.023：完整 `scripts/ci.sh --real` 87822 terminal exit0，所有 hard gates green，日誌 `tmp/lab-station-module-configurations/ci-module-configurations.log`。T1/T2、既有電極臂完整動作／拆装／承壓／讀回，及新配置讀回均通過。
- `scripts/lab_electrode_module.py` 從主檔搬出93行零件建構；主檔306行，domain367行，clamp288行，未提高380行預警門檻。`ProbeHeadSpec`、`ElectrodeAssemblySpec` 與唯讀 `ELECTRODE_ASSEMBLIES` 保持尺寸／位置唯一來源。`build_scene(configuration, output=...)` 共用入口，輸出隔離，場景存 `electrode_configuration`。
- baseline 與 cable-clearance 均69件，共用入口連建原版、候選、候選重建：單殼／非流形、夾座與探頭實際14mm偏移、杯位−6mm、另一頭／腕軸／平台不變、重建不累加皆通過。`configuration-readback.json` 是整套CI中的證據；先前34509單獨重建亦通過。
- 原始配置測試因缺少規格介面而紅；76536實體差異檢查拒絕候選非流形。`_solid_boolean` 將中間清理收進共用圓角夾座路徑，再驗兩配置通過。13項配置／夾座、18項配置／預算／嵌入碼、50項相關測試通過，完整CI亦涵蓋；既有教訓「中間輸入有效」及「消費端須跟上參數」已有守衛，不重複追加教訓。
- 研究保留 `tmp/lab-station-full-route/README.md`：114姿態、298單頭維修取樣、出線候選與失敗證據；十份舊夾座字串替換腳本已搬到 `archive-generators/`，不得作新變體入口。跨肘51樣本研究仍見 `tmp/lab-station-cable-lift/README.md`。
- 84634 terminal exit0：baseline與cable-clearance保存檔重新開啟，場景配置與輸入規格相符，兩張PNG已目視；`baseline-saved-configuration.json`／`cable-clearance-saved-configuration.json`保留讀回內容。
- 5S：新增的是共用模組及其測試，不是另一份設計變體；無新依賴／公开工具。R46、13模組配置、09來源更新。先查cqparts／blender-cad並沿用本專案既有spec/instance模式，未取用外部程式碼。

### Open failures

- cable-clearance 是候選配置，不是通過整機資格的替代預設。兩頭同時抬起拆蓋會碰撞；一次抬一頭維修298樣本通過，但此操作順序尚未進入共用驗證情境配置。預設baseline維持原完整資格範圍。
- 毛細管端保留的走線候選仍碰撞；pH雙線僅工作／抬升端點找到淨空候選。完整路徑、固定端／可滑動點、跨段線間距、中間變形、材料最小半徑與拉力未資格化；Ø6mm是假設，180mm不是裁線規格。
- 目前模組是既有150mm臂與單／雙孔頭的家族；沒有宣稱任意臂長、孔徑、負載可互換。全走線、底座／LCD、電路、載荷、材料與實體列印仍待完成。

### Next step

- **使用者要求優先：**後續變體以不可變配置＋共用模組＋共用驗證進行，禁止再複製一份產生器或inspect.getsource後字串替換。先把走線研究的共通輸入／候選／檢查收斂成同一入口，再處理毛細管干涉；保存失敗案例作回歸。
- 規格在 `src/core/domain/lab_station.py`，零件建構在 `scripts/lab_electrode_module.py`，組裝入口在 `scripts/model_lab_platform.py`；配置真機閘門在 `scripts/verify/lab_electrode_readback_real.py::verify_electrode_configurations`，由既有lab_simple real入口呼叫。試作可直接傳dataclass，不改或複製建模函式。
- 已跑完整CI87822 terminal exit0，無執行中的驗證。Blender操作仍必須串行，執行中不改產生器；逾時先查同一handle。正式視圖還原guides-aligned/arm-seated，配置產出在module-configurations/，不要開舊offset-head當最新候選。


### V01.0R.022 封存接手

### Verified facts

- V01.0R.022：完整 `scripts/ci.sh --real` 8784 terminal exit 0，所有 hard gates green（`tmp/lab-station-electrode-guides-aligned/ci-aligned-guides.log`）。先由舊 frame 觸發通道異側紅例，改位置／方向分離後通過；red-facing-recheck.json 留下再次注入舊方向的拒絕證據。初次 red-facing.log 僅收 stdout，原錯誤在工具 stderr，不把空檔當證據。
- 現行正式輸出 `tmp/lab-station-electrode-guides-aligned/`。只將前臂導線夾通道轉向與上臂同側，保留桿中心、尺寸、四件數量與原五金。90 通道／孔壁射線、8 徑向止擋、46 姿態、4140 插銷樣本、60 轉位樣本及完整肩轉位仍通過。
- guide-controls.json 四反例：缺件、穿桿、裝錯 parent、反轉實際網格；還原後重驗幾何。保存檔重讀及近照已核對。Blender 已還原新 arm-seated，restored-file-check.json 再查四導線夾及六組承壓鏈。
- 線路研究保留 `tmp/lab-station-cable-study/` 與 `tmp/lab-station-cable-sameside/`。原朝向加 6 mm 孔口直段，72 組只有 32 組找到保留候選中的實體淨空路徑；同側後為 72／72，但獨立挑線產生 18／144 個未通過線間距的配對，不能宣稱整組通過。
- 雙線改為共用控制柄／鼓出側，分別解固定長度。180 mm 的八姿態都有配對候選，27311 terminal exit 0：paired-structure-clearance.json 對全部可見實體通過 8／8。最小取樣半徑 17.272 mm、兩線中心距離下界 6.111 mm（Ø6 包絡餘量約 0.111 mm）；未指定材料通過半徑。paired-work／paired-service 圖與 blend 已產出，抬升圖已檢視。
- 5S：沒有新增生產模組／公開介面／依賴。routes 268、main 372 行；朝向與實際孔壁的正負對照沿用既有 real gate，研究脚本留 tmp。R45、規格、GitHub／igus 來源與鏡射方向教訓同步；研究曲線未加入正式產生器。

### Open failures

- 八個離散姿態不代表中間變形、迴圈不翻面、動作中的線間距、材料半徑／疲勞／拉力合格。研究最小間距很小，不是實物公差資格；180 mm 不能當裁線指示。
- 導線夾沒有已驗證的軸向抓線能力；固定夾間段長只是邊界條件。尚需定義探頭到基座的完整路徑、兩端固定點、總長、夾孔滑動及鬆弛餘量。
- 其餘肩角與連續掃掠、螺紋／彈性預緊、工具／手指空間、軟襯／卡扣保持力、底座／LCD、載荷及實體列印仍未資格化。線材外徑、實際容器／探頭／板件、負載、材料、溫度／液體與精度資料未齊；沒有現行整機製造 STL。

### Next step

- 8784、27311 均 terminal exit 0，沒有執行中的驗證。先釐清完整線路的固定端與可滑動導引點，再將雙線共同路徑接到中間動作檢查；保留真實未確認的線徑／彎曲半徑假設，不能拿離散曲線當柔性力學結果。
- 從 paired-structure-clearance.json 的八組候選接手；readme 記有研究腳本與早期失败。工作／抬升研究檔是 paired-work.blend／paired-service.blend，正式檔是 guides-aligned/arm-seated.blend。研究曲線只覆蓋跨肘段。
- guide_frame 將桿中心位置與通道朝向分開；兩頭各自同側。不要回復「role 決定通道方向」。導線夾直接 parent 到臂，不重複加入肩變換；相對 take-up 不可累加。
- 真機仍串行，執行中不改產生器。開檔後用 fresh 命令；超時先排空。新模組先查 GitHub，render 379 行，新增呈現前按責任拆分，不能縮寫規避預算。後续仍需底座／LCD 及物理資格。


### V01.0R.021 接手事實（歷史）

### Verified facts

- V01.0R.021：完整 `scripts/ci.sh --real` 86223 terminal exit 0，所有 hard gates green（`tmp/lab-station-electrode-guides/ci-guides-phased.log`）。領域測試先缺類別紅，再 21/21 通過；完整動作 study 56519 exit 0，31 focused tests 通過。
- 現行輸出 `tmp/lab-station-electrode-guides/`。四個可換沿臂導線夾，不增加金屬五金；毛細管單通道、pH／溫度雙通道。暫定線外徑 6 mm、孔 6.4 mm、側口 4.8 mm、壁厚 1.6 mm，夾在既有 8 × 12 mm 臂上。實際線徑未確認。
- 四件均單一封閉網格；90 個孔壁射線及 8 個徑向止擋樣本通過。缺件、錯誤父物件與撞臂三反例均拒絕。導線夾直接隨所屬臂運動，既有動作、退齒、收隙、拆卸及肩部 176 狀態轉位均包含導線夾障礙檢查。
- 首次完整 1474 在合併動作命令 300 秒逾時，背景完成後只讀排空。改為两頭串行獨立驗證再合併報告，保留全場情境；phase-equivalence.json 確認與拆分前相同的 46 姿態、4140 插銷樣本、60 轉位樣本，以及姿態清單／齒位清單一致。86223 完整重跑通過。
- guide-file-check.json 由保存檔重新讀回；導線夾近照及 arm-seated 全機圖已檢視。Blender 已還原 arm-seated，restored-file-check.json 再查四導線夾與兩頭肩／肘／腕六組承壓鏈。
- 5S：新 routes 模組建立前已查 GitHub Cable Clips／slide-n-snap，來源在 09-references.md；未複製外部碼或新增套件。guide 規格屬純領域，幾何與檢查隔離；main 372、closure 364、motion 362、render 379、driver 371 行，低於 380 警戒。R44／規格／導航同步，生成物僅留 tmp。

### Open failures

- 跨關節線材迴圈、彎曲半徑、夾片彈性與保持力、軸向防滑仍未資格化；剛體止擋不能證明卡扣可裝拆。Ø6 mm 是包絡假設。
- 其餘肩角與連續掃掠、螺紋／彈性預緊、工具／手指空間、軟襯、底座／LCD 保持、載荷與實體列印未資格化，無現行整機製造 STL。實際容器／探頭／板件尺寸、負載、材料、溫度／液體及浸入精度資料仍缺。

### Next step

- 86223 terminal exit 0，無正在執行的驗證；下一步依實際導線夾錨點建立跨關節鬆弛迴圈與路徑檢查，再續底座／LCD。線徑未知不等於吻合實物，仍用明示假設包絡。
- guide_frame 定義臂局部座標；上／下臂通道分居不同側，跨肘需處理軸向偏移，不能直接穿關節。導線夾父物件是所屬 arm，避免肩部整組變換重複套用。尚未建線材曲線。
- 真機串行且執行中不改來源；build、每頭 verify、render、反例各獨立 300 秒。build 清除舊 phase 報告，第二階段缺第一階段即失敗。開檔後 fresh 命令讀回，逾時先排空。
- 新模組先查 GitHub；render 379 行，新增呈現前需移既有責任或合適拆分。工作檔 arm-seated 六關節貼合；service-seated 只兩腕貼合，肩肘退開。既有相對 take-up 不可累加。

### V01.0R.020 接手事實（歷史）

### Verified facts

- V01.0R.020：最終完整 `scripts/ci.sh --real` 89292 terminal exit 0，所有 hard gates green（`tmp/lab-station-electrode-wrist-seated/ci-wrist-seated-entry.log`）。腕收隙領域測試先缺類別紅，再 7/7 通過；十二姿態 study 51743 exit 0，focused 48918 exit 0（tmp/wrist-seated-focused.log），最後完整閘門包含新增的肩轉位保持腕部貼合。
- 現行輸出 `tmp/lab-station-electrode-wrist-seated/`。沿用原幾何與五金；腕部四接面總收隙 0.7 mm，螺母 −0.2、螺栓 +0.5、旋鈕 +0.3、整組夾頭／探頭 +0.2 mm，平台固定。十二配置共 180 狀態，查實際接面、螺栓外露量與全場障礙。未就座及另一頭擋路的反例均拒絕。
- arm-seated.blend 是两頭肩／肘／腕六組承壓鏈同時貼合；service-seated.blend 是抬高 100 mm、腕角 19.313° 的兩腕貼合，肩肘仍退開。fresh readback 最大殘差：工作 0.000130、維修 0.000094 mm。完整腕部近照 wrist-seated-detail 與先前維修圖已檢視；沒有隱藏零件。
- 絕對腕部控制由平台求軸心，螺母沿平台朝向；新控制先因共用螺栓角度使六角座相撞，修正後十二姿態與回讀循環通過。對已三關節貼合存檔執行腕部退開 2 mm、回名義間隙、重新就座，再查三關節與障礙，不累加偏移。
- 肩部 176 狀態轉位新增腕部保持貼合，每個狀態量腕部接面；另一頭固定、探頭隨臂轉。終點 fresh readback 三關節，最大殘差 0.000108 mm，擋路反例仍拒絕。Blender 已還原現行 arm-seated，restored-file-check.json 重讀六組承壓鏈。
- 首次完整 96066 T2 發現四處嵌入專案 import，於確認失敗後停止該 CI／子程序（143），只讀 20062 exit 0 確认 Blender 排空。改以 model 入口取得函式，不放寬守衛；17 focused tests 通過，89292 完整重跑全綠。失敗日誌與最終日誌均保留。
- 5S：無新模組／公開介面，wrist 幾何檢查由 closure 移到既有 motion，收隙沿用純領域規格與幾何量測。main 348、closure 361、motion 327、render 379、readback 93、driver 359 行，均低於 380 警戒。規格移除舊腕部未整合敘述並補導航，R43 與新教訓同步；生成檔只在 tmp。

### Open failures

- 全機走線、其餘肩角及連續掃掠、螺紋／彈性預緊、工具／手指空間、軟襯／卡扣保持力、底座／LCD 保持、載荷與實體列印未資格化，無現行整機製造 STL。剛體面貼合不能替代鎖緊力。
- 與參考產品仍有走線整合及關節／底座外形差距。氣管、pH 與溫度線外徑仍未回覆；Ø6 mm 僅是假設，可換夾片尚未建立。實際容器／探頭／板件尺寸、負載、材料、溫度／液體及浸入精度資料仍缺。

### Next step

- 89292 terminal exit 0，無正在執行的驗證。下一步沿臂走線與關節鬆弛空間，優先讓外觀與可操作性更接近參考；線徑未定可做明示尺寸的可換夾片／包絡，不能假定吻合實物。另續底座／LCD 工程資格與物理試片。
- 新模組先查 GitHub；前輪走線參考在 09-references.md，但要依這次新增模組實際職責查找。render 已 379 行，新增呈現前先移既有責任或合適拆分，不能壓短語意躲預算。
- closure_spec／bearing_pairs／joint_frame 現支援 tip；tip 使用平台不動框架与 6.2／7／7.8 mm 齒面半徑。take_up_offsets 連動夾頭、夾具和探頭。apply_take_up 是相對位移；verify_take_up 各樣本還原，不能累加。set_electrode_wrist_pose 可由已收隙狀態回到名義配置。
- 全機工作檔是 arm-seated；service 保留名義間隙，service-seated 只腕貼合，wrist-released 是腕退開 2 mm。杯／盤 +3.5 mm、平台浮動 2 mm、維修抬高 100 mm／19.313° 保留。真機串行且執行中不改来源；生成、反例、肩轉位各獨立 300 秒，開檔後 fresh 命令讀回，逾時先排空。

### V01.0R.01Z 接手事實（歷史）

### Verified facts

- V01.0R.01Z：完整 `scripts/ci.sh --real` 63949 terminal exit 0，所有 hard gates green（`tmp/lab-station-electrode-wrist-teeth/ci-wrist-teeth-split.log`）。領域齒位方法先紅再 20/20 通過；真機涵蓋生成、動作、反例及存檔讀回。
- 現行輸出 `tmp/lab-station-electrode-wrist-teeth/`。腕部夾頭／平台內嵌半徑 8 mm、24 齒配對面，不增五金。局部齒面 20 案例；腕部 42 個退開及 42 個傾角狀態，保留全部原肩肘／拆卸／碰撞檢查。另一頭固定。
- 抬高 100 mm 的平台角度由領域模型推導：下一腕齒位相對鉛直 19.3134208°。轉角時夾頭、探頭、腕螺栓及旋鈕退開 2 mm，螺母留平台側；一般自由姿態亦退開腕部。對齒仍留 0.2 mm 名義間隙，沒有宣稱腕部就座。
- 工作／維修／退開存檔 fresh readback 通過，腕齒面間隙分別約 0.2／0.2／2.2 mm，偏差 <0.00011 mm；維修兩腕角 19.3134237°、298 夾具與 156 插銷樣本通過。肩部 176 狀態轉位、擋路拒絕及終點讀回仍通過。已檢視 service 與 wrist-teeth-detail 圖；後者暫時隱藏夾頭以展示齒面，wrist-released.blend 保留完整組件。
- 鏡射布林先因工具法向翻轉失敗，負 determinant 後翻回法向修正；兩側封閉性／正負齒位守衛通過。新增半齒／抬高後錯齒拒絕。腕部退開後原直立拆卸阻擋不再成立，保留為 released-untilted-service 正例，改以實測錯齒干涉為負例，未放寬碰撞。
- 初次完整 44078 exit 1：生成／出圖／反例合併等待 300 秒逾時。背景完成並開檔後，fresh oracle 確認排空；舊只讀等待 81703 的回呼受開檔清除，明確停止觀察程序（143）。沿用原入口將生成與反例分為串行獨立命令，各 300 秒，不增全域期限；63949 完整重跑全綠。舊失敗日誌保留。
- 5S：無新增模組／公開 DTO，維修動作從 check 移入既有 motion。main 333、check 360、closure 366、motion 292、joints 337、rig 322、driver 349、readback 74 行，低於 380 警戒；R42／規格／兩條抽象教訓同步，輸出仍留 tmp。Blender 已還原 arm-seated，另以 restored-file-check.json 查兩頭肩肘就座及腕間隙。

### Open failures

- 腕部整組收隙／就座、其他肩角與連續掃掠、螺紋及彈性預緊、工具／手指空間、軟襯／卡扣保持力、底座／LCD 保持、載荷及實體列印尚未資格化，無現行整機製造 STL。
- 與參考產品仍有走線整合及關節／底座外形差距，沒有宣稱外觀定稿。氣管、pH 與溫度線外徑未回覆；Ø6 mm 只是假設，可換夾片尚未建立。實際容器／探頭／板件尺寸、負載、材料、溫度／液體及浸入精度資料仍缺。

### Next step

- 63949 terminal exit 0，無執行中的驗證；下一步腕部承壓鏈收隙與就座。腕部負側 head、正側 platform，邏輯近肘部，但連動夾具與探頭；量齒面半徑 6.2／7／7.8 mm，不可直接沿用肩肘外圈。
- set_electrode_wrist_pose 為絕對控制，使用 tip_bolt 的 wrist_release_mm 反算原框架；尚未處理未來收隙位移，套收隙後須先 reset，不能直接再次調角。set_electrode_service_tilt 明示角度時退開 2 mm，省略才回到推導齒位的名義 0.2 mm 間隙。
- arm-seated.blend 僅肩肘就座；wrist-released.blend 為兩腕退開，wrist-teeth-detail 只是隱藏夾頭的診斷視角。杯／盤 +3.5 mm、平台浮動 2 mm 保留；維修抬高 100 mm，腕角更新為 19.313°，不可再用舊 15°。
- 真機流程串行且執行中不改來源；生成、反例、完整肩轉位各獨立 300 秒期限。開檔後另下 fresh 命令，超時先確認排空。新模組先查 GitHub，沿用 blender-mcp-studio／版本／checkpoint 流程。


### V01.0R.01Y 接手事實（歷史）

### Verified facts

- V01.0R.01Y：完整 `scripts/ci.sh --real` 80821 terminal exit 0，所有 hard gates green（`tmp/lab-station-electrode-shoulder-transfer/ci-shoulder-transfer.log`）。FK 圓弧測試先缺方法失敗再 19/19 通過；獨立完整路徑 study 96665 exit 0（`tmp/shoulder-transfer-first.log`）與障礙反例通過，最終完整閘門涵蓋重建、圖片及存檔讀回。
- 現行輸出 `tmp/lab-station-electrode-shoulder-transfer/`。幾何與五金數未變：14 螺絲／14 螺母，六列印軸／卡扣。一般工作仍 `arm-seated.blend`；新增兩頭各 start／mid／end 圖，`transfer-end-capillary.blend` 與 `transfer-end-pH_temp.blend` 是單頭換位終點，另一頭保持工作位置。
- 從肘 +15°／肩原位且兩關節就座開始：肩退回收隙 15 狀態、軸向退齒 21、剛體轉 0–15° 共 16、回軸向 21、收緊 15。兩頭各 88、共 176 狀態，肘保持貼合、固定支座與另一頭矩陣不動。逐點查全場障礙、接面與插銷保持；獨立 FK 比对 tip 位置 0.001 mm，另驗探頭姿態隨臂轉動。有限取樣，不代表連續掃掠或任意肩角。
- 插入另一探頭擋路必須拒絕，`red-shoulder-transfer-blocked.json` 為 `S_capillary_upper`／`S_pH_temp_head`。新終點存檔 fresh command 讀回肩／肘與插銷，最大接面殘差 0.000108 mm，見 `transfer-file-check.json`。`shoulder-transfer.json` 保留全段階段、角度、行程。
- 已檢視毛細管中途與 pH 終點圖。額外讀回 pH 終點實際頂點：最低探頭端高於杯口 37.495 mm（`transfer-end-clearance.json`），只屬該終點；全段仍以交叉檢查為證據。Blender 已還原現行 `arm-seated.blend`。
- 5S：先查 Robotics Toolbox／PyBullet Planning（`09-references.md`），再將原 main 的整段動作移到 `lab_electrode_motion`，原 real verifier 的 fresh readback 移到 `lab_electrode_readback_real`。不複製外部碼、不引入引擎、不新增公開 DTO／傳輸；main 288、motion 232、real driver 335、readback 68 行。既有守衛保留，R41 與規格同步，舊輸出保留。

### Open failures

- 腕部齒槽／就座、其他肩角與連續掃掠、螺紋及彈性預緊、工具／手指空間、軟襯／卡扣保持力、底座／LCD 保持、載荷及實體列印尚未資格化，無現行整機製造 STL。
- 與參考產品仍有走線整合及關節／底座外形差距；本輪建立操作證據，沒有宣稱外觀定稿。
- 氣管、pH 與溫度線外徑問題未回覆，可換夾片尚未建立；Ø6 mm 仍是假設。實際容器／探頭／板件尺寸、負載、材料、溫度／液體與浸入精度資料仍缺。

### Next step

- 80821 terminal exit 0，沒有執行中的驗證；下一步腕部鎖定與就座，並維持 15° 維修傾角及目前肩部轉位路徑。物理規格未確定時先做幾何與裝配，不假定承載合格。
- `angular_target(elbow_deg, shoulder_deg)` 提供前向運動學，indexed_target 委派給它；肩轉位用整組實際矩陣繞固定支座旋轉，不能以兩端點直線插值或把頭暗中扶正代替。`verify_shoulder_transfer` finally reset 自己，另一頭保持初始矩陣；預設情境固定肘 +15°。
- `render_shoulder_transfer` 由 real readback 階段單獨呼叫，先 reset 兩頭，再按驗證回呼儲存 start／mid／end。一般 main 只生成原姿態組。`verify_saved_electrode` 依序讀肩肘就座、維修、完整轉位、終點，再還原工作檔；各 open_mainfile 後以 fresh 命令使用場景。
- 保留杯／盘 +3.5 mm、平台 2 mm 浮動、抬高 100／前傾 15° 維修。真機流程串行且執行中不改來源，逾時先排空；生成與轉位各使用獨立 300 秒期限。新模組前先查 GitHub；仍沿用 blender-mcp-studio／版本／checkpoint 流程。


### V01.0R.01X 接手事實（歷史）

### Verified facts

- V01.0R.01X：focused 88548 terminal exit 0（`tmp/shoulder-seated-focused.log`）；完整 `scripts/ci.sh --real` 51833 exit 0，所有 hard gates green（`tmp/lab-station-electrode-shoulder-seated/ci-shoulder-seated.log`）。肩部領域測試先缺類別失敗，再 6/6 通過；完整 lint／format／mypy、模型與交付回歸通過。
- 現行輸出 `tmp/lab-station-electrode-shoulder-seated/`；`arm-seated.blend` 是兩頭肩、肘同時就座，取代現行交付中的 elbow-only 檔名。`electrode-concept.blend` 仍保留名義間隙，`service.blend` 仍抬高／前傾。旧版輸出保留，不修改其證據。
- 肩固定支座，總收隙 0.7 mm。相對原間隙最終位移：螺母 −0.4、螺栓 +0.3、旋鈕 +0.1、整組前臂 −0.2 mm；螺母已包含前臂位移，不得重複疊加。沿用既有 primitive／closure／render，零件與 14 螺絲／14 螺母數量不變。
- 兩頭原四齒位及肩 +15°／肘 +15° 額外姿態，共十配置／150 肩部收隙狀態。每狀態四對接面、全場障礙及螺栓外露量通過；未就座宣稱被拒絕，證據 `red-unseated-shoulder.json`。`verify_interference` 只對肩／肘已知承壓接面允許 0.01 mm 微分離後無交叉，其他障礙沒有豁免。
- 真機入口重新讀取 `arm-seated.blend`，四組承壓鏈全部在 0.01 mm 容差內，最大絕對殘差 0.000130 mm；`seated-file-check.json` 保留每面上下界。service 讀回仍通過 298 夾具及 156 插銷取樣。整機圖與肩部近照已檢視；Blender 已還原現行 arm-seated 檔並 fresh readback 確認。
- 5S：改動沿用六個既有程式檔（domain、unit test、closure、main、render、real verifier），沒有新增模組或公開 DTO。main 372、closure 362、render 377、real verifier 360 行，皆低於 380 警戒；肩部收隙與肘部共用驗證而保留不同運動規則。R40 與規格同步。

### Open failures

- 肩齒位間完整退齒／轉位路徑、腕部齒槽／就座、螺紋及彈性預緊、工具空間、软襯／卡扣保持力、底座／LCD 保持、載荷及實體列印未資格化；無現行整機製造 STL。
- 與參考產品仍有走線整合與關節／底座外形差距；肩部就座補的是工程組裝狀態，並非外觀定稿。
- 氣管、pH 與溫度線外徑問題仍未回覆，可換夾片尚未建立；Ø6 mm 只是假設。容器／探頭／板件尺寸、負載、材料、溫度／液體與浸入精度資料仍缺。

### Next step

- 88548、51833 均 terminal exit 0，沒有執行中的驗證；下一步驗肩部兩齒位間完整閉鏈轉位，再續腕部齒槽／就座與走線。線徑未知不阻止前兩項工程驗證。
- `apply_take_up(label, travel, joint)` 仍是相對位移，不可累加；joint 只允許 shoulder／elbow。`take_up_offsets` 的肩部映射先套整個前臂，再以絕對最終偏移覆蓋螺母等鍵。固定 base 不動；肩部閉合與釋放方向相反。
- `verify_bearing_chains` 分別還原後驗肩／肘，`render_electrode_seated` 才依肩→肘兩者同時套入並查碰撞。讀回驗兩頭、兩關節；不能拿原間隙檔宣稱就座。保留杯／盤 +3.5 mm、平台 2 mm 浮動及抬高 100／前傾 15° 維修流程。
- 盤點技能／工具後沿用 blender-mcp-studio／version-management／checkpoint，無直接暴露 Blender MCP 工具，使用既有內部 verifier。新模組若需要，先查 GitHub。真機流程串行，執行期間不改來源；大型電極臂階段期限 300 秒，逾時先排空。

### V01.0R.01W 接手事實（歷史）

### Verified facts

- V01.0R.01W：最後完整 `scripts/ci.sh --real` 93636 terminal exit 0，所有 hard gates green（`tmp/lab-station-electrode-slim-wrist/ci-slim-wrist-final-retry.log`）；含重建、負對照、保存檔讀回、lint／format／mypy 及全部回歸。先前 focused 12588（薄旋鈕）、77864（平台插銷）皆 exit 0，最後完整閘門才涵蓋全部變更。
- 現行輸出 `tmp/lab-station-electrode-slim-wrist/`。腕旋鈕厚度 10→7.5 mm，承壓面不動、底厚維持 2.5 mm；兩頭 96 射線及封閉實體检查通過。固定視角 `wrist-before.png`／`wrist-detail.png` 已檢視；`wrist-comparison.json` 實測五金軸向包絡 27.3000→24.8000 mm，不代表整個夾頭寬度。
- 兩個三角平台的螺絲／螺母改為列印溝槽軸與 C 卡扣；名義五金減為 14 螺絲／14 螺母，列印軸／卡扣各 6。平台軸身 24 mm，其他 22 mm，保留肘部退齒的 2 mm 軸向浮動。46 單頭位置共 4140 被動軸樣本、11 雙頭前伸及既有齒位／就座／HMI 收折通過。
- 兩頭抬高 100 mm、腕部各前傾 15° 時，六軸共 156 個全場抽出樣本通過；另一探頭擋路、平台卡扣缺失、旋鈕外凸及底厚削薄均被拒絕。service 保存檔重新讀取：兩腕角 14.99998°、298 夾具拆裝／止擋與 156 插銷樣本通過，之後還原 `elbow-seated.blend`。
- 初次完整 36809 因大型電極臂階段 180 秒等待逾時而 exit 1，未繼續後續場景。原工作仍完成並留下負對照；確認排空後，只將該階段期限改 300 秒，最後 93636 全綠。排空時首次唯讀命令遇到開檔清除 timer，終止該等待程序後以新命令確認目前檔案；沒有重送建模或重啟 Blender。原失敗日誌保留。
- 5S：沿用六個腳本、未新增模組／公開介面；main 373、check 376、closure 319、render 357、real verifier 366 行，低於 380 警戒。出圖配置移至既有 render，負對照共用 helper；R38–R39 與規格同步，舊輸出保留。

### Open failures

- 與參考產品仍有走線整合、關節／底座外形差距；這次只收整腕部與平台軸頭，非全機外觀定稿。
- 肩部整組就座與完整轉位、腕部齒槽／就座、螺紋及彈性預緊、工具空間、軟襯／卡扣保持力、底座／LCD 保持、載荷與實體列印尚未資格化；未發布現行整機製造 STL。
- 氣管、pH 與溫度線外徑已詢問，尚未回覆；可換夾片為下一步方向，Ø6 mm 只是假設，尚未建立走線幾何。容器／探頭／板件尺寸、負载、材料、溫度及液體資訊仍缺；浸入精度未回覆。

### Next step

- 93636 terminal exit 0，無執行中的驗證；Blender 還原現行 `elbow-seated.blend`。優先沿此版設計可換走線夾片，再續肩／腕鎖定與底座／螢幕工程資格。走線 GitHub 前置查找已記 `09-references.md`；未複製程式或增加外部 CAD 依賴。
- `pose(label)` reset 所有零件後再套退齒；平台浮動軸不可換回夾死螺栓。`set_electrode_service_tilt` 設絕對 0–15°，先抬高 100 mm 再前傾；`verify_pin_service` 僅在此維修姿態宣稱全場拆卸，卡扣假設已移除。
- `electrode-concept.blend` 保留名義間隙供運動；`elbow-seated.blend` 僅肘部就座。維修檔由 `render_electrode_details` 產生，fresh addon 命令讀回。保留杯／盤 +3.5 mm，真機流程串行且執行中不改來源；逾時先排空，不能直接重跑。

### V01.0R.01V 接手事實（歷史）

### Verified facts

- V01.0R.01V：focused 16984 exit 0（`tmp/electrode-coplanar-service.log`）；最後完整 `scripts/ci.sh --real` 95639 exit 0，所有 hard gates green（`tmp/lab-station-electrode-coplanar/ci-coplanar-final.log`）。23 focused domain tests 通過；完整 lint／format／mypy／回歸通過。
- 現行輸出 `tmp/lab-station-electrode-coplanar/`；兩根前臂在同一軸向層，被動軸／卡扣繞支承層反向安裝。工作配置桿件包絡實測 24.8→8.6 mm，記錄 `stack-comparison.json`；不含上臂、旋鈕與五金，鬆開姿態另有 2 mm 退開量。未削薄桿件或增加五金。
- 毛細管夾座螺絲孔由 ±10 改 ±8 mm。兩頭抬高 100 mm 後，各自腕軸前傾 15° 才可完整拆裝；32 個 0–15° 獨立腕角、298 個拆裝／止擋取樣通過。各姿態自碰加入夾具金屬件；原 46 單頭位置、11 共同前伸、齒位／退齒／肘部就座及螢幕收折守衛保留。
- `red-forearm-stack.json`、`red-clamp-bolt-collision.json`、`red-service-untilted.json` 均拒絕，還原後通過。原同側候選因螺栓碰連桿／軸頭失敗，證據留在 `tmp/electrode-coplanar-first.log`、`tmp/electrode-coplanar-bolt-clearance.log`、`tmp/electrode-coplanar-static-red.log` 與 service／wrist study JSON。
- `electrode-concept.blend` 為原間隙基線；`elbow-seated.blend` 仍只有肘部就座；`service.blend` 為抬高／前傾拆装姿態。真機入口在新 addon 命令重新讀檔，`service-file-check.json` 兩腕角 14.99998°、298 拆裝／止擋通過，之後還原肘部就座檔。working／service 圖已檢視。
- 首次完整 CI 2415 exit 0，但額外讀檔發現 service 存檔誤加到舊版出圖分支；修正後將實際 service 讀回納入固定 real gate，最終 95639 再次全部通過，不能以第一次綠燈當該檔交付證據。
- 5S：沿用 6 個既有腳本，未新增模組／公開介面；main 377、check 365、rig 303、render 336、real verifier 367 行，均低於 380 警戒。R37、規格與五金漏驗教訓已同步；舊檔及失敗日誌保留。

### Open failures

- 與參考產品仍有腕端接頭整合、外露關節與沿臂走線的差距；此輪完成同側排列，不宣稱全機外觀定稿。
- 肩部整組就座與完整轉位、腕部齒槽／就座、螺紋與彈性預緊、工具空間、軟襯保持力、底座／LCD 保持、載荷及實體列印尚未資格化；沒有現行整機製造 STL 發布。
- 精確容器、探頭、板件、負載、材料、溫度及液體資料仍缺；15° 是粗定位，浸入深度精度未回覆。

### Next step

- focused 16984、完整 95639 均 terminal exit 0，無在跑的驗證；依使用者「仍與參考產品有差」的方向，沿用同側排列，優先收整腕端接座／軸頭與走線，且保留拆裝前傾路徑；肩部就座等工程資格仍在範圍內。
- `set_electrode_service_tilt` 在既有 tip 軸設定絕對 0–15° 腕角；先 `pose(label, 0, 100)`，再前傾。`pose(label)` 會還原所有頭部零件。`verify_service_tilt` 留在 15°，`verify_clamps` 不自行移動手臂。
- 原位探頭不應側取；抬高但未前傾也會撞被動軸頭。存檔必須由 `render_electrode_details` 的 service 分支產生，再由 fresh addon 命令讀回，不能拿舊出圖分支的同名檔代替。
- 保留杯／承液盤 +3.5 mm；肩／肘鬆開與收隙仍是相對位移，禁止累加。真機流程串行，過程中禁止改來源；建立新模組前先查 GitHub。

### V01.0R.01U 接手事實（歷史）

### Verified facts

- V01.0R.01U：focused 74702 exit 0（`tmp/electrode-shoulder-indexed.log`），完整 `scripts/ci.sh --real` 43531 exit 0，所有 hard gates green（`tmp/lab-station-electrode-shoulder-teeth/ci-shoulder-teeth.log`）。18 domain tests 先紅後綠；完整 lint／format／mypy、回歸與交付守衛通過。
- 現行输出 `tmp/lab-station-electrode-shoulder-teeth/`；`electrode-concept.blend` 保留原裝配間隙，`elbow-seated.blend` 僅肘部已就座，肩部仍保留間隙。working、shoulder-released、indexed-shoulder-raised 已檢視；上輪各輸出目錄保留。
- 肩部支座／上臂內嵌 24 齒／15°，整個前臂組沿共同軸向退開 2 mm，保持探頭、夾具、被動軸連接；固定支座與肩螺栓／旋鈕保持原位。兩頭各工作角和 +15° 肩位共 40 局部齒面、84 軸向取樣通過；新增肩 +15°／肘 +15° 姿態约後退 24.05／抬高 89.79 mm，閉鏈／避碰／肘部就座通過。
- 杯與承液盤共同右移 3.5 mm；移回杯的負對照在 1.2 mm 退開時撞溫度探頭，退開上臂卻宣稱咬合亦拒絕，還原後通過。未增加五金，仍 16 螺絲／16 螺母。
- 原 46 單頭位置、11 共同前伸、298 拆裝、2760 被動軸及肘部 120 收隙狀態保留；新增兩個肩位各 15 肘部收隙狀態，存檔重新讀取通過。這些都是有限剛體幾何取樣，不代表預緊／承載。
- 第二處齒槽布林曾破壞原有效曲面；`tmp/electrode-shoulder-topology.json` 定位切除後 141 非流形邊。細部 Boolean 改本地毫米運算並還原後，封閉性／接面／就座全通過；原失敗日誌保留，教訓回寫。
- 5S：驗證移至既有 closure／check，局部出圖移至既有 render；main 366、check 323、closure 259、render 329、joints 308 行。無新模組或公開介面；R36 對應肩部正反例與圖。舊接手事实移至本檔歷史段，進度只由索引導引。

### Open failures

- 肩部整組收隙／就座、兩肩齒位之間的完整轉位路徑、腕部齒槽離合及就座尚未完成。
- 螺紋／彈性預緊、其餘五金裝入及工具空間、探頭軟襯保持力、底座承力、LCD 保持與走線、載荷及實體列印資格未取得；沒有現行整機製造 STL 發布。
- 精確容器、探頭與板件尺寸、負載、材料、溫度及液體資料仍缺；佔位尺寸不可當固定孔依據。深度微調精度未回覆；15° 為粗定位。

### Next step

- 74702、43531 均 terminal exit 0，無執行中的驗證。下一步以固定支座與整前臂位移為基準，建立肩部收隙模型及實際接觸面量測，再驗完整肩轉位與腕齒槽。
- `pose(label)` 會先還原全部矩陣，再套用肩／肘鬆開量；一般連續姿態兩關節各退 2 mm。指定整齒姿態才用 `elbow_release=0`，肩部亦回原間隙。額外肩位透過 `indexed_target(..., shoulder_step=1)`。
- `apply_take_up` 與 `apply_shoulder_release` 都是相對位移，禁止累加當絕對姿態。舊中立檢查先 reset pose 或讀原間隙檔；就座檔不適合直接作中立基線。
- 保留杯／承液盤 +3.5 mm 配置；退齒碰杯的負對照已納入 real gate。新模組若有必要，建立前先查 GitHub；保持所有真機流程串行，等待逾時先確認原工作排空。

### V01.0R.01R–01T 接手事實（歷史）

- 01T 緊湊平台 focused 81981 exit 0：`tmp/electrode-platform-mirror-fixed.log`。輸出 `tmp/lab-station-electrode-compact-platform/`，兩平台實測 40 mm（舊 50 mm）、零非流形，144 孔周材料取樣與過寬／缺材料負對照通過，原運動／拆裝／就座讀回保留。領域偏置先紅後綠，38 domain／DCC tests 通過。首輪上臂破面，診斷 `tmp/electrode-platform-topology.json` 定位清理由 0→19 邊；保留有效三角化並讓鏡射沿用後通過。平台每步布林整理亦修復螺母座開口。未新增模組。完整 `scripts/ci.sh --real` 4805 exit 0，所有 hard gates green，日誌 `tmp/lab-station-electrode-compact-platform/ci-compact-platform.log`。

- 2026-10-03 短腕版 focused 43488 exit 0：`tmp/electrode-short-head-integrated.log`。毛細管／pH 溫度夾座中心落差由 22／44 改 20／38 mm，外角半徑 4 mm，腕盤夾蓋讓位。實際夾蓋底緣到腕軸 29／47 mm，過長接頭負對照拒絕；46 單頭位置、11 共同前伸、298 拆裝、2760 止擋與就座存檔重讀通過。working／extended／clamp-detail 已檢視。38 domain／DCC tests 與四檔 lint／format／mypy 通過。初期 18 mm 毛細管撞旋鈕，36 mm pH 在共同前伸撞另一夾蓋，均未採用；各輪失敗日誌保留。上一輪因執行中修改來源造成讀回 import 不同步，固定来源後本輪重驗通過；之後完整驗證期間不得改碼。
- 前輪未完成的肩部退齒 helpers／泛化改名已從生產來源移除；原工作差異保存在 `tmp/shoulder-and-short-head-wip.patch`，避免未接入驗證的試作混入此輪。此為當時未完成試作；本輪肩部及杯座由現行模組實作並重新驗證。

- 現行候選輸出在 `tmp/lab-station-electrode-shoulder-teeth/`（01U）；前版 `tmp/lab-station-electrode-compact-platform/`（01T）保留；上輪 `tmp/lab-station-electrode-short-head/` 與更早 `tmp/lab-station-electrode-seated/` 保留。`electrode-concept.blend` 是原間隙的運動基線，`elbow-seated.blend` 是四對承壓面同時就座的檔案。已檢視 `elbow-seated.png` 並重讀就座檔量測通過。
- 肘部名義收隙行程 0.7 mm：螺母先入座、螺栓頭接觸旋鈕、旋鈕接觸下臂，再合齒。八個整齒位配置各 15 個狀態，共 120 個；每步射線查齒面三半徑各 192 角點和三平面各 12 角點，並查障礙與螺栓外露。這是剛體就座，未證明預緊力。
- 修復齒面近似不匹配：原實測間隙約 0.13–0.27 mm，配對面與每齒區改用一致三角分割後，各齒位均能就座。齒面側 Ø5.6 mm 局部孔讓位，主孔最小仍 Ø5.4 mm，避免五條破邊。前兩次整合失敗與表面量測日誌保留於 `tmp/electrode-closure-*`、`tmp/electrode-seated-integrated-*.log`。
- focused 真機 26022 exit 0，日誌 `tmp/electrode-seated-integrated-third.log`；既有齒位／移動／夾具／止擋檢查保留。領域收隙先紅後綠，五個 joints tests 通過。
- V01.0R.01R 完整 CI 77945 exit 0，日誌 `tmp/lab-station-electrode-seated/ci-seated.log`。所有 hard gates green；未就座負對照與保存檔重讀也通過。

- 01S 5S：沿用四個既有模組，主生成器 364 行、checker 357 行、clamp 277 行；沒有新模組或公開介面。舊模型與失敗日誌保留，未驗的肩部试作移出來源；R34 追溯實際包絡與共同前伸，四張視圖已檢視。完整 CI 18874 exit 0，整機仍未具製造／載荷資格。

- 01T 5S：沿用既有模組，生成器 375 行、checker 376 行、arm 368 行，皆低於 380 行警戒；後續擴充需先分離職責，若新增模組仍先查 GitHub。working／extended／clamp-detail 已檢視，`platform-comparison.json` 獨立讀取新舊檔證實 50→40 mm；R35 與網格清理教訓已回寫。無新增五金或製造資格。

### V1–V9 已驗證事實

- 使用者接受整體概念，但指出頭部不能連在一起、必須各自活動。暫沿用先前兩臂分組；已詢問是否三探頭都需獨立，尚未收到答覆。
- 末端改為左右分離、前後錯開 16 mm、高度錯開 30 mm。新增各臂獨立的 yaw／shoulder／elbow／head tilt／probe slide 控制，真 Blender 10 組隔離試驗通過，另一頭的 matrix delta 均為 0；產出 `independent-motion.png/json`。
- 官方機械圖已下載至 `tmp/lab-station-v1/references/`。
- API 首查 disconnected；查詢正式 scene 後自動重連，health 回 connected；沒有重啟服務。
- `test_lab_station.py` 首跑因缺少 domain module 失敗，實作後 4/4 通過；新增腕部間隙測試先紅再綠，最後 5/5。
- 已建 `.blend`、四個實際模型視角、六件外殼試配 STL；說明見 `docs/verification/lab-station/10-model.md`。
- 獨立 STL parser 六件尺寸符合設計，誤差小於 0.01 mm，單件 X/Y 均小於 240 mm。
- 正式 FQDN MCP + artifact contract 10/10 通過；六件各一個連通實體。readiness=review（薄壁／懸垂提醒），並非無條件列印通過。
- `scripts/ci.sh` 與 `scripts/ci.sh --real` 全綠。腕部微調後 focused tests 5/5、ruff／format／mypy 通過；最後另重建本模型並重跑專屬 real contract。
- 檢測副本首輪在隱藏前未更新 world matrix，oracle 誤判重疊；移動後、隱藏前立即 view-layer update 修正，零重疊由 real contract 守衛。射線改讀可見的實際上蓋，避免 hidden mesh 無 evaluated data。這是既有教訓，不另複製一條。

- V2 使用者確認放射狀齒槽。新增 24 齒／15° 試片、單側齒槽螢幕支架、2 mm 軸向釋放與 0–75° 控制；兩臂仍獨立。
- 新增 domain tests 與真網格 motion probes：8 個單元測試；16 個螢幕角度與 4 個齒盤狀態。齒面由每齒 4 段改為 8 段，修正粗三角化導致的互穿。
- V2 齒盤布林合併需先完成簡單耳座與孔，再合併齒盤。左右固定雙齒盤改成單側鎖定／對側滑動，避免無法退出；縮短臂根軸佔位以避開收納後罩。

- V2 專屬 real contract 10/10 通過，九件各一個封閉連通實體；獨立 STL parser 九件尺寸誤差小於 0.01 mm。MCP 保留薄壁／懸垂 review。
- 增長觸發 400 行檔案預算測試；將渲染拆至 `scripts/lab_station_render.py`，預算測試恢復通過。

- V2 最終 `scripts/ci.sh --real` 全部 hard gates 通過（涵蓋 T1/T2/T3）；完整日誌 `tmp/lab-station-v2/ci-real.log`。實際檢視工作／折平／齒盤特寫；V2 試配包含 23 個設計與驗證檔，另附 CI 日誌。

- V3 已重現 V2 失敗：35 mm 提升後 pH 底端 73.5 mm，低於 120 mm 清杯平面（`tmp/lab-station-v3/red-v2.json`）。先新增 domain 失敗測試再實作；行程有效性再做一輪紅綠，focused 共 13 個通過。
- 使用驗證規劃、VOC 追溯、DDD/SOLID、TDD、SDD 與 checkpoint 技能；技能／工具盤點、GitHub 相似機構查找與沿用決策記於 `docs/verification/lab-station/`。追溯表 8 條通過結構檢查，不能因此聲稱所有需求已完成。
- V3 增加兩組 Ø8 導桿、背架／端座、滑座；腕點後退 40 mm，兩頭各有 100 mm 直上行程。13 件試配 STL；完整探頭軟夾、臂連桿與五金仍不是已完成製造件。
- 真模型：兩頭各 21 個升降位置、其他物件矩陣與探頭 XY 不變；直線凸包掃掠無交叉。毛細管底端 175 mm，pH/溫度 138.5 mm；杯口 110 mm。`probe-lift.json` 記錄證據與限制。
- 雙頭提起後，左右各 16 個向外旋轉取樣通過（0–45°，每 3°），`probe-parking.json`；已檢視 `probe-raised.png`、`probe-parked.png`。
- readiness 超過單次取樣上限時如實失敗；改成外殼 9 件／升降 4 件兩份 contract，皆要求沒有截斷，不放寬門檻。

- V3 最終靜態／單元／Web gate：`scripts/ci.sh` → `tmp/lab-station-v3/ci-final.log` 全綠；real run 的 T3 34 項全通過，包括兩份工作站 contract。整次初始 real 命令 exit 1，因當時 lint／型別／版本更新與測試收集競態；修正後 T1/T2 重跑全綠，不能把初始命令說成 exit 0。彙整見 `verification-summary.json`。
- 螢幕在升程 0／100 mm 各 16 個角度通過；STL 獨立 parser 13 件尺寸誤差 <0.01 mm。V01.0R.014 封存此工程 checkpoint，保留 ACTIVE；依使用者持續推進指示不要求清除上下文。
- 5S：模型說明由舊 `lab-station-v1.md` 移入單一 DCC 目錄，無重複進度表；來源／結果分離；生成件留 `tmp/`；AGENTS／技能未膨脹。

- V4：23 件 STL 三份 real contract 通過；兩片式軟襯、可拆夾蓋、導桿壓蓋及 8 組金屬五金參考；拆夾路徑 126 個取樣無表面干涉。螢幕收折已加入 LS_HW_，選取測試先紅再綠；focused 42 passed，ruff 通過。
- V01.0R.015：`scripts/ci.sh --real` exit 0，T1／T2／T3 全部 hard gates green，完整紀錄 `tmp/lab-station-v4/ci-real.log`；共用 oracle 排序修正通過所有既有模型回歸。23 件試配與模型未正式發布，保留 ACTIVE。
- 本輪 5S：幾何、夾具檢查與渲染分檔；輸出留 tmp，無新增執行通道；來源與裝配限制同步 DCC。下一步先完成滑座 M4 鎖緊五金與防滑保持，再完成腕部到背架承力介面。

- V5：先由真模型重現缺少滑座鎖緊螺絲，再加入兩組 M4×12 名義五金。`tmp/lab-station-v5/red-missing-lock.log` 為失敗證據；fit contract 通過，52 focused tests 與 ruff 通過。實際間隙 0.50002／0.50001 mm；0.49 mm 旋入無卡阻、0.7 mm 過行程能抓到撞桿。已檢視 clamp-detail.png。
- V01.0R.016：完整 `scripts/ci.sh --real` exit 0、全部 hard gates green，紀錄 `tmp/lab-station-v5/ci-real.log`；補充追溯文件後 DCC 16 passed。保持力、二次防墜、旋鈕操作包絡與鎖緊狀態防誤升降仍未取得證據，不能宣告滑座承載合格。
- 5S：沿用既有五金與升降檢查模組，沒有新增通道；V5 輸出獨立於 V4；新增 S7／R12 與失效追溯，AGENTS／技能不變。下一步完成腕部到背架的實際螺栓連接；已詢問探頭含線重量、最高溫度與液體種類，未答覆不阻止幾何裝配工作。

- V6 前置實測發現 V5 腕部並非已裝配介面：左右背架／腕圓柱有 16／14 對表面交叉，背架／下臂 57／59，腕圓柱／下臂 19／15。證據 `tmp/lab-station-v6/red-wrist-interface.json`。新增真模型拒絕穿插的守衛，目前預期 RED，尚未修復；不可把舊全綠當作腕部合格。
- 負對照已結束 exit 1，錯誤為 `Wrist reference is not an assembled interface`；紀錄 `tmp/lab-station-v6/red-wrist-contract.log`。下一步必須重建腕部叉耳／轉動件並調整下臂末端，不能只補螺栓或刪除檢查。工作樹未提交，尚未封存新版本。

- V6 修正：腕軸後退到探頭後方 60 mm，中間轉動件與背架合一、叉耳與下臂合一。橋接改到腕軸上方，修掉原後方橋接在螢幕 65° 時碰右下臂。布林相切面造成下臂 231 條非流形邊，改用有重疊且不共面的接合後消除；25 件各單一封閉實體。
- 新 `scripts/lab_station_wrist.py` 沿用既有 primitive／Boolean；已有 GitHub 前置查找紀錄。補兩支下臂試配 STL，仍未完成肘端安裝與腕部鎖定保持。`probe-lift.json` 加入腕部兩側各 11 個 −15°..15° 局部姿態，包含軸與螺母干涉；全行程升降、拆夾、螢幕收折通過。48 focused tests 通過，已檢視 assembly.png；完整 gate 尚未跑。
- 升降／夾具契約均已通過、無截斷，輸出 `tmp/lab-station-v6/verification-lifts.log`／`verification-clamps.log`。下一步核對結果、補腕軸裝入與螺母保持，再補完整 CI／版本 checkpoint。現有穿軸是名義 M5×35，無墊片、無防鬆／力矩資格，不得稱完整機構完成。

- V6 腕部補兩側墊片；缺件負對照 `red-wrist-washers.log`。原位裝右墊片被另一臂擋住，改為雙頭提起、另一臂外轉 45° 的裝配姿態；兩側共 126 個 2 mm 步距插入位置通過，紀錄 `wrist-assembly.json`。48 focused tests／ruff 通過。V01.0R.017：初次 `scripts/ci.sh --real` exit 1，唯一失敗是已修正的 wrist_samples 型別註記；T3 共 35 項通過。修正後 `scripts/ci.sh` exit 0，T1／T2 全綠。兩份日誌与 verification-summary.json 位於 tmp/lab-station-v6，不宣稱初次命令全綠。
- V6 5S：來源／輸出分開；腕部幾何模組沿用 primitive／Boolean；25 件試配描述與 manifest 對齊；無公開 execute_code、無新增執行通道。此 checkpoint 保留 ACTIVE，下一步腕部保持與工具空間，以及肘端實際連接。
- 下輪先完成完整 gate／checkpoint；腕部扳手空間、防鬆、預緊保持力與肘端连接仍需完成，不能把本輪當全機製造合格。

- V7：先以真模型重現實心腕軸頭阻擋六角扳手（`tmp/lab-station-v6/red-wrist-tools.log`），補六角孔後工具就位包絡通過。工具視圖與檢查共用 `wrist_tool_envelopes`；新增圖片腕部前視被背架遮擋，已改後視待完整重建。ruff／兩檔 explicit-package-bases mypy 通過。V01.0R.018 完整 `scripts/ci.sh --real` exit 0，全部 hard gates green；日誌 `tmp/lab-station-v7/ci-real.log`。已檢視新後視圖，工具入口可辨認。5S：工具包絡由同一 helper 供檢查與渲染，診斷形體不留在模型或 STL，25 件數量不變。
- 下一步轉到肘端的實際装配：齒盤／上下臂連接、穿軸、釋放間隙與硬體保持；腕部工具手柄擺幅、保持力與防鬆仍未取得資格，未解除全機 H6。

- V8 肘端實測：舊版上下臂互穿，且軸穿過實心連桿，完整配對證據 `tmp/lab-station-v8/red-elbow-interface.json`。領域 elbow_necks 先紅再綠，11 個 domain tests 通過。
- 新 `scripts/lab_station_arm.py`：上下臂各 ±14 mm 側向接座，先沿 YZ 離齒盤 30 mm 再回接連桿；齒盘與各自臂一體布林，打通 Ø5.4 軸孔，補名義 M5×60 螺栓與螺母。原布林後再穿孔造成 139 條非流形邊，改成先穿孔再接齒盤修復；目前 25 件專屬 fit contract 通過，中立姿態上下臂／軸／螺母無表面干涉。
- 尚未封存 V8。下一步：新增上臂 STL，將上下臂獨立 readiness 分批；加入肘部軸向脫齒控制、鎖定／釋放轉角負對照及五金保持／裝入。不得以中立姿態通過宣稱可調角或承重；root/shoulder 仍為參考組裝。

- V8 肘部新控制 `elbow_release_mm`：缺控制先紅，加入軸向 0..2 mm 位移後通過兩側各五狀態（0°合齒、7.5°合齒必須撞齒、7.5°脫齒無交叉、15°脫齒與合齒無交叉）。這只查上下臂局部網格，不能當全臂可動證據。
- 上臂新增 STL，重命名下臂為 arm_lower，清除 V8 輸出內舊 lower 檔；合計 27 件。readiness 獨立 arm 4 件／lift 4 件，新增 `lab_station_arms.json` 與 CI gate。首次手臂契約抓到退化面 1 與自交 3，先三角化後局部 0.01 mm 合點、0.005 mm 退化清理後 arm contract 通過、無截斷，沒有放寬契約。證據 `tmp/lab-station-v8/verification-arms.log`。
- 尚未封存版本；已將脫齒加入兩頭隔離檢查，最新生成正在執行：exec session `88576`，tmp/lab-station-v8/verification.log。先輪詢同一 handle，再跑其餘三份 skip-generate 契約與完整 gate。仍需肘部五金保持／裝入、全臂姿態、肩根承力；readonly angle samples 不替代負載測試。

- V8 最新生成通過，隔離案例 12 個；四份契約曾全部通過。封存前補查脫齒五金，先紅重現螺栓跟隨下臂平移撞上臂（red-elbow-release-hardware.log）；改成 bolt 隸屬上臂、nut 隸屬下臂，五狀態檢查重新通過。ruff／三檔 explicit-package-bases mypy 通過。
- V01.0R.019 完整 `scripts/ci.sh --real` exit 0，所有 hard gates green，包含四份工作站契約；日誌 `tmp/lab-station-v8/ci-real.log`。肩根仍為參考幾何，肘部墊片／裝入／保持、全臂動作與承力均未完成，不能解除 H6。
- 5S：新增 arm 模組僅處理偏置接座與既有齒盤接合；臂件独立 readiness 分批，無放寬取樣或退化判準；V8 清除旧命名的兩件下臂 STL，輸出 27 件與契約一致。下步補肘部保持／裝入再轉肩根，不重跑已封存的設計工作。

- V9：肘部兩側墊片缺件先紅（tmp/lab-station-v8/red-elbow-assembly.log），補入後 216 個名義裝入位置通過。新增軸向餘量檢查：刻意把螺母向外移 4 mm，0 mm 穿出量被拒絕，證據 tmp/lab-station-v9/red-axial-coverage.json。49 focused tests、兩檔 mypy 通過；正例重建通過：合齒穿出約 4 mm、脫齒穿出約 2 mm。
- V01.0R.01A：完整 CI 的 T3 全部通過；命令 exit 1，唯一失敗為 model_lab_station.py 排版，已以 ruff 修正。T1/T2 重跑 exit 0、全部 hard gates green，紀錄 tmp/lab-station-v9/ci-final.log；原始完整日誌 tmp/lab-station-v9/ci-real.log。肩根連接仍是下一個結構缺口；肘部防鬆／保持力沒有因軸向覆蓋而取得資格。

### 歷史 V9 未完成項目

- 材料、精確瓶口／瓶高、零件型號、負載、工作溫度與液體尚未確定。
- 本階段是配置／試配原型，不得聲稱全機可直接裝配或固定力已通過。

### 歷史 V9 後續與版本紀錄

- V3 直上抽出修正保留為可重現 checkpoint；持續完成下列機構資格，不能宣告全目標完成。
- 優先完成探頭軟夾與滑座的實際固定、背架到腕部的螺栓介面、導桿防脫、根部與底座承力、平台連接、LCD PCB 保持、線材與全姿態／載荷驗證。

- V9 5S：沿用 arm 模組，未新增執行通道；27 件輸出、契約與說明一致，生成件保留 tmp；已檢視 probe-raised.png。下一步完成肩根到機箱底部的實際承力連接。


- V10 肩根基線已量測，舊 root／固定齒盤／上臂／軸有多處互穿；證據 tmp/lab-station-v10/red-shoulder-interface.json。肩根守衛先拒絕舊模型，domain shoulder_neck 測試先紅再綠。
- 沿用 arm 模組，將接合／五金 helper 命名為 connect_serrated_joint／joint_hardware，加入肩部一體支座、上臂活動齒盤與 shoulder_release_mm。新增兩件肩部 rotor，契約改 29 件；肩部局部五狀態曾通過，完整回歸仍待通過。
- 修復布林軸孔共面造成一／兩條四面共邊：齒盤孔半徑 2.75、軸座 2.7。縮短肩部軸向尺寸並加入螺栓頭／墊片座，因直接沿用肘部寬接座會擋住折平 LCD。最後一次失敗為 LCD 後罩與右肩支座／螺栓互穿，已將固定接頸外移 1 mm、減薄螺栓頭；重建中 exec session `96569`，tmp/lab-station-v10/verification.log。先輪詢此 handle，勿並行啟動 Blender 驗證。
- 夾具場景完整性改為必要零件逐名核對，原 >=50 因合併件數失效；新名單 48 件，缺件負對照仍待補。58 focused tests、四檔 mypy 通過；版本未 bump、未提交。支座到機箱的軸承／底板承力連接未完成，不能聲稱整機可承重。

- 使用者最新修正：質疑線性滑座對 3D 列印的適用性，提出增加活動臂／自由度。接下來優先評估以獨立平行四連桿取代末端導桿滑座；不得繼續把直線滑座當定案。V10 最新 fit 生成 exit 0（session 96569 已結束），肩部／折屏修正獲得局部與 fit 契約證據；其餘 readiness、完整 CI、版本 checkpoint 未跑。
- 純解析候選：130 mm 平行桿，自 -22.62° 到 +22.62° 提升 100 mm，最大水平偏移 10 mm，向 -Y 運動時原有三探頭在假設 ID66 mm 圓筒內保有正間隙。tmp/lab-station-v10/rotary-lift-concept.json；尚非實體四連桿、臂間／瓶口掃掠或承載驗證。下一步依此候選建可見的旋轉式升降概念並檢查機構空間，保留兩頭獨立。

- 四連桿候選已建立 scripts/model_lab_rotary.py 與純領域 RotaryLiftSpec。先紅再綠的閉合／行程測試，13 個領域測試通過。以實際桿端局部座標驗證旋轉後的閉合；停掉單桿驅動會被拒絕（red-broken-link.json），重新啟用後正例通過。
- 第一輪整機探測發現下桿撞支撐與右側螢幕；改成末端架向外 66 mm、支撐由軸後方接入，最新 202 個探頭取樣與 42 個整機姿態通過；固定支撐對外殼／HMI 無非名義接觸，見 tmp/lab-station-rotary/assembly-motion.json。已檢視 working／both-raised 圖；生成器再現 motion 與負對照通過，非製造資格。
- 新真機入口 scripts/verify/lab_rotary_verify_real.py 已接入 ci.sh --real，沿用既有 oracle；無新增公開執行通道。三個動作圖、模型、報告由同一生成器再現；來源參考與限制寫於 11-rotary-concept.md。
- V01.0R.01B 準備完整 gates；未提交。四連桿所有移動件相互干涉、全組合／線材、實體轉軸與鎖定／平衡、機箱承力仍未完成；使用者資料缺口仍保留。

- V01.0R.01B 完整 CI 執行中：exec session `21530`，tmp/lab-station-rotary/ci-real.log。接手輪詢此 handle，勿並行重建 Blender。5S：新增概念頁納入導航，舊滑座頁標示為基線；新模組沿用原語意與工具，單檔低於 400 行，生成件留 tmp。

- V01.0R.01B 最終完整 `scripts/ci.sh --real` exit 0，全部 hard gates green；日誌 tmp/lab-station-rotary/ci-final.log，session 46584 已結束。初次 ci-real.log 的六件手臂超過 20000 面分析上限而失敗，且執行中改 CI 檔造成尾端解析錯誤 exit 2；已凍結腳本並完整重跑，不能把初次命令說成成功。
- V10 六件臂分成左右各三件 readiness，新增 lab_station_arms_right.json，維持禁止截斷；四連桿 gate 則只驗運動與場景表面碰撞，沒有冒用 readiness。新候選三張圖皆已實際檢視，文件與來源已入導航，DCC 16 passed。
- 下一步以 rotary 候選為主：補四連桿所有移動件互相干涉及雙頭同動；將支撐／轉軸佔位改成真正可裝配、可鎖定且能保持的機構，完成機箱底板承力。V10 夾具新逐名完整性守衛的缺件負對照尚需納入；不回到線性滑座主方案。

- 使用者明確要求四連桿僅負責升降，保留其他位置的原鉸鍊自由度。已加入每頭 base_yaw_deg／shoulder_deg／elbow_deg／wrist_deg，加上 lift_mm 共五個獨立控制；腕部手動調角，不自動對地補償。真 Blender 10 個隔離案例通過；支撐仍是包絡，尚非可鎖定的實體關節。
- 本輪未提交：新增 M5 名義轉軸／三墊片／螺母／雙軸套包絡，末端外移由 66 改 74 mm；同頭移動件配對、雙頭 121 高度組合、折屏取樣及交叉侵入負對照均由 focused 真機生成通過，日誌 tmp/lab-station-rotary/articulation-verification.log（exit 0）。新增控制最初 driver 無效，完整建立屬性／父子關係後重新編譯解決；缺控制負對照 red-missing-articulation.log。尚未跑本輪完整 CI／版本 checkpoint。下一步補支撐實體齒槽關節與抬起後側移姿態碰撞，更新概念頁並完成 gates；不能把五個控制的隔離測試當任意姿態安全或承力證據。

- V01.0R.01C focused 重建 exit 0，新增停用 yaw 驅動的 red-articulation.json 通過，恢復後 10 項正例通過；入口主動 reload 三個既有 helper。已檢視 pivot-detail.png，五金可見。5S：沿用既有模組（最大 337 行），更新概念頁與 R18 追溯；生成件留 tmp，沒有公開任意執行通道。準備完整 CI，尚未提交。

- 首次 V01.0R.01C 完整 CI exit 1，唯一失敗為嵌入字串內的專案 import 守衛，真機項目通過；修正為沿用 reload_modules_for 推導完整相依閉包，並設定根目錄後以資料清單載入。該守衛 5 個 focused tests 通過，無放寬規則；將重新完整跑 CI。

- V01.0R.01C 最終完整 scripts/ci.sh --real exit 0，全部 hard gates green，日誌 tmp/lab-station-rotary/ci-01C-final.log，session 62719 已結束。首次失敗紀錄保留 ci-01C.log。下一步將 rotary 肘部支撐包絡改為實體兩成員與齒槽／脫齒介面，再驗證轉動和裝入；肩／腕、底座承力與全姿態仍未完成。

- V01.0R.01D：舊 rotary 肘部被 integrated tooth 守衛拒絕後，沿用 connect_serrated_joint／joint_hardware 建兩成員齒盤與 2 mm 脫齒。右側下臂斜穿齒盤，改回接路徑後又碰升降桿；最後改從齒盤後上方繞回，focused 生成 exit 0，兩側五狀態與整機升降／折屏通過，tmp/lab-station-rotary/elbow-verification.log。新增 elbow-detail.png 與脫齒隔離項，待完整 CI。5S：僅沿用既有模組，沒有新增模組／公開執行通道；來源與 tmp 生成件分離，R19 與概念頁同步。

- V01.0R.01D 完整 scripts/ci.sh --real exit 1，唯一失敗為新增 rows 的 mypy 容器型別推導；T3 真機全數通過。補明確 list[dict[str, object]] 註記後 scripts/ci.sh exit 0，T1／T2 全綠。證據分別 ci-01D.log 與 ci-01D-static-final.log；不宣稱第一次完整命令成功。肘部 10 狀態、含脫齒 12 隔離案例與局部圖已核對。下一步肘部五金裝入／工具空間、支撐網格製造契約，再進肩／腕／底座承力，仍 ACTIVE。

- V01.0R.01E：網格基線 elbow-mesh-baseline.json 抓到四件支撐各 15／438／107／711 非流形邊，部分有退化面。固定接頸改實心 beam，不再挪用含孔圓耳的 bar，沿用 finish_arm 後四件單殼／零非流形／零退化通過。裝入檢查抓到立起 HMI 阻擋內側墊片；先收折到 tilt_step=0 後 216 取樣通過。曾誤用 tilt_deg 與反向端點，已依 screen_control 既有定義修正，沒有改變螢幕語意。focused 重建 exit 0，日誌 support-mesh-verification.log。準備完整 CI 與開面負對照。5S：沿用既有梁、收尾與裝入驗證，模組最多 349 行；生成件留 tmp，R20 同步。

- V01.0R.01E 完整 scripts/ci.sh --real exit 0，所有 hard gates green，tmp/lab-station-rotary/ci-01E.log，session 17752 已結束。support-mesh.json 四件均單殼／零非流形／零退化；red-support-mesh.json 開面後 3 邊拒絕；elbow-assembly.json 216 取樣通過。新局部圖已檢视，固定接頸無多餘圓耳孔。下一步工具空間、四件支撐自交／匯出契約，再肩／腕／底板承力，整機仍未完成。

- V01.0R.01F：工具基線 red-elbow-tools.log 重現實心螺栓頭擋住扳手，rotary 螺栓補 4 mm 名義內六角孔；兩側六角扳手與套筒四項就位、封孔負對照通過，focused log elbow-tools-final.log exit 0。沿用現有 arm／motion 模組，最大 356 行，新增 R21；不更動 V10 螺栓或公開工具。待完整 CI。自交／匯出契約、手柄掃掠與承力仍需完成。

- V01.0R.01F 完整 scripts/ci.sh --real exit 1，唯一失敗為 model_lab_rotary.py 格式，所有真機項目通過。ruff format 後 scripts/ci.sh exit 0，T1／T2 全綠；證據 ci-01F.log／ci-01F-static-final.log，不將初次命令稱為成功。已檢視六角孔局部圖，elbow-tools.json 四項零表面碰撞、red-elbow-drive.json 封孔拒絕。下一步優先補四件支撐自交／匯出契約，再處理工具掃掠與肩／腕／底座承力。

- V01.0R.01G：先紅拒絕缺少 LR_CHECK／STL 的場景（red-support-contract.log），新增四件獨立副本與毫米 STL、左右 readiness 契約。第一次副本碰撞量測讀到隱藏前的舊矩陣，調整為位移→update→hide 後重新生成，左右契約首次均 exit 0，無禁止問題或截斷。support-export-final.log 四 STL 對世界頂點尺寸差 ≤0.02 mm；沿用 binary_stl_metrics 與既有契約框架，無新增 Python 模組。5S：模型 371 行，輸出留 tmp，R22 同步。準備完整 CI，整機未完成。

- V01.0R.01G 首次完整 CI exit 1：checks 缺註記、STL 比對未使用收窄工具、契約沿用場景來源未被架構守衛辨識。改 list[str]、as_sequence／as_finite_number，第一份支撐契約明確生成、第二份沿用；12 架構 tests 通過。最終 scripts/ci.sh --real exit 0、所有 hard gates green，ci-01G-final.log，session 83040 已結束。首次 log 保留 ci-01G.log。四件 STL 仍為試配，未發布整機；下一步肩部／腕部實體介面與底座承力，工具手柄掃掠、載荷／線材仍未完成。

- 使用者指出「一堆實體與連接組件都斷開」。已中止原先逐件擴充，查明新肩部兩側各有 2 殼（disconnected-audit.json），薄梁 6 mm 套用原接頸偏置形成間隙；肩接頸中心由 ±13 改 ±12 mm。移除獨立 support_envelope_2，前臂與接回段／叉耳整合，固定框加入舌片／82 mm 後置腕部橋接與穿軸。腕部曾撞肘部／斜接段，改後置並先上升再橫接。14 件結構網格、肩部五狀態、腕部 −15／0／15° 共同孔／實體／五金檢查及既有回歸 focused exit 0；日誌 reconnect-verification.log。
- V01.0R.01H 待完整 CI，新增腕部斷接負對照；渲染搬到既有 lab_station_render，沒有新模組。底座仍只接觸上蓋、沒有機箱固定／底板承力，不能說全部斷接已修完。下一步先完成底座機箱連接，並維持整條實際介面檢查；不以單件水密代替整機連接。

- V01.0R.01H 首次完整 CI 唯一失敗為共用肩部偏置變更使舊 V10 肩座擋折屏；改 neck_plane_mm 參數，預設保留 13 mm，rotary 顯式 12 mm。最終 scripts/ci.sh --real exit 0，所有 hard gates green，ci-01H-final.log，session 4868 已結束。新 working.png 已檢視；14 結構件、14 控制隔離、10 肩部狀態與 6 腕部同軸介面案例核對，red-wrist-disconnection.json 移開叉耳會被拒絕。5S：渲染移到既有 render 模組、契約 reload 清單更新，無新模組或放寬判準。下一步最高優先：底座至機箱的實際固定／底板承力，然後全臂介面／載荷／線材；不可宣稱所有斷接已完成。

- V01.0R.01I：底座未保持的 RED 已確認（red-base-retention.log）；新增獨立 lab_station_base，旋轉腳軸頸／金屬軸套／M5×90 穿軸與薄螺母／上下墊片，支承柱接 6 mm 底板與側壁，8 mm 底腳避讓頭部。泵浦佔位內移 10 mm。base-final.log focused exit 0，兩侧十個止擋位移、共同開孔、中立間隙與移走墊片負對照通過；base-section.png 已檢視，為切開副本。5S：新模組前已查 GitHub，沿用原語意工具；model 375 行，生成件留 tmp，R24／參考／限制同步。準備完整 CI，尚未提交。下一步新機箱／旋轉腳網格匯出契約、穿軸／工具裝入與整體受力；不可宣稱整機可印可承重。

- V01.0R.01I 首次完整 CI 全綠（ci-01I-final.log），但尺寸複查發現新支柱高出上蓋底面 0.2 mm，原守衛漏掉機箱／上蓋配合。補查先紅（red-base-lid.log），支柱頂端降至 75.9 mm，上蓋底面 76 mm；加入凸柱穿入負對照。首次全綠不足以接受修改後模型，需完整重跑。

- 使用者中止複雜機構方向並明確要求「開始」簡化。01I 舊底座補查後 CI rechecked exit 0，但新主線改為 `model_lab_simple.py`：雙節臂每頭 150+150 mm，四調整點，取消四連桿／長穿軸／軸套／墊片；HMI 支座整合上蓋。`SimpleArmSpec` 先紅後綠，15 domain tests；新真機入口驗 202 個探頭／杯壁取樣、另一頭不動、22 個單臂空間姿態與三個雙臂展示姿態，移走上臂材料必須失敗。右臂原撞 LCD，鏡射局部錯位後通過；先挖孔再聯集留下內部蓋面，改實體聯集後開孔，實體孔檢查通過。`/tmp/lab-simple-final.log` exit 0。新主線仍為光滑關節概念，齒槽、埋入螺母、探頭夾紧、五金裝入、完整收折路徑／受力未完成，不能冒稱製造模型。準備本輪完整 CI。

- 簡化版首次完整 CI exit 1（tmp/lab-station-simple/ci-simple-final.log），新簡化 gate 通過，但旧 V10 重建被「使用中函式庫不可覆寫」拒絕。簡化生成器直接 append 會保留原來源，改沿用 rotary 的獨立 baseline 副本載入；清回已知生成場景後 focused independent-load.log exit 0。入口增加禁止持有可重建來源庫的檢查。需完整重跑，不將首次整體執行稱為成功。

- V01.0R.01I 最終 `scripts/ci.sh --real` exit 0，所有 hard gates green，tmp/lab-station-simple/ci-simple-rechecked.log，session 14080 結束。獨立 baseline 修復已由整套重建確認；簡化模型 202 探頭／杯壁取樣、22 單臂空間取樣與三展示姿態通過，斷接材料負對照會拒絕。working／parked 圖已檢視。5S：新主線導航 12-simple-concept、R25、範圍與五金表同步；新生成器 <300 行，重用原語、domain／oracle，生成件留 tmp。下一步只細化簡化版齒槽、埋入螺母、探頭夾緊與完整取出／停放路徑，保持減件方向；未發布 STL 或承重資格。

- 使用者拒絕獨立五連桿候選，要求參考常見設計，再接受 Agilent／ELMETRON／GOnDO 電極臂方向並要求延伸。已停用 five-bar domain，候選原稿留 tmp/lab-station-platform/rejected-fivebar；保留 simple 基線。新增 ElectrodeArmSpec 先紅後綠，16 domain tests。model_lab_platform 改成肩鉸鍊＋前臂平行雙桿＋三角末端，手調探頭角度；借用商用品用途，不冒稱整臂自動水平。
- electrode focused 真機入口 exit 0（/tmp/lab-electrode-verified.log）：46 單頭位置、六結構件全配對自碰／共同孔軸、雙頭／HMI／外殼／杯壁、16 折屏角度與移走 follower 負對照通過；已檢視 working／raised。修正舊夾座碰三角板、內側 follower 擋 LCD、夾座側移後兩頭相碰；改一體外側夾座、follower 外側錯層與根部 yaw 補償保持共杯位置。這些是既有「全配對／閉合」失效類別，沿用實網格守衛。
- 五金範圍：12 螺絲／12 螺母，4 列印被動軸包絡，零軸套／獨立墊片；被動軸尚無防脫，不是製造件。下一步被動軸保持、旋鈕齒槽與夾頭固定；全五金互碰／連續掃掠／線材／負載仍未驗。5S：新說明 13-electrode-arm 接入導航及 R26，生成件留 tmp，沿用 oracle 入口，不新增公開通道。完整 CI 待跑。

- V01.0R.01J 完整 `scripts/ci.sh --real` exit 0，全部 hard gates green，日誌 tmp/lab-station-electrode/ci-real.log，session 69710 結束。四張視圖皆已檢視；前臂及螢幕仍為有明確驗證邊界的概念模型。5S：模組 250 行、沿用驗證入口，未發布 STL；下一步在此電極臂上完成被動軸防脫、齒槽／旋鈕與夾緊，禁止回到被拒絕的五連桿候選。

- 使用者回饋「好一點但還是跟參考產品有差」。已透過瀏覽器實際檢視 GOnDO 兩張原廠圖；先前未充分核對照片比例，這輪將 Ø36 端盤→Ø22、梁寬16→12、桿距40→24、平台偏置45→28。上臂內藏連動不能僅憑照片宣稱同款；沒有套用 Agilent 的整臂自動水平功能。輸出分離至 tmp/lab-station-electrode-compact，01J 保存原檔供比較。尺寸測試先紅後綠，16 domain tests；focused real /tmp/lab-electrode-compact.log exit 0，46 位置／16 折屏／斷接負對照通過，working 已檢視。完整 CI 待跑。

- V01.0R.01K `scripts/ci.sh --real` exit 0，全部 hard gates green；tmp/lab-station-electrode-compact/ci-real.log，session 49468 結束。四張新視圖均已檢視。5S：沿用兩個生成器與既有驗證入口，修改 link 增加保留預設的端盤半徑參數，舊 simple 不受影響；比例說明覆寫 13-electrode-arm，舊實體輸出保留對照。仍需被動軸防脫、旋鈕／齒槽與夾具，未聲稱完全還原商用電極架。

- 2026-10-02 接手：01K 工作樹乾淨，上輪屬已完成 checkpoint 的進展。Blender LaunchAgent 為 exited／addon socket 無監聽，kickstart 同一已安裝服務後 PID 95354、addon socket LISTEN，重載 compact 模型。新增實網格基線 tmp/lab-station-electrode-compact/passive-pin-baseline.json：四被動軸於三高度共 12 案例對六結構件無表面交叉。passive-pin-retention-red.json 的 20 軸向位移案例證實：四軸向內 −2 mm 皆被 follower 擋住，向外 +2／5／10／20 mm 取樣皆無阻擋；現有單頭軸缺另一側止擋。未改模型、未執行新完整 CI、未新增製造資格。下一步補可裝入的列印防脫構造，再將中立間隙／雙向止擋與移除止擋負對照接入既有 real gate。

- 01L：missing-retainer 先紅；四被動軸加入 Ø3.4 × 1.8 mm 溝槽、厚 1.4 mm 的 C 形卡扣（Ø9／Ø3.8／開口 3 mm），不加金屬件。focused /tmp/lab-pin-focused.log exit 0，46 位置合計 2760 個軸向止擋／槽肩／拔插取樣通過；working 已檢視。32 domain／DCC tests 通過（首次 DCC 拒絕接手筆記重複埠號，改引用 addon socket），ruff／兩檔 mypy 通過。完整 CI session 59559 執行中，ci-retainer.log 目前服務檢查因三個 /tmp 日誌缺檔失敗；先等同一 handle 結束，再重裝 api/web 與完整重跑。卡扣彈性未驗，不能以剛體止擋宣稱實體保持力。5S：沿用現有模組，model 329 行，無新模組／公開通道，新增 R27 與局部圖，輸出仍留 tmp。

- 01L 首次完整 CI session 59559 exit 1，共 8 gate 失敗：服務日誌缺檔、readiness 缺報告／回報其他模型的 bounds、交付 502；新增電極臂 gate（含 displaced-retainer 負對照）通過。已檢視 retainer-detail.png，卡扣開口可見。使用正式 install api／web 恢復服務，health connected、Web 正式 preview 監聽後重跑 session 73908，日誌 ci-retainer-rechecked.log；不要並行操作 Blender。版本已 bump 01L，尚未提交。

- 01L 第二次完整 CI session 73908 exit 1：服務一致性已通過，但仍有 5 個回應缺失／錯配相關 gates 失敗。追查共用 socket，發現 timeout／cancel 後沿用舊串流會誤收遲到回應。新增 loopback 兩案例先紅（red-late-reply.log 都收到 request 1 而非 2），改中止時 disconnect、不 replay，22 adapter tests 全綠。沿用原模組，無新增通道／公開 DTO；LESSONS 新增無 request ID 之中止隔離失效類別，T2 納入守衛。API 正式重載修正後需第三次完整 CI。

- V01.0R.01L 第三次完整 scripts/ci.sh --real exit 0，全部 hard gates green，ci-retainer-final.log，session 13650 結束。實際載入新 socket 修正後，前兩輪的 report 缺失／錯配與 REST 交付失敗均未重現；初次／二次日誌保留。新卡扣局部圖與 working 已檢視，2760 軸向取樣、46 位置、16 折屏及 displaced-retainer 負對照通過。5S：沿用兩 CAD／驗證模組與既有 socket adapter/test，無新模組／公開 DTO；新失效守衛納入 T2。下一步完成緊湊臂旋鈕／齒槽與夾具，卡扣彈性／材料、全五金／線材／負載與製造匯出仍未取得資格；整體目標保持 ACTIVE。

- 01M：旋鈕缺件守衛先紅；沿用 lab_station_joints 增加六個帶六角孔的列印旋鈕、六角螺栓頭與臂件內螺母座。肩／肘 Ø25，末端 Ø17；較大的末端旋鈕曾撞夾座，縮徑後 /tmp/lab-knob-focused.log exit 0。46 位置下同頭旋鈕碰撞、頭／螺母中立間隙與 30° 相對止轉通過；working 已檢視。三檔 ruff／mypy 通過。5S：沿用三模組，主生成器 393 行，無新模組／公開通道；新增 R28，金屬件仍 12 螺絲／12 螺母。完整 CI session 60392 執行中，ci-knobs.log；先輪詢，不並行操作 Blender。旋鈕承壓鏈同時閉合與預緊、裝入路徑、齒槽與實際鎖緊力未完成，不能稱全關節可鎖定。

- 01M 完整 CI session 60392 尚在執行，已知失敗：T2 主生成器 393 行觸發 380 行預警；simple/electrode 與 rotary oracle 等待逾時。Blender 日誌確認逾時後仍繼續渲染；程序取樣 blender-sample.txt 顯示主執行緒仍在執行 Python，並非停住，電腦另有其他高負載工作，未終止它們。不要重啟同一驗證或並行操作 Blender；先輪詢 60392，最新 child 為 rotary support contract。
- 旋鈕真機階段已結束後，將旋鈕五金與 retained_pivot 建立抽到既有 lab_station_joints（無新模組），主生成器降回預算內；verify_knobs 在每姿態快取不動的 BVH，保留全部碰撞／30°咬合檢查。21 budget／DCC tests、兩檔 mypy 與 ruff 通過。這些整理尚未重新通過真機；版本 01M 已 bump 但未提交，不得當已封存。等待當前 CI terminal 後，先 focused 重建量測耗時／看圖／驗 red-knob-drive，再完整 CI，成功才 checkpoint。下一機械工作仍是旋鈕承壓與裝入、齒槽與夾具。

- 接手重驗 37 domain／DCC／budget tests 與 ruff 通過，上一 goal turn 屬具體幾何／守衛進展。60392 已確認持續執行，但已有確定失敗且使用整理前來源，故明確終止該 CI 及所屬子程序（exit 143），並非誤把觀察逾時當停止；Blender read-only barrier 成功回覆，確認先前工作已排空。現以整理後程式 focused 重建，exec 46829，knobs-refactored.log，含實際 elapsed_seconds；等待此 handle，勿並行生成。

- 整理後 focused 46829 的等待於 300 秒逾時（exit 1，knobs-refactored.log），不能推論 Blender 已停。knobs-sample.txt 取樣主執行緒主要為 C_BVHTree_FromPolygons／平衡與頂點讀取；共用 model_lab_simple.verify_clearance 仍在每配對重建相同 BVH，是下一修正目標。已排入只讀空間檢查的計數負對照，exec 9163／red-clearance-rebuild.log，將在前一主執行緒工作後執行；目前仍 live。不要另啟生成或重啟 Blender，先輪詢 9163，再查 red-clearance-rebuild.json。預期舊版每物件多次建 BVH，修正為每姿態一次且保留全配對，將計數守衛納入既有 real 入口。修正尚未寫入；旋鈕與 extracted helpers 的 real acceptance 仍未完成。

- 01M 計數負對照 9163 exit 1，red-clearance-rebuild.json 實測 31 物件／580 次 BVH／單物件最多 27 次，確定為重複計算。model_lab_simple.verify_clearance 改每呼叫一次局部快取，保留原全配對；正例變 31／31／1，移右上臂入左臂拒絕、還原通過。既有 real 入口加入計數與 red-cross-arm 守衛，LESSONS 記錄同姿態重建失效類別。四檔 ruff／mypy 通過。
- 整理後完整 lab_simple real 入口 exec 8736 exit 0，knobs-cache-verified.log：simple／electrode 重建、卡扣／旋鈕與快取負對照全部通過；working 已重新檢視。完整 CI exec 51041 正執行，ci-knobs-final.log，先輪詢同一 handle；未提交。主生成器 372 行、既有 joints 215 行，無新增模組。

- 01M CI 51041 的 REST o_names 發生 JSONDecodeError，MCP/chat 後續通過；檢查找到整段 stdout 當 JSON、artifact 只取末行的脆弱解析。以背景日誌前後夾入資料的案例重現同類失敗（red-oracle-logging.log、red-artifact-logging.log），REST/chat 名單、REST 頂點數、protocol/artifact JSON 都改沿用標記解析且維持 schema 檢查；11 parser tests、四檔 mypy 通過。停止已失敗且過期的 CI 51041（143），目前排空確認與新版 execute_json 真機呼叫 exec 47523 等待中；先輪詢此 handle，不要並行操作 Blender。成功後重新完整 CI，尚未封存。

- 47523 exit 0 回報 drained=True，確認排空及新版 artifact 標記解析真機通過。第三輪完整 CI exec 48990 執行中，ci-knobs-rechecked.log；目前 T1/T2、REST/MCP/chat 與 readiness fixtures 通過。先輪詢此 handle，不並行 Blender；所有尚未封存的 01M 修改仍需本輪全部 gates 通過。

- 01M 第三輪 CI 48990 仍 live，但 batch-transform 在 seed oracle 的 20 秒等待逾時，隨後 lab-station 生成 oracle 也逾時。REST/MCP/chat/print-readiness 已通過，未復發場景清單 JSON 雜訊錯誤。將 Blender 帶回前景仍無足夠證據支持 App Nap 推論；CUA getApp 觀察亦逾時，不能當應用程式已停證據。PID 95354 仍在運算，其他高負載程序存在但未干預。保留目前 CI 以收集其餘結果，先輪詢 48990／ci-knobs-rechecked.log，不並行 Blender，不宣稱完整通過或 checkpoint。

- 01M：第三輪 CI 48990 已確認失敗後仍跑依賴場景，明確停止所屬程序（143）；只讀 barrier 78019 exit 0，drained=True。既有 test_ci_failure_log 新增真機失敗後不得續改場景，2 red → 6 green；ci.sh 真機 hard failure 現立即退出，靜態仍彙整。完整靜態 CI 97855 exit 0（ci-failfast-static.log）。正在單獨重驗先前 batch seed 逾時，exec 23852／batch-isolated.log；這筆結束前不要並行操作 Blender。最新 working 圖已檢視，方塊夾頭與軸端整合仍與參考有差；未改這些幾何，也未封存01M。

- batch isolated 23852 exit 0，2/2 通過且已清理測試物件。修正後完整 CI exec 47627 正執行，ci-knobs-failfast.log；先輪詢這個 handle，真機失敗即停，不在運行中改 CI、不並行生成。靜態 CI 全綠不替代本次完整真機資格，01M 仍未提交。

- 01M 完整 CI 47627 exit 1，前面所有已執行 gates（含工作站與現行臂）通過，尾端 REST generation delivery 502，fail-fast 阻止後續 determinism。只讀 barrier 通過；舊 API 單獨重驗29325在31.155秒再次502。定位到30秒通用期限，TimeoutError 又被 MCPClient 一般例外分支變成空錯誤的腳本失敗。新增真 loopback 分類與三個期限案例先紅後綠；只為 registry 完整生成碼注入900秒，一般操作30秒不變。54 tests、mypy、ruff通過，API已正式重載75026 exit 0；focused REST 69589／delivery-timed-fixed.log 執行中，不並行生成。無新模組／公開DTO，01M未提交。

- focused REST 69589 exit 0（delivery-timed-fixed.log），5/5 STL重現與API回報一致，耗時28.854秒；這次低於原30秒，長期限邊界由真loopback與接線守衛證明，不將此單次耗時當超時邊界證據。最新完整 CI 58285／ci-knobs-deadline.log 正執行，先輪詢同一handle。前次47627已terminal；不要重跑或並行生成。01M未提交，下一步待全綠後checkpoint；夾頭造型／軟襯與鎖緊仍未完成。

- V01.0R.01M 最終完整 `scripts/ci.sh --real` exit 0，session58285結束，ci-knobs-deadline.log所有hard gates green，包括先前失敗的REST交付及末項determinism。新API已正式載入期限／分類修正。最新工作／抬起視圖與旋鈕負對照已檢視。5S：主生成器372行、socket adapter351行、專案技能150行；既有模組重用、現行與歷史規格分開，新增來源查找紀錄，生成件留tmp。沒有整機製造資格；下一步可側拆軟襯夾頭、軸端與關節過渡，再齒槽／承壓／裝配與負載。
