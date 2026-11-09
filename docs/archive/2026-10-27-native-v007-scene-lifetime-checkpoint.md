# Task index — progress SSOT

Read this file first after a new conversation, compaction, or terminal restart.

## 接手

- **V008原3MF座標綁定（後續輪）：** 新mesh_binding重用binary_stl_surface／parse_closed_surface，以唯一24種正向換軸＋平移、頂點一對一映射及完整有向三角面多重集合核對原件，不做ICP／合點／修面。11例涵蓋改面、反向、鏡射、縮放、空／無效輸入、對稱歧義、舍入；來源模板7例中duplicate-owner／empty-owner先真RED、補非空唯一guard後GREEN，合計18例。check_plate_bindings已接同一原件factory正例，讀當次captured 3MF／原STL收據，不另選來源；原Back／Lid各唯一換軸，最大4.3794e-6／5.3760e-6mm，與獨立NumPy全距離probe之有向面讀回一致。SciPy不在環境，探針改NumPy分塊、正式模組只用標準庫，無新增依賴。最初all-with-binding執行時補guard，不作凍結驗收；最終20734 exit0的all-binding-frozen前後696來源集合與SHA皆相同，完整69 STL／原態／重開／三拒絕控制均通過。43279完整static exit0，docs DCC16過；未做新3MF、未切候選、未接public NativeRunner。主原685集合及104資產已本輪重核零差，post-resume-source-readback.json。主007同一65198／31268仍執行，目前registered MCP已PASS；禁止改主來源／VERSION／重啟或並行共用Blender。新增證據與來源已保存主native-v008-isolation/plate-binding-supplement，749檔SHA逐項相同；更早未凍結all-with-binding僅保留logs／verdicts並標示exploratory，不移用其成功作驗收。
- **V008附掛進度（主007仍凍結）：** 本輪是實質進展。19份007工作檔已獨立備份到主native-v007-isolation/before-v008/manifest.json後，以version.py先升V01.0T.008再收集測試；主VERSION仍007，未從附掛部署。新封閉screen-clamp request只允許recipe與indexed target；screen_revision_plan24例RED→GREEN。既有CDT／rebase／paired-contact與Boolean被實際原件配方重用，來源準備明確列出3 fastener CDT及Back／Lid／wrist canonical綁定，不再讀研究candidate作來源。
- **V008真實缺陷與修正：** 第一原件factory在建primitive時落入原window collection，原態被改，保護機制拒絕candidate。只加collection／layer_collection仍不能讓operator安全；window=None在獨立worker segfault139，crash已存tmp/native-revision-v008/window-override-crash.txt，未碰主Blender，禁止重試此解。既有primitives新增顯式collection BMesh與顯式depsgraph evaluated Boolean，預設生成器路徑保留；NativeSceneSession只補collection／layer_collection，不切window。primitive-context真RED後GREEN，修正測試是在同一內部context前後觀察，不拿暫時改名後的全資料與外部快照誤比；外部完整原態仍嚴格驗。lifetime新19／18例（含當前原model144）與fresh reopen皆過，77668 exit0。
- **V008原件與完整STL結果：** 新factory經同一catalog＋NativeRevisionService／staging抓目前來源，原場景亦載入同一整機144物件；all-final（65871 exit0）13階段CGAL與材料內外點皆過，candidate仍144／113／active144／0庫，raw geometry／frames／parents／driver bindings重開相同、0無效driver、原態相同。worker70029 background／無MCP addon／無TCP。兩個修訂：原LS_FIT_lcd_back左避空、原LS_FIT_lid整合止擋，無新增剛體身份；canonical配準最大3.17e-5mm、其他frame最大3.52e-5mm。skip-cut先真RED（無作用仍被接受），補material witness後skip-cut／skip-stop各因指定材料變化缺失拒絕；stale canonical改header即在mutation前拒絕；三例均原態相同、無candidate。SrcData只用本輪current manifest，不選歷史native。
- **V008檔案交付原語：** 新NativeStlWriter注入既有MeshIntegrityPort／ImportLimits，完整69 STL獨立驗過；67件逐bytes相同，只2件新export。晚到有效幾何tamper／extra、空verdict、existing receipts、3次取消排空等12個IO案例過；新plan／factory wiring加總42例過。94057完整static exit0，T1／T2全PASS；full mypy與ruff過，SWIG既有metadata warnings留存、不過濾。gate已接附掛ci.sh --real（正例＋三控制），不是主007已跑過的新gate；未整合或公開NativeRunner／新工具／同一job路徑，不得當完整原件服務或整機資格。
- **V008保存與可見成果：** 主tmp/current-native-qualification/native-v008-isolation/已保留1981檔（含28份當時來源），evidence-sha256.json逐項核對；完整STL與native為evidence/all-final/none/complete-stl，另有same-parts-screen-clamp-69-STL.zip（69 STL＋對應SHA256，ZIP SHA6c49be3d70dfe535e5636b59180a0dfc8e171e81870daf883cab91ec570d90e7），已在對話交付可檢查連結，仍為候選。zip／README在writer產物根之外，不改已簽集合。全104原資產與主685來源凍結維持；未改model-spec.json、未產生新3MF、未啟印。
- **下一步必須收斂：** 完整STL已先提供，後續3MF必須替換實際兩件幾何並驗身份／plate碰撞，不能copy舊mesh／舊Gcode冒充新件。唯讀看過目前3MF：70個.model entries＝1 wrapper＋69 mesh，model_settings69 object；Lid wrapper id2→3D/Objects/object_1.model／inner1，Back wrapper id6→object_3.model／inner5。兩新STL bbox extents與各自原件完全相同，但模板mesh已換軸居中（Lid66×150×230、Back128×54×165），不可直接塞未轉換座標；原69擺位可作候選，仍須實際幾何碰撞與真切片。NativeRunner還須綁完整request、一次captured ModelSpec／print target／source receipt、共享AppRuntime／job／lease及同task grant；不能在preparation後重查mutable provider取設定，也不能把IPC timeout當worker terminal。持續接主007同一65198／31268，不改主來源或重啟。
- **V007已正式載入並開始核心：** 主77785完整static exit0、installer79489 exit0；loaded plist／API freshness均過，API29065、Blender28877、Web29295。68907公開bootstrap通過：REST／MCP／schema例／本機同v80、default_native104／69、獨立oracle零差、21工具且無public execute_code，實際production JS／CSS可讀、無HMR。初始恢復42782 exit0，原native144／113／active144／0庫與raw geometry一致；正式頁面已實看原v80機構、console error／warning0，主tmp/current-native-qualification/native-v007-production-restored-v80.png，browser已關閉。這是核心前初始狀態，核心終態後仍須再恢復與讀回。
- **V007本輪新閘門已過：** 同一65198核心已PASS T1/T2、installed／freshness、isolated native lifetime、REST／MCP／readiness／batch；父31268在3m00仍存活，後續機構／切片未終態。這次真實CI的factory工作為主tmp/native-session-7100c14f8993490783bcbe04bf03b3e1，合成18／選定v80 17例與重開皆過；native-v007-core-native-session.json記兩份結果及來源集合685檔零差。不要拿V006正反run當007切片證據。下一輪應直接推進原件閉集合recipe／native runner與同一AppRuntime／job；重用既有screen_clamp、mesh_frames、Boolean／STL／CGAL，不再擴張無關通用框架。
- **目前唯一執行中的核心：** session65198／父PID31268，主tmp/current-native-qualification/native-v007-real.log；起跑前685個來源／依賴／選版宣告已凍結（native-v007-source-freeze.json及freeze-recipe）。主來源／VERSION不可修改、不可部署／重啟／並行共享Blender。等待同一handle終態；007的factory生命週期是新增T3閘門，但未通過同一輪前不得當正式資格。附掛仍可headless開發下一步，若動新source必須先固定新版；不得從附掛部署。完整native runner／原件幾何修訂／STL先於新3MF仍未完成。
- **最新基線與V007：** 主V006已封存33c851f，session55541 exit0、封存static91892 exit0、checkpoint42906 exit0／C1–C5全PASS；push58682 exit0、origin/main已到33c851f。正式服務已從主目錄載入V007、共用模型仍v80，原模型／69 STL／3MF未動。附掛branch codex/native-revision-service已用mixed reset對齊33c851f，48份原工作檔在reset前後逐項SHA相同，僅同步新封存歷史與文件結論；附掛VERSION仍未commit V01.0T.007；正式部署只從主目錄執行。
- **V007可重用原場景保存：** scripts/blender_native_session.py封裝append／臨時ID名稱隔離／single-scene context／subset write／batch_remove及原態核對；raw geometry、父關係、driver定義、property UI／選取／原context分開觀察。pending僅在清理通過後排他發布，晚到同名檔保留；故意改原driver或UI會restoration error且無候選，不能說已回滾。最新67497 exit0，tmp/native-session-v007/modular-all-preconditions合成18／實選v80 17例、新程序reopen144／113／active144／0庫，原SHA相同；新門接附掛ci.sh --real，尚未由正式共用服務跑007整輪。
- **V007當次工作授權：** RequestScriptAuthority限定逐字程式／有限正deadline／owning task／有效scope；子task與原task副本重播各有真RED，finally撤銷共享permit＋reset後GREEN。可選scoped_timeout同一callback接sandbox與socket factory；預設靜態授權不變，SSE只有明確要求新policy才拒絕。新19例及鄰近73例通過，15891完整static exit0（request-authority-full-static.log）；已記教訓與GitHub CPython前置查找。尚未注入正式AppRuntime，應隨native runner同一組裝完成，沒有公開新script／path工具。
- **證據保存與下一步：** 主tmp/current-native-qualification/native-v007-isolation首批349檔、preconditions-final414檔與request-authority60檔（含48份工作來源）均有獨立SHA清單且逐項重核。對齊006後只有19份007預期差異，3825完整static exit0；已用native-v007.patch明確整合主，19檔逐項相同（含新檔），未改models。正式部署已完成，接續同一65198核心；native runner／閉集合修訂／同job與lease仍是後續真餘項。IPC timeout不表示Blender worker已完成，不可只shield網路await即釋放lease或宣稱恢復。同步封存文件時曾取錯CHANGELOG段落而assert停止，未改原工作bytes；已改按唯一行取值並續行。

