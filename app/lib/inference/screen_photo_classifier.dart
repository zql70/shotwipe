import 'dart:async';
import 'dart:io';
import 'dart:isolate';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/services.dart';
import 'package:image/image.dart' as img;
import 'package:path_provider/path_provider.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

import '../core/recognition_config.dart';

/// 一次模型推理的产物。
class Classification {
  const Classification({
    required this.category,
    required this.confidence,
    required this.scores,
  });

  final String category;
  final double confidence;
  final Map<String, double> scores;

  @override
  String toString() =>
      'Classification($category, ${(confidence * 100).toStringAsFixed(1)}%)';
}

class ClassifierException implements Exception {
  ClassifierException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// 屏摄图分类器：MobileNetV4-Conv-S 三分类（截图/屏摄/其他）。
///
/// 模型在独立 isolate 中加载与推理，主线程只负责发缩略图字节、收分类结果。
/// TFLite 输入为 NHWC 224×224 float32（0–1，ImageNet 归一化已烘焙进模型），
/// 输出 3 个 logits，顺序与 [RecognitionConfig] 的训练标签一致。
class ScreenPhotoClassifier {
  static const _inputSize = RecognitionConfig.inputSize;
  static const _numClasses = 3;
  static const _requestTimeout = Duration(seconds: 30);

  Isolate? _isolate;
  ReceivePort? _receivePort;
  ReceivePort? _exitPort;
  ReceivePort? _errorPort;
  SendPort? _workerPort;
  Completer<void>? _initCompleter;
  final _pending = <int, Completer<Classification>>{};
  int _nextId = 1;
  bool _ready = false;
  bool _disposed = false;

  bool get isReady => _ready;

  /// 加载模型、提取资产、启动 isolate。可重复调用，失败后允许重试。
  Future<void> init({void Function(String status)? onStatus}) {
    if (_ready) return Future.value();
    final existing = _initCompleter;
    if (existing != null) return existing.future;

    final completer = _initCompleter = Completer<void>();
    _init(onStatus, completer);
    return completer.future;
  }

  Future<void> _init(
    void Function(String status)? onStatus,
    Completer<void> completer,
  ) async {
    try {
      onStatus?.call('正在准备识别模型…');
      final modelFile = await _ensureModelFile();

      onStatus?.call('正在加载模型…');
      final receive = ReceivePort();
      final exitPort = ReceivePort();
      final errorPort = ReceivePort();
      _receivePort = receive;
      _exitPort = exitPort;
      _errorPort = errorPort;
      exitPort.listen((_) => _onIsolateExit(0));
      errorPort.listen((message) {
        final details = message as List;
        _onIsolateError(
          details.first,
          StackTrace.fromString('${details.last}'),
        );
      });
      _isolate = await Isolate.spawn(
        _classifierIsolateMain,
        [receive.sendPort, modelFile.path],
        debugName: 'shotwipe-classifier',
        errorsAreFatal: true,
        onExit: exitPort.sendPort,
        onError: errorPort.sendPort,
      );
      receive.listen(_onWorkerMessage);
      Timer(const Duration(seconds: 60), () {
        if (!completer.isCompleted) {
          _failAll(ClassifierException('识别模型加载超时，请重试'));
        }
      });
    } catch (e) {
      _initCompleter = null;
      if (!completer.isCompleted) {
        completer.completeError(ClassifierException('识别模型加载失败：$e'));
      }
    }
  }

  Future<File> _ensureModelFile() async {
    await _cleanupLegacyModels();
    // 模型可随时重新生成，放 cache 目录，避免进 iCloud/系统备份。
    final cache = await getApplicationCacheDirectory();
    final dir = Directory('${cache.path}/models');
    if (!await dir.exists()) await dir.create(recursive: true);
    // 按模型资产版本落盘；prompt/阈值变化不影响模型文件。
    final file = File(
      '${dir.path}/${RecognitionConfig.modelAssetVersion}.tflite',
    );
    if (await file.exists()) {
      await _removeStaleModels(dir, file);
      return file;
    }

    final asset = await rootBundle.load(RecognitionConfig.modelAsset);
    final bytes = asset.buffer.asUint8List(
      asset.offsetInBytes,
      asset.lengthInBytes,
    );
    final temp = File('${file.path}.tmp');
    await temp.writeAsBytes(bytes, flush: true);
    await temp.rename(file.path);
    await _removeStaleModels(dir, file);
    return file;
  }

