# Changelog

本專案所有值得注意的變更記錄於此。格式依 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)；
版號依全域 version-management 規範（base36 固定寬度 VXX.XX.XXX；任何修改至少 bump 段3）。

## [Unreleased]

### V01.0C.004

#### Fixed

- **產生器從來沒有清掉自己上一輪的產出,而本機永遠看不到**。`run_generator` 的預設前綴是
  `HH_`(既有產生器都用它),V3 用 `HJ_`,所以 `clear_previous` 一個東西都沒刪。
  真機上每跑一次就疊一整隻手:契約量到 **9 個佈局零件而不是 5**,兩對重疊 196／203 個面,
  就緒檢查回報 `intersections`。本機用 `--factory-startup` 跑幾次都不會出現——**場景每次都是空的**。
- 產生器結束前自己數一次每種物件的數量,數不對就 raise。用「同一 session 連跑兩次、
  第二次故意用錯前綴」證明它會紅,用「連跑兩次、前綴正確」證明它不會誤報。

#### Added

- `models/hand-v3/README.md`:印什麼、怎麼印、**哪些是機器驗過的、哪些完全沒有**。
  氣壓夾層一個字都不宣稱,因為它一次都還沒被做出來。

### V01.0C.003

#### Fixed

- **每一張總覽圖都是裁掉的,而且從第一張起就是**。相機的正交尺度是挑一個「看起來對」的數字
  (260),而畫面是 1400×1100,所以垂直視野只有 204 mm——對上 229 mm 的手指。
  改成**從實際包絡量出來**再乘 1.25 邊界。
- 總覽圖現在拍的是**整隻手**(四指 + 對生拇指 + 掌盤),不是單一根手指。整手已經存在了,
  而使用者要看的是手。

### V01.0C.002

#### Fixed

- **列印佈局的三個缺陷,每一個都是量出來的**:
  1. **固定節距把掌盤排進鄰居身上**。節距是照 24 mm 的指節挑的,掌盤 140 mm——實測相鄰
     重疊 846/846/846/422 個面。改成照各自量到的寬度排開。
  2. **靠 transform 擺位的東西存檔後不見了**。行程內每一次檢查都正確、存檔前最後一行印出來
     也正確(-190.50 … 154.00),**重新開啟同一個檔全部變成 0**,五個零件疊在同一點。
     改用 `location`/`rotation_euler` 也一樣。最後把擺位**烤進每個複本自己的網格頂點**。
  3. **不重疊之後變成一列 413.5 mm,放不進 256 mm 的床**。佈局現在照床身換行,
     最後 **182.5 × 100.5 mm,一盤放得下**,相鄰重疊全 0。

兩條教訓落檔:交付用的 `.blend` 一律重新開檔再驗,不要信行程內讀值;
「排得下」與「不重疊」是兩個問題,少驗一條就會出一種很像成功的失敗。

### V01.0C.001

#### Added

- 整手組裝:1 個掌盤 + 19 個指節(四指各 4、拇指 3)。實測**零非流形邊、
  不同手指之間零靜止干涉**。組裝包絡 140.0 × 44.1 × 319.5 mm——**超過 256 mm 床身是正常的**,
  零件分開印,單件最大是掌盤 140 × 44 × 90。
- 掌盤加進列印佈局,所以就緒檢查也涵蓋它。它是最可能出現薄壁與無支撐懸空的零件,
  漏掉它會讓檢查結果看起來一樣乾淨。

#### Fixed

- **拇指基節撞進承載它自己的凸台**。第一版重疊 219 個面;從「基節軸向底端」推導後還剩 114,
  因為**傾斜物體的最低點不是它的軸向端點**——本體有寬有深,一傾斜就有角落盪到端點之下。
  把 `hypot(寬, 深)/2 × sin(擺角)` 算進去,真正的最低點是 -24.76 而不是 -14.30。
  凸台最後改成整個坐在拇指根之下(人手的大魚際也長在關節下面),餘裕 5.24 mm,重疊歸零。

### V01.0C.000

#### Added

- 掌盤幾何:四個指根 + 拇指根(由 spec 自己的 frame 擺位,不是打在程式裡的數字)、
  thenar 凸台、五條腱道、袖口夾槽、進氣口。實測:**一個殼**、零非流形邊、
  **五條腱道全部真的貫通**、進氣口貫通。
- 產生器多一道「殼數必須是 1」的閘。

#### Fixed

- **拇指根本來是浮在空中的第二塊**。它被放在 x=-71,掌板只到 -57。實測兩個殼,小的那個
  88 個面、與掌板毫無連接——而且**非流形邊是 0、完全水密**,因為分離的實體本來就是水密的。
  它會當成一個小零件從床上掉下來。加了 thenar 凸台(人手在同一個位置也長了一塊)。
- **我的腱道探針回報「5/5 全通」是假的**。拇指那條的 x 在掌板之外,射線穿過的是空氣,
  而那條 PASS 與真正鑽通的四條在輸出上一模一樣。改成先做旁證取樣確認該處有材料,
  沒有材料就標 vacuous、不併入 pass。
- **一條沒有牙齒的守衛**:我先寫的不變式問「凸台有沒有接到掌板」,而凸台是被**定義**成
  一定接到的——那條斷言永遠為真。改成量**懸伸長度**(26.0 mm,上限 57.0),那才是會出事的量。

兩條教訓落檔:水密性看不見分離的第二塊;射線說「通了」可能只是那裡什麼都沒有。

### V01.0B.001

#### Fixed

- **拇指的座標系是斜的**。第一版先把軸繞 Y 轉、再把指腹繞**全域 Z** 轉——那不是繞
  「手指自己的軸」滾動。實測兩者內積 **-0.166**:那個 frame 是平行四邊形而不是直角,
  於是在裡面算出來的每一個指尖位置都錯,而且錯的量隨姿態變化——單點抽查看不出來的那種錯。
  改成 Rodrigues 繞自身軸滾動,並加兩條斷言:frame 必須正交且單位長,滾動不得動到軸本身。
  修正後結論不變:對指 18.2 mm(原 17.6)、平放 29.9 mm、判準 22.0。