- **目前：** 任務16 ACTIVE、任務17階段1 AWAITING-ACCEPTANCE。主目錄V01.0T.006的來源識別／來源暫存與取消排空已正式載入；本次提交封存這個階段，不代表原生修訂或整機工程資格完成。歷史開發與失敗逐字保留 [V006交接快照](2026-10-27-native-source-checkpoint.md)，更早研究只按其連結追溯。
- **本輪完整核心已終態：** 同一session55541 exit0，父60690／末子14919已退出，`tmp/current-native-qualification/native-v006-real.log` 全部T1/T2/T3 PASS。註冊MCP11套與5控制皆真；當輪正例dfad4f94de454c7f8a4da4751fab8744完成69件geometry 0失敗、print／package PASS，實際3MF ZIP只有Metadata/plate_1.gcode；反例edc197aa3018424ab41046fb1ee511c4只走import／geometry並拒絕，未進print。沒有選對話套件，也沒有宣稱Ollama或Claude LLM對話通過。
- **同輪交付閉環：** 679來源／依賴／選版宣告與完整集合逐項相同，104原模型資產SHA皆相同；REST／MCPcatalog／schema例／本機唯一選版相等，default_native獨立本機oracle無差，公開正反report等於持久化檔。`native-v006-final-public-readback.json`與`native-v006-public-check.log`留證；唯一manifest native已恢復144物件／113mesh／active144／0外部庫，raw geometry等於獨立factory來源記錄且原SHA不變（`native-v006-final-native-restoration.json`）。本輪結果不可被005報告代替。
- **Claude與正式頁面：** 既有Claude Code project server blender-mcp-studio解析同canonical HTTP URL，再由標準MCP Client讀回104／69與21工具；`native-v006-claude-config-readback.json`是CLI配置＋實際MCP讀回，不是Claude LLM對話。正式production頁已實讀hashed assets，health connected，browser error／warning0；公開頁面的實際操作與未完成原生修訂不可用配置成功取代。模型仍由models/lab-station/model-spec.json選定v80，不新增入口／fallback。
- **後續開發保留：** 附掛`/Users/bearmacmini/.codex/worktrees/native-revision-service/Blender_MCP_drawer`、branch codex/native-revision-service有未commit V007。它將append／subset-save／原場景核對模組化，factory合成18例／目前v80 17例與新程序reopen通過；新增當次task／scope／逐字腳本授權的19例與鄰近73例通過，完整static15891 exit0。尚未把新authority及native runner接入正式AppRuntime，無新完整修訂STL／3MF，不能宣稱公開修訂完成。研究及來源備份已保留主tmp/current-native-qualification/native-v007-isolation（349＋414檔）；authority本輪60檔已另存request-authority並核SHA。不要從附掛目錄部署，先以明確diff整合。
- **下一步：** V006已完成checkpoint C1–C5與push58682；V007已對齊006，接續檢查diff、整合與核心。真正餘項仍是閉集合原件配方、native executor／來源還原、同一job／lease／REST／MCP、完整原身份STL先於新3MF；IPC逾時不能當作Blender worker已排空。持續goal下暫不切換context，checkpoint後繼續。
- **工程驗收仍開放：** 允許拆支撐／brim，不接受鑽孔、研磨或修整配合面；雙獨立探頭、雙上下臂、四點梯形、約200mm、250mL共杯、折平HMI、後開通風、PLA 0.4／0.2與完整STL先於單盤3MF均保留。頭高與軸向鬆量須耦合，現有±.28樣本不足完整公差；右端8mm保護／工具UX及實際配合／負載／全機連續姿態仍待量化。幫浦、感測器、pH／電源板、線管尺寸已問未答，不重問、不把佔位當尺寸。原檔保留，修訂另存，未啟動實體列印。

