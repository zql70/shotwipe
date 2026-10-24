/// 识别管线的共享常量：类别、来源、置信度阈值、模型版本。
///
/// 阈值：≥0.55 确定（默认勾选）、0.35–0.55 疑似（默认不勾）、<0.35 忽略，
/// 由 TinyCLIP 40M/32 在本地样本集上校准。模型或 prompt 变更时递增
/// [modelVersion]，扫描会自动重跑模型。
class RecognitionConfig {
  RecognitionConfig._();

  static const modelVersion = 'mobilenetv4_v2_v1';
  static const metadataVersion = 'metadata';

  static const categoryScreenshot = 'screenshot';
  static const categoryScreenPhoto = 'screen_photo';
  static const categoryOther = 'other';
  static const categoryUnknown = 'unknown';

  static const sourceMetadata = 'metadata';
  static const sourceModel = 'model';

  static const stateScanned = 'scanned';
  static const stateKept = 'kept';
  static const stateDismissed = 'dismissed';
  static const stateDeleted = 'deleted';

  // 端上模型只把 screen_photo 结果展示给用户；模型判出的 screenshot 不可靠
  // （会把山景/普通照片当成截图），截图 Tab 只信系统元数据。
  // 当前模型：MobileNetV4-Conv-S 三分类（自训 v2），224 输入，动态量化 TFLite；
  // 模型只输出候选，App 不自动勾选屏摄图。阈值在 golden v1 calibration 上校准。
  static const confirmedThreshold = 0.65;
  static const suspiciousThreshold = 0.35;
  static const inputSize = 224;

  static const modelAsset = 'assets/models/v2_screen_classifier.tflite';
  // 仅模型文件变化时递增；prompt 变化用 modelVersion 控制重扫。
  static const modelAssetVersion = 'mobilenetv4_v2_v1';

  /// 结果为建议删除的类别（截图为元数据命中，屏摄为模型命中）。
  static bool isActionableCategory(String category) =>
      category == categoryScreenshot || category == categoryScreenPhoto;

  /// 模型结果按置信度分级；元数据截图始终是「确定」。
  static bool isConfirmed({
    required String source,
    required double confidence,
  }) => source == sourceMetadata || confidence >= confirmedThreshold;

  static bool isSuspicious(double confidence) =>
      confidence >= suspiciousThreshold && confidence < confirmedThreshold;
}
