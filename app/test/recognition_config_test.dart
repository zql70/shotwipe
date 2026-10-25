import 'package:flutter_test/flutter_test.dart';
import 'package:shotwipe/core/recognition_config.dart';

void main() {
  group('isConfirmed 分级边界', () {
    test('元数据来源恒为确定（即使置信度为 0）', () {
      expect(
        RecognitionConfig.isConfirmed(
          source: RecognitionConfig.sourceMetadata,
          confidence: 0,
        ),
        isTrue,
      );
    });

    test('模型结果 ≥0.65 为确定', () {
      expect(
        RecognitionConfig.isConfirmed(
          source: RecognitionConfig.sourceModel,
          confidence: RecognitionConfig.confirmedThreshold,
        ),
        isTrue,
      );
      expect(
        RecognitionConfig.isConfirmed(
          source: RecognitionConfig.sourceModel,
          confidence: 0.99,
        ),
        isTrue,
      );
    });

    test('模型结果 <0.65 不为确定（疑似层）', () {
      expect(
        RecognitionConfig.isConfirmed(
          source: RecognitionConfig.sourceModel,
          confidence: 0.6499,
        ),
        isFalse,
      );
      expect(
        RecognitionConfig.isConfirmed(
          source: RecognitionConfig.sourceModel,
          confidence: RecognitionConfig.suspiciousThreshold,
        ),
        isFalse,
      );
    });
  });

  group('isActionableCategory', () {
    test('截图与屏摄图进入结果页', () {
      expect(
        RecognitionConfig.isActionableCategory(
          RecognitionConfig.categoryScreenshot,
        ),
        isTrue,
      );
      expect(
        RecognitionConfig.isActionableCategory(
          RecognitionConfig.categoryScreenPhoto,
        ),
        isTrue,
      );
    });

    test('普通/未知不进入结果页', () {
      expect(
        RecognitionConfig.isActionableCategory(RecognitionConfig.categoryOther),
        isFalse,
      );
      expect(
        RecognitionConfig.isActionableCategory(
          RecognitionConfig.categoryUnknown,
        ),
        isFalse,
      );
    });
  });
}