  /// 早期版本把模型放在 Application Support，升级后清掉。
  Future<void> _cleanupLegacyModels() async {
    try {
      final support = await getApplicationSupportDirectory();
      final dir = Directory('${support.path}/models');
      if (!await dir.exists()) return;
      await for (final entity in dir.list()) {
        if (entity is File &&
            (entity.path.endsWith('.tflite') || entity.path.endsWith('.tmp'))) {
          try {
            await entity.delete();
          } catch (_) {
            // 清理失败不影响本次使用。
          }
        }
      }
      if (await dir.list().isEmpty) await dir.delete();
    } catch (_) {
      // 旧目录不存在/不可读时忽略。
    }
  }

  Future<void> _removeStaleModels(Directory dir, File keep) async {
    try {
      await for (final entity in dir.list()) {
        if (entity is! File) continue;
        if (entity.path == keep.path) continue;
        if (entity.path.endsWith('.tflite') || entity.path.endsWith('.tmp')) {
          try {
            await entity.delete();
          } catch (_) {
            // 清理失败不影响本次使用。
          }
        }
      }
    } catch (_) {
      // 目录读取失败不影响本次使用。
    }
  }

  /// 输入为相册缩略图（JPEG/PNG 字节，建议 512px）。
  Future<Classification> classify(Uint8List thumbnailBytes) async {
    if (_disposed) {
      throw ClassifierException('识别器已关闭');
    }
    if (!_ready) {
      await init();
    }
    final port = _workerPort;
    if (port == null) {
      throw ClassifierException('识别器尚未就绪');
    }
    final id = _nextId++;
    final completer = Completer<Classification>();
    _pending[id] = completer;
    port.send({'type': 'classify', 'id': id, 'bytes': thumbnailBytes});
    return completer.future.timeout(
      _requestTimeout,
      onTimeout: () {
        _pending.remove(id);
        throw ClassifierException('单张图片识别超时');
      },
    );
  }

  void _onWorkerMessage(Object? message) {
    if (message is! Map) return;
    switch (message['type']) {
      case 'ready':
        _workerPort = message['port'] as SendPort?;
        _ready = true;
        final init = _initCompleter;
        if (init != null && !init.isCompleted) init.complete();
      case 'init_error':
        // 允许下次扫描重试：清掉初始化状态与 isolate。
        _failAll(ClassifierException('识别模型初始化失败：${message['error']}'));
        _isolate?.kill(priority: Isolate.immediate);
        _isolate = null;
      case 'result':
        final id = message['id'] as int?;
        final pending = id == null ? null : _pending.remove(id);
        if (pending == null) return;
        pending.complete(
          Classification(
            category: message['category'] as String,
            confidence: (message['confidence'] as num).toDouble(),
            scores: (message['scores'] as Map).map(
              (k, v) => MapEntry(k as String, (v as num).toDouble()),
            ),
          ),
        );
      case 'error':
        final id = message['id'] as int?;
        final pending = id == null ? null : _pending.remove(id);
        pending?.completeError(ClassifierException('识别失败：${message['error']}'));
    }
  }

  void _onIsolateError(Object error, StackTrace stackTrace) {
    _failAll(ClassifierException('识别进程异常：$error'));
  }

  void _onIsolateExit(int exitCode) {
    if (_disposed) return;
    _failAll(ClassifierException('识别进程已退出（$exitCode）'));
  }

  void _failAll(Object error) {
    _ready = false;
    _workerPort = null;
    final init = _initCompleter;
    if (init != null && !init.isCompleted) init.completeError(error);
    _initCompleter = null;
    for (final pending in _pending.values) {
      if (!pending.isCompleted) pending.completeError(error);
    }
    _pending.clear();
    _receivePort?.close();
    _receivePort = null;
    _exitPort?.close();
    _exitPort = null;
    _errorPort?.close();
    _errorPort = null;
  }

