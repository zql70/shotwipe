import 'package:photo_manager/photo_manager.dart';

import '../core/recognition_config.dart';
import '../data/app_database.dart';

/// 保护规则（技术方案 §6）：用户保留过的、收藏的、最近 7 天的截图不自动勾选。
/// 模型结果（屏摄图候选）一律不自动勾选，必须人工确认；只有系统元数据截图
/// 通过保护规则后才会默认选中。
class ProtectRules {
  ProtectRules._();

  static const recentWindowDays = 7;

  static bool shouldAutoSelect(
    ScannedAsset row,
    AssetEntity? entity,
    DateTime now,
  ) {
    if (row.state != 'scanned') return false;
    if (row.source != RecognitionConfig.sourceMetadata) return false;
    if (entity != null && entity.isFavorite) return false;
    final taken = DateTime.fromMillisecondsSinceEpoch(row.takenAtMs);
    if (now.difference(taken).inDays < recentWindowDays) return false;
    return true;
  }
}
