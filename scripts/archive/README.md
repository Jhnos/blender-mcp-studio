# scripts/archive — 已停用的產生器與示範

這裡的東西**還在版控裡，但不再是現行程式碼**。它們被移進來的理由只有一個：
全樹搜尋後**零引用**——沒有 contract、沒有測試、沒有文件、沒有腳本呼叫它們。

歸檔不是刪除。要復用哪一支，先確認它依賴的模組還在，再移回 `scripts/`。

| 檔案 | 行 | 被什麼取代 |
|---|---:|---|
| `model_tendon_joint.py` | 391 | V6 biaxial 線（`scripts/model_biaxial_hinge.py`）。V4／V5 歷史見 `docs/archive/tendon-hinge-v4.md`、`v5.md`，兩者都標 SUPERSEDED |
| `tendon_joint_render.py` | 185 | 同上；只被 `model_tendon_joint.py` 引用 |
| `model_hinge_chain.py` | 456 | 同上 |
| `hinge_chain_render.py` | 176 | 同上；只被 `model_hinge_chain.py` 引用 |
| `demo_cat_stand.py` | 350 | 早期示範，非產品路徑 |
| `run_cat_stand.py` | 137 | 同上，與前者題材重複 |
| `get_scene_preview_use_case.py` | 40 | 原 `src/core/use_cases/get_scene_preview.py`；`GetScenePreviewUseCase` 全樹零引用，預覽走 `GET /api/preview` → `SceneOperationsService` |

## 為何不留在原處

`hinge_chain_render.py` 與 `tendon_joint_render.py` 的 `diff` 只有 77 行相異，
函式同名同序——它們是彼此 fork 出來的。留在現行樹裡，任何「消除重複」的努力都會
先撞上這兩支**沒人用**的檔案，而抽象化一段死程式碼是純粹的浪費。

若日後要復活 tendon 或 hinge-chain 線，正確做法是先定義一個
`PresentationProfile`（前綴／解析度／相機模式／燈光／地板尺寸），再讓三支 render
變成三個 profile 常數——而不是把 fork 移回去。

## 這裡不受 CI 檢查

`scripts/archive/` 被排除在 lint 與型別檢查之外。這是刻意的：歸檔內容是歷史，
不該因為現行規範演進而被反覆改寫。要復用就要先讓它通過現行閘門。
