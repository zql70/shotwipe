# ShotWipe · 屏净

清理相册里的截图与屏摄图（拍屏幕的照片）。**全端上识别、无上传、无账号**，照片不离开手机。

![版本](https://img.shields.io/badge/release-v1.0.0-8BFFE0) ![平台](https://img.shields.io/badge/platform-Android%20%7C%20iOS%20(待构建)-10263C)

## 功能

- **截图清理**：系统元数据识别（iOS `photoScreenshot` / Android 截图目录），零误判
- **屏摄图识别**：自训 MobileNetV4 三分类模型（2.7MB TFLite，CPU 推理），
  分「模型候选 ≥0.65」「疑似 0.35–0.65」两个层级，默认不勾选
- **安全删除**：只弹系统确认框，进系统「最近删除」；勾选与删除均按 Tab 作用域
- **增量扫描**：中断/被杀后重开自动续扫（每 50 张落盘），只重跑新增照片

## 仓库结构

| 目录 | 内容 | 说明 |
|---|---|---|
| `app/` | Flutter 应用（Android/iOS） | [app/README.md](app/README.md) |
| `ml/` | 数据管线：合成数据、蒸馏训练、golden 评测、本地复核工具 | [ml/README.md](ml/README.md) |
| `技术方案.md` | 产品定位、技术选型、里程碑与已拍板决策 | — |

## 快速开始

```
cd app
flutter pub get
flutter run                    # 真机调试
flutter build apk --release --split-per-abi   # 分架构打包
```

模型已内置（`app/assets/models/v2_screen_classifier.tflite`），无需训练即可构建运行；
重新训练/评测见 `ml/README.md`。

## 下载

见 [Releases](https://github.com/zql70/shotwipe/releases)（私有仓库，需登录）。
真机选 `app-arm64-v8a-release.apk`。

## 现状与边界

- Android（minSdk 30）已真机验证：小米 15 / Android 16，9.5k 张全库扫描约 20 分钟
- 模型指标与数据集说明见 `ml/README.md`（屏摄精度 72.9% 端上实测，未达自动勾选标准，
  因此模型结果一律由用户确认）
- iOS 资源已就位，构建验证需 macOS 环境
- 隐私立场：不收集任何数据，App Store/Play 可填「不收集」
