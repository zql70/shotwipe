import 'package:flutter_test/flutter_test.dart';
import 'package:shotwipe/core/recognition_config.dart';
import 'package:shotwipe/domain/results_grouper.dart';

import 'helpers.dart';

void main() {
  group('resultBucket 三个 Tab 的分拣', () {
    test('元数据截图 → 截图 Tab', () {
      final bucket = resultBucket(
        buildRow(
          id: 'a',
          category: RecognitionConfig.categoryScreenshot,
          source: RecognitionConfig.sourceMetadata,
        ),
      );
      expect(bucket, ResultBucket.screenshot);
    });

    test('模型屏摄 ≥0.65 → 屏摄图 Tab（候选）', () {
      expect(
        resultBucket(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryScreenPhoto,
            confidence: 0.65,
          ),
        ),
        ResultBucket.candidate,
      );
      expect(
        resultBucket(
          buildRow(
            id: 'b',
            category: RecognitionConfig.categoryScreenPhoto,
            confidence: 0.99,
          ),
        ),
        ResultBucket.candidate,
      );
    });

    test('模型屏摄 0.35–0.6499 → 疑似 Tab', () {
      expect(
        resultBucket(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryScreenPhoto,
            confidence: 0.6499,
          ),
        ),
        ResultBucket.suspect,
      );
      expect(
        resultBucket(
          buildRow(
            id: 'b',
            category: RecognitionConfig.categoryScreenPhoto,
            confidence: 0.35,
          ),
        ),
        ResultBucket.suspect,
      );
    });

    test('模型屏摄 <0.35 不展示', () {
      expect(
        resultBucket(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryScreenPhoto,
            confidence: 0.3499,
          ),
        ),
        ResultBucket.hidden,
      );
    });

    test('模型判出的截图不可信，不展示', () {
      expect(
        resultBucket(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryScreenshot,
            source: RecognitionConfig.sourceModel,
            confidence: 0.99,
          ),
        ),
        ResultBucket.hidden,
      );
    });

    test('元数据来源的屏摄类别不展示（不存在该组合，防御）', () {
      expect(
        resultBucket(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryScreenPhoto,
            source: RecognitionConfig.sourceMetadata,
          ),
        ),
        ResultBucket.hidden,
      );
    });

    test('普通照片与未知类别不展示', () {
      expect(
        resultBucket(buildRow(id: 'a', category: RecognitionConfig.categoryOther)),
        ResultBucket.hidden,
      );
      expect(
        resultBucket(
          buildRow(id: 'b', category: RecognitionConfig.categoryUnknown),
        ),
        ResultBucket.hidden,
      );
    });

    test('kept/dismissed 状态的行不进入结果页（上游 activeRows 已过滤，防御）', () {
      expect(
        resultBucket(
          buildRow(
            id: 'a',
            category: RecognitionConfig.categoryScreenshot,
            source: RecognitionConfig.sourceMetadata,
            state: RecognitionConfig.stateKept,
          ),
        ),
        // 分桶只看类别/来源/置信度；状态过滤由 activeRows 负责，
        // 此用例固化「分桶本身不做状态判断」的契约。
        ResultBucket.screenshot,
      );
    });
  });
}
