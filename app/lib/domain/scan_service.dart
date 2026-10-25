import 'package:drift/drift.dart';

import '../core/recognition_config.dart';
import '../data/app_database.dart';
import '../data/media_repository.dart';
import '../inference/screen_photo_classifier.dart';

class ScanProgress {
  const ScanProgress({
    required this.phase,
    required this.processed,
    required this.total,
    required this.classified,
  });

  /// collecting | scanning | model
  final String phase;
  final int processed;
  final int total;
  final int classified;
}

class ScanSummary {
  const ScanSummary({
    required this.processed,
    required this.screenshots,
    required this.screenPhotos,
    required this.others,
    required this.modelInferences,
    required this.cancelled,
    this.modelError,
  });

  final int processed;
  final int screenshots;
  final int screenPhotos;
  final int others;
  final int modelInferences;
  final bool cancelled;
  final String? modelError;

  bool get hasModelError => modelError != null;
}

/// 元数据截图是否需要（重）写库：新资产，或 scanned 状态但还不是元数据截图行
/// （例如旧模型版本把它写成了别的类别，本次应归位）。
/// kept/dismissed/deleted 等用户已决策的状态不动。
bool needsScreenshotWrite(ScannedAsset? row) {
  if (row == null) return true;
  return row.state == RecognitionConfig.stateScanned &&
      (row.category != RecognitionConfig.categoryScreenshot ||
          row.source != RecognitionConfig.sourceMetadata);
}

/// 该资产是否需要跑模型：新资产；或 scanned 状态下模型版本过期 / 类别未知。
/// 用户已决策的状态（kept/dismissed/deleted）永不重跑，增量续扫即依赖此规则。
bool needsModelInference(ScannedAsset? row, String modelVersion) {
  if (row == null) return true;
  if (row.state != RecognitionConfig.stateScanned) return false;
  return row.modelVersion != modelVersion ||
      row.category == RecognitionConfig.categoryUnknown;
}

/// 扫描服务：一次遍历全图库。
///
/// 1. 系统元数据命中 → 截图（零成本、置信度 1.0）；
/// 2. 其余图片 → v2 MobileNetV4 三分类（屏摄图/普通/截图；
///    模型判的截图不可靠，仅入库不展示）；
/// 3. 已按当前模型版本分类过的资产直接跳过，实现增量扫描；
/// 4. 结果分批写库，中断/取消后可继续。
class ScanService {
  ScanService(this._repo, this._db, this._classifier);

  final MediaRepository _repo;
  final AppDatabase _db;
  final ScreenPhotoClassifier _classifier;

  bool _cancelled = false;
  bool _modelDisabled = false;

  static const _batchSize = 50;

  void cancel() => _cancelled = true;

  Future<ScanSummary> scan({void Function(ScanProgress)? onProgress}) async {
    _cancelled = false;
    _modelDisabled = false;

    onProgress?.call(
      const ScanProgress(
        phase: 'collecting',
        processed: 0,
        total: 0,
        classified: 0,
      ),
    );
    final existing = {
      for (final row in await _db.allRows()) row.platformId: row,
    };
    final total = await _repo.allImageCount();

    final seen = <String>{};
    var processed = 0;
    var screenshots = 0;
    var screenPhotos = 0;
    var others = 0;
    var modelInferences = 0;
    String? modelError;
    final batch = <ScannedAssetsCompanion>[];

    Future<void> flush() async {
      if (batch.isEmpty) return;
      await _db.upsertAssets(batch);
      batch.clear();
    }

    await for (final asset in _repo.allImages()) {
      if (_cancelled) break;
      seen.add(asset.id);
      processed++;
      final row = existing[asset.id];
      final nowMs = DateTime.now().millisecondsSinceEpoch;
      final metadataShot = _repo.isScreenshotMetadata(asset);

      if (metadataShot) {
        if (needsScreenshotWrite(row)) {
          batch.add(
            ScannedAssetsCompanion.insert(
              platformId: asset.id,
              takenAtMs: asset.createDateTime.millisecondsSinceEpoch,
              width: Value(asset.width),
              height: Value(asset.height),
              category: const Value(RecognitionConfig.categoryScreenshot),
              confidence: const Value(1.0),
              source: const Value(RecognitionConfig.sourceMetadata),
              state: RecognitionConfig.stateScanned,
              modelVersion: const Value(RecognitionConfig.metadataVersion),
              updatedAtMs: nowMs,
            ),
          );
          screenshots++;
        }
      } else {
        final needsInference = needsModelInference(
          row,
          RecognitionConfig.modelVersion,
        );
        if (needsInference && !_modelDisabled) {
          if (!_classifier.isReady) {
            onProgress?.call(
              ScanProgress(
                phase: 'model',
                processed: processed,
                total: total,
                classified: modelInferences,
              ),
            );
          }
          try {
            final bytes = await _repo.thumbnail(asset);
            if (bytes != null) {
              final result = await _classifier.classify(bytes);
              modelInferences++;
              switch (result.category) {
                case RecognitionConfig.categoryScreenshot:
                  screenshots++;
                case RecognitionConfig.categoryScreenPhoto:
                  screenPhotos++;
                default:
                  others++;
              }
              batch.add(
                ScannedAssetsCompanion.insert(
                  platformId: asset.id,
                  takenAtMs: asset.createDateTime.millisecondsSinceEpoch,
                  width: Value(asset.width),
                  height: Value(asset.height),
                  category: Value(result.category),
                  confidence: Value(result.confidence),
                  source: const Value(RecognitionConfig.sourceModel),
                  state: RecognitionConfig.stateScanned,
                  modelVersion: const Value(RecognitionConfig.modelVersion),
                  updatedAtMs: nowMs,
                ),
              );
            }
          } catch (e) {
            modelError ??= '$e';
            // 模型初始化失败时不再逐张重试；单张坏图只跳过该张。
            if (!_classifier.isReady) {
              _modelDisabled = true;
            }
          }
        }
      }

      if (batch.length >= _batchSize) {
        await flush();
      }
      if (processed % 5 == 0) {
        onProgress?.call(
          ScanProgress(
            phase: 'scanning',
            processed: processed,
            total: total,
            classified: modelInferences,
          ),
        );
      }
    }

    await flush();
    if (!_cancelled) {
      await _db.markMissing(seen);
      await _db.setState(
        'last_scan_ms',
        DateTime.now().millisecondsSinceEpoch.toString(),
      );
      await _db.setState('last_scan_total', processed.toString());
    }
    onProgress?.call(
      ScanProgress(
        phase: 'done',
        processed: processed,
        total: total,
        classified: modelInferences,
      ),
    );

    return ScanSummary(
      processed: processed,
      screenshots: screenshots,
      screenPhotos: screenPhotos,
      others: others,
      modelInferences: modelInferences,
      cancelled: _cancelled,
      modelError: modelError,
    );
  }
}
