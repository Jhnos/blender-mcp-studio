# VOC 追溯

Population: 本次 V4 產生的 LS_ 兩頭、三探頭、單杯與 HMI；排除歷史模型、LS_CHECK_ 佈局副本與 LS_DIAG_；任何必要族群為零即 FAIL。

| ID | Requirement | Tier | User-visible | Kind | Verified-by |
|---|---|---|---|---|---|
| R1 | 探頭能直上離杯至少 10 mm | voc | yes | behavior | artifact:probe-lift.json/H1 |
| R2 | 兩頭可單獨提起 | voc | yes | behavior | artifact:probe-lift.json/H2 |
| R3 | 提起途中不撞杯或自己 | product | yes | behavior | artifact:probe-lift.json/H3 |
| R4 | 全行程保有導向 | engineering | yes | behavior | artifact:probe-lift.json/H4 |
| R5 | 使用者看得到前後差別 | voc | yes | behavior | artifact:probe-raised.png |
| R6 | 製造包有可靠固定與裝配 | voc | yes | behavior | artifact:manufacturing-qualification/H6 |
| R7 | 不以自動調平假裝實體機構 | product | yes | behavior | artifact:README.md/limitations |
| R8 | 純領域與幾何／渲染／檢查解耦 | engineering | no | behavior | static:scripts/ci.sh |
| R9 | 夾爪五金可裝入且探頭可側向拆換 | engineering | yes | behavior | artifact:clamp-assembly.json,jaw-service.json |
| R10 | 導桿上下具有幾何防脫止擋 | engineering | yes | behavior | artifact:clamp-assembly.json |
| R11 | 螢幕收折檢查納入探頭五金 | engineering | yes | behavior | artifact:joint-motion.json |