- ruff format 漏跑,上一個 commit 讓 Mac 的格式閘門翻紅。

### V01.0B.000

#### Added

- `AnthropomorphicPalmSpec`:四指一排 + 對生拇指,而且**對指是算出來的**。手指是平面連桿鏈,
  段長與關節極限已知,所以指尖能到哪裡是算術;兩組可達集合會不會靠到接觸距離內也是算術。
  實測對指後最近 **17.6 mm**,接觸判準 22.0;**拇指不轉留在指列裡則是 29.9 mm**——
  那條斷言有鑑別力,不是永遠為真。
- 手指契約 `hand_v3_finger.json` **在真機跑過,12/12 全 PASS**,包含新的
  `center_channel` 宣告式期望(軸上是實心的)、腱孔射線、±50° 十一個取樣角掃掠、
  兩組碰撞群與平鋪佈局的就緒檢查。

#### Fixed

- **兩個被量測推翻的假設**:
  1. **拇指不能是第五根手指**。三關節拇指長 168.5 mm,擺過 114 mm 寬的掌盤會把指尖送到
     對面外側 78 mm——任何姿態都在追過手指而不是碰到它們。改成**兩個關節**(114.5 mm),
     這也正是人手:拇指只有兩節指骨。
  2. **只轉角度沒有用**。拇指根還必須站在掌面前方,否則它只在手指的平面裡擺動,永遠側對側
     相遇。上限是掌盤自己的厚度 22 mm——再往前,拇指就長在一根伸出手掌的柱子上,那能碰到
     食指尖,但不是拇指。這也是我第一次掃描掃到 0.5 mm 卻**拒絕採用**的組態:
     指標可以被退化的設計滿足,所以擺位範圍要先受物理約束再最佳化。

### V01.0A.000

#### Added

- V3 手指的 JSON 契約 `hand_v3_finger.json`:四件、旋轉全 0、腱孔射線、±50° 十一個
  取樣角的掃掠、兩組碰撞群、平鋪佈局的就緒檢查。把驗證從我臨時寫的探針搬進真機管線。
- oracle 新增 `center_channel_expected_open`。**不是每個重複件都是空心觸手**:V5、V6 與
  兩隻章魚手的本體都有中央纜線通道,手指沒有,而且不能有——中央通道會直接切穿銷孔。
  做成**契約宣告期望值**而不是把檢查變成選配,理由有二:本專案的規則是「量不到就是失敗,
  不是跳過」,而且「軸上是實心的」本身就是一條有內容的斷言(它說的是腱孔偏心而非置中)。
  判定對非布林值一律 fail-closed,預設仍是 True,所以既有四份契約一個字都不用改。

### V01.09.002

#### Fixed

- `setup_render` 原本的型別是「兩個具名 spec 的聯集」——那是一份**呼叫者名單**,不是
  需求的陳述。第三個呼叫者(V3 手指)因此在 Mac 的 mypy 上掛掉,而那個錯誤沒有任何人
  能據以行動:它讀的只有 `assembly_unit_count` 與 `unit_pitch_mm`,用來把相機瞄準
  整疊的中點,其餘一概不碰。改成 `StackedAssembly` Protocol,並加一條測試證明四個
  spec 都滿足它、而一個空物件不滿足。
  (本機 mypy 當時是綠的,Mac 才紅——閘門以 Mac 為準。)

### V01.09.001

#### Fixed

- **借來的連桿在靜止姿態就互相穿透,這是繼承來的缺陷**。`HingePhalanxSpec` 預設關節中心
  24 mm、耳片半徑 6.5,耳片伸到 30.5;下一節本體(節距 48、長 40)從 28 開始——兩個
  分開列印的零件重疊 **2.5 mm**。實測三對相鄰件各重疊 303／302／302 個面。
  借來的規格允許它:那條規則只要求關節中心越過本體**中心**,對一個節距外的鄰居沒有意見;
  而寫出這個排列的產生器**被歸檔時從來沒有契約驗過**(歸檔理由是「零引用」)。
  V3 把關節中心推到 27.0 mm(間隙 +0.50),節距 54,整指 229 mm。重建後靜止與
  ±50° 全行程掃掠**都是零重疊**,並加了 `adjacent_body_clearance_mm` 這條不變式擋著。
- 呈現模組把相機目標用公尺傳給只吃毫米的 `look_at`,鏡頭因此瞄向地板、手指跑出畫面。

#### Changed

- **力矩臂改成三節相同(6.6 mm),四件共用一個網格 = 一個零件編號**。這是量測導出的結論
  而不是簡化:可用窗只有 6.05–7.20 mm,最陡比值 1.19,**排不動三個關節**。順序本來就
  只能靠彈簧勁度梯度,力矩臂只微調力量分配。用三個零件編號換 16% 的效果不划算。
  對應的單元測試由「嚴格遞減」**有意識地修訂**為「不得遞增」,理由寫在測試自己的
  docstring 裡——不是為了轉綠而改測試。
- 手指產生器加上三張渲染圖與平鋪列印佈局,走 `FINGER_PROFILE`,不是第四份 render fork。

#### Added

- `adjacent_body_clearance_mm`:相鄰件間隙的具名推導量。既有連桿沒有任何一條不變式
  在看它,因為它問的是「一個節距外的鄰居」,而規格只描述單一零件。

### V01.09.000

#### Added

- V3 手指的幾何產生器:`finger_v3_geometry.py` + `model_finger_v3.py`,四個共面指節、
  每節一個腱孔、公舌母叉兩端同軸。實測:四個獨立網格、**零非流形邊**、
  整指 205 mm 高、腱孔中心與各自的力矩臂 **4/4 相符**(沿孔軸射線量)。
- `add_ellipsoid` 進共用 primitive 並登錄 SSOT。它原本只活在被歸檔的產生器裡,
  複製過來就會變成第四個有兩個家的 primitive。

#### Fixed

