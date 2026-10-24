import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:photo_manager/photo_manager.dart';

/// photo_manager 封装。
///
/// Layer 0（截图元数据）：
///  - iOS 用 PHAssetMediaSubtype 位掩码（photoScreenshot = 4）；
///  - Android 用相册目录名白名单 + MediaStore RELATIVE_PATH 兜底。
/// Layer 2（屏摄图）：调用方对非元数据命中的图片取缩略图跑模型。
class MediaRepository {
  MediaRepository();

  static const androidAlbumNames = {'Screenshots', 'Screenshot', '截屏', '截图'};
  static const iosScreenshotSubtypeBit = 4;
  static const _pageSize = 500;

  Future<bool> ensurePermission() async {
    final state = await PhotoManager.requestPermissionExtend();
    return state.hasAccess;
  }

  Future<AssetEntity?> loadAsset(String id) => AssetEntity.fromId(id);

  /// 图库中所有图片数量（用于进度）。
  Future<int> allImageCount() async {
    final path = await _allImagesPath();
    return path?.assetCountAsync ?? 0;
  }

  /// 全部图片，按拍摄时间倒序分页枚举。
  Stream<AssetEntity> allImages() async* {
    final path = await _allImagesPath();
    if (path == null) return;
    yield* _iterate(path);
  }

  /// 该资产是否能由系统元数据直接判定为截图。
  ///
  /// iOS 读 PHAssetMediaSubtype；Android 读 MediaStore RELATIVE_PATH（minSdk 30
  /// 上必定可用），避免为截图相册再完整枚举一遍图库。
  bool isScreenshotMetadata(AssetEntity asset) {
    if (Platform.isIOS) {
      return (asset.subtype & iosScreenshotSubtypeBit) != 0;
    }
    final relative = asset.relativePath;
    if (relative == null) return false;
    return relative
        .split('/')
        .where((segment) => segment.isNotEmpty)
        .any((segment) => androidAlbumNames.contains(segment));
  }

  /// 512px 缩略图，供模型推理（isolate 内中心裁剪并缩放到 224）。失败返回 null。
  Future<Uint8List?> thumbnail(AssetEntity asset, {int size = 512}) async {
    try {
      return await asset.thumbnailDataWithSize(
        ThumbnailSize(size, size),
        quality: 90,
      );
    } catch (_) {
      return null;
    }
  }

  /// 批量删除（触发系统确认弹窗，返回成功删除的 id 列表）。
  Future<List<String>> delete(List<AssetEntity> assets) =>
      PhotoManager.editor.deleteWithIds(assets.map((a) => a.id).toList());

  static final _newestFirst = FilterOptionGroup(
    orders: [const OrderOption(type: OrderOptionType.createDate)],
  );

  Future<AssetPathEntity?> _allImagesPath() async {
    final paths = await PhotoManager.getAssetPathList(
      type: RequestType.image,
      onlyAll: true,
      filterOption: _newestFirst,
    );
    return paths.isEmpty ? null : paths.first;
  }

  Stream<AssetEntity> _iterate(AssetPathEntity path) async* {
    final count = await path.assetCountAsync;
    for (var start = 0; start < count; start += _pageSize) {
      final end = math.min(start + _pageSize, count);
      final page = await path.getAssetListRange(start: start, end: end);
      if (page.isEmpty) return;
      for (final asset in page) {
        yield asset;
      }
    }
  }
}
