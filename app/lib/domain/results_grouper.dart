import '../core/recognition_config.dart';
import '../data/app_database.dart';

/// 结果页 Tab 的分桶结果。
enum ResultBucket {
  /// 截图 Tab：系统元数据命中的截图。
  screenshot,

  /// 屏摄图 Tab：模型候选（置信度 ≥0.65）。
  candidate,

  /// 疑似 Tab：模型屏摄结果 0.35–0.65。
  suspect,

  /// 不展示。
  hidden,
}

/// 把一行扫描结果分拣到结果页的 Tab。
///
/// 规则（与技术方案 §3/§7 一致）：
/// - 模型判出的 screenshot 不可信（实测会把山景当截图），不展示；
/// - 屏摄结果只认模型来源，置信度 <0.35 不展示；
/// - 元数据截图恒为「确定」；模型结果 ≥0.65 为候选，0.35–0.65 为疑似。
ResultBucket resultBucket(ScannedAsset row) {
  if (!RecognitionConfig.isActionableCategory(row.category)) {
    return ResultBucket.hidden;
  }
  if (row.category == RecognitionConfig.categoryScreenshot &&
      row.source != RecognitionConfig.sourceMetadata) {
    return ResultBucket.hidden;
  }
  if (row.category == RecognitionConfig.categoryScreenPhoto &&
      row.source != RecognitionConfig.sourceModel) {
    return ResultBucket.hidden;
  }
  if (row.source != RecognitionConfig.sourceMetadata &&
      row.confidence < RecognitionConfig.suspiciousThreshold) {
    return ResultBucket.hidden;
  }
  if (row.category == RecognitionConfig.categoryScreenshot) {
    return ResultBucket.screenshot;
  }
  return RecognitionConfig.isConfirmed(
        source: row.source,
        confidence: row.confidence,
      )
      ? ResultBucket.candidate
      : ResultBucket.suspect;
}