- **三個真缺陷,都是「每個零件單獨看都對」那一類**:
  1. **兩端不同軸卻宣稱不轉就能疊**。借來的連桿公舌在 X、母叉在 Y,它的鏈之所以每節轉
     90° 就是為了讓兩端接得上。V3 宣稱共面直疊卻沿用垂直兩端——那是一隻**組不起來**的
     手指,尺寸全對、印得出來、第二節裝不上第一節。現在兩個決定被一條斷言綁在一起。
  2. **力矩臂 (7.0, 5.5, 4.0) 有兩個違法**。腱孔與銷孔共用一個斷面,5.5 只剩 1.85 mm 壁、
     4.0 只剩 0.35 mm,對上 2.4 mm 的最小壁厚。實測後把窗算出來:**只有 6.05–7.20 mm,
     寬 1.15 mm**。改成 (7.1, 6.6, 6.1),並加上下限的 raise。
     設計結論隨之改變:**閉合順序只能靠彈簧勁度梯度,力矩臂比值 1.16 排不動三個關節。**
  3. **腱孔深度照本體算,停在凸耳之前**。孔深寫成 `body_length + 6` = 46 mm,零件實際
     61 mm,於是腱要通過的那段是實心的。包絡看不出來(bbox 不變)、水密、零非流形,
     只有射線看得見。**這是同一個 class 第二次**——`octopus_tip_geometry` 的註解早就
     寫著「The drill has to clear the cap, not the disc」。已落檔為獨立教訓。

### V01.08.002

#### Added

- `scripts/presentation_profile.py`——算繪的相機、燈光、地板與前綴變成資料。
  `scripts/archive/README.md` 早就寫下復活 hinge-chain 那條線的正確做法:先命名一個
  profile,再讓每個 fork 變成一個常數,**而不是把 fork 搬回現行樹**。兩支被歸檔的 render
  模組 diff 只差 77 行、函式同名同序——它們是彼此 fork 出來的,而在沒有人需要之前,
  抽象化一段死程式碼是純粹的浪費。現在有人需要了。
- 兩個 profile 常數:`MECHANICAL_PROFILE`(現行,驅動 V5、V6 與兩隻章魚手)與
  `FINGER_PROFILE`(從歸檔的 fork 原樣抄出來)。加上一條**必須不同**的斷言——
  兩個都合法與兩個是同一個,在其他每一條檢查底下長得一模一樣。

#### Changed

- `hollow_hinge_render.setup_render` 改讀 profile,預設是現行那組,所以四個已交付的模型
  一個數字都不動。證明分兩段接起來:單元測試把 `MECHANICAL_PROFILE` 的值釘在重構前
  原始碼的數字上;再把場景建出來讀回,16 項(解析度、背景色、兩個曲率、相機位置、
  正交尺度、地板高度、三盞燈的能量/尺寸/位置)全部相符,場景物件也仍是那五個。

#### Fixed

- 一條差點讓我做出錯誤結論的教訓落檔:**拿一個自己就不穩定的東西當基準,「有差異」不帶
  任何資訊**。重構後 V6 的九張 PNG 雜湊全變,我差一點宣告重構弄壞了算繪;實測**同一份
  程式連續跑兩次,九張 PNG 同樣全部不同**——Blender 的 workbench 輸出不是逐位元組可重現的。
  同一次比對裡四個 STL 位元組完全相同,那才是有效訊號。

### V01.08.001

#### Added

- `SingleTendonFingerSpec`——V3 手指的域規格,**組合** `HingePhalanxSpec` 而不繼承章魚手。
  它把一個沒有任何逐件檢查看得到的量命名出來:**一條腱關掉三個關節需要多少線**。
  每個關節把自己的力矩臂拉過自己的弧,所以需求是三段之和;一隻手指可以水密、無碰撞、
  可列印,同時需要比致動器行程更長的線——那樣它永遠關不起來,而每個零件單獨看都是對的。
  實測預設值:需要 14.40 mm,行程 30.0 mm。
- 力矩臂必須朝指尖嚴格遞減的不變式。反過來手指會從指尖捲起,把東西滾出手心,
  而網格上看不出任何錯。
- 一條雙面的架構閘門:V3 **不是**章魚手的子型別。同一個述詞對 V2(它真的是 V1 的子型別)
  會開火,所以一個退化成「永遠為真」的述詞會在這裡被抓到,而不是永遠通過。

#### Fixed

- 兩份 V3 文件把 `HingePhalanxSpec` 寫成「單軸指節鏈」,實測後證明不精確:
  **單軸的是連桿,串接規則是交替軸的**(`assembly_rotations_deg` 回 `(0, 90, 0, 90)`,
  `axis_names` 回 `J1_X, J2_Y, J3_X`)。那對觸手是對的,對手指是錯的——手指必須在單一
  平面內捲曲,否則指尖碰不到拇指。V3 借連桿、換規則,並用一條「必須不等於借來的值」的
  斷言把它釘住。

### V01.08.000

#### Added

- 靈巧手 V3 的文件樹,`docs/hand-v3/` 下二十一個檔,掛進既有的 DCC 導航樹而不是
  另開一套。V3 與 V1／V2 是不同的機器:擬人手、四指一排加對生拇指、每指三個單軸
  指節由一條腱連動,外面套兩層手套,手指閉合後用針筒往夾層打氣。文件先行,這一版
  一行幾何程式都沒寫,但使用者可以立刻依 `08-inmoov.md` 開始採購與列印。
- 需求追溯矩陣,二十二條需求全部有驗證器,R1–R6 綠。寫的時候檢查器抓到一個真缺口:
  「外層不可延展時壓力才建得起來」原本只有對照驗證器,沒有任何東西斷言在使用者會讀到
  的那份台架報告上,已補。這正是那條規則存在的理由——單元測試全綠從來不證明交付物是對的。
- 驗證計畫十檔,含失效模式表與實體台架協定。抓持力現有管線量不到
  (`generated-artifacts.md` 自己寫著 retention probe「do not measure holding force」),
  所以那部分改由腳本化、有母數、有配對、有信賴區間的台架協定量,判準仍是數字。
- `NOTICE`,記錄 InMoov 的 CC BY-NC 3.0 與署名。它的 STL 不進版控樹:非商業條款會傳染
  給整包交付物,而且匯入的網格進不了 spec 驅動的驗證管線。

