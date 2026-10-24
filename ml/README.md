# ShotWipe 识别模型管线

屏摄图识别的模型工具链。当前 App 使用**自训 MobileNetV4-Conv-S 三分类模型**
（v2，2.7MB TFLite）。TinyCLIP 是 M2 的商用过渡模型；MobileCLIP 只保留内部研究。

> **许可说明**
> - 当前 v2 模型：MobileNetV4 主干来自 timm 的 **Apache-2.0** ImageNet 权重；
>   教师 SigLIP 2 是 **Apache-2.0**，只离线做特征蒸馏；产出模型归项目所有。
> - TinyCLIP（MIT）是 M2 过渡模型，训练数据来自 LAION-400M；App 已不再分发。
> - MobileCLIP 是 Apple ML Research Model License，**仅限非商业研究**；
>   仅保留在 `ml/` 做历史回归，不随 App 发布。
> - 训练数据来自用户自采相册 + 合成屏摄；上架前仍需完成数据/隐私合规审查。

## v2 模型产物

| 文件 | 说明 |
|---|---|
| `models/v2_screen_classifier.onnx` | 学生模型 ONNX，输入 `[1,3,224,224]` 0–1，输出 3 logits |
| `tflite_v2_dr/v2_screen_classifier_dynamic_range_quant.tflite` | **2.7MB** 动态量化模型，App 实际使用 |
| `app/assets/models/v2_screen_classifier.tflite` | 拷贝进 App 的模型资产 |
| `data/train_manifest_v2.csv` | 训练/验证/校准/测试清单 |
| `data/teacher_embeddings.npy` | SigLIP 2 教师 768 维特征缓存（训练用，不随包） |
| `data/v2_student_distill.pt` | 最终学生 checkpoint |
| `data/v2_metrics_distill.json` | 校准/测试指标 |

输入 NHWC `[1,224,224,3]`、0–1；ImageNet 归一化已烘焙进图里。
App 在后台 isolate 做中心裁剪 + 双线性缩放 + 前向，只依赖 2.7MB TFLite。

## v2 训练流程

```bash
cd ml
# 1) 合成屏摄（真实截图 + 真实背景 + 透视/摩尔纹/眩光/反光/噪声）
.venv/Scripts/python.exe train/synthetic_screens.py \
  --root "<相机胶卷>" --count 8000 --workers 10

# 2) 320px 缓存 + 训练 manifest（严格排除 golden test/cal 路径）
.venv/Scripts/python.exe train/build_manifest.py --root "<相机胶卷>"

# 3) SigLIP 2 教师特征（RTX 4080，约 2 分钟）
.venv-gpu/Scripts/python.exe train/teacher_embed.py

# 4) 训练：8k 合成 + 3k 自动截图 + 2k 弱负 + 798 真实标注（128 做 val）
#    6 epoch 预训练 + 3 epoch 真实数据 fine-tune；特征蒸馏 λ=0.5
.venv-gpu/Scripts/python.exe train/train_student.py --epochs 6 --finetune-epochs 3

# 5) 导出 ONNX + 校准集
.venv/Scripts/python.exe train/export_v2.py

# 6) 动态范围量化 TFLite（权重 int8、激活 float）
.venv/Scripts/onnx2tf.exe -i models/v2_screen_classifier.onnx \
  -o tflite_v2_dr -tb tf_converter -odrqt
```

### 量化说明

- **动态范围量化**：2.7MB，float 输入/输出，CPU 可跑，端上精度最接近 float。
  选它作为 App 版本。
- **全整型严格量化**：flatbuffer_direct 的 per-channel 路径报
  `quantized_dimension`/`DEPTHWISE_CONV` 校验错误；per-tensor 版可以生成
  2.56MB 模型，但导入 ai-edge-litert 在 CPU 上极慢，未采用。
- **float32/float16 TFLite**：9.6MB / 4.8MB；float16 在 CPU 卷积上不可靠。

## v2 真实指标（golden v1，iPhone 单用户）

golden v1：分层 500 test（142 屏摄 / 280 普通 / 78 截图；高/中/低分段都覆盖）。

| 版本 | 阈值 | 精度 | 召回 | 说明 |
|---|---|---|---|---|
| PyTorch float，App 预处理 | 0.64 | **94.6%** | **74.6%** | 离 95/70 只差一点 |
| TFLite 动态量化 | 0.65 | 92.9% | 73.2% | App 实际模型 |
| TFLite 动态量化 | 0.70 | 96.1% | 69.7% | 更保守 |

**没有阈值同时满足 95% 精度 / 70% 召回**，所以 App 继续只把模型结果当候选，
默认不勾选；只有系统元数据截图自动勾选。误差集中在会议投影幕、打印海报/标牌、
导视牌等标签边界模糊的样本上——这需要标签规则和一轮清理，而不是继续调阈值。

**域外泛化警告**：在 Commons 的域外屏摄测试集上，v2 只召回 8/15，低于
TinyCLIP 的 12/15。v2 对当前用户相册拟合较好，但跨用户/跨设备还不够；
Android 相册和更多用户样本必须补进训练与 golden。

## 真实相册标注与 golden v1（2026-10-19）

iPhone 18k 分层标注 1,499 条后的真实结果（与 Commons 小样本差异很大）：