  Future<void> dispose() async {
    _disposed = true;
    _workerPort?.send({'type': 'close'});
    _receivePort?.close();
    _isolate?.kill(priority: Isolate.immediate);
    _isolate = null;
    _receivePort = null;
    _workerPort = null;
    _failAll(ClassifierException('识别器已关闭'));
  }
}

// ---------------------------------------------------------------------------
// Isolate 侧实现。以下代码运行在后台 isolate 中。
// ---------------------------------------------------------------------------

void _classifierIsolateMain(List<Object?> args) {
  final parent = args[0] as SendPort;
  final modelPath = args[1] as String;

  Interpreter? interpreter;
  try {
    final options = InterpreterOptions()..threads = 4;
    interpreter = Interpreter.fromFile(File(modelPath), options: options);

    final input = interpreter.getInputTensor(0);
    final output = interpreter.getOutputTensor(0);
    if (input.shape.length != 4 ||
        input.shape[1] != ScreenPhotoClassifier._inputSize ||
        input.shape[2] != ScreenPhotoClassifier._inputSize ||
        input.shape[3] != 3 ||
        output.shape.last != ScreenPhotoClassifier._numClasses) {
      throw StateError('模型输入/输出形状不符：in=${input.shape} out=${output.shape}');
    }

    final reply = ReceivePort();
    parent.send({'type': 'ready', 'port': reply.sendPort});

    reply.listen((message) {
      if (message is! Map) return;
      switch (message['type']) {
        case 'classify':
          final id = message['id'] as int;
          try {
            final bytes = message['bytes'] as Uint8List;
            final logits = _infer(interpreter!, bytes);
            parent.send({
              'type': 'result',
              'id': id,
              ..._classify(logits),
            });
          } catch (e) {
            parent.send({'type': 'error', 'id': id, 'error': '$e'});
          }
        case 'close':
          interpreter?.close();
          reply.close();
          Isolate.exit();
      }
    });
  } catch (e) {
    parent.send({'type': 'init_error', 'error': '$e'});
    interpreter?.close();
  }
}

/// 缩略图 → 224×224 中心裁剪 RGB，取值 [0, 1]。
Float32List _preprocess(Uint8List bytes) {
  final decoded = img.decodeImage(bytes);
  if (decoded == null) {
    throw StateError('缩略图解码失败');
  }
  final side = math.min(decoded.width, decoded.height);
  final cropped = img.copyCrop(
    decoded,
    x: (decoded.width - side) ~/ 2,
    y: (decoded.height - side) ~/ 2,
    width: side,
    height: side,
  );
  final resized = img.copyResize(
    cropped,
    width: ScreenPhotoClassifier._inputSize,
    height: ScreenPhotoClassifier._inputSize,
    interpolation: img.Interpolation.linear,
  );
  final rgb = resized.getBytes(order: img.ChannelOrder.rgb);
  final floats = Float32List(rgb.length);
  for (var i = 0; i < rgb.length; i++) {
    floats[i] = rgb[i] / 255.0;
  }
  return floats;
}

Float32List _infer(Interpreter interpreter, Uint8List jpegBytes) {
  final input = _preprocess(jpegBytes);
  final inputTensor = interpreter.getInputTensor(0);
  inputTensor.data = input.buffer.asUint8List(
    input.offsetInBytes,
    input.lengthInBytes,
  );
  interpreter.invoke();
  final outputBytes = interpreter.getOutputTensor(0).data;
  final view = outputBytes.buffer.asFloat32List(
    outputBytes.offsetInBytes,
    ScreenPhotoClassifier._numClasses,
  );
  return Float32List.fromList(view);
}

Map<String, Object> _classify(Float32List logits) {
  var maxLogit = double.negativeInfinity;
  for (final value in logits) {
    if (value > maxLogit) maxLogit = value;
  }
  var sum = 0.0;
  final probabilities = <String, double>{};
  const categories = [
    RecognitionConfig.categoryScreenshot,
    RecognitionConfig.categoryScreenPhoto,
    RecognitionConfig.categoryOther,
  ];
  for (var i = 0; i < categories.length; i++) {
    final e = math.exp(logits[i] - maxLogit);
    probabilities[categories[i]] = e;
    sum += e;
  }
  var bestCategory = RecognitionConfig.categoryOther;
  var bestProb = -1.0;
  for (final entry in probabilities.entries) {
    final p = entry.value / sum;
    probabilities[entry.key] = p;
    if (p > bestProb) {
      bestProb = p;
      bestCategory = entry.key;
    }
  }
  return {
    'category': bestCategory,
    'confidence': bestProb,
    'scores': probabilities,
  };
}