#### Changed

- `docs/README.md` 的導航表與 `docs/tasks/00_INDEX.md` 各加一列。V3 是目前唯一的
  ACTIVE 任務。

### V01.07.001

#### Fixed

- The V2 tip cap now meets every grip direction on a flat face. Aiming the pads at the
  cardinals had left the cap where V1 put it, and a hexagon cannot face four directions
  at any rotation: measured on the built tip, two of the four bending axes ended their
  finger on a corner, 30° off square. Face centres reach all four cardinals only when the
  facet count is a multiple of four *and* the ring is turned half a facet — so eight
  facets at 22.5°, which is the count that fixes it without narrowing the contact face as
  far as twelve would. Rebuilt, all four now read 0.0° off a face, the tip gains 24
  triangles and no dimension moves.
- The rotation is a property on the grip spec rather than a constant in the cap builder,
  and V1 answers zero, so V1's cap is built from exactly the coordinates it always was.

#### Added

- A generator gate that measures the built tip instead of the spec that described it. The
  first attempt at the fix changed the facet count, left `create_cap` building at phase
  zero, and passed every domain test with a wrong mesh — arithmetic about a spec cannot
  see that. The first version of the gate scanned polygon normals and was **not
  discriminating**: the centre channel and cable bores are drilled with twenty-four
  segments, so their walls supply a normal within half a degree of any heading, and the
  scan passed a cap deliberately turned off-aim. Replaced with a ray, which can only see
  the surface a finger would touch, and proved by turning the built mesh half a facet.

#### Changed

- The V2 package's manifest revision is now `octopus-hand-V2.1`. `octopus-hand-V2` already
  names a published set of bits, and one set of bits gets exactly one name; the corrected
  geometry ships in the same directory because nothing has been printed from either and
  git history still holds the six-sided cap.

### V01.07.000

#### Added

- Octopus hand V2, shipped as its own controlled package beside an untouched V1. The
  pentagon is turned so a corner stands on each arm, which is the whole point: V1's
  corners fell eighteen degrees off every arm — the phase Blender's five-sided cylinder
  happens to start at, never a decision — so the thickest material sat in the empty
  sectors and the thinnest against the socket carrying the load. Turning it lets the
  edges clear a socket at 36° off the heading instead of along it, so `cos 36` comes off
  the requirement: the plate shrinks from 151.8 mm across corners to 126.5 while the
  material behind each socket grows from one wall to 3.7 mm, and that surplus becomes a
  buttress. Also a wire bore per arm, both rims chamfered, the five points cut back, and
  the bed declared as the machine that actually exists (256 mm, not 220).
- Grip pads aimed rather than merely placed. V1 put them on the diagonals because "the
  ears occupy the cardinals" — true inside the disc and false out at the rim, where the
  pads live: measured on the real mesh, no ear or root reaches past 16.70 mm and the pad's
  buried face starts at 17.20. Since a body's twist is 0 or 90 and the palm's centre lies
  at `180 - twist`, both answers are cardinals, so every body now presents a pad to what
  the hand is closing on — from one shared mesh, and with nearly three times the swept
  clearance the diagonals had (0.553 mm against 0.204 at full travel).
- `bore_probe_points_mm` in the generated-artifact oracle: the centre probe answers one
  axis, and a plate carrying a bore per arm needs a ray each. A short list of results
  fails closed, because two misses out of five reported as "all open" is exactly the
  partial answer that reads as a pass.
- `loft_rings` in the shared Blender primitives. Two hand-written ring-stack lofts already
  existed; this would have been the third.

#### Changed

- `/api/health` derives its status from the dependency instead of asserting `ok` beside
  it. See below for why that mattered on a live machine.
- Four modules split rather than compressed when the file-budget gate fired twice: the
  palm's outline, the stem's swept envelope, the aimed grip surfaces, and the verdict half
  of the artifact contract each answer a different question from the module they left.

#### Fixed

- **`export_stl_mm` restored two visibility flags out of three.** Generators hide their
  master bodies before exporting them and the STL exporter honours `hide_render`, so
  `arm_body`, `arm_tip` and `test_coupon` were written as 84-byte STLs containing zero
  triangles — valid files, non-zero bytes, past every existence check. Held everything
  else constant: one 876-face body exported 84 bytes with the flag set and 168,984 with it
  clear. **V1's own unmodified generator reproduces the empty files**; the copies shipped
  in `models/octopus-hand-v1/` were built on a Blender that did not do this. An export
  that writes no triangles now raises.
- **A 45-degree cap flare grazes the disc rim.** With the flare's run equal to its rise,
  the cap's radius at the trim plane is exactly the disc's, so the surface touches the
  trimmed rim edge instead of crossing it; the next Boolean opened twelve boundary edges
  and the tendon drills turned those into 204 non-manifold ones. V1 survives it only
  because its diagonal pads happen to bury four of the six facet corners in solid
  material — luck, and it ran out when the pads moved.
- **The API never dialled Blender back.** `connect()` was only ever called at startup, so
  a link dropped once stayed dropped for the life of the process: `/api/health` answered
  `{"status": "ok", "blender": "disconnected"}` on the production machine for hours while
  Blender sat alive and listening, every contract run died at the readiness step, and
  restarting the service was the only cure. Detection was never the problem — `is_connected`
  reads the peer's FIN correctly. Recovery did not exist. Redialling now happens at the one
  chokepoint every command already funnels through, which also covers an API that started
  before Blender was ready. Verified on the real machine by restarting Blender underneath a
  running API: health went `degraded`, and the next call succeeded on the same process id.
- `disconnect()` no longer raises when the peer already reset the socket — `wait_closed()`
  re-raises whatever killed the transport, turning "the connection is gone" into "we failed
  to let go of it", during teardown.
- A dropped connection reaching a caller as `ConnectionResetError`. The module already
  promised that a hang-up must never surface as a content error, but it only translated
  FIN; a socket written to after the addon left gets RST instead. `TimeoutError` is
  deliberately still not translated — a slow addon is not a gone one.
