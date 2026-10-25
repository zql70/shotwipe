import 'package:shotwipe/core/recognition_config.dart';
import 'package:shotwipe/data/app_database.dart';

/// 测试用的扫描结果行，其余列用不影响判断的默认值。
ScannedAsset buildRow({
  required String id,
  String category = RecognitionConfig.categoryOther,
  double confidence = 0.9,
  String source = RecognitionConfig.sourceModel,
  String state = RecognitionConfig.stateScanned,
  String modelVersion = RecognitionConfig.modelVersion,
}) {
  return ScannedAsset(
    platformId: id,
    takenAtMs: 0,
    category: category,
    confidence: confidence,
    source: source,
    state: state,
    modelVersion: modelVersion,
    scanVersion: 2,
    updatedAtMs: 0,
  );
}
