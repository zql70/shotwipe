# ShotWipe · 屏净

本地化、隐私优先的双端（iOS + Android）相册清理工具：自动识别**截图**与**屏摄图**（拍摄电子屏幕的照片），按置信度分组，用户确认后批量删除。全部处理在本机完成，无账号、无上传。

- 技术方案：见仓库根目录 [技术方案.md](../技术方案.md)
- ML 模型管线与评测：[ml/README.md](../ml/README.md)
- 当前进度：**M2 + v2 模型完成（Android 模拟器端到端验证）**。M0/M1 已完成。
  iOS 代码路径已接好，但本机是 Windows，尚未在 macOS 上编译验证。

> **模型许可现状**
> App 现在内置的是**自训 MobileNetV4-Conv-S 三分类模型**（2.7MB TFLite）。
> 学生主干来自 timm 的 Apache-2.0 预训练权重；训练时用 SigLIP 2（Apache-2.0）
> 做离线特征蒸馏。App 不再分发 MobileCLIP（Apple 研究许可）或 TinyCLIP 权重。
> 训练数据来自用户自采相册 + 合成屏摄，上架前仍需完成数据和隐私合规审查。

## 技术栈

Flutter + photo_manager + drift + tflite_flutter（LiteRT）。

## 当前模型

- **MobileNetV4-Conv-S，2.5M 参数，3 分类**：截图 / 屏摄 / 其他。
- 输入 224×224，输出 3 个 logits；ImageNet 归一化烘焙进模型，App 只喂 0–1。
- 动态范围量化 TFLite：**2.7MB**，CPU 可跑；比 TinyCLIP 40M（40.8MB）小 15 倍。
- 训练：合成 8,000 张屏摄 + 3,000 张真实截图 + 2,000 弱负样本 +
  golden v1 训练 split（238 屏摄 / 422 硬负 / 138 截图）；SigLIP 2 特征蒸馏 +
  交叉熵，真实数据最后 fine-tune。
- 阈值：**模型候选 ≥0.65、疑似 0.35–0.65、低于 0.35 忽略**。

### golden v1 真实指标（用户 iPhone 相册，分层 500 test）

| 评测 | 精度 | 召回 | 说明 |
|---|---|---|---|
| PyTorch float，阈值 0.64 | **94.6%** | **74.6%** | 离 95/70 只差一点 |
| TFLite int8，阈值 0.65 | 92.9% | 73.2% | App 实际模型 |
| TFLite int8，阈值 0.70 | 96.1% | 69.7% | 更保守 |

**尚未正式达到 95%/70% 的自动勾选标准**，而且误差集中在会议投影幕、打印海报/
标牌、导视牌等标签边界模糊的样本上。因此 App 继续把模型结果当**候选**：
默认不勾选，只有系统元数据截图会自动勾选；「全选截图」只选元数据截图。

另外，在 Commons 的域外测试图库上，v2 只召回 8/15 张屏摄，低于 TinyCLIP 的
12/15。说明 v2 对当前用户的相册分布拟合较好，但跨用户/跨设备泛化还不够；
安卓相册和更多用户数据必须补进训练/golden。

## 实现要点

- **品牌色**：主色深海蓝 #10263C、点缀薄荷绿 #8BFFE0（图标/主题/启动页统一；
  生成脚本 `ml/convert/icon/gen_icons.js`，源 SVG 本地保存不入库）。

- **扫描**：一次遍历全图库（新→旧），分批写库。
  - 系统元数据命中 → 截图，置信度 1.0（iOS subtype / Android RELATIVE_PATH）。
  - 其余图片 → 512px 缩略图 → 后台 isolate 跑 MobileNetV4 → 三类概率。
  - 已按当前 `modelVersion` 分类过的资产直接跳过，实现增量扫描。
- **截图 Tab 只展示元数据命中**：模型判出的 screenshot 不可靠，结果只入库不展示。
- **无默认勾选**：扫描后不自动选中任何照片（含截图）；全选按钮和底部删除栏
  都只作用于当前 Tab（截图 / 屏摄图 / 疑似）。
