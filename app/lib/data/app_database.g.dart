// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'app_database.dart';

// ignore_for_file: type=lint
class $ScannedAssetsTable extends ScannedAssets
    with TableInfo<$ScannedAssetsTable, ScannedAsset> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ScannedAssetsTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _platformIdMeta = const VerificationMeta(
    'platformId',
  );
  @override
  late final GeneratedColumn<String> platformId = GeneratedColumn<String>(
    'platform_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _takenAtMsMeta = const VerificationMeta(
    'takenAtMs',
  );
  @override
  late final GeneratedColumn<int> takenAtMs = GeneratedColumn<int>(
    'taken_at_ms',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _widthMeta = const VerificationMeta('width');
  @override
  late final GeneratedColumn<int> width = GeneratedColumn<int>(
    'width',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _heightMeta = const VerificationMeta('height');
  @override
  late final GeneratedColumn<int> height = GeneratedColumn<int>(
    'height',
    aliasedName,
    true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
  );
  static const VerificationMeta _categoryMeta = const VerificationMeta(
    'category',
  );
  @override
  late final GeneratedColumn<String> category = GeneratedColumn<String>(
    'category',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('screenshot'),
  );
  static const VerificationMeta _confidenceMeta = const VerificationMeta(
    'confidence',
  );
  @override
  late final GeneratedColumn<double> confidence = GeneratedColumn<double>(
    'confidence',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: false,
    defaultValue: const Constant(1.0),
  );
  static const VerificationMeta _sourceMeta = const VerificationMeta('source');
  @override
  late final GeneratedColumn<String> source = GeneratedColumn<String>(
    'source',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant('metadata'),
  );
  static const VerificationMeta _stateMeta = const VerificationMeta('state');
  @override
  late final GeneratedColumn<String> state = GeneratedColumn<String>(
    'state',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _modelVersionMeta = const VerificationMeta(
    'modelVersion',
  );
  @override
  late final GeneratedColumn<String> modelVersion = GeneratedColumn<String>(
    'model_version',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant(RecognitionConfig.metadataVersion),
  );
  static const VerificationMeta _scanVersionMeta = const VerificationMeta(
    'scanVersion',
  );
  @override
  late final GeneratedColumn<int> scanVersion = GeneratedColumn<int>(
    'scan_version',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultValue: const Constant(2),
  );
  static const VerificationMeta _updatedAtMsMeta = const VerificationMeta(
    'updatedAtMs',
  );
  @override
  late final GeneratedColumn<int> updatedAtMs = GeneratedColumn<int>(
    'updated_at_ms',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    platformId,
    takenAtMs,
    width,
    height,
    category,
    confidence,
    source,
    state,
    modelVersion,
    scanVersion,
    updatedAtMs,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'scanned_assets';
  @override
  VerificationContext validateIntegrity(
    Insertable<ScannedAsset> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('platform_id')) {
      context.handle(
        _platformIdMeta,
        platformId.isAcceptableOrUnknown(data['platform_id']!, _platformIdMeta),
      );
    } else if (isInserting) {
      context.missing(_platformIdMeta);
    }
    if (data.containsKey('taken_at_ms')) {
      context.handle(
        _takenAtMsMeta,
        takenAtMs.isAcceptableOrUnknown(data['taken_at_ms']!, _takenAtMsMeta),
      );
    } else if (isInserting) {
      context.missing(_takenAtMsMeta);
    }
    if (data.containsKey('width')) {
      context.handle(
        _widthMeta,
        width.isAcceptableOrUnknown(data['width']!, _widthMeta),
      );
    }
    if (data.containsKey('height')) {
      context.handle(
        _heightMeta,
        height.isAcceptableOrUnknown(data['height']!, _heightMeta),
      );
    }
    if (data.containsKey('category')) {
      context.handle(
        _categoryMeta,
        category.isAcceptableOrUnknown(data['category']!, _categoryMeta),
      );
    }
    if (data.containsKey('confidence')) {
      context.handle(
        _confidenceMeta,
        confidence.isAcceptableOrUnknown(data['confidence']!, _confidenceMeta),
      );
    }
    if (data.containsKey('source')) {
      context.handle(
        _sourceMeta,
        source.isAcceptableOrUnknown(data['source']!, _sourceMeta),
      );
    }
    if (data.containsKey('state')) {
      context.handle(
        _stateMeta,
        state.isAcceptableOrUnknown(data['state']!, _stateMeta),
      );
    } else if (isInserting) {
      context.missing(_stateMeta);
    }
    if (data.containsKey('model_version')) {
      context.handle(
        _modelVersionMeta,
        modelVersion.isAcceptableOrUnknown(
          data['model_version']!,
          _modelVersionMeta,
        ),
      );
    }
    if (data.containsKey('scan_version')) {
      context.handle(
        _scanVersionMeta,
        scanVersion.isAcceptableOrUnknown(
          data['scan_version']!,
          _scanVersionMeta,
        ),
      );
    }
    if (data.containsKey('updated_at_ms')) {
      context.handle(
        _updatedAtMsMeta,
        updatedAtMs.isAcceptableOrUnknown(
          data['updated_at_ms']!,
          _updatedAtMsMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_updatedAtMsMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {platformId};
  @override
  ScannedAsset map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ScannedAsset(
      platformId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}platform_id'],
      )!,
      takenAtMs: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}taken_at_ms'],
      )!,
      width: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}width'],
      ),
      height: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}height'],
      ),
      category: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}category'],
      )!,
      confidence: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}confidence'],
      )!,
      source: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}source'],
      )!,
      state: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}state'],
      )!,
      modelVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}model_version'],
      )!,
      scanVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}scan_version'],
      )!,
      updatedAtMs: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}updated_at_ms'],
      )!,
    );
  }

  @override
  $ScannedAssetsTable createAlias(String alias) {
    return $ScannedAssetsTable(attachedDatabase, alias);
  }
}

