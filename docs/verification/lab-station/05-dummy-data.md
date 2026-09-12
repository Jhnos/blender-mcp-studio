# 受控假件

族群：兩個獨立頭、三根探頭、一個容器、HMI、兩組固定導向與移動滑座。

由 `scripts/model_lab_station.py` 呼叫現有 `run_generator(prefix="LS_")` 建立；只清除自己命名空間。診斷件用 `LS_DIAG_`，finally 清理；操作 finally 恢復所有姿態。

V3 用 `tmp/lab-station-v3/`，不覆寫 V2 產物。每次生成必須用新網格更新實際矩陣後再驗證。陰性對照只改升程，其他配置相同。