| State | Task | Priority |
|---|---|---|
| AWAITING-ACCEPTANCE | [`17_mcp-complete-pipeline.md`](../tasks/17_mcp-complete-pipeline.md) | 讓 MCP 完整——階段 1：`ModelSpec` 進、可列印包與機器驗證證據出；第一實例為工作站目前交付件匯入路徑；設計與計畫在 `docs/superpowers/` |
| ACTIVE | [`16_lab-station.md`](../tasks/16_lab-station.md) | 雙探頭量測工作站：250 mL 共杯、約 20 cm 伸距、P2S；獨立電極臂、齒槽與折平螢幕；全機工程資格待完成 |
| AWAITING-ACCEPTANCE | [`15_scene-list-and-chat-gate.md`](../tasks/15_scene-list-and-chat-gate.md) | **場景清單不再只有十個**——上游 addon 截斷到 10;改由 adapter 有上界地讀,碰到上界會說。H6 綠了,對話路徑第一次有真機閘門;`--real` 32 條全綠 |
| TODO | [`14_hand-long.md`](../tasks/14_hand-long.md) | **第五個實例:每指三關節**——`joint_count` 第一次建在 2 以外;主要風險是指掌比 |
| WAITING-ON-USER | [`07_hand-v3-coupon.md`](../tasks/07_hand-v3-coupon.md) | **印一件指節、量七項公差**——幾何側全部完成且真機驗證通過,往下每一件事都要從這一件實體反推。**使用者執行** |
| AWAITING-ACCEPTANCE | [`06_hand-v3.md`](../tasks/06_hand-v3.md) | 靈巧手 V3:文件樹 21 檔 + 追溯矩陣 22 條;域規格、手指、掌盤、整手、佈局全部做完,兩份真機契約 11/11 全綠,印製包已發布;**實體列印與台架量測未做** |
| AWAITING-ACCEPTANCE | [`05_octopus-hand-v2.md`](../tasks/05_octopus-hand-v2.md) | 章魚手 V2:角點對齊手臂 + 加強莖 + 瞄準式抓取墊 + 每臂電線孔 + 全面倒角;兩份契約真機全綠,包已發布;實體列印未做,視覺 rubric 未判 |
| AWAITING-ACCEPTANCE | [`04_octopus-hand-v1.md`](../tasks/04_octopus-hand-v1.md) | 五臂章魚手 V1：五邊形掌盤 + 五隻 V6 萬向臂，兩份契約真機全綠；實體列印未做 |
| AWAITING-ACCEPTANCE | [`03_knowledge-dcc-and-abstraction.md`](../tasks/03_knowledge-dcc-and-abstraction.md) | docs DCC tree, duplication removed, anti-regeneration gates; `--real` tier green 2026-09-05; only the taste calls remain |
| AWAITING-ACCEPTANCE | [`02_tendon-universal-joint.md`](../tasks/02_tendon-universal-joint.md) | V6 PIN models checksum-controlled under models/ (PR #4 merged 2026-09-05, `901cb53`); physical print coupon remains |

`WAITING-ON-USER` = 機器側已完成,下一步只有使用者能做(印、量、裁決);它不是 ACTIVE,checkpoint 不會把它當進行中。

Accepted 2026-09-09: [`archive/13_conversation-reaches-the-generators.md`](../tasks/archive/13_conversation-reaches-the-generators.md) — 對話能產出可印的零件:`list_instances` / `build_instance` 進對話工具清單,與公開九項目錄分離且有守衛;使用者「13 可以歸檔」(V01.0R.012)。

Accepted 2026-09-09: [`archive/12_hand-gripper.md`](../tasks/archive/12_hand-gripper.md) — 第四個實例三站夾爪:兩指＋對位拇指九節,真機首建 20/14 全過,走產品路徑建成,使用者 Lane B 通過後發布 `models/hand-gripper/`;使用者「12 可以歸檔」(V01.0R.00E)。

Accepted 2026-09-09: [`archive/11_determinism-budget.md`](../tasks/archive/11_determinism-budget.md) — 碎片預算改由實測支撐:探針擴到所有 `chains` 與 `palm`,實測八個零件只有一個會動、差 2;`--real` 28 條全綠,`models/` 位元組未動;使用者「11 可以歸檔」(V01.0R.00B)。

Accepted 2026-09-09: [`archive/10_generation-delivery-path.md`](../tasks/archive/10_generation-delivery-path.md) — 參數化產生器接上交付路徑:`POST /api/instances/{slug}/build` 與 `GET /api/instances`,sandbox 的豁免鍵在逐字相同的推導字串而非呼叫者;`--real` 27 條全綠,交付路徑閘門 5/5 重現已發布的包;使用者「10 可以歸檔」(V01.0R.009)。

Accepted 2026-09-09: [`archive/09_core-boundaries.md`](../tasks/archive/09_core-boundaries.md) — 核心邊界收債:port 回傳 typed DTO、外部服務與 LLM provider 的 domain error → 502、孤島刪除;使用者「09 可以歸檔」(V01.0R.004)。

Accepted 2026-09-09: [`archive/08_hand-framework.md`](../tasks/archive/08_hand-framework.md) — 靈巧手框架 M0–M6,使用者 Lane B 通過三張圖,`models/hand-compact/` 已發布(V01.0R.000)。

New tasks start from [`templates/task_template.md`](../tasks/templates/task_template.md).
Accepted tasks are moved to [`archive/`](../tasks/archive/). Historical feature campaigns are under
[`../archive/`](./) and are not active work.