- **点按/长按**：点按一律勾选或取消（薄荷绿圆底打勾角标）；长按查看大图，
  保留这张 / 不是X 点选高亮并显示说明，右侧「确认」生效（纠错写 `feedback`
  表并 `state=dismissed`，以后不再推荐）。
- **删除**：直接弹系统确认（App 内无二次确认）→ 完成页提示「最近删除/回收站」30 天；
  仅删除当前 Tab 的选中项。

## 目录

```
lib/
  core/recognition_config.dart   # 阈值、模型版本、资产路径
  inference/screen_photo_classifier.dart  # TFLite 后台 isolate + 3 分类
  data/                          # photo_manager 封装、drift v2 schema
  domain/                        # 扫描编排、保护规则
  ui/                            # 首页 / 结果页（截图·屏摄·疑似三 Tab）
assets/models/v2_screen_classifier.tflite  # 2.7MB 生成物
```

数据库 `scanned_assets` 含 `confidence`、`model_version`；`feedback` 表存纠错。
schemaVersion=2，旧 M1 数据库自动迁移。

## 开发

```bash
cd app
flutter pub get
dart run build_runner build     # 改了 drift 表后
flutter run
```

构建需要把 `JAVA_HOME` 指向 Android Studio 的 JBR：

```bash
export JAVA_HOME="/c/Program Files/Android/Android Studio/jbr"
export PATH="$JAVA_HOME/bin:$PATH"
flutter build apk --debug
```

`android/gradle.properties` 里的代理默认注释掉了：本机实测 `dl.google.com`
直连可用，走 7890 代理反而 TLS 握手失败；只有直连失败时才打开。

## 训练与导出

完整流程见 [ml/README.md](../ml/README.md)。核心脚本：

```bash
cd ml
.venv/Scripts/python.exe train/synthetic_screens.py --root "<相机胶卷>" --count 8000
.venv/Scripts/python.exe train/build_manifest.py --root "<相机胶卷>"
.venv-gpu/Scripts/python.exe train/teacher_embed.py
.venv-gpu/Scripts/python.exe train/train_student.py --epochs 6 --finetune-epochs 3
.venv/Scripts/python.exe train/export_v2.py
.venv/Scripts/onnx2tf.exe -i models/v2_screen_classifier.onnx \
  -o tflite_v2_dr -tb tf_converter -odrqt
```

## 端到端验证（Android）

1. 安装 debug APK，授予 `READ_MEDIA_IMAGES` 权限。
2. 往 `/sdcard/Pictures/Screenshots/` 推截图（走元数据），
   往 `/sdcard/DCIM/Camera/` 推屏摄图/普通照片（走模型）。
3. 对每个文件广播 `android.intent.action.MEDIA_SCANNER_SCAN_FILE` 触发入库。
4. App 内扫描 → 结果页三 Tab（截图/屏摄/疑似，右上角全选按 Tab 作用）→ 勾选删除/长按纠错。
5. 再次扫描应在数秒内完成（增量跳过已分类资产）。

## 已知限制

- v2 在 golden v1 上 92.9%/73.2%（int8，0.65），尚未达到自动勾选标准；
  投影幕/打印牌等边界样本标签有歧义，需一轮标签规则和清理。
- 域外/跨用户泛化不足；Android 数据已标注并微调出 v2.1（Android test 86.4%/73.1%，
  0.65），但单模型会让 iPhone 掉到 91.1%/64.8%；目前 App 仍用 v2，正在评估
  “按平台选模型”（iPhone v2 / Android v2.1）。
- 模型截图兜底暂不展示；截图 Tab 仍只信系统元数据。
- iOS 尚未在真机/模拟器编译；CoreML 加速后置。
- 正式产品 golden 仍需扩充到 Android + 多用户，当前 v1 是 iPhone 单用户分层集。