- `ExportPanel`'s inspection test waited for `onInspect` to have been *called* and then
  asserted on figures that had not rendered yet — the panel is still showing 檢查中 at that
  point. It now waits for the paint, which is what the test was about.

### V01.06.001

#### Changed

- The octopus hand's visual rubric is judged. A fresh context, given the ten renders and
  nothing else, returned eleven PASS with no FAIL and no UNCLEAR. It took three rounds, and
  the first two are the interesting part: each round's UNCLEAR items were about the evidence,
  never the model, which is how four overview shots became ten framed views. The two items
  the reviewer marked as inferred rather than seen each have a machine measurement behind
  them — a ray cast down the palm axis, and a unit test pinning four pad headings — so no
  further renders were made for them.

### V01.06.000

#### Added

- Six close-up renders in all, driven by what two fresh reviewers could not judge from the
  overview shots. Round one returned six of eleven rubric items UNCLEAR, round two four; each
  new view is framed on one named question — the palm alone for counting tendon holes, a
  socket in profile, one arm looked at down its own radius so alternating pin axes read as
  one centred disc against two side-by-side, the tip from above and below, and a single body
  showing pads on the diagonals against ears on the axes.

#### Changed

- Close-ups render without shadows. At that range the view label sits inside the scene and
  threw a shadow across the part; a reviewer read it as a double exposure and stopped
  trusting the edges it fell on.
- Rubric item I — "no arm touches its neighbour" — is withdrawn from the visual rubric. Two
  reviewers in a row declined to call it and both were right: a shaded isometric cannot
  separate projected overlap from contact, least of all at the pad corners. The
  `HH_OCT_SEG_` collision group measures it directly, nineteen adjacent pairs at zero
  overlap. A rubric item nobody can answer is not a gate, and the eye is the wrong
  instrument for this one.

### V01.05.000

#### Added

- `models/octopus-hand-v1/` — the controlled print package, so the STL is reachable from the
  cloud repository instead of only from ignored working output. Five STL files, the `.blend`
  source, a SHA-256 / byte-length / triangle-count / millimetre manifest, and a README that
  leads with the coupon and states plainly that no physical print has happened.
- `tests/unit/scripts/test_octopus_print_package.py` re-reads every committed binary rather
  than trusting the manifest that shipped beside it, and asserts the README still says the
  package is unprinted and must not be auto-arranged.

#### Changed

- `scripts/publish_print_package.py` takes a `--package` argument and holds one `Package`
  record per model. It was hard-wired to V6's paths, file list, revision and contracts; a
  second model had no way in that was not a fork. `--package biaxial-hinge-v6` stays the
  default, so the documented command is unchanged.
- The task hand-off claimed promotion waits for a physical print, "following V6's
  precedent". That was wrong in both halves: V6 was promoted before any print, and its own
  open failures still say so. Corrected in place rather than quietly dropped.

### V01.04.000

#### Added

- `test_coupon_mm.stl` — a fit coupon cut from the real geometry: a Ø48 mm chunk of palm
  carrying two bodies and four captive pins, 47.8 × 48.0 × 56.8 mm in 7 shells. It carries
  both pin headings and a grip pad, so the one question the upright pose leaves open —
  horizontal bores printing as bridges, captive pins with an unsupported crown — costs an
  hour to answer instead of a night.
- `boolean()` now refuses a target that is hidden in the viewport. `hide_viewport` drops an
  object out of the depsgraph and `modifier_apply` then removes the modifier without
  applying it — no error, no geometry. Three features shipped as silent no-ops that way in
  one sitting, each looking fine because none changed a bounding box. Proven in real
  Blender both ways: a hidden target raises, a visible one still goes 6 faces to 12.
  V6's own contract stays green at 11/11.

#### Changed

- `docs/LESSONS_LEARNED.md` records the meta-lesson: when a documented class recurs, the
  fix is a gate at the choke point every path goes through, not another line of guidance.
  A hand-written workaround already in the codebase is the signal that the gate is missing —
  `hinge_retention` had been toggling visibility around its Booleans all along.

### V01.03.001

#### Fixed

- The one-piece STL left out all fifty captive pins. `export_stl_mm([palm, *bodies])` looked
  complete and sliced without complaint, but every joint would have printed as an empty bore
  and the hand would have come off the bed as a pile of loose discs. The export now carries
  the pins too, and the generator fails loud if the list does not match
  `printed_part_count` — palm, 25 bodies, 50 pins, 76 shells.

### V01.03.000

#### Added

- Grip pads on every repeated arm body: four per body, on the plain diagonals, Ø42 across
  their flat faces. The diagonals are the only rim free of joint hardware and the only
  headings unchanged by the chain's ninety degree twist, so one pattern serves every body.
  Each pad's outer face is flat — a flat face beds against an object where a cylinder
  touches it on a line — and its underside is chamfered 45° so it is not a bare overhang.
- The tip is now a terminal segment rather than a body with parts glued on. Everything
  above the disc is cut away, unused ears included, and replaced by a six-faced cap that
  flares off the disc at a printable angle and then only narrows. Two through-bores anchor
  the four cables, each crossing one opposed pair of tendon holes inside the cap.
- `src/core/domain/octopus_grip.py` — the grip surfaces split into their own spec when
  `octopus_hand.py` reached the god-file warning. The seam is real: one module lays the
  hand out, the other owns what presses on an object.

#### Fixed

- Spacing the arms on the pads' face diameter let neighbouring pads intersect at their
  corners. A flat face is a chord, so its corners stand further out than its middle:
  Ø42 across the faces is an envelope of Ø46.35. `grip_envelope_radius_mm` is what the
  spacing invariant measures now, and the stations moved out to 41.5 mm to suit.
- The tip cap's closed bottom sat flush with the disc's own surface, leaving the Boolean
  two coplanar sheets and readiness reporting `non_manifold_edges`. The cap now starts a
  fuse depth inside solid material.
- The tip's centre wire channel was drilled to the body's depth, not the cap's, leaving it
  blind above z=13 while the cap top sits at z=18. Invisible in the bounding box; caught by
  the centre-ray probe.

#### Changed

