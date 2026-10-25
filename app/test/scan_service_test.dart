import 'dart:typed_data';

import 'package:drift/drift.dart' show Value;
import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:photo_manager/photo_manager.dart';
import 'package:shotwipe/core/recognition_config.dart';
import 'package:shotwipe/data/app_database.dart';
import 'package:shotwipe/data/media_repository.dart';
import 'package:shotwipe/domain/scan_service.dart';
import 'package:shotwipe/inference/screen_photo_classifier.dart';

/// 直接构造 AssetEntity（扫描只用 id/createDateTime/width/height/relativePath，
/// 这些字段均可通过构造函数赋值，不触发平台通道）。
AssetEntity fakeAsset(String id, {String relativePath = '/DCIM/Camera/'}) =>
    AssetEntity(
      id: id,
      typeInt: 1,
      width: 100,
      height: 100,
      createDateSecond: 1700000000,
      relativePath: relativePath,
    );

class FakeMediaRepository extends MediaRepository {
  FakeMediaRepository(this.assets, {this.onThumbnail});

  final List<AssetEntity> assets;
  final void Function(String id)? onThumbnail;

  @override
  Future<int> allImageCount() async => assets.length;

  @override
  Stream<AssetEntity> allImages() async* {
    for (final asset in assets) {
      yield asset;
    }
  }

  @override
  bool isScreenshotMetadata(AssetEntity asset) =>
      (asset.relativePath ?? '').contains('Screenshots');

  /// 用首字节携带资产下标，供 FakeClassifier 区分图片。
  @override
  Future<Uint8List?> thumbnail(AssetEntity asset, {int size = 512}) async {
    onThumbnail?.call(asset.id);
    return Uint8List.fromList([assets.indexOf(asset)]);
  }
}

class FakeClassifier extends ScreenPhotoClassifier {
  FakeClassifier({this.failIndex = -1});

  final int failIndex;
  int calls = 0;
  String category = RecognitionConfig.categoryScreenPhoto;
  double confidence = 0.9;

  @override
  bool get isReady => true;

  @override
  Future<Classification> classify(Uint8List thumbnailBytes) async {
    calls++;
    final index = thumbnailBytes[0];
    if (index == failIndex) {
      throw ClassifierException('bad image');
    }
    return Classification(category: category, confidence: confidence);
  }
}

