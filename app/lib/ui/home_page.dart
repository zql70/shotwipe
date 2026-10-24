import 'package:flutter/material.dart';

import '../core/recognition_config.dart';
import '../data/app_database.dart';
import '../data/media_repository.dart';
import '../domain/scan_service.dart';
import 'results_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({
    super.key,
    required this.db,
    required this.repo,
    required this.scanner,
  });

  final AppDatabase db;
  final MediaRepository repo;
  final ScanService scanner;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _screenshots = 0;
  int _screenPhotos = 0;
  int _indexed = 0;
  bool _scanning = false;
  int _processed = 0;
  int _total = 0;
  int _classified = 0;
  String _phase = '';
  String? _error;

  @override
  void initState() {
    super.initState();
    _refreshCounts();
  }

  Future<void> _refreshCounts() async {
    final rows = await widget.db.allRows();
    if (!mounted) return;
    setState(() {
      _indexed = rows.length;
      _screenshots = rows
          .where(
            (r) =>
                r.state == RecognitionConfig.stateScanned &&
                r.category == RecognitionConfig.categoryScreenshot &&
                r.source == RecognitionConfig.sourceMetadata,
          )
          .length;
      _screenPhotos = rows
          .where(
            (r) =>
                r.state == RecognitionConfig.stateScanned &&
                r.category == RecognitionConfig.categoryScreenPhoto &&
                r.source == RecognitionConfig.sourceModel &&
                r.confidence >= RecognitionConfig.suspiciousThreshold,
          )
          .length;
    });
  }

  Future<void> _scan() async {
    setState(() {
      _scanning = true;
      _processed = 0;
      _total = 0;
      _classified = 0;
      _phase = '正在读取图库…';
      _error = null;
    });
    try {
      final ok = await widget.repo.ensurePermission();
      if (!ok) {
        setState(() => _error = '需要照片「完全访问」权限才能扫描');
        return;
      }
      final summary = await widget.scanner.scan(
        onProgress: (p) {
          if (!mounted) return;
          if (p.phase != 'collecting' &&
              p.phase != 'model' &&
              p.processed - _processed < 5) {
            return;
          }
          setState(() {
            _processed = p.processed;
            _total = p.total;
            _classified = p.classified;
            _phase = switch (p.phase) {
              'collecting' => '正在读取图库…',
              'model' => '正在加载识别模型…',
              _ => _classified > 0 ? '正在识别 $_classified 张…' : '正在扫描图库…',
            };
          });
        },
      );
      await _refreshCounts();
      if (!mounted) return;
      if (summary.modelError != null) {
        setState(() => _error = '部分图片未识别：${summary.modelError}');
      }
      if (summary.cancelled) {
        _showSnack('已暂停，可再次扫描继续');
        return;
      }
      if (_screenshots + _screenPhotos == 0) {
        _showSnack('没有发现可清理的截图或屏摄图');
        return;
      }
      await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ResultsPage(db: widget.db, repo: widget.repo),
        ),
      );
      await _refreshCounts();
    } catch (e) {
      if (mounted) setState(() => _error = '扫描失败：$e');
    } finally {
      if (mounted) setState(() => _scanning = false);
    }
  }

  Future<void> _viewResults() async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ResultsPage(db: widget.db, repo: widget.repo),
      ),
    );
    await _refreshCounts();
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final actionable = _screenshots + _screenPhotos;
    return Scaffold(
      appBar: AppBar(title: const Text('ShotWipe · 屏净')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: _scanning
              ? _buildScanning(theme)
              : _buildIdle(theme, actionable),
        ),
      ),
    );
  }

  Widget _buildIdle(ThemeData theme, int actionable) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Spacer(),
        Icon(
          Icons.photo_library_outlined,
          size: 72,
          color: theme.colorScheme.primary,
        ),
        const SizedBox(height: 20),
        Text(
          actionable > 0 ? '发现 $actionable 张可清理' : '清理相册里的截图与屏摄图',
          textAlign: TextAlign.center,
          style: theme.textTheme.headlineSmall,
        ),
        const SizedBox(height: 12),
        if (actionable > 0)
          Text(
            '截图 $_screenshots 张 · 屏摄图 $_screenPhotos 张',
            textAlign: TextAlign.center,
            style: theme.textTheme.titleMedium,
          )
        else
          Text(
            '截图靠系统元数据识别，屏摄图由端上模型识别。\n照片不会离开你的手机。',
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        if (_indexed > 0) ...[
          const SizedBox(height: 8),
          Text(
            '已索引 $_indexed 张图片',
            textAlign: TextAlign.center,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
        const SizedBox(height: 32),
        FilledButton.icon(
          onPressed: _scan,
          icon: const Icon(Icons.search),
          label: Text(actionable > 0 ? '重新扫描' : '开始扫描'),
        ),
        if (actionable > 0) ...[
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _viewResults,
            icon: const Icon(Icons.photo_library_outlined),
            label: Text('查看上次扫描结果（$actionable 张）'),
          ),
        ],
        if (_error != null) ...[
          const SizedBox(height: 16),
          Text(
            _error!,
            textAlign: TextAlign.center,
            style: TextStyle(color: theme.colorScheme.error),
          ),
        ],
        const Spacer(flex: 2),
      ],
    );
  }

  Widget _buildScanning(ThemeData theme) {
    final progress = _total > 0 ? _processed / _total : null;
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.auto_awesome, size: 56, color: theme.colorScheme.primary),
        const SizedBox(height: 20),
        Text('正在扫描', style: theme.textTheme.headlineSmall),
        const SizedBox(height: 16),
        LinearProgressIndicator(value: progress, minHeight: 8),
        const SizedBox(height: 12),
        Text(
          _phase,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        if (_total > 0) ...[
          const SizedBox(height: 4),
          Text('$_processed / $_total 张'),
        ],
        const SizedBox(height: 24),
        TextButton(onPressed: widget.scanner.cancel, child: const Text('暂停')),
        const SizedBox(height: 8),
        Text(
          '首次扫描需要逐张识别，耗时取决于机型和图库大小；可随时暂停',
          textAlign: TextAlign.center,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}
