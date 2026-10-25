import 'package:flutter_test/flutter_test.dart';
import 'package:shotwipe/core/recognition_config.dart';
import 'package:shotwipe/domain/scan_service.dart';

import 'helpers.dart';

void main() {
  group('needsModelInference 增量决策（断点续扫的基础）', () {
    test('新资产（无历史行）需要推理', () {
      expect(needsModelInference(null, RecognitionConfig.modelVersion), isTrue);
    });

    test('同版本已分类的行跳过（二扫零推理）', () {
      expect(
        needsModelInference(
          buildRow(id: 'a'),
          RecognitionConfig.modelVersion,
        ),
        isFalse,
      );
    });

    test('旧模型版本的行重新推理（模型升级触发重扫）', () {
      expect(
        needsModelInference(
          buildRow(id: 'a', modelVersion: 'mobilenetv4_v1'),
          RecognitionConfig.modelVersion,
        ),
        isTrue,
      );
    });

    test('类别未知的行重新推理（上次推理失败）', () {
      expect(
        needsModelInference(
          buildRow(id: 'a', category: RecognitionConfig.categoryUnknown),
          RecognitionConfig.modelVersion,
        ),
        isTrue,
      );
    });

    test('用户已决策的状态永不重跑：kept / dismissed / deleted', () {
      for (final state in [
        RecognitionConfig.stateKept,
        RecognitionConfig.stateDismissed,
        RecognitionConfig.stateDeleted,
      ]) {
        expect(
          needsModelInference(
            buildRow(id: 'a', state: state, modelVersion: 'ancient'),
            RecognitionConfig.modelVersion,
          ),
          isFalse,
          reason: 'state=$state 时即使模型版本过期也不应重跑',
        );
      }
    });
  });

  group('needsScreenshotWrite 元数据归位', () {
    test('新资产需要写', () {
      expect(needsScreenshotWrite(null), isTrue);
    });

    test('已是元数据截图行则跳过', () {
      expect(
        needsScreenshotWrite(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryScreenshot,
            source: RecognitionConfig.sourceMetadata,
          ),
        ),
        isFalse,
      );
    });

    test('旧行是模型结果时归位为元数据截图', () {
      expect(
        needsScreenshotWrite(
          buildRow(id: 'a', category: RecognitionConfig.categoryOther),
        ),
        isTrue,
      );
    });

    test('用户已决策的状态不覆盖', () {
      expect(
        needsScreenshotWrite(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryOther,
            state: RecognitionConfig.stateKept,
          ),
        ),
        isFalse,
      );
    });
  });
}