void main() {
  late AppDatabase db;

  setUp(() {
    db = AppDatabase(NativeDatabase.memory());
  });

  tearDown(() async {
    await db.close();
  });

  Future<Map<String, ScannedAsset>> rowsById() async {
    final rows = await db.allRows();
    return {for (final r in rows) r.platformId: r};
  }

  test('首扫：元数据截图直写、其余走模型、状态键落盘', () async {
    final repo = FakeMediaRepository([
      fakeAsset('shot', relativePath: '/Pictures/Screenshots/x.png'),
      fakeAsset('a'),
      fakeAsset('b'),
    ]);
    final classifier = FakeClassifier();
    final service = ScanService(repo, db, classifier);

    final summary = await service.scan();

    expect(summary.processed, 3);
    expect(summary.cancelled, isFalse);
    expect(summary.modelError, isNull);
    expect(classifier.calls, 2, reason: '元数据截图不走模型');

    final rows = await rowsById();
    expect(rows.length, 3);
    final shot = rows['shot']!;
    expect(shot.category, RecognitionConfig.categoryScreenshot);
    expect(shot.source, RecognitionConfig.sourceMetadata);
    expect(shot.confidence, 1.0);
    final a = rows['a']!;
    expect(a.category, RecognitionConfig.categoryScreenPhoto);
    expect(a.source, RecognitionConfig.sourceModel);
    expect(a.confidence, 0.9);
    expect(await db.getState('last_scan_ms'), isNotNull);
    expect(await db.getState('last_scan_total'), '3');
  });

  test('增量：二扫零推理、已有行保持不变', () async {
    final assets = [
      fakeAsset('shot', relativePath: '/Pictures/Screenshots/x.png'),
      fakeAsset('a'),
    ];
    final first = FakeClassifier();
    await ScanService(FakeMediaRepository(assets), db, first).scan();
    final rowsBefore = await rowsById();

    final second = FakeClassifier();
    final summary = await ScanService(
      FakeMediaRepository(assets),
      db,
      second,
    ).scan();

    expect(second.calls, 0, reason: '同模型版本的已分类资产应全部跳过');
    expect(summary.processed, 2);
    final rowsAfter = await rowsById();
    expect(rowsAfter.length, rowsBefore.length);
    expect(rowsAfter['a']!.updatedAtMs, rowsBefore['a']!.updatedAtMs);
  });

  test('模型版本升级：旧版本行重新推理', () async {
    await db.upsertAssets([
      ScannedAssetsCompanion.insert(
        platformId: 'a',
        takenAtMs: 0,
        state: RecognitionConfig.stateScanned,
        modelVersion: const Value('mobilenetv4_v1'),
        updatedAtMs: 1,
      ),
    ]);
    final classifier = FakeClassifier();

    await ScanService(
      FakeMediaRepository([fakeAsset('a')]),
      db,
      classifier,
    ).scan();

    expect(classifier.calls, 1);
    final row = (await rowsById())['a']!;
    expect(row.modelVersion, RecognitionConfig.modelVersion);
  });

  test('中途取消：已处理项落库、last_scan_ms 不写、可续扫', () async {
    late ScanService service;
    final repo = FakeMediaRepository(
      [
        fakeAsset('shot', relativePath: '/Pictures/Screenshots/x.png'),
        fakeAsset('a'),
        fakeAsset('b'),
      ],
      // 在处理 'a' 的缩略图时触发取消
      onThumbnail: (id) {
        if (id == 'a') service.cancel();
      },
    );
    final classifier = FakeClassifier();
    service = ScanService(repo, db, classifier);

    final summary = await service.scan();

    expect(summary.cancelled, isTrue);
    expect(await db.getState('last_scan_ms'), isNull,
        reason: '取消的扫描不应标记为完成');
    final rows = await rowsById();
    expect(rows.containsKey('shot'), isTrue);
    expect(rows.containsKey('a'), isTrue, reason: '取消前已处理的项应已落库');

    // 续扫：剩余资产补齐
    final resumed = await ScanService(
      FakeMediaRepository([
        fakeAsset('shot', relativePath: '/Pictures/Screenshots/x.png'),
        fakeAsset('a'),
        fakeAsset('b'),
      ]),
      db,
      FakeClassifier(),
    ).scan();
    expect(resumed.cancelled, isFalse);
    final after = await rowsById();
    expect(after.length, 3);
    expect(await db.getState('last_scan_ms'), isNotNull);
  });

  test('单张识别失败：记录 modelError，其余图片继续', () async {
    final repo = FakeMediaRepository([
      fakeAsset('shot', relativePath: '/Pictures/Screenshots/x.png'),
      fakeAsset('a'),
      fakeAsset('b'),
    ]);
    final classifier = FakeClassifier(failIndex: 1); // 'a' 失败

    final summary = await ScanService(repo, db, classifier).scan();

    expect(summary.modelError, isNotNull);
    expect(classifier.calls, 2, reason: '失败后不应禁用模型，b 仍要推理');
    final rows = await rowsById();
    expect(rows.containsKey('a'), isFalse, reason: '失败项不落库');
    expect(rows.containsKey('b'), isTrue);
  });

  test('图库消失的活跃行标记 deleted；用户已决策的行不动', () async {
    await db.upsertAssets([
      ScannedAssetsCompanion.insert(
        platformId: 'ghost',
        takenAtMs: 0,
        state: RecognitionConfig.stateScanned,
        updatedAtMs: 1,
      ),
      ScannedAssetsCompanion.insert(
        platformId: 'kept-row',
        takenAtMs: 0,
        state: RecognitionConfig.stateKept,
        updatedAtMs: 1,
      ),
    ]);

    await ScanService(
      FakeMediaRepository([fakeAsset('a')]),
      db,
      FakeClassifier()..category = RecognitionConfig.categoryOther,
    ).scan();

    final rows = await rowsById();
    expect(rows['ghost']!.state, RecognitionConfig.stateDeleted);
    expect(rows['kept-row']!.state, RecognitionConfig.stateKept);
  });
}