- `docs/LESSONS_LEARNED.md` records the envelope class: a nominal face dimension is the
  nearest point of a non-circular part, not its farthest, and clearance invariants that
  read it are measuring the wrong thing.

### V01.02.000

#### Fixed

- The octopus hand's base joint swung the wrong way. The palm socket faced along its arm's
  radius, so the pin lay along the radius too and the first joint swung the arm sideways
  around the palm — it opened and closed nothing. `palm_socket_twist_deg` now turns each
  socket a quarter turn so the pin lies across the radius and the arm carries in toward the
  palm centre and back out, which is the joint that actually closes a grip. Every body above
  is twisted to match, so the ears still meet, and the pins follow the same alternation.
  Measured in the live scene: the base pin axis sits 90.0° to the radius at all five stations.

#### Changed

- `octopus_hand_tips.json` no longer sweeps the tip against a copy of itself. That measured a
  joint the hand does not have — nothing mates above a tip — and it passed for an unrelated
  reason before the axes changed and failed for an equally unrelated one after. What replaces
  it is a spec invariant: every tip feature starts above the body's mid-plane, clear of the
  ears the tip actually hangs from. `tip_feature_fuse_mm` moved into the spec so that
  clearance is a checked dimension rather than a constant in the generator.
- `docs/LESSONS_LEARNED.md` records the class: a proxy test whose configuration does not exist
  in the product carries no information green or red, and looks identical to a real guard.

### V01.01.001

#### Changed

- `docs/tasks/04_octopus-hand-v1.md` records that the octopus hand's visual rubric has not
  been judged by a fresh context yet. The rubric existing is not the rubric having passed,
  and the hand-off was letting the next reader assume otherwise.

### V01.01.000

#### Added

- Octopus hand V1: a five-armed print-in-place gripper built entirely from new files. A
  pentagonal palm carries five V6 biaxial arms, twenty tendon holes and one central wire
  channel; each tip gets four cross-drilled cable eyelets and an inward claw. `OctopusHandSpec`
  composes `BiaxialHingeSpec` rather than subclassing it, so V6's contract is untouched — no
  V6 domain, generator or `models/` file changed.
- The printer bed is a spec invariant, not a comment: `upright_footprint_mm > max_bed_mm`
  raises. Splayed flat the hand needs 275.9 mm and does not fit a 220 mm bed; upright it
  needs 133.3 mm square by that bound and exports at 126.8 × 120.6 × 113.8 mm.
- Two artifact contracts, `octopus_hand.json` and `octopus_hand_tips.json`, green on real
  Blender with no skips. Between them they measure per-arm collision, **inter-arm** collision
  (twenty bodies sorted level by level), tip-to-tip clearance, a −34°…+34° joint sweep for
  both the plain body and the tip, an open wire channel, an open cable path through the tip,
  and an untruncated readiness report.
- `docs/verification/octopus-hand-v1.md` — target, evidence table, a ten-item visual rubric
  and the evidence boundaries.

#### Changed

- `docs/LESSONS_LEARNED.md` records the class this build walked into: a feature that does not
  change an object's bounding box is invisible to dimension readback. A hidden object drops
  out of Blender's depsgraph and its Booleans are silently skipped, so the tip exported
  byte-identical to the plain body while fourteen contract checks stayed green. The generator
  now fails loud if the tip's face count did not grow.

### V01.00.00C

#### Fixed

- `BlenderSocketClient.is_connected` now folds in the reader's EOF instead of trusting
  `StreamWriter.is_closing()` alone. `is_closing()` reports whether *this* side asked to
  close, so it stayed True after Blender exited and `/api/health` kept answering
  `blender: connected` with port 9876 shut — the field `docs/30-verification.md` tells
  reviewers to trust as the readiness signal.
- A dropped addon connection now raises `BlenderConnectionError` instead of degrading into
  a decode failure. `send_command` broke out of its read loop on the peer's EOF and handed
  the stump to `_decode_response`, so a dead engine surfaced as `JSONDecodeError` and sent
  the reader hunting for a data-format bug. `LESSONS_LEARNED.md` recorded this class and
  its prevention item in V01.00.00B; this implements it.

#### Added

- `tests/unit/adapters/test_blender_socket_liveness.py`: three tests over a real loopback
  server (no mock socket) pinning both halves of the signal — false once the peer hangs up,
  true while the peer holds the socket.

#### Changed

- `docs/LESSONS_LEARNED.md` records the class behind the above: a connection flag that only
  reads local state cannot be a readiness signal, and the V01.00.00B lesson's premise
  ("health honestly said disconnected") held only for one startup ordering.

### V01.00.00B

#### Fixed

- `deploy/launchd/install.sh blender` now waits for the addon listener and restarts the API
  as well. Restarting Blender orphans the socket the API holds — it connects once at startup
  and never reconnects — so a bare `blender` install left the API answering from a dead
  socket. `/api/health` correctly said `disconnected`, but the data path failed as
  "scene info is missing fields" (422) rather than "Blender is unreachable" (503), which
  points a reader at the payload instead of the connection.

#### Added

- `scripts/check_installed_plists.py` and its eight tests: a real-tier gate asserting every
  installed LaunchAgent resolves to this checkout. `docs/12-deployment.md` rule 7 called a
  clean diff between installed plist and template "the contract" and then left it to manual
  checking; this is the missing machine check.

#### Changed

- `docs/LESSONS_LEARNED.md` records two more classes found while finishing this release:
  restarting a depended-on service does not restore the side that depends on it, and a
  filesystem sync service disguises itself as bugs in git, npm and the agent.

#### Verified

- `scripts/ci.sh --real` — all hard gates green, including the new installed-LaunchAgent
  gate and all four real-machine tiers against live Blender.

### V01.00.00A

#### Fixed

- The four T3 verifiers gained a `src.` import in V01.00.009 and could not run: `ci.sh`
  executes them as subprocesses, where nothing puts the repository root on `sys.path`.
  T1 and T2 stayed green because pytest does. Each now carries the `PROJECT_ROOT` block
  that `generated_artifact_verify_real.py` already had.
