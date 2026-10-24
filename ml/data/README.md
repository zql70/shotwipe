# 相册扫描与复核清单

这一目录存放**本地**扫描脚本和生成物，用于把个人相册变成可标注的候选池。
生成物包含个人照片路径，**不要提交、不要上传**；只在本机使用。

## 脚本

| 脚本 | 作用 |
|---|---|
| `scan_iphone_library.py` | 第一遍：元数据 + 自动标截图；输出 manifest |
| `mine_tinyclip.py` | 第二遍：TinyCLIP 打分 + dHash；输出全量分数与候选 |
| `build_review_lists.py` | 生成屏摄候选、低分漏检、截图抽检三份复核 CSV |

运行（当前已跑完 iPhone）：

```bash
cd ml
.venv/Scripts/python.exe data/scan_iphone_library.py \
  --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷" \
  --out data/iphone_manifest.csv

.venv/Scripts/python.exe data/mine_tinyclip.py \
  --manifest data/iphone_manifest.csv \
  --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷" \
  --out data/iphone_scores.csv \
  --candidates data/iphone_screen_photo_candidates.csv \
  --workers 6

.venv/Scripts/python.exe data/build_review_lists.py \
  --scores data/iphone_scores.csv --out-dir data
```

## 本次 iPhone 扫描结果

- 文件：18,298；图片 15,652；视频 2,645（v1 排除）。
- 自动标签：
  - `screenshot` 3,777（PNG 尺寸匹配 iPhone/iPad 屏幕；其中 3,687 张为 1170×2532）
  - `photo_candidate` 11,725
  - `other_png` 94
  - `screenshot_candidate_low` 56（800×480 等，需复核）
- TinyCLIP 屏摄候选（pHash 去重后）：
  - p≥0.20：2,675
  - p≥0.35：1,968
  - p≥0.55：1,397
  - p≥0.99：147

**重要：候选不是标签。** 随机抽样显示 p≥0.55 的组里仍混有大量假阳性
（打印海报、标牌、房间里的电视、花艺、车辆等）；p≥0.99 的组更好但仍非 100%
（打印地图/课表、房间里的黑屏电视等）。所以：
- 这些列表只用于**人工复核 / 构建 golden set / 挖硬负样本**；
- App 里模型结果已改为默认不勾选，只有系统元数据截图自动勾选。

## 复核文件

| 文件 | 内容 | 建议 |
|---|---|---|
| `review_screen_photo_candidates.csv` | 按分数排序的前 500 个候选（pHash 去重） | 优先标注；`human_label=screen_photo/other/ignore` |
| `review_low_score_photos.csv` | p<0.20 的随机 500 张 | 找漏网屏摄；顺便补硬负样本 |
| `review_screenshots.csv` | 高置信截图随机 200 张 | 抽检自动标签是否准确 |
| `review_top60.jpg`、`review_random_confirmed60.jpg`、`review_low60.jpg`、`band_*.jpg` | 候选拼图 | 快速目测，不必逐张打开原图 |

`human_label` 取值：
- `screenshot`：系统截屏/像素级平整
- `screen_photo`：相机拍正在显示的屏幕
- `other`：普通照片、屏幕关着、打印品、海报、标牌、窗户等
- `ignore`：模糊、无法判断、合成渲染

## Golden v1（2026-10-19 冻结）

- `labeled_all.csv`：1,499 条标注
- `screen_photo_positives.csv` / `hard_negatives.csv` / `labeled_screenshots.csv`：
  456 / 790 / 253
- `golden_test_v1.csv`：500（142 屏摄 / 280 普通 / 78 截图）
- `golden_calibration_v1.csv`：201
- `train_labeled_v1.csv`：798
- `golden_v1_manifest.json`：版本、SHA256、采样设计

真实分层指标：高分候选 59.9%，中分段 38.0%，低分随机 8.4% 仍是屏摄，截图
抽检 99.5%。外推约 1,865 张屏摄，TinyCLIP 高分召回约 16%。这是 v2 的训练
起点和验收基线；golden_test 不参与训练。

## 下一步

1. 先复核 `review_screen_photo_candidates.csv` 的前 300–500 条，标出真实屏摄。
2. 复核 `review_low_score_photos.csv` 的随机样本，找漏检和硬负样本。
3. 抽检 `review_screenshots.csv`，确认截图自动标签。
4. 中分段 0.20–0.90 是 v0 golden 的唯一缺口；标完这 300 张后可冻结 v1 golden。
5. 按日期/场景分组 + pHash 去重，切出 golden test（400–500）和 calibration（150–200），
   其余进训练池。Golden 一旦冻结，不再参与训练。
5. 安卓相册到位后重复同一流程；Android 样本要占 golden 的至少 30%。


## 复核页面

```bash
cd ml
.venv/Scripts/python.exe data/review_server.py   --root "C:/Users/killian/Desktop/文档/SWT_iPhone13_photos/相机胶卷"
```

浏览器打开 `http://127.0.0.1:8765`（只绑本机，不上传）。

- 四个 Tab：屏摄候选 500 / 低分漏检 500 / 截图抽检 200 / 中分段 300。
- 点标签按钮或数字键 `1/2/3/4` 标注；`U` 取消；方向键切换；`Enter` 看大图。
- 标签和备注自动保存到 `data/review_labels.json`；右上角「导出 CSV」导出
  带 `human_label`/`notes` 的完整表格。
- 缩略图按需生成并缓存到 `data/.review_cache/`；HEIC 也能直接预览。
- 标注以 `relative_path` 为键，三个列表共享同一张图的标签。
