# 雙探頭量測工作站外殼

**Status:** ACTIVE

導航：[目標](#goal) · [規格](#specification) · [驗收](#acceptance-checks) · [現行接手](#hand-off) · [執行收據](#durable-native-execution-contract) · [歷史驗證](../archive/2026-10-27-lab-station-handoff-history.md)

## Goal

以 Blender MCP 專案設計動態氣泡表面張力計與 pH／溫度計共用的可列印外殼。

## Specification

- 使用者確定：拓竹 P2S；250 mL 燒杯或廣口瓶；三探頭共用一杯；約 20 cm 可調伸距。
- 共用桌面底座、LCD 可調與折平、兩組分節旋鈕鎖定臂；一組毛細管，一組 E201-C 與防水 DS18B20。
- 毛細管與 pH／溫度兩頭各自獨立活動、可鎖定；前後伸縮與上下升降可分別調整，探頭角度另行手調。
- 沿用原零件演進：上臂也採兩臂結構並可獨立上下抬升，上下臂交界為四點梯形板，分別連接兩支上臂與兩支下臂；不能換成新的單自由度機構來通過測試。
- 八支連桿須為完全相同、可互換的列印件。主上臂兩端使用可換齒盤，固定側也有對齒，沿用原五金驗退齒、調角、回座及鎖緊。
- pH、溫度與 DJS-1 EC 探頭採緊湊三角配置；三個積木模組有相同公榫、母槽與按壓防脫介面，內孔依探頭不同。共用腕端快換座容納毛細管座或三探頭座，保留原調角，接頭可徒手拆裝。
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
- 驗收依目前共用模型的原零件逐項進行，配對呈現受測操作及同姿態出圖。歷史研究夾具、其他產品回歸和管路數值試算各自通過，不解除本機構要求。感測器電路與電測適用性由使用者另行處理，機構驗證聚焦外殼、接頭空間、實際操作與列印裝配。

## Source Boolean contract (2026-10-27)

- LCD 鉸鍊耳片須在每個正式布林步驟後保持封閉、零退化／薄片與零非相鄰自交；不能靠末端合點掩蓋同孔重切的缺陷。
- 沿用 `serrated_joint_verify_real` 的逐步觀測及獨立 CGAL；新增實際後殼輸入與雙側鉸鍊耳片案例，原相切 bore 反例保留。沿用既有生成、三角化、二進位讀取與驗證模組，無新模組／依賴；保存的 v80 模型、STL、3MF 不改。
- 除來源階段外，實際列印原點／毫米匯出的二進位 STL 必須獨立讀回並通過拓樸與 CGAL；只允許完全相同座標去重，不得合併鄰近頂點或修補後再驗。
- 配對接觸齒面共用週期三角分割規劃；修訂前須辨識完整雙環、唯一角點及一致方向，修訂後所有原頂點／非接觸面保留。以實際匯出幾何做就座前行程、不同對角線與過行程控制；此規劃不等於螺紋／保持力驗收。
- 保留鉸鍊軸心、孔徑及齒面位置；共用孔在耳片及齒盤合併後一次貫穿。需重驗螢幕活動／齒面與全核心 CI，不以來源階段通過冒稱整機資格。

## Hand-off

### Verified facts

偏移縮頸與上移套管須用同一外形重驗裝配、停臂調腕與中立腕角入杯。各動畫交界須由原生檔獨立讀回四線控制點、零件顯示狀態及世界位置，核對同一管端和原件姿態。裝配順序須涵蓋縮頸及套管的各自下降包絡，以及軟管避讓與復位。格間半徑保守界限不足時，保留原始反例並提高曲線細分，維持原管形與既定半徑門檻。

調腕避讓須保留原腕板及五金，分別驗新增接合外形、原玻璃對杯、隨動軟管與原位轉接。停臂和入杯兩姿態分開核對；入杯干涉須用原玻璃及名目杯的實體反例紀錄。

接管後入杯驗證從兩端就座的原生姿態連回原操作時間軸。軟管首直段固定，導夾直段及探頭端跟隨各原局部座標，跨距按定長重擬。格間剛體界限由原線性位置、歐拉角、父階與控制器推導並獨立比對，新增縮頸與套管須作隨腕障礙。杯緣深度、實際液位及接管後調腕各有驗收。

兩端接管動畫須連接同一管長與共同位姿，將不同分段數的曲線以精確分割接續。曲線端點重合仍需驗格間相鄰切向，平口管端側移須用含徑向偏移的包絡。先驗箱體端就座後到探頭待接，再為套管掃掠留出高度，驗就座後插入。未驗的縮頸件本體置入須標在同一時間軸。

玻璃管套管尺寸以軟管外徑、玻璃實際外徑及材料密封界面決定。軸向佈置先驗套管外形與腕端五金，再從原量測格確認玻璃下端仍可入杯；只為套管挪高整支探頭會損失浸入深度。縮頸候選須同時保留尖端高度、驗證縮頸及套管掃掠和定長插入，接頭實物與箱體接管後的整段過渡另驗。

穿壁接頭以原廠對應料號的 DXF 區塊提取兩管口、螺紋及螺帽軸向基準。明列箱壁上採用的夾持位置，再從外管口與原廠插深推導管止擋，從管口量外露直段。定長改線保留導夾內直段、其他線路與待接端。名目外形參考件只供檢視，內部鎖管、實際密合及施力各有驗收。

扣環入槽須核對原形碰撞反例、規定張開下的格間淨空、就座後的軸向止退。接管動畫須區分管端模型定位點與接頭內止擋；穿壁接頭總長扣除箱壁厚度所得是外口最遠名目界限，不能用作插入深度。裝配檔若尚缺實際接口，時間軸標記須明確指出，並從另存檔重開核對原運動。

延後裝從動桿及關節銷須分階段記錄在場零件。軟管暫避要保存定長、接點與共同切向，驗證變形前後及銷軸掃掠。可播放的裝配副本須依每階段的在場零件重開核對，扣環延後時明列其入槽尚待驗證。

導夾的操作空間須沿保存裝配路徑掃掠夾爪外側量規，並用原網格定位阻礙。工作台預裝應明列當時在場零件，確認後裝件的局部路徑，再另驗五金、線路與施力。量規尺寸是幾何測試條件，手部姿態及裝配力須有獨立證據。

穿管後側推的全管路徑須從既有長度及保存姿態延續，讓導夾中的管段隨夾，並核對自由跨距、格間彎曲、自距和周邊。未接合階段依平口包絡驗兩端分離，既定接合排除只用於指定的接合行程。另存裝配動畫後獨立讀回導夾頂點、軟管控制點、固定零件及共用件身份。

導夾裝入共用連桿要測端部與側裝。規定張開量需以不足張開的實體交集作對照，並沿張開、側推與放鬆分段證明格間間隙。已穿管的候選須涵蓋局部管口及原裝配周邊，整條軟管、手部空間及實際回彈另有驗收。

原導夾通道的刀路驗證須以完整有向面註冊連結原生局部座標、3MF 元件和建置座標，再用實際 G-code 的具名物件、線寬與層高核對管包絡。粗略沉積包絡標記的近接須保留原刀路並以宣告截面細查，支撐、brim、其他零件及本體均須涵蓋；接床刀路與通道淨空分別記錄。

管材滑移應由保存動畫的箱體端起算弧長，分開記錄最大單向與往返累積量，並確認管段在導夾局部座標的對準。置中通徑、偏心後餘量和側入口各自驗證；通徑須與同一交付 STL 完整面註冊及實際管包絡核對。側裝若需要材料變形，須另驗裝配路徑與材料反力。

格間線路對剛體的驗證須讀取保存檔的 FCurve、驅動和父階鏈，並對照 Blender 實際整格／半格矩陣。用曲線控制點包絡與剛體位移上界處理格間，另以封閉材料分類確認非接合段起點在材料外。保守界限、同幀網格實測及偏移反例各自記錄。接頭故意共用的管段、位姿數值預算及未覆蓋的製造公差須明列。

操作動畫另存後，以獨立 Blender 重開擷取原件與線控，並將出圖、時間軸格號、取樣及連續界限綁定同一檔案。復位須核對起終姿態與線控；固定螢幕角與起始臂位列入適用範圍。判讀 FCurve 自訂角度時使用 Blender 的實際儲存精度，網格世界矩陣及線控誤差分別量測。

維修姿態若起點尚在退齒，先以原軸向行程回座上臂，再獨立重播下臂鬆鎖與收隙。線路取樣以原導管夾與探頭實際姿態為邊界，核對總長、局部彎曲與通過導管夾的材料滑移。位姿矩陣與網格同樣在單位轉換前提升各分量精度，量距引擎的剛體旋轉與原伸縮分量分別處理。

端點煙霧測試在 TestClient 進入啟動程序前注入測試 runtime。共用切片驗證只使用正式入口，保留同工作曾回報的狀態與其後讀回的終態。

腕端互換須分開核原榫槽接合特徵、原配對／跨配對、未按卡扣的止擋反例及帶原探頭子件的整頭拆出。外部空間使用原抬臂姿態；若跨座頭較長，須另驗原行程內的維修姿態，不能移除原杯或其他臂來製造通過結果。螢幕固定角要保留驅動、只暫停 action，並從實際網格旋轉讀回角度。原網格毫米擷取沿用共用觀測器，完整記錄精度與來源；原件、理想釋放後空間、按壓彈性及完整拆裝流程分別驗收。

四點肘板須由原 P/R/A/B 銷軸與兩上臂、兩下臂端孔逐一核對；腕端 C/D 另驗，錯接從動桿的反例須失敗。下臂自己的鬆鎖、調角與收隙分段觀測旋鈕轉角、螺栓軸向行程、另一臂固定及各孔軸對準；近照以固定連接座為參考，另附同姿態原顯示整機圖。

原五金與連桿的表面距離須配合實體交集檢查；夾緊面的近零表距不能直接當成活動干涉。先量兩件相對姿態及孔軸，分開驗各自鬆鎖／調角路徑；以偏移近接面的數位反例核對偵測能力，不將反例寫入原模型。

上臂操作驗證以目前原生時間軸標記定位鬆開、退出、轉動、回座與收緊，不能沿用舊版格號。齒盤／連桿相對位置、對固定側退齒量、另一臂固定與原五金回位各自核對；取消同姿態退齒須能檢出齒面實體干涉。近照若隱藏五金，須另附含五金整機圖。動畫的回位不等於螺紋、鎖緊力或實印配合驗收。

共用件核對須從目前組裝檔確認實際實例引用的母件，並以同一原生幾何核對兩端定位面、可換齒盤與固定側對齒。名目配合與刻意錯位的反例成對記錄；裝配說明圖須標明抽出量，幾何配合、整機拆裝及實印配合分別驗收。

主專案與工作樹的同源驗證器隨相同修訂整合，保留主專案原有的工程收據索引。工作站目前選版從共用 ModelSpec 解析。正式切片閘門先比對本機與服務選版，再對原生、預覽、動作樣本、全部 STL 及切片驗來源；共用 Blender 應重開該選版並讀回實際影格、世界座標及四線控制點。機構圖如果隱藏測試中的物件，另出同姿態、含受測物件的對照圖。

目前進度、實際驗證與執行中工作只記在 [任務索引](00_INDEX.md)。
目前模型由 [共用應用服務](../../models/lab-station/README.md) 決定；不得由歷史檔名推斷版本。
新交付的 STL 收據依[共用驗證規則](../30-verification.md#t3-裡的產出物閘門2026-09-08-起)逐件核對；切換選版前，仍須另外驗收同源動作與實際單盤刀路。
原逐輪交接已搬到 [歷史快照](../archive/2026-10-27-lab-station-handoff-history.md)，僅修正搬移後的相對連結，只在追溯指定事件時載入。

### Open failures

完整驗收仍須覆蓋本檔 Acceptance checks 與 [範圍規格](../verification/lab-station/01-scope.md)；單件網格、固定姿態與切片通過，均不能取代整機動作、實際接口、材料及負載證據。具體未解除項目見任務索引。

### Next step

接續任務索引所記的工作及實際 handle。共用 Blender 的驗證、場景讀回和復原依序執行，驗證期間凍結其來源。離線候選可由獨立 Blender 背景程序處理，使用專用設定目錄、來源快照和新輸出路徑，並確認沒有 addon 與監聽 socket。原模型／STL／3MF 保留，後續修改另存修訂。 候選切換前，須用同一選版的原生檔重開出圖及匯出，並核對正式入口讀回的原生檔、完整 STL 和實際切片收據。 目前選版的預覽由核心 factory 步驟與原生測試共用快照。公開交付閘門提交前須交叉核對該選版的預覽、腕端取樣、匯出與切片收據。腕端診斷圖須由同一候選檔重播實際測試樣本，將影格、螢幕角度、腕角和退齒行程連同原生與圖片指紋保存於成對的 review-test-poses／review-render-poses 收據。研究夾具的原生檔指紋另行保留，其結果不能用於目前交付件驗收。

切換選版時，主專案與服務執行目錄須同時具備新模型及可讀該收據的驗證器。公開讀回後，另核對已開啟的 Blender 場景與獨立重開的網格快照。切換前若原場景有未存變更，保留原場景並明列讀回結果。局部支撐驗證應綁定實際 3MF 的雜湊；若重切產生不同刀路，須對新產物重新量測。

用已動畫的模型出指定姿態圖時，在隔離程序暫停姿態控制的動畫，核對出圖前後的世界座標，保存原生檔的動畫。

試作包的取杯檢查使用同一份候選 ModelSpec，見[驗證規則](../30-verification.md#t3-裡的產出物閘門2026-09-08-起)。以同源網格核對停臂與杯壁近點後，接續驗證兩個姿態樣本之間的連續移動，並保持另一支臂在同一姿態。

名目候選杯的停臂後取出沿用[共用驗證規則](../30-verification.md#t3-裡的產出物閘門2026-09-08-起)。候選杯壁干涉與空間包絡使用相同封閉實體判定；實際杯尺寸與操作驗收仍依上列 Acceptance checks。 接管後須核對先抬毛細管臂、再抬三探頭臂的交界與四線，並涵蓋垂直抬杯、越盤緣、前移及逆序復位。格間碰撞模型遇鏡射零件，將固定反射納入原網格座標，再對相對矩陣建立等距變換及伸縮誤差界。

候選若已存放名目杯和接液盤，請在同一原生檔保存停臂影格，並將取杯收據、碰撞掃掠和預覽綁定該檔。 杯位公差驗收須涵蓋中心、內外徑、杯緣及杯內底的同時誤差，並將計算出的容許偏差和接液盤可重複落座的實際偏差分別量測。 加入導斜定位時，須用杯腳直徑連動的落座高度包絡重驗臂與移杯，另由實際刀路查杯腳接觸面與支撐介面的淨空。 切片後的落座預估要用受檢零件的盤位、實際線寬、層厚與整個杯底包絡，並標明理想沉積模型與實印量測的界線。取杯收據的 `cup_source` 須為 `saved_mesh`，以免把夾具的取杯結果當作畫面中的杯位資格。

審查候選時，取杯與 MCP 切片使用同一份明確的候選 ModelSpec。出圖來源和共用 Blender 除了影格與姿態，還須比對檔案雜湊及本次修改的網格指紋。舊場景須被這項比對拒絕；切換後獨立讀回再記錄。維持候選同步與孔位實際刀路為兩項驗收，切片工作完成時仍須檢查孔內的支撐。

含穿壁孔的修訂在提交交付前，提供 `驗證/bulkhead-bore.json`，用共用驗證器比對實際單盤刀路與 Ø14.9 mm 數位量規。取消局部支撐時，對側懸空面另存支撐介面和第一層橋接跨距；實印尺寸、橋接品質和接頭試配仍是工程驗收。

穿壁管路以所選接頭的管口為起點，使用該接頭和管材要求的直段、外徑上限、彎曲半徑及拆管行程。若原廠圖面只給總長，分別驗內外口最遠位置的包絡，並將管口精確位置和實體試配留為獨立驗收。不同端的直段由共用定長規劃器指定，重擬一段後須與其他兩段及全機動作重新核對。

驗收雙頭獨立抬升時，先建立兩頭都浸在同一杯的起點。左右分別由該點抬升，保留另一頭、杯、螢幕及五金的世界座標，並用原始順序在這個起點的跨臂穿透作反例。候選需從保存的 Blender 檔重開取樣，核對溫度探頭原襯套包覆及杯底淨空。若旋轉既有底座，機構和線路各自驗證，固定的箱體出線點須保留。 原時間軸與獨立操作若共用檔案，片段切換需明列並保持原片段姿態；重開後驗另一臂、各端點、導夾、回程及線間連續距離。調整軟管自由跨距時，箱體接頭、玻璃首彎和端直段應保留。量測玻璃末端附近可用平口圓柱另驗。

若補肋與腕端在退齒時相交，先在原零件座標定位交集，確認改動未進入快換母槽、卡扣與環座。原零件與修正版使用同一退齒、轉動及回座路徑，對照整機每個樣本的新交叉，並以獨立封閉實體確認正反例。只有已修訂的零件從同檔重開匯出並換入原盤位。 接近零的原配合用具名偏移與封閉實體相交作反例。調角有剛體淨空後，仍須讓管端隨探頭移動，分開核對直段、首彎和固定螺帽。先以封閉管包絡定位軸向障礙，再搜索可保留原端口與彎曲半徑的路徑。

腕端線路先依同一原生模型區分固定導夾與隨探頭移動的線端，再重擬中間跨距。保留接頭直段與名目線長，並核對關鍵格之間的曲率、障礙淨空、自碰和探頭跟隨誤差。固定臂位的腕端重播須另存且標示適用臂位，與整機操作檔分開驗收。 雙槽出口若必須交錯避開鄰近線夾，先驗兩線同時離開導夾的首彎，再核完整線路。移動原導夾時，另驗沿連桿的配合、附近剛體、既有線路及上游跨夾段。 接回原整機動畫時，保留既有驅動與原線，獨立從另存檔讀回整格、半格的剛體與線控。原腕端重播的同臂位端點應一致。碰撞取樣、線間連續淨空和連續曲率分別記錄。

玻璃若沿原夾持軸滑移，分別核對原襯套的軸向包覆、玻璃與其他零件的干涉、杯口與液面深度、平端管的貼合，以及整條管路的半格掃掠和連續曲率。以朝固定螺栓轉彎及過度滑移作拒絕對照。襯套包覆量和名目杯口淨空各自保留，實際保持力與浸入深度需另驗。

## Screen clamp control contract (2026-10-27)

- Shared immutable clamp values own pitch, axial seating, target tooth angle and passive-pin float. Reuse the existing five-phase motion; do not duplicate its ramps in Blender bindings.
- Existing fold behavior defaults to a zero-degree target. An explicit target is finite and within the starting angle; physical clamp endpoints must lie on the joint's indexed tooth angles.
- Active screw follows body rotation and subtracts screw lead; passive pin and retainer follow body rotation and the same axial float. Preserve all five original rigid identities and mesh data.
- Baked hardware coordinates may have an off-axis object origin. Keep the actual shaft coaxial through screw rotation by compensating Y/Z around the existing hinge; factor the hinge offset into polar radius/phase so each output uses one trig call and reads raw progress directly. Do not chain a driven custom property into other drivers: appended controls must update without a one-sample lag. Every indexed target must be bound to the real original roles and survive full-file save/reopen, with raw local surfaces and rigid identities preserved.
- BDD: given each indexed target from 0 through 60 degrees, forward/reverse numerical and evaluated-driver poses agree, including after save/reload; removing rotation-follow or retainer-float must fail. Invalid geometry roles or binding state are rejected before mutation.
- This contract is a dependency of the shared native-revision service. Control fixtures do not qualify full model collisions, complete hardware tolerances, printing or holding force; no public revision capability is claimed before its adapter and delivery paths are integrated.

## Native revision service contract

- Input is a registered recipe identifier and validated mechanical parameters. No caller-supplied Python, native path, output path or client-specific version selector. The shared application catalog resolves the current selection; a narrow artifact port resolves its unique native file from the verified checksum manifest and returns typed provenance.
- One injected application service orchestrates the existing Blender lease and socket adapter for every client. An isolated factory process used for research is not a second public runtime or acceptance path.
- Source hash mismatch, unknown recipe, ambiguous native source or invalid parameters fail before Blender mutation. No fallback to an older directory. Revisions use exclusive new output directories; source files and the selected delivery are not overwritten or promoted automatically.
- Any required input triangulation or coordinate rebase is an explicit registered preparation step with named owners and preservation evidence. Invalid source surfaces cannot be silently repaired or relabelled as validated geometry.
- After each source operation, validate the affected surface independently. Save/reopen checks include original object identities, descendants, all rigid controls, external-library absence and unchanged unrelated surfaces. Actual binary STL bytes must pass topology and strict geometry checks.
- Capture the selected spec, print target, request and complete source receipt before queueing; preparation and execution consume that captured context without selecting again.
- Complete the same-identity STL set before deriving a new 3MF. Unchanged parts retain source bytes; changed parts carry source/native/export provenance. Reuse the existing slicing and packaging services for single-plate qualification; a successful imported-v80 run does not qualify a revised candidate.
- REST and MCP submit optional closed revision intent to the same DesignPipeline and existing JobStore. Invalid or conflicting spec/revision inputs create no job; the native import stage consumes the captured context and the same-product port, then shares geometry, mechanism applicability, slicing and packaging stages. Unknown remote completion remains RUNNING and quarantined; verified late receipts may resolve isolation but cannot retroactively qualify skipped stages or replay the command.
- Native job downloads and packaging share one closed public-file policy; source snapshots, programs and execution receipts remain private, including aliases and future unknown directories.
- NativeProductPort returns one job-relative product receipt. Its filesystem adapter reuses the complete STL writer before revising the captured plate template; no second geometry or plate rewriting implementation lives in verification. An invalid plate retains completed STL evidence but cannot publish a successful product receipt; existing destinations remain untouched.
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


## Durable native execution contract

- NativeRunnerPort consumes one PreparedNativeRevision and returns a job-relative NativeRevisionResult; it never reselects a source or creates a second job store. NativeRevisionService and the composition root inject the existing port, lease and exact-program authority. Public execution remains a separate delivery qualification.
- Each existing job owns an exclusive native-execution directory. Pending identity, callback start, terminal and acknowledgement are bounded, immutable JSON receipts, flushed to disk and published without overwriting. Identity binds protocol, nonce, generated program SHA and source SHA. The generated program also pins its transitive Blender and host-checker source files; dependency reloads come from the existing import-closure helper.
- The closed callback reuses source preparation, Boolean/material checks, controls and NativeSceneSession. It writes its native candidate only after the original snapshot matches, then records terminal state. Restoration failure, missing or incoherent receipts, altered outputs, symlinks and mismatched acknowledgement never release quarantine. A failed operation with proven restoration may release it while preserving the private error.
- Socket success, timeout and disconnection do not replace the terminal receipt or trigger a replay. Repeated cancellation drains dispatched work; queued work cancels before reservation or dispatch. Only a matching, restored terminal with verified output fingerprints can be acknowledged and resolve that execution's quarantine.
- Startup inspects durable receipts before generic orphan-job recovery. Unresolved native run IDs remain excluded from ordinary interrupted-job failure marking; native recovery failure cannot serve scene-changing requests. A persisted pending state is uncertainty, not proof of a live callback.
- The existing native factory --all includes the actual callback program, an independent original-scene comparison, full-file reopening/control motion, complete same-part STL and same-template Bambu loader checks. This is isolated qualification, not public MCP, physical fit or load acceptance.

## Failed-restoration recovery contract

- A callback terminal with `restored=false` remains an immutable failure. It must never be rewritten, acknowledged as ordinary success, deleted, or hidden outside the job scan to unlock Blender.
- Recovery requires proof that the same callback ended. Preserve the failed live scene as a new native file and record its digest before any reset; preserve the original input and all job receipts.
- An explicit maintenance reset may load only the verified current catalog native, after an independent isolated Blender load produces the expected object identities, raw surfaces and active-scene membership. Read back the loaded shared runtime and require equality to that baseline, with no external libraries and the original source SHA unchanged.
- Record reset as reset, not restoration of the previous operator scene. A separate durable receipt must bind the failed execution identity and terminal digest, the preserved failed-scene file, selected source, independent expected baseline and observed state. Invalid or missing evidence keeps quarantine. The old job remains failed and cannot publish its pending candidate or continue slicing.
- Startup recovery must validate the separate receipt before releasing quarantine. No public arbitrary-script capability or caller-provided model path is introduced; all clients continue using the same catalog and application services. Resume a new run only after readback and recovery checks succeed.