class ScannedAsset extends DataClass implements Insertable<ScannedAsset> {
  final String platformId;
  final int takenAtMs;
  final int? width;
  final int? height;
  final String category;
  final double confidence;
  final String source;
  final String state;
  final String modelVersion;
  final int scanVersion;
  final int updatedAtMs;
  const ScannedAsset({
    required this.platformId,
    required this.takenAtMs,
    this.width,
    this.height,
    required this.category,
    required this.confidence,
    required this.source,
    required this.state,
    required this.modelVersion,
    required this.scanVersion,
    required this.updatedAtMs,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['platform_id'] = Variable<String>(platformId);
    map['taken_at_ms'] = Variable<int>(takenAtMs);
    if (!nullToAbsent || width != null) {
      map['width'] = Variable<int>(width);
    }
    if (!nullToAbsent || height != null) {
      map['height'] = Variable<int>(height);
    }
    map['category'] = Variable<String>(category);
    map['confidence'] = Variable<double>(confidence);
    map['source'] = Variable<String>(source);
    map['state'] = Variable<String>(state);
    map['model_version'] = Variable<String>(modelVersion);
    map['scan_version'] = Variable<int>(scanVersion);
    map['updated_at_ms'] = Variable<int>(updatedAtMs);
    return map;
  }

  ScannedAssetsCompanion toCompanion(bool nullToAbsent) {
    return ScannedAssetsCompanion(
      platformId: Value(platformId),
      takenAtMs: Value(takenAtMs),
      width: width == null && nullToAbsent
          ? const Value.absent()
          : Value(width),
      height: height == null && nullToAbsent
          ? const Value.absent()
          : Value(height),
      category: Value(category),
      confidence: Value(confidence),
      source: Value(source),
      state: Value(state),
      modelVersion: Value(modelVersion),
      scanVersion: Value(scanVersion),
      updatedAtMs: Value(updatedAtMs),
    );
  }

  factory ScannedAsset.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ScannedAsset(
      platformId: serializer.fromJson<String>(json['platformId']),
      takenAtMs: serializer.fromJson<int>(json['takenAtMs']),
      width: serializer.fromJson<int?>(json['width']),
      height: serializer.fromJson<int?>(json['height']),
      category: serializer.fromJson<String>(json['category']),
      confidence: serializer.fromJson<double>(json['confidence']),
      source: serializer.fromJson<String>(json['source']),
      state: serializer.fromJson<String>(json['state']),
      modelVersion: serializer.fromJson<String>(json['modelVersion']),
      scanVersion: serializer.fromJson<int>(json['scanVersion']),
      updatedAtMs: serializer.fromJson<int>(json['updatedAtMs']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'platformId': serializer.toJson<String>(platformId),
      'takenAtMs': serializer.toJson<int>(takenAtMs),
      'width': serializer.toJson<int?>(width),
      'height': serializer.toJson<int?>(height),
      'category': serializer.toJson<String>(category),
      'confidence': serializer.toJson<double>(confidence),
      'source': serializer.toJson<String>(source),
      'state': serializer.toJson<String>(state),
      'modelVersion': serializer.toJson<String>(modelVersion),
      'scanVersion': serializer.toJson<int>(scanVersion),
      'updatedAtMs': serializer.toJson<int>(updatedAtMs),
    };
  }

  ScannedAsset copyWith({
    String? platformId,
    int? takenAtMs,
    Value<int?> width = const Value.absent(),
    Value<int?> height = const Value.absent(),
    String? category,
    double? confidence,
    String? source,
    String? state,
    String? modelVersion,
    int? scanVersion,
    int? updatedAtMs,
  }) => ScannedAsset(
    platformId: platformId ?? this.platformId,
    takenAtMs: takenAtMs ?? this.takenAtMs,
    width: width.present ? width.value : this.width,
    height: height.present ? height.value : this.height,
    category: category ?? this.category,
    confidence: confidence ?? this.confidence,
    source: source ?? this.source,
    state: state ?? this.state,
    modelVersion: modelVersion ?? this.modelVersion,
    scanVersion: scanVersion ?? this.scanVersion,
    updatedAtMs: updatedAtMs ?? this.updatedAtMs,
  );
  ScannedAsset copyWithCompanion(ScannedAssetsCompanion data) {
    return ScannedAsset(
      platformId: data.platformId.present
          ? data.platformId.value
          : this.platformId,
      takenAtMs: data.takenAtMs.present ? data.takenAtMs.value : this.takenAtMs,
      width: data.width.present ? data.width.value : this.width,
      height: data.height.present ? data.height.value : this.height,
      category: data.category.present ? data.category.value : this.category,
      confidence: data.confidence.present
          ? data.confidence.value
          : this.confidence,
      source: data.source.present ? data.source.value : this.source,
      state: data.state.present ? data.state.value : this.state,
      modelVersion: data.modelVersion.present
          ? data.modelVersion.value
          : this.modelVersion,
      scanVersion: data.scanVersion.present
          ? data.scanVersion.value
          : this.scanVersion,
      updatedAtMs: data.updatedAtMs.present
          ? data.updatedAtMs.value
          : this.updatedAtMs,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ScannedAsset(')
          ..write('platformId: $platformId, ')
          ..write('takenAtMs: $takenAtMs, ')
          ..write('width: $width, ')
          ..write('height: $height, ')
          ..write('category: $category, ')
          ..write('confidence: $confidence, ')
          ..write('source: $source, ')
          ..write('state: $state, ')
          ..write('modelVersion: $modelVersion, ')
          ..write('scanVersion: $scanVersion, ')
          ..write('updatedAtMs: $updatedAtMs')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    platformId,
    takenAtMs,
    width,
    height,
    category,
    confidence,
    source,
    state,
    modelVersion,
    scanVersion,
    updatedAtMs,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ScannedAsset &&
          other.platformId == this.platformId &&
          other.takenAtMs == this.takenAtMs &&
          other.width == this.width &&
          other.height == this.height &&
          other.category == this.category &&
          other.confidence == this.confidence &&
          other.source == this.source &&
          other.state == this.state &&
          other.modelVersion == this.modelVersion &&
          other.scanVersion == this.scanVersion &&
          other.updatedAtMs == this.updatedAtMs);
}

class ScannedAssetsCompanion extends UpdateCompanion<ScannedAsset> {
  final Value<String> platformId;
  final Value<int> takenAtMs;
  final Value<int?> width;
  final Value<int?> height;
  final Value<String> category;
  final Value<double> confidence;
  final Value<String> source;
  final Value<String> state;
  final Value<String> modelVersion;
  final Value<int> scanVersion;
  final Value<int> updatedAtMs;
  final Value<int> rowid;
  const ScannedAssetsCompanion({
    this.platformId = const Value.absent(),
    this.takenAtMs = const Value.absent(),
    this.width = const Value.absent(),
    this.height = const Value.absent(),
    this.category = const Value.absent(),
    this.confidence = const Value.absent(),
    this.source = const Value.absent(),
    this.state = const Value.absent(),
    this.modelVersion = const Value.absent(),
    this.scanVersion = const Value.absent(),
    this.updatedAtMs = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ScannedAssetsCompanion.insert({
    required String platformId,
    required int takenAtMs,
    this.width = const Value.absent(),
    this.height = const Value.absent(),
    this.category = const Value.absent(),
    this.confidence = const Value.absent(),
    this.source = const Value.absent(),
    required String state,
    this.modelVersion = const Value.absent(),
    this.scanVersion = const Value.absent(),
    required int updatedAtMs,
    this.rowid = const Value.absent(),
  }) : platformId = Value(platformId),
       takenAtMs = Value(takenAtMs),
       state = Value(state),
       updatedAtMs = Value(updatedAtMs);
  static Insertable<ScannedAsset> custom({
    Expression<String>? platformId,
    Expression<int>? takenAtMs,
    Expression<int>? width,
    Expression<int>? height,
    Expression<String>? category,
    Expression<double>? confidence,
    Expression<String>? source,
    Expression<String>? state,
    Expression<String>? modelVersion,
    Expression<int>? scanVersion,
    Expression<int>? updatedAtMs,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (platformId != null) 'platform_id': platformId,
      if (takenAtMs != null) 'taken_at_ms': takenAtMs,
      if (width != null) 'width': width,
      if (height != null) 'height': height,
      if (category != null) 'category': category,
      if (confidence != null) 'confidence': confidence,
      if (source != null) 'source': source,
      if (state != null) 'state': state,
      if (modelVersion != null) 'model_version': modelVersion,
      if (scanVersion != null) 'scan_version': scanVersion,
      if (updatedAtMs != null) 'updated_at_ms': updatedAtMs,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ScannedAssetsCompanion copyWith({
    Value<String>? platformId,
    Value<int>? takenAtMs,
    Value<int?>? width,
    Value<int?>? height,
    Value<String>? category,
    Value<double>? confidence,
    Value<String>? source,
    Value<String>? state,
    Value<String>? modelVersion,
    Value<int>? scanVersion,
    Value<int>? updatedAtMs,
    Value<int>? rowid,
  }) {
    return ScannedAssetsCompanion(
      platformId: platformId ?? this.platformId,
      takenAtMs: takenAtMs ?? this.takenAtMs,
      width: width ?? this.width,
      height: height ?? this.height,
      category: category ?? this.category,
      confidence: confidence ?? this.confidence,
      source: source ?? this.source,
      state: state ?? this.state,
      modelVersion: modelVersion ?? this.modelVersion,
      scanVersion: scanVersion ?? this.scanVersion,
      updatedAtMs: updatedAtMs ?? this.updatedAtMs,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (platformId.present) {
      map['platform_id'] = Variable<String>(platformId.value);
    }
    if (takenAtMs.present) {
      map['taken_at_ms'] = Variable<int>(takenAtMs.value);
    }
    if (width.present) {
      map['width'] = Variable<int>(width.value);
    }
    if (height.present) {
      map['height'] = Variable<int>(height.value);
    }
    if (category.present) {
      map['category'] = Variable<String>(category.value);
    }
    if (confidence.present) {
      map['confidence'] = Variable<double>(confidence.value);
    }
    if (source.present) {
      map['source'] = Variable<String>(source.value);
    }
    if (state.present) {
      map['state'] = Variable<String>(state.value);
    }
    if (modelVersion.present) {
      map['model_version'] = Variable<String>(modelVersion.value);
    }
    if (scanVersion.present) {
      map['scan_version'] = Variable<int>(scanVersion.value);
    }
    if (updatedAtMs.present) {
      map['updated_at_ms'] = Variable<int>(updatedAtMs.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ScannedAssetsCompanion(')
          ..write('platformId: $platformId, ')
          ..write('takenAtMs: $takenAtMs, ')
          ..write('width: $width, ')
          ..write('height: $height, ')
          ..write('category: $category, ')
          ..write('confidence: $confidence, ')
          ..write('source: $source, ')
          ..write('state: $state, ')
          ..write('modelVersion: $modelVersion, ')
          ..write('scanVersion: $scanVersion, ')
          ..write('updatedAtMs: $updatedAtMs, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $ScanStateTable extends ScanState
    with TableInfo<$ScanStateTable, ScanStateData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $ScanStateTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _keyMeta = const VerificationMeta('key');
  @override
  late final GeneratedColumn<String> key = GeneratedColumn<String>(
    'key',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _valueMeta = const VerificationMeta('value');
  @override
  late final GeneratedColumn<String> value = GeneratedColumn<String>(
    'value',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [key, value];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'scan_state';
  @override
  VerificationContext validateIntegrity(
    Insertable<ScanStateData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('key')) {
      context.handle(
        _keyMeta,
        key.isAcceptableOrUnknown(data['key']!, _keyMeta),
      );
    } else if (isInserting) {
      context.missing(_keyMeta);
    }
    if (data.containsKey('value')) {
      context.handle(
        _valueMeta,
        value.isAcceptableOrUnknown(data['value']!, _valueMeta),
      );
    } else if (isInserting) {
      context.missing(_valueMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {key};
  @override
  ScanStateData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return ScanStateData(
      key: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}key'],
      )!,
      value: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}value'],
      )!,
    );
  }

  @override
  $ScanStateTable createAlias(String alias) {
    return $ScanStateTable(attachedDatabase, alias);
  }
}

class ScanStateData extends DataClass implements Insertable<ScanStateData> {
  final String key;
  final String value;
  const ScanStateData({required this.key, required this.value});
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['key'] = Variable<String>(key);
    map['value'] = Variable<String>(value);
    return map;
  }

  ScanStateCompanion toCompanion(bool nullToAbsent) {
    return ScanStateCompanion(key: Value(key), value: Value(value));
  }

  factory ScanStateData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return ScanStateData(
      key: serializer.fromJson<String>(json['key']),
      value: serializer.fromJson<String>(json['value']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'key': serializer.toJson<String>(key),
      'value': serializer.toJson<String>(value),
    };
  }

  ScanStateData copyWith({String? key, String? value}) =>
      ScanStateData(key: key ?? this.key, value: value ?? this.value);
  ScanStateData copyWithCompanion(ScanStateCompanion data) {
    return ScanStateData(
      key: data.key.present ? data.key.value : this.key,
      value: data.value.present ? data.value.value : this.value,
    );
  }

  @override
  String toString() {
    return (StringBuffer('ScanStateData(')
          ..write('key: $key, ')
          ..write('value: $value')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(key, value);
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is ScanStateData &&
          other.key == this.key &&
          other.value == this.value);
}

class ScanStateCompanion extends UpdateCompanion<ScanStateData> {
  final Value<String> key;
  final Value<String> value;
  final Value<int> rowid;
  const ScanStateCompanion({
    this.key = const Value.absent(),
    this.value = const Value.absent(),
    this.rowid = const Value.absent(),
  });
  ScanStateCompanion.insert({
    required String key,
    required String value,
    this.rowid = const Value.absent(),
  }) : key = Value(key),
       value = Value(value);
  static Insertable<ScanStateData> custom({
    Expression<String>? key,
    Expression<String>? value,
    Expression<int>? rowid,
  }) {
    return RawValuesInsertable({
      if (key != null) 'key': key,
      if (value != null) 'value': value,
      if (rowid != null) 'rowid': rowid,
    });
  }

  ScanStateCompanion copyWith({
    Value<String>? key,
    Value<String>? value,
    Value<int>? rowid,
  }) {
    return ScanStateCompanion(
      key: key ?? this.key,
      value: value ?? this.value,
      rowid: rowid ?? this.rowid,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (key.present) {
      map['key'] = Variable<String>(key.value);
    }
    if (value.present) {
      map['value'] = Variable<String>(value.value);
    }
    if (rowid.present) {
      map['rowid'] = Variable<int>(rowid.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('ScanStateCompanion(')
          ..write('key: $key, ')
          ..write('value: $value, ')
          ..write('rowid: $rowid')
          ..write(')'))
        .toString();
  }
}

class $FeedbackTable extends Feedback
    with TableInfo<$FeedbackTable, FeedbackData> {
  @override
  final GeneratedDatabase attachedDatabase;
  final String? _alias;
  $FeedbackTable(this.attachedDatabase, [this._alias]);
  static const VerificationMeta _idMeta = const VerificationMeta('id');
  @override
  late final GeneratedColumn<int> id = GeneratedColumn<int>(
    'id',
    aliasedName,
    false,
    hasAutoIncrement: true,
    type: DriftSqlType.int,
    requiredDuringInsert: false,
    defaultConstraints: GeneratedColumn.constraintIsAlways(
      'PRIMARY KEY AUTOINCREMENT',
    ),
  );
  static const VerificationMeta _platformIdMeta = const VerificationMeta(
    'platformId',
  );
  @override
  late final GeneratedColumn<String> platformId = GeneratedColumn<String>(
    'platform_id',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _originalCategoryMeta = const VerificationMeta(
    'originalCategory',
  );
  @override
  late final GeneratedColumn<String> originalCategory = GeneratedColumn<String>(
    'original_category',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _correctedLabelMeta = const VerificationMeta(
    'correctedLabel',
  );
  @override
  late final GeneratedColumn<String> correctedLabel = GeneratedColumn<String>(
    'corrected_label',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _confidenceMeta = const VerificationMeta(
    'confidence',
  );
  @override
  late final GeneratedColumn<double> confidence = GeneratedColumn<double>(
    'confidence',
    aliasedName,
    false,
    type: DriftSqlType.double,
    requiredDuringInsert: true,
  );
  static const VerificationMeta _modelVersionMeta = const VerificationMeta(
    'modelVersion',
  );
  @override
  late final GeneratedColumn<String> modelVersion = GeneratedColumn<String>(
    'model_version',
    aliasedName,
    false,
    type: DriftSqlType.string,
    requiredDuringInsert: false,
    defaultValue: const Constant(''),
  );
  static const VerificationMeta _createdAtMsMeta = const VerificationMeta(
    'createdAtMs',
  );
  @override
  late final GeneratedColumn<int> createdAtMs = GeneratedColumn<int>(
    'created_at_ms',
    aliasedName,
    false,
    type: DriftSqlType.int,
    requiredDuringInsert: true,
  );
  @override
  List<GeneratedColumn> get $columns => [
    id,
    platformId,
    originalCategory,
    correctedLabel,
    confidence,
    modelVersion,
    createdAtMs,
  ];
  @override
  String get aliasedName => _alias ?? actualTableName;
  @override
  String get actualTableName => $name;
  static const String $name = 'feedback';
  @override
  VerificationContext validateIntegrity(
    Insertable<FeedbackData> instance, {
    bool isInserting = false,
  }) {
    final context = VerificationContext();
    final data = instance.toColumns(true);
    if (data.containsKey('id')) {
      context.handle(_idMeta, id.isAcceptableOrUnknown(data['id']!, _idMeta));
    }
    if (data.containsKey('platform_id')) {
      context.handle(
        _platformIdMeta,
        platformId.isAcceptableOrUnknown(data['platform_id']!, _platformIdMeta),
      );
    } else if (isInserting) {
      context.missing(_platformIdMeta);
    }
    if (data.containsKey('original_category')) {
      context.handle(
        _originalCategoryMeta,
        originalCategory.isAcceptableOrUnknown(
          data['original_category']!,
          _originalCategoryMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_originalCategoryMeta);
    }
    if (data.containsKey('corrected_label')) {
      context.handle(
        _correctedLabelMeta,
        correctedLabel.isAcceptableOrUnknown(
          data['corrected_label']!,
          _correctedLabelMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_correctedLabelMeta);
    }
    if (data.containsKey('confidence')) {
      context.handle(
        _confidenceMeta,
        confidence.isAcceptableOrUnknown(data['confidence']!, _confidenceMeta),
      );
    } else if (isInserting) {
      context.missing(_confidenceMeta);
    }
    if (data.containsKey('model_version')) {
      context.handle(
        _modelVersionMeta,
        modelVersion.isAcceptableOrUnknown(
          data['model_version']!,
          _modelVersionMeta,
        ),
      );
    }
    if (data.containsKey('created_at_ms')) {
      context.handle(
        _createdAtMsMeta,
        createdAtMs.isAcceptableOrUnknown(
          data['created_at_ms']!,
          _createdAtMsMeta,
        ),
      );
    } else if (isInserting) {
      context.missing(_createdAtMsMeta);
    }
    return context;
  }

  @override
  Set<GeneratedColumn> get $primaryKey => {id};
  @override
  FeedbackData map(Map<String, dynamic> data, {String? tablePrefix}) {
    final effectivePrefix = tablePrefix != null ? '$tablePrefix.' : '';
    return FeedbackData(
      id: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}id'],
      )!,
      platformId: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}platform_id'],
      )!,
      originalCategory: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}original_category'],
      )!,
      correctedLabel: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}corrected_label'],
      )!,
      confidence: attachedDatabase.typeMapping.read(
        DriftSqlType.double,
        data['${effectivePrefix}confidence'],
      )!,
      modelVersion: attachedDatabase.typeMapping.read(
        DriftSqlType.string,
        data['${effectivePrefix}model_version'],
      )!,
      createdAtMs: attachedDatabase.typeMapping.read(
        DriftSqlType.int,
        data['${effectivePrefix}created_at_ms'],
      )!,
    );
  }

  @override
  $FeedbackTable createAlias(String alias) {
    return $FeedbackTable(attachedDatabase, alias);
  }
}

class FeedbackData extends DataClass implements Insertable<FeedbackData> {
  final int id;
  final String platformId;
  final String originalCategory;
  final String correctedLabel;
  final double confidence;
  final String modelVersion;
  final int createdAtMs;
  const FeedbackData({
    required this.id,
    required this.platformId,
    required this.originalCategory,
    required this.correctedLabel,
    required this.confidence,
    required this.modelVersion,
    required this.createdAtMs,
  });
  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    map['id'] = Variable<int>(id);
    map['platform_id'] = Variable<String>(platformId);
    map['original_category'] = Variable<String>(originalCategory);
    map['corrected_label'] = Variable<String>(correctedLabel);
    map['confidence'] = Variable<double>(confidence);
    map['model_version'] = Variable<String>(modelVersion);
    map['created_at_ms'] = Variable<int>(createdAtMs);
    return map;
  }

  FeedbackCompanion toCompanion(bool nullToAbsent) {
    return FeedbackCompanion(
      id: Value(id),
      platformId: Value(platformId),
      originalCategory: Value(originalCategory),
      correctedLabel: Value(correctedLabel),
      confidence: Value(confidence),
      modelVersion: Value(modelVersion),
      createdAtMs: Value(createdAtMs),
    );
  }

  factory FeedbackData.fromJson(
    Map<String, dynamic> json, {
    ValueSerializer? serializer,
  }) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return FeedbackData(
      id: serializer.fromJson<int>(json['id']),
      platformId: serializer.fromJson<String>(json['platformId']),
      originalCategory: serializer.fromJson<String>(json['originalCategory']),
      correctedLabel: serializer.fromJson<String>(json['correctedLabel']),
      confidence: serializer.fromJson<double>(json['confidence']),
      modelVersion: serializer.fromJson<String>(json['modelVersion']),
      createdAtMs: serializer.fromJson<int>(json['createdAtMs']),
    );
  }
  @override
  Map<String, dynamic> toJson({ValueSerializer? serializer}) {
    serializer ??= driftRuntimeOptions.defaultSerializer;
    return <String, dynamic>{
      'id': serializer.toJson<int>(id),
      'platformId': serializer.toJson<String>(platformId),
      'originalCategory': serializer.toJson<String>(originalCategory),
      'correctedLabel': serializer.toJson<String>(correctedLabel),
      'confidence': serializer.toJson<double>(confidence),
      'modelVersion': serializer.toJson<String>(modelVersion),
      'createdAtMs': serializer.toJson<int>(createdAtMs),
    };
  }

  FeedbackData copyWith({
    int? id,
    String? platformId,
    String? originalCategory,
    String? correctedLabel,
    double? confidence,
    String? modelVersion,
    int? createdAtMs,
  }) => FeedbackData(
    id: id ?? this.id,
    platformId: platformId ?? this.platformId,
    originalCategory: originalCategory ?? this.originalCategory,
    correctedLabel: correctedLabel ?? this.correctedLabel,
    confidence: confidence ?? this.confidence,
    modelVersion: modelVersion ?? this.modelVersion,
    createdAtMs: createdAtMs ?? this.createdAtMs,
  );
  FeedbackData copyWithCompanion(FeedbackCompanion data) {
    return FeedbackData(
      id: data.id.present ? data.id.value : this.id,
      platformId: data.platformId.present
          ? data.platformId.value
          : this.platformId,
      originalCategory: data.originalCategory.present
          ? data.originalCategory.value
          : this.originalCategory,
      correctedLabel: data.correctedLabel.present
          ? data.correctedLabel.value
          : this.correctedLabel,
      confidence: data.confidence.present
          ? data.confidence.value
          : this.confidence,
      modelVersion: data.modelVersion.present
          ? data.modelVersion.value
          : this.modelVersion,
      createdAtMs: data.createdAtMs.present
          ? data.createdAtMs.value
          : this.createdAtMs,
    );
  }

  @override
  String toString() {
    return (StringBuffer('FeedbackData(')
          ..write('id: $id, ')
          ..write('platformId: $platformId, ')
          ..write('originalCategory: $originalCategory, ')
          ..write('correctedLabel: $correctedLabel, ')
          ..write('confidence: $confidence, ')
          ..write('modelVersion: $modelVersion, ')
          ..write('createdAtMs: $createdAtMs')
          ..write(')'))
        .toString();
  }

  @override
  int get hashCode => Object.hash(
    id,
    platformId,
    originalCategory,
    correctedLabel,
    confidence,
    modelVersion,
    createdAtMs,
  );
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      (other is FeedbackData &&
          other.id == this.id &&
          other.platformId == this.platformId &&
          other.originalCategory == this.originalCategory &&
          other.correctedLabel == this.correctedLabel &&
          other.confidence == this.confidence &&
          other.modelVersion == this.modelVersion &&
          other.createdAtMs == this.createdAtMs);
}

class FeedbackCompanion extends UpdateCompanion<FeedbackData> {
  final Value<int> id;
  final Value<String> platformId;
  final Value<String> originalCategory;
  final Value<String> correctedLabel;
  final Value<double> confidence;
  final Value<String> modelVersion;
  final Value<int> createdAtMs;
  const FeedbackCompanion({
    this.id = const Value.absent(),
    this.platformId = const Value.absent(),
    this.originalCategory = const Value.absent(),
    this.correctedLabel = const Value.absent(),
    this.confidence = const Value.absent(),
    this.modelVersion = const Value.absent(),
    this.createdAtMs = const Value.absent(),
  });
  FeedbackCompanion.insert({
    this.id = const Value.absent(),
    required String platformId,
    required String originalCategory,
    required String correctedLabel,
    required double confidence,
    this.modelVersion = const Value.absent(),
    required int createdAtMs,
  }) : platformId = Value(platformId),
       originalCategory = Value(originalCategory),
       correctedLabel = Value(correctedLabel),
       confidence = Value(confidence),
       createdAtMs = Value(createdAtMs);
  static Insertable<FeedbackData> custom({
    Expression<int>? id,
    Expression<String>? platformId,
    Expression<String>? originalCategory,
    Expression<String>? correctedLabel,
    Expression<double>? confidence,
    Expression<String>? modelVersion,
    Expression<int>? createdAtMs,
  }) {
    return RawValuesInsertable({
      if (id != null) 'id': id,
      if (platformId != null) 'platform_id': platformId,
      if (originalCategory != null) 'original_category': originalCategory,
      if (correctedLabel != null) 'corrected_label': correctedLabel,
      if (confidence != null) 'confidence': confidence,
      if (modelVersion != null) 'model_version': modelVersion,
      if (createdAtMs != null) 'created_at_ms': createdAtMs,
    });
  }

  FeedbackCompanion copyWith({
    Value<int>? id,
    Value<String>? platformId,
    Value<String>? originalCategory,
    Value<String>? correctedLabel,
    Value<double>? confidence,
    Value<String>? modelVersion,
    Value<int>? createdAtMs,
  }) {
    return FeedbackCompanion(
      id: id ?? this.id,
      platformId: platformId ?? this.platformId,
      originalCategory: originalCategory ?? this.originalCategory,
      correctedLabel: correctedLabel ?? this.correctedLabel,
      confidence: confidence ?? this.confidence,
      modelVersion: modelVersion ?? this.modelVersion,
      createdAtMs: createdAtMs ?? this.createdAtMs,
    );
  }

  @override
  Map<String, Expression> toColumns(bool nullToAbsent) {
    final map = <String, Expression>{};
    if (id.present) {
      map['id'] = Variable<int>(id.value);
    }
    if (platformId.present) {
      map['platform_id'] = Variable<String>(platformId.value);
    }
    if (originalCategory.present) {
      map['original_category'] = Variable<String>(originalCategory.value);
    }
    if (correctedLabel.present) {
      map['corrected_label'] = Variable<String>(correctedLabel.value);
    }
    if (confidence.present) {
      map['confidence'] = Variable<double>(confidence.value);
    }
    if (modelVersion.present) {
      map['model_version'] = Variable<String>(modelVersion.value);
    }
    if (createdAtMs.present) {
      map['created_at_ms'] = Variable<int>(createdAtMs.value);
    }
    return map;
  }

  @override
  String toString() {
    return (StringBuffer('FeedbackCompanion(')
          ..write('id: $id, ')
          ..write('platformId: $platformId, ')
          ..write('originalCategory: $originalCategory, ')
          ..write('correctedLabel: $correctedLabel, ')
          ..write('confidence: $confidence, ')
          ..write('modelVersion: $modelVersion, ')
          ..write('createdAtMs: $createdAtMs')
          ..write(')'))
        .toString();
  }
}

abstract class _$AppDatabase extends GeneratedDatabase {
  _$AppDatabase(QueryExecutor e) : super(e);
  $AppDatabaseManager get managers => $AppDatabaseManager(this);
  late final $ScannedAssetsTable scannedAssets = $ScannedAssetsTable(this);
  late final $ScanStateTable scanState = $ScanStateTable(this);
  late final $FeedbackTable feedback = $FeedbackTable(this);
  @override
  Iterable<TableInfo<Table, Object?>> get allTables =>
      allSchemaEntities.whereType<TableInfo<Table, Object?>>();
  @override
  List<DatabaseSchemaEntity> get allSchemaEntities => [
    scannedAssets,
    scanState,
    feedback,
  ];
}

typedef $$ScannedAssetsTableCreateCompanionBuilder =
    ScannedAssetsCompanion Function({
      required String platformId,
      required int takenAtMs,
      Value<int?> width,
      Value<int?> height,
      Value<String> category,
      Value<double> confidence,
      Value<String> source,
      required String state,
      Value<String> modelVersion,
      Value<int> scanVersion,
      required int updatedAtMs,
      Value<int> rowid,
    });
typedef $$ScannedAssetsTableUpdateCompanionBuilder =
    ScannedAssetsCompanion Function({
      Value<String> platformId,
      Value<int> takenAtMs,
      Value<int?> width,
      Value<int?> height,
      Value<String> category,
      Value<double> confidence,
      Value<String> source,
      Value<String> state,
      Value<String> modelVersion,
      Value<int> scanVersion,
      Value<int> updatedAtMs,
      Value<int> rowid,
    });

class $$ScannedAssetsTableFilterComposer
    extends Composer<_$AppDatabase, $ScannedAssetsTable> {
  $$ScannedAssetsTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get platformId => $composableBuilder(
    column: $table.platformId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get takenAtMs => $composableBuilder(
    column: $table.takenAtMs,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get width => $composableBuilder(
    column: $table.width,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get height => $composableBuilder(
    column: $table.height,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get category => $composableBuilder(
    column: $table.category,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get state => $composableBuilder(
    column: $table.state,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get modelVersion => $composableBuilder(
    column: $table.modelVersion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get scanVersion => $composableBuilder(
    column: $table.scanVersion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get updatedAtMs => $composableBuilder(
    column: $table.updatedAtMs,
    builder: (column) => ColumnFilters(column),
  );
}

class $$ScannedAssetsTableOrderingComposer
    extends Composer<_$AppDatabase, $ScannedAssetsTable> {
  $$ScannedAssetsTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get platformId => $composableBuilder(
    column: $table.platformId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get takenAtMs => $composableBuilder(
    column: $table.takenAtMs,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get width => $composableBuilder(
    column: $table.width,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get height => $composableBuilder(
    column: $table.height,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get category => $composableBuilder(
    column: $table.category,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get source => $composableBuilder(
    column: $table.source,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get state => $composableBuilder(
    column: $table.state,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get modelVersion => $composableBuilder(
    column: $table.modelVersion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get scanVersion => $composableBuilder(
    column: $table.scanVersion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get updatedAtMs => $composableBuilder(
    column: $table.updatedAtMs,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$ScannedAssetsTableAnnotationComposer
    extends Composer<_$AppDatabase, $ScannedAssetsTable> {
  $$ScannedAssetsTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get platformId => $composableBuilder(
    column: $table.platformId,
    builder: (column) => column,
  );

  GeneratedColumn<int> get takenAtMs =>
      $composableBuilder(column: $table.takenAtMs, builder: (column) => column);

  GeneratedColumn<int> get width =>
      $composableBuilder(column: $table.width, builder: (column) => column);

  GeneratedColumn<int> get height =>
      $composableBuilder(column: $table.height, builder: (column) => column);

  GeneratedColumn<String> get category =>
      $composableBuilder(column: $table.category, builder: (column) => column);

  GeneratedColumn<double> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => column,
  );

  GeneratedColumn<String> get source =>
      $composableBuilder(column: $table.source, builder: (column) => column);

  GeneratedColumn<String> get state =>
      $composableBuilder(column: $table.state, builder: (column) => column);

  GeneratedColumn<String> get modelVersion => $composableBuilder(
    column: $table.modelVersion,
    builder: (column) => column,
  );

  GeneratedColumn<int> get scanVersion => $composableBuilder(
    column: $table.scanVersion,
    builder: (column) => column,
  );

  GeneratedColumn<int> get updatedAtMs => $composableBuilder(
    column: $table.updatedAtMs,
    builder: (column) => column,
  );
}

class $$ScannedAssetsTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ScannedAssetsTable,
          ScannedAsset,
          $$ScannedAssetsTableFilterComposer,
          $$ScannedAssetsTableOrderingComposer,
          $$ScannedAssetsTableAnnotationComposer,
          $$ScannedAssetsTableCreateCompanionBuilder,
          $$ScannedAssetsTableUpdateCompanionBuilder,
          (
            ScannedAsset,
            BaseReferences<_$AppDatabase, $ScannedAssetsTable, ScannedAsset>,
          ),
          ScannedAsset,
          PrefetchHooks Function()
        > {
  $$ScannedAssetsTableTableManager(_$AppDatabase db, $ScannedAssetsTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ScannedAssetsTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ScannedAssetsTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ScannedAssetsTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> platformId = const Value.absent(),
                Value<int> takenAtMs = const Value.absent(),
                Value<int?> width = const Value.absent(),
                Value<int?> height = const Value.absent(),
                Value<String> category = const Value.absent(),
                Value<double> confidence = const Value.absent(),
                Value<String> source = const Value.absent(),
                Value<String> state = const Value.absent(),
                Value<String> modelVersion = const Value.absent(),
                Value<int> scanVersion = const Value.absent(),
                Value<int> updatedAtMs = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => ScannedAssetsCompanion(
                platformId: platformId,
                takenAtMs: takenAtMs,
                width: width,
                height: height,
                category: category,
                confidence: confidence,
                source: source,
                state: state,
                modelVersion: modelVersion,
                scanVersion: scanVersion,
                updatedAtMs: updatedAtMs,
                rowid: rowid,
              ),
          createCompanionCallback:
              ({
                required String platformId,
                required int takenAtMs,
                Value<int?> width = const Value.absent(),
                Value<int?> height = const Value.absent(),
                Value<String> category = const Value.absent(),
                Value<double> confidence = const Value.absent(),
                Value<String> source = const Value.absent(),
                required String state,
                Value<String> modelVersion = const Value.absent(),
                Value<int> scanVersion = const Value.absent(),
                required int updatedAtMs,
                Value<int> rowid = const Value.absent(),
              }) => ScannedAssetsCompanion.insert(
                platformId: platformId,
                takenAtMs: takenAtMs,
                width: width,
                height: height,
                category: category,
                confidence: confidence,
                source: source,
                state: state,
                modelVersion: modelVersion,
                scanVersion: scanVersion,
                updatedAtMs: updatedAtMs,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$ScannedAssetsTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ScannedAssetsTable,
      ScannedAsset,
      $$ScannedAssetsTableFilterComposer,
      $$ScannedAssetsTableOrderingComposer,
      $$ScannedAssetsTableAnnotationComposer,
      $$ScannedAssetsTableCreateCompanionBuilder,
      $$ScannedAssetsTableUpdateCompanionBuilder,
      (
        ScannedAsset,
        BaseReferences<_$AppDatabase, $ScannedAssetsTable, ScannedAsset>,
      ),
      ScannedAsset,
      PrefetchHooks Function()
    >;
typedef $$ScanStateTableCreateCompanionBuilder =
    ScanStateCompanion Function({
      required String key,
      required String value,
      Value<int> rowid,
    });
typedef $$ScanStateTableUpdateCompanionBuilder =
    ScanStateCompanion Function({
      Value<String> key,
      Value<String> value,
      Value<int> rowid,
    });

class $$ScanStateTableFilterComposer
    extends Composer<_$AppDatabase, $ScanStateTable> {
  $$ScanStateTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnFilters(column),
  );
}

class $$ScanStateTableOrderingComposer
    extends Composer<_$AppDatabase, $ScanStateTable> {
  $$ScanStateTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<String> get key => $composableBuilder(
    column: $table.key,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get value => $composableBuilder(
    column: $table.value,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$ScanStateTableAnnotationComposer
    extends Composer<_$AppDatabase, $ScanStateTable> {
  $$ScanStateTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<String> get key =>
      $composableBuilder(column: $table.key, builder: (column) => column);

  GeneratedColumn<String> get value =>
      $composableBuilder(column: $table.value, builder: (column) => column);
}

class $$ScanStateTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $ScanStateTable,
          ScanStateData,
          $$ScanStateTableFilterComposer,
          $$ScanStateTableOrderingComposer,
          $$ScanStateTableAnnotationComposer,
          $$ScanStateTableCreateCompanionBuilder,
          $$ScanStateTableUpdateCompanionBuilder,
          (
            ScanStateData,
            BaseReferences<_$AppDatabase, $ScanStateTable, ScanStateData>,
          ),
          ScanStateData,
          PrefetchHooks Function()
        > {
  $$ScanStateTableTableManager(_$AppDatabase db, $ScanStateTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$ScanStateTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$ScanStateTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$ScanStateTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<String> key = const Value.absent(),
                Value<String> value = const Value.absent(),
                Value<int> rowid = const Value.absent(),
              }) => ScanStateCompanion(key: key, value: value, rowid: rowid),
          createCompanionCallback:
              ({
                required String key,
                required String value,
                Value<int> rowid = const Value.absent(),
              }) => ScanStateCompanion.insert(
                key: key,
                value: value,
                rowid: rowid,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$ScanStateTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $ScanStateTable,
      ScanStateData,
      $$ScanStateTableFilterComposer,
      $$ScanStateTableOrderingComposer,
      $$ScanStateTableAnnotationComposer,
      $$ScanStateTableCreateCompanionBuilder,
      $$ScanStateTableUpdateCompanionBuilder,
      (
        ScanStateData,
        BaseReferences<_$AppDatabase, $ScanStateTable, ScanStateData>,
      ),
      ScanStateData,
      PrefetchHooks Function()
    >;
typedef $$FeedbackTableCreateCompanionBuilder =
    FeedbackCompanion Function({
      Value<int> id,
      required String platformId,
      required String originalCategory,
      required String correctedLabel,
      required double confidence,
      Value<String> modelVersion,
      required int createdAtMs,
    });
typedef $$FeedbackTableUpdateCompanionBuilder =
    FeedbackCompanion Function({
      Value<int> id,
      Value<String> platformId,
      Value<String> originalCategory,
      Value<String> correctedLabel,
      Value<double> confidence,
      Value<String> modelVersion,
      Value<int> createdAtMs,
    });

class $$FeedbackTableFilterComposer
    extends Composer<_$AppDatabase, $FeedbackTable> {
  $$FeedbackTableFilterComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnFilters<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get platformId => $composableBuilder(
    column: $table.platformId,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get originalCategory => $composableBuilder(
    column: $table.originalCategory,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get correctedLabel => $composableBuilder(
    column: $table.correctedLabel,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<double> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<String> get modelVersion => $composableBuilder(
    column: $table.modelVersion,
    builder: (column) => ColumnFilters(column),
  );

  ColumnFilters<int> get createdAtMs => $composableBuilder(
    column: $table.createdAtMs,
    builder: (column) => ColumnFilters(column),
  );
}

class $$FeedbackTableOrderingComposer
    extends Composer<_$AppDatabase, $FeedbackTable> {
  $$FeedbackTableOrderingComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  ColumnOrderings<int> get id => $composableBuilder(
    column: $table.id,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get platformId => $composableBuilder(
    column: $table.platformId,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get originalCategory => $composableBuilder(
    column: $table.originalCategory,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get correctedLabel => $composableBuilder(
    column: $table.correctedLabel,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<double> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<String> get modelVersion => $composableBuilder(
    column: $table.modelVersion,
    builder: (column) => ColumnOrderings(column),
  );

  ColumnOrderings<int> get createdAtMs => $composableBuilder(
    column: $table.createdAtMs,
    builder: (column) => ColumnOrderings(column),
  );
}

class $$FeedbackTableAnnotationComposer
    extends Composer<_$AppDatabase, $FeedbackTable> {
  $$FeedbackTableAnnotationComposer({
    required super.$db,
    required super.$table,
    super.joinBuilder,
    super.$addJoinBuilderToRootComposer,
    super.$removeJoinBuilderFromRootComposer,
  });
  GeneratedColumn<int> get id =>
      $composableBuilder(column: $table.id, builder: (column) => column);

  GeneratedColumn<String> get platformId => $composableBuilder(
    column: $table.platformId,
    builder: (column) => column,
  );

  GeneratedColumn<String> get originalCategory => $composableBuilder(
    column: $table.originalCategory,
    builder: (column) => column,
  );

  GeneratedColumn<String> get correctedLabel => $composableBuilder(
    column: $table.correctedLabel,
    builder: (column) => column,
  );

  GeneratedColumn<double> get confidence => $composableBuilder(
    column: $table.confidence,
    builder: (column) => column,
  );

  GeneratedColumn<String> get modelVersion => $composableBuilder(
    column: $table.modelVersion,
    builder: (column) => column,
  );

  GeneratedColumn<int> get createdAtMs => $composableBuilder(
    column: $table.createdAtMs,
    builder: (column) => column,
  );
}

class $$FeedbackTableTableManager
    extends
        RootTableManager<
          _$AppDatabase,
          $FeedbackTable,
          FeedbackData,
          $$FeedbackTableFilterComposer,
          $$FeedbackTableOrderingComposer,
          $$FeedbackTableAnnotationComposer,
          $$FeedbackTableCreateCompanionBuilder,
          $$FeedbackTableUpdateCompanionBuilder,
          (
            FeedbackData,
            BaseReferences<_$AppDatabase, $FeedbackTable, FeedbackData>,
          ),
          FeedbackData,
          PrefetchHooks Function()
        > {
  $$FeedbackTableTableManager(_$AppDatabase db, $FeedbackTable table)
    : super(
        TableManagerState(
          db: db,
          table: table,
          createFilteringComposer: () =>
              $$FeedbackTableFilterComposer($db: db, $table: table),
          createOrderingComposer: () =>
              $$FeedbackTableOrderingComposer($db: db, $table: table),
          createComputedFieldComposer: () =>
              $$FeedbackTableAnnotationComposer($db: db, $table: table),
          updateCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                Value<String> platformId = const Value.absent(),
                Value<String> originalCategory = const Value.absent(),
                Value<String> correctedLabel = const Value.absent(),
                Value<double> confidence = const Value.absent(),
                Value<String> modelVersion = const Value.absent(),
                Value<int> createdAtMs = const Value.absent(),
              }) => FeedbackCompanion(
                id: id,
                platformId: platformId,
                originalCategory: originalCategory,
                correctedLabel: correctedLabel,
                confidence: confidence,
                modelVersion: modelVersion,
                createdAtMs: createdAtMs,
              ),
          createCompanionCallback:
              ({
                Value<int> id = const Value.absent(),
                required String platformId,
                required String originalCategory,
                required String correctedLabel,
                required double confidence,
                Value<String> modelVersion = const Value.absent(),
                required int createdAtMs,
              }) => FeedbackCompanion.insert(
                id: id,
                platformId: platformId,
                originalCategory: originalCategory,
                correctedLabel: correctedLabel,
                confidence: confidence,
                modelVersion: modelVersion,
                createdAtMs: createdAtMs,
              ),
          withReferenceMapper: (p0) => p0
              .map((e) => (e.readTable(table), BaseReferences(db, table, e)))
              .toList(),
          prefetchHooksCallback: null,
        ),
      );
}

typedef $$FeedbackTableProcessedTableManager =
    ProcessedTableManager<
      _$AppDatabase,
      $FeedbackTable,
      FeedbackData,
      $$FeedbackTableFilterComposer,
      $$FeedbackTableOrderingComposer,
      $$FeedbackTableAnnotationComposer,
      $$FeedbackTableCreateCompanionBuilder,
      $$FeedbackTableUpdateCompanionBuilder,
      (
        FeedbackData,
        BaseReferences<_$AppDatabase, $FeedbackTable, FeedbackData>,
      ),
      FeedbackData,
      PrefetchHooks Function()
    >;

class $AppDatabaseManager {
  final _$AppDatabase _db;
  $AppDatabaseManager(this._db);
  $$ScannedAssetsTableTableManager get scannedAssets =>
      $$ScannedAssetsTableTableManager(_db, _db.scannedAssets);
  $$ScanStateTableTableManager get scanState =>
      $$ScanStateTableTableManager(_db, _db.scanState);
  $$FeedbackTableTableManager get feedback =>
      $$FeedbackTableTableManager(_db, _db.feedback);
}