| 分层 | 样本数 | 屏摄精度 |
|---|---|---|
| 高分段候选（top 500，约 p≥0.90） | 499 | **59.9%** |
| 中分段（0.20–0.90，每段 75 张） | 300 | **38.0%** |
| 低分随机（p<0.20） | 500 | **8.4% 仍是屏摄** |
| 截图抽检 | 200 | 99.5% 为截图 |

按分层样本外推，图库中约 **1,865 张真实屏摄**；TinyCLIP 的高分检测只覆盖约
**16%**，候选池（p≥0.20）约 58%。这是 v2 的训练起点和 TinyCLIP 淘汰的直接依据。

已冻结的数据（`data/`，本地）：

- `labeled_all.csv`：1,499 条人工标签 + 分数/pHash/日期
- `screen_photo_positives.csv`：456 张真实屏摄
- `hard_negatives.csv`：790 张普通/硬负样本
- `labeled_screenshots.csv`：253 张截图
- `golden_test_v1.csv`：500 张（142 屏摄 / 280 普通 / 78 截图）
- `golden_calibration_v1.csv`：201 张
- `train_labeled_v1.csv`：798 张
- `golden_v1_manifest.json`：版本、SHA256、采样设计

采样设计：高分段是 top-500 截断样本；低分是 500/9,035 随机样本；中分段是
每个 0.2 宽区间 75 张的分层样本；截图是 200/3,777 随机样本。Golden 是分层
集合，不是简单随机样本，评价时按分层报告；61 张高分段尾部候选和安卓相册
仍未纳入。`golden_test_v1.csv` 不参与训练。

## Android golden 与 v2.1（2026-10-20）

Android 复核 1,036 行，去重后 **852 条唯一标签**（76 屏摄 / 618 普通 / 158 截图）；
182 条候选/中分段重复标签一致，已合并。Android 独有数据 3,305 张，
已排除 `DCIM/Camera/APPLE`（6,115 张 iPhone 导入）和 96 张 iPhone test/cal 重复。

Android v2 精度分层：p≥0.90 **85.7%**、0.80–0.90 **69.7%**、0.65–0.80 **60.6%**、
0.35–0.65 **31.5%**、0.20–0.35 **7.8%**、p<0.20 **0.6%**。Android 明显比 iPhone 难。

Android golden：

| 文件 | rows | 屏摄 | 普通 | 截图 |
|---|---:|---:|---:|---:|
| `android_golden_test.csv` | 328 | 26 | 254 | 48 |
| `android_golden_calibration.csv` | 126 | 7 | 104 | 15 |
| `android_train_labeled.csv` | 398 | 43 | 260 | 95 |

v2.1 微调对比（App 预处理，阈值 0.65）：

| 模型 | iPhone test | Android test |
|---|---|---|
| v2（当前 App） | **94.6% / 73.9%** | 75.0% / 69.2% |
| v2.1（Android 高权重） | 91.1% / 64.8% | **86.4% / 73.1%** |
| v2.1b（平衡权重） | 90.6% / 88.0% | 59.0% / 88.5% |

没有任何单模型同时在 iPhone/Android 上达到 95%/70%；Android test 只有 26 个
屏摄正样本，指标只作方向性参考。当前结论：**按平台选模型**（iPhone 用 v2，
Android 用 v2.1）比强行单模型更合理；或者保留 v2，继续补 Android 正样本/多用户数据。
App 仍未自动勾选。

## TinyCLIP 过渡模型（M2，历史）

M2 曾用 TinyCLIP ViT-40M/32（MIT）作为商用过渡模型，40.8MB 动态量化 TFLite。
在 Commons 小样本上确定组 97.4% / 召回 77.1%，但真实相册高分精度只有 59.9%、
低分仍有 8.4% 屏摄。App 已换成 v2；TinyCLIP 仅保留用于回归对比。

- 产物：`tflite_noerf_sim_dr/…dynamic_range_quant.tflite`（40.8MB）
- Erf→tanh GELU 脚本：`convert/replace_erf_gelu.py`
- 评测：`eval/evaluate_tinyclip.py`

## MobileCLIP（仅内部研究，不随 App 发布）

旧的 MobileCLIP-S0 管线仍保留用于历史回归：

```bash
.venv/Scripts/python.exe convert/export_onnx.py
.venv/Scripts/python.exe convert/export_text_embeddings.py
.venv/Scripts/onnx2tf.exe -i models/mobileclip_s0_image.onnx -o tflite_out
```

Apple 许可明确禁止商业分发；不要把它的权重或派生模型放进上架包。

## 数据与评测脚本

| 脚本 | 作用 |
|---|---|
| `eval/fetch_sample_set.py` | 拉 Commons 小样本做 sanity check |
| `eval/evaluate.py` | MobileCLIP 回归评测 |
| `eval/evaluate_tinyclip.py` | TinyCLIP 回归评测 |
| `eval/calibrate.py` | 阈值/温度扫描（MobileCLIP） |
| `data/build_labeled_sets.py` | 合并 1,499 条标签、生成 golden v1 |
| `data/build_mid_review.py` | 生成 0.20–0.90 中分段复核清单 |

正式 golden 需要扩充到 Android + 多用户；当前 v1 是 iPhone 单用户分层集。