- Removed two `from src.…` lines that an automated edit had inserted *inside* the
  triple-quoted Blender scripts these files build. Blender executes those strings in its
  own interpreter, where this repository does not exist.

#### Added

- `tests/unit/scripts/test_embedded_blender_code.py` — no project import may sit inside a
  Blender code string. Nothing else can catch this: ruff, mypy and the narrowing gate all
  see a string, and no test tier executes it. Blender's own dialect is allowed.

#### Changed

- The eslint wiring proof runs the installed binary instead of `npx`, and asserts that
  binary exists. `npx` performs its own resolution and stalled under load, which made the
  gate flake; runtime drops from 7.7s to 2.0s.
- `docs/LESSONS_LEARNED.md` records the environment root cause found while verifying this
  release: the project directory is inside macOS Desktop-and-Documents iCloud sync, which
  produced the " 2" conflict copies, the broken git ref, the dataless `web/dist` files and a
  corrupted `web/node_modules` — four symptoms that each looked like a different tool's bug.

#### Verified

- `scripts/ci.sh --real` — all hard gates green, including all four real-machine tiers
  against live Blender through the Tailnet endpoint with the addon socket as an
  independent oracle.

### V01.00.009

#### Fixed

- Repaired `POST /api/refine`, which called `adapter_factory.create_llm_adapter()` — a method
  that exists on neither the port nor the concrete factory. `app.state` returns `Any`, so mypy
  could not see the call, and the only factory double in the suite was a bare `MagicMock` that
  answers to any attribute name. The endpoint had no test at all; it has two now.

#### Changed

- Domain errors map to HTTP status in one place (`api/main.py`). Fourteen hand-written
  clauses across four routers are gone; the same condition no longer produces `str(exc)` in
  some endpoints and `f"Blender unreachable: {e}"` in others.
- Use cases are assembled at the composition root instead of per request in routers, which is
  what makes their wiring type-checked.
- `api/routers/scene.py` (749 lines, seven services) is split into eight routers by the service
  each owns; the largest is now 171 lines. The OpenAPI route set is unchanged.
- Every `bpy` statement the REST layer needed moved to `src/adapters/blender_scripts/`, where
  each operation has a name and returns a typed `ScriptOutcome`. Transport failures now
  propagate to the shared handler instead of being swallowed into a 500 by some routes and
  turned into a 503 by others.
- Five copies of JSON narrowing collapse onto `src/infrastructure/narrowing.py`, which grows a
  predicate layer plus a `required()` combinator that keeps each caller's exception type and
  message — those strings reach REST clients verbatim as a 422 `detail`.
- Five frontend call sites share `runTracked`; the print-readiness inspection now reports into
  the operation store like every other operation instead of only its own panel state.
- `scripts/` joins every Python gate (ruff, format, mypy strict, container-narrowing). It was
  outside all of them, including the gate's own source file.
- The container-narrowing gate now recognises `Mapping`, `Sequence` and the other abstract
  container types. It had listed only `dict` and `list` while four shipped call sites used the
  abstract names.

#### Added

- Gates with should-fire and should-pass fixtures for each new rule: no hand-mapped domain
  errors, no use-case construction or `bpy` source in routers, no re-defined script primitives,
  a 400-line file budget warning at 380, DCC doc rules, and an eslint rule proven by driving
  real eslint over stdin.
- `tests/unit/scripts/test_check_container_narrowing.py` — the blocking gate had no test of
  its own, which is how its blind spot survived.
- `docs/DEFERRALS.md` recording three deliberate non-abstractions with firing triggers.
- `scripts/blender_generator_runner.py` replacing the clear/hide/build/restore wrapper that
  three generators each carried.

#### Removed

- Archived to `scripts/archive/`: two generators and their render adapters with zero
  references anywhere, two cat-stand demos, and an unreferenced use case. Nothing deleted.

### V01.00.008

#### Changed

- Restructured `docs/` into a DCC tree: a `README.md` navigation table with a
  "when to read" column, numbered topic files (`00-context`, `01-architecture`,
  `10-runtime-ssot`, `11-mcp-clients`, `12-deployment`, `20-conventions`,
  `30-verification`), and `[[wikilink]]` cross-links. Renames use `git mv`, so
  history follows each file.
- Collapsed seven duplicated fact groups into single sources. Ports, routes,
  canonical URLs and environment variables now exist only in
  `docs/10-runtime-ssot.md`; CI tiers, commands and "what does not count as
  evidence" only in `docs/30-verification.md`. Other documents link instead of
  restating.
- Rewrote `docs/KNOWLEDGE.md` as a knowledge-placement map only; navigation moved
  to `docs/README.md`, removing the second, drifting navigation surface.
- Corrected stale statements verified against the running system: the task index
  and task 02 said PR #4 was open (merged as `901cb53`); engineering standards
  said two LaunchAgents run (three plists exist) and called the service an
  "MCP-style HTTP API"; `deploy/launchd/README.md` omitted the `blender` install
  target that `install.sh` supports.

#### Added

- Added `tests/unit/core/test_docs_dcc.py`, a hard gate for three DCC rules:
  wikilinks resolve, every live doc is reachable from the navigation root within
  two hops, and ports appear only in their SSOT file. Each rule ships with
  should-fire and should-pass fixtures, so a guard that degenerates into
  "always fails" or "never fires" is itself caught.

#### Removed

- Removed `web/README.md` (unreferenced Vite template boilerplate) and five
  cloud-sync duplicate files under `web/dist/`.
- Archived `docs/TECH_SPEC.md` to `docs/archive/2026-09-tech-spec-superseded.md`
  and removed `docs/ENGINEERING_STANDARDS.md` after distributing their content
  (§1 scope to `00-context`, §11 plist rules to `12-deployment`, the remainder to
  `20-conventions`, `10-runtime-ssot` and `30-verification`).

### V01.00.007

#### Added

- Added the checksum-controlled V6 print package under `models/biaxial-hinge-v6/`: five
  millimetre STL coupons and parts, the complete `.blend` source, and a `manifest.json`
  with independent byte-length, SHA-256, triangle-count and dimension readback.
