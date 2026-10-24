import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';

import '../core/recognition_config.dart';

part 'app_database.g.dart';

/// 扫描到的资产。
/// M2 起同时保存截图元数据命中与模型分类结果，[confidence] 用于「确定/疑似」分组。
class ScannedAssets extends Table {
  TextColumn get platformId => text()();
  IntColumn get takenAtMs => integer()();
  IntColumn get width => integer().nullable()();
  IntColumn get height => integer().nullable()();
  TextColumn get category => text().withDefault(const Constant('screenshot'))();
  RealColumn get confidence => real().withDefault(const Constant(1.0))();
  TextColumn get source => text().withDefault(const Constant('metadata'))();
  TextColumn get state => text()(); // scanned | kept | dismissed | deleted
  TextColumn get modelVersion =>
      text().withDefault(const Constant(RecognitionConfig.metadataVersion))();
  IntColumn get scanVersion => integer().withDefault(const Constant(2))();
  IntColumn get updatedAtMs => integer()();

  @override
  Set<Column> get primaryKey => {platformId};
}

/// 扫描断点与配置（key-value）
class ScanState extends Table {
  TextColumn get key => text()();
  TextColumn get value => text()();

  @override
  Set<Column> get primaryKey => {key};
}

/// 用户对误判的纠正，本地留存并作为 v2 训练数据来源。
class Feedback extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get platformId => text()();
  TextColumn get originalCategory => text()();
  TextColumn get correctedLabel => text()();
  RealColumn get confidence => real()();
  TextColumn get modelVersion => text().withDefault(const Constant(''))();
  IntColumn get createdAtMs => integer()();

  @override
  List<String> get customConstraints => const [
    'UNIQUE(platform_id, original_category)',
  ];
}

@DriftDatabase(tables: [ScannedAssets, ScanState, Feedback])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(name: 'shotwipe'));

  @override
  int get schemaVersion => 2;

  @override
  MigrationStrategy get migration => MigrationStrategy(
    onCreate: (m) => m.createAll(),
    onUpgrade: (m, from, to) async {
      if (from < 2) {
        await m.addColumn(scannedAssets, scannedAssets.confidence);
        await m.addColumn(scannedAssets, scannedAssets.modelVersion);
        await m.createTable(feedback);
      }
    },
  );

  Future<void> upsertAssets(List<ScannedAssetsCompanion> rows) =>
      batch((b) => b.insertAllOnConflictUpdate(scannedAssets, rows));

  Future<void> setState(String key, String value) => into(
    scanState,
  ).insertOnConflictUpdate(ScanStateCompanion.insert(key: key, value: value));

  Future<String?> getState(String key) async {
    final row = await (select(
      scanState,
    )..where((t) => t.key.equals(key))).getSingleOrNull();
    return row?.value;
  }

  Future<List<ScannedAsset>> allRows() => select(scannedAssets).get();

  Future<List<ScannedAsset>> activeRows() => (select(
    scannedAssets,
  )..where((t) => t.state.equals(RecognitionConfig.stateScanned))).get();

  Future<void> markState(List<String> ids, String state) async {
    if (ids.isEmpty) return;
    await (update(scannedAssets)..where((t) => t.platformId.isIn(ids))).write(
      ScannedAssetsCompanion(
        state: Value(state),
        updatedAtMs: Value(DateTime.now().millisecondsSinceEpoch),
      ),
    );
  }

  /// 图库中已不存在的资产：仅清理还在推荐列表里的，保留用户已处理的状态。
  Future<void> markMissing(Set<String> seenIds) async {
    final active = await activeRows();
    final missing = active
        .map((r) => r.platformId)
        .where((id) => !seenIds.contains(id))
        .toList();
    if (missing.isEmpty) return;
    await markState(missing, RecognitionConfig.stateDeleted);
  }

  /// 用户纠错：写入 feedback 并把资产移出推荐列表。
  Future<void> recordCorrection({
    required ScannedAsset row,
    required String correctedLabel,
  }) async {
    await transaction(() async {
      await into(feedback).insert(
        FeedbackCompanion.insert(
          platformId: row.platformId,
          originalCategory: row.category,
          correctedLabel: correctedLabel,
          confidence: row.confidence,
          modelVersion: Value(row.modelVersion),
          createdAtMs: DateTime.now().millisecondsSinceEpoch,
        ),
        mode: InsertMode.insertOrReplace,
      );
      await markState([row.platformId], RecognitionConfig.stateDismissed);
    });
  }
}