- Added `scripts/publish_print_package.py`, an allowlisted promoter from ignored
  `tmp/biaxial-hinge-v6/` output into the tracked package, with a package readback test and
  a CLI bootstrap regression test.
- Added `.gitattributes` marking `.stl` and `.blend` files as binary.

#### Changed

- Documented the promoted package in the README, V6 hand-off, verification guides and
  project Skill; `tmp/` stays ignored working state and is never unignored wholesale.

### V01.00.006

#### Added

- Added the V6 Ø36 mm repeatable hinge body with biaxial in-disc roots, a clear Ø10 mm
  sensor channel, four tendon bores and a reduced 19 mm pitch.
- Added two 3D-print PIN workflows using the same body: a two-body print-in-place coupon
  with double-headed captive pins, and a six-part coupon with grooved pins plus C clips.
- Added reusable retention geometry, PIP/separate presentation adapters, declarative
  readiness contracts, world-space hardware probes and displaced stop-contact evidence.

#### Changed

- Generalized the V5 body and pin builders to accept an injected immutable specification,
  preserving the earlier model while avoiding a second copy of its Blender construction.
- Archived the superseded V5 task contract and updated the project Skill, artifact workflow,
  V6 hand-off and independent A–I visual evidence.

#### Fixed

- Synchronized Blender view-layer transforms before hidden-layout export/BVH measurement,
  preventing stale world matrices from collapsing split hardware to the origin.
- Separated product and presentation object prefixes so diagnostic render copies cannot
  contaminate readiness selection, intersection counts or truncation state.

### V01.00.005

#### Added

- Added the V5 in-disc hinge prototype: Ø34 mm body, shallow reinforced roots, a clear
  Ø10 mm sensor channel, four tendon bores and separately printable Ø4 mm headed pins.
- Added body/pin/coupon millimetre STL outputs, detail/top views, JSON-driven hole/slope/
  hardware probes, fail-closed evidence tests and independent visual acceptance targets.

#### Changed

- Extracted shared Blender mesh primitives for V4/V5 reuse; preserved public REST/MCP DTOs.
- Superseded V4 task notes with a V5 hand-off, preserving V4 history and generated files.
- Documented sequential real-verification transactions, Blender STL import scale 0.001,
  and prototype limits: body support warnings, untested physical fit and missing pin retention.

### V01.00.004

#### Added

- Added nine short repeated hollow modules, eight alternating side-mounted hinges, a clear
  10 mm sensor-wire channel, four tendon routes and a single-module millimetre STL export.
- Added reusable geometry, render and explicit-mesh export helpers plus a JSON-driven
  generator/oracle/MCP verifier with independent binary STL readback and sampled joint motion.
- Added RED-to-GREEN tests for geometry constraints, artifact parsing, fail-closed reports,
  missing motion samples and assembly-camera restoration; documented the reusable workflow.

#### Fixed

- Removed static and bent bridge/lug collisions by deriving bridge placement from the
  motion envelope; real geometry checks pass 15 discrete poses from −34 to +34 degrees.
- Prevented overlapping/cropped print layouts and camera state leaking from the last render
  into the saved assembly file. Thin-wall and support warnings remain visible for trial prints.

### V01.00.003

#### Added

- Added an immutable hinge-phalanx domain contract, RED-to-GREEN validation tests, and a
  Blender generator for five identical links sharing one mesh across four serviceable
  X-Y-X-Y revolute joints.
- Added deterministic assembly and three-view print-layout evidence with 4 mm pins, optional
  MR84 4x8x3 bearing interfaces, and four continuous tendon guides.

#### Changed

- Replaced the active bowl-shaped ball-socket concept with alternating single-axis clevis
  hinges that are suitable for FDM prototyping and map directly to machined pins and bearings.
- Changed tendon routing to a quarter-turn-invariant cross pattern so the same printed part
  can be installed at alternating 0/90-degree orientations without changing hole alignment.

### V01.00.002

#### Added

- Added an immutable one-part vertebra contract and Blender generator: three instances share
  one mesh, while two ball-socket interfaces provide four named X/Y rotational axes and four
  continuous tendon routes.

#### Changed

- Replaced the earlier disc-and-cross-gimbal prototype with one repeatable 42 mm vertebra
  carrying a 10.0 mm male ball and 10.6 mm Y-split female socket.
- Removed the whole-part bevel after real MCP analysis exposed slot-edge defects; the final
  report has no non-manifold or intersection findings and retains honest support warnings.

### V01.00.001

#### Added

- Added an immutable, validated two-cell tendon-joint specification with RED-to-GREEN tests
  and a Blender 5.1 generator for three female-yoke discs, two male cross-gimbals, four
  named hinge axes, four continuous tendon routes, and separated print-layout evidence.

#### Changed

- Made concept renders deterministic in a shared Blender runtime by isolating unrelated
  scene objects, using scale-stable Workbench colors, and restoring prior visibility.
- Reduced generated mesh density and removed degenerate gimbal geometry so MCP print
  readiness completes without truncation; remaining support and tip-snap warnings stay
  visible as design-review items.
- Archived the accepted project-knowledge 5S task and opened the tendon-joint task as the
  sole current progress record.

### V01.00.000

#### Added

- Added project task/checkpoint SSOT, knowledge 5S budgets, and a repository-specific
  `blender-mcp-studio` Skill.
- Established the base36 `VERSION` release SSOT and exposed it through FastAPI metadata.
- Added a machine gate for broken local Markdown links, including archived documentation.

#### Changed

- Consolidated agent instructions in `AGENTS.md`, with `CLAUDE.md` importing the shared rules.
- Archived the completed 2026-07 campaign and replaced the legacy knowledge monolith with a
  current navigation map.
- Made production startup delegate to launchd and reserved Vite port 5173 for foreground dev.

#### Deprecated

#### Removed

- Removed stale local agent permission entries and generated cache/build artifacts from the
  working directory; secrets, dependencies, runtime databases, and launch configuration remain.

#### Fixed

- Made `install.sh all` wait for measured Blender addon readiness before starting the API,
  preventing a one-shot startup connection from remaining disconnected after a cold boot.

#### Security
