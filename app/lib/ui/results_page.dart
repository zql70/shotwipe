import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:photo_manager/photo_manager.dart';

import '../core/recognition_config.dart';
import '../data/app_database.dart';
import '../data/media_repository.dart';
import '../domain/results_grouper.dart';

class ResultsPage extends StatefulWidget {
  const ResultsPage({super.key, required this.db, required this.repo});

  final AppDatabase db;
  final MediaRepository repo;

  @override
  State<ResultsPage> createState() => _ResultsPageState();
}

class _Item {
  _Item(this.row, this.entity);

  final ScannedAsset row;
  final AssetEntity entity;

  /// 缩略图/预览图的 Future 只创建一次并缓存。
  /// FutureBuilder 若在每次 rebuild 时拿到新 Future，会先回到等待态
  /// （灰底占位）再恢复图片——点选/切选项时整个网格就会闪一下。
  late final Future<Uint8List?> thumbnail = entity.thumbnailDataWithSize(
    const ThumbnailSize.square(256),
    quality: 85,
  );
  late final Future<Uint8List?> preview = entity.thumbnailDataWithSize(
    const ThumbnailSize(1280, 1280),
    quality: 92,
  );

  String get id => row.platformId;
  bool get isMetadata => row.source == RecognitionConfig.sourceMetadata;
  bool get isConfirmed => RecognitionConfig.isConfirmed(
    source: row.source,
    confidence: row.confidence,
  );
  int get confidencePercent => (row.confidence * 100).round();
  String get categoryLabel =>
      row.category == RecognitionConfig.categoryScreenshot
      ? '截图'
      : row.category == RecognitionConfig.categoryScreenPhoto
      ? '屏摄图'
      : '照片';
}

class _MonthGroup {
  _MonthGroup(this.key, this.items);

  final DateTime key;
  final List<_Item> items;
}

class _ResultsPageState extends State<ResultsPage>
    with SingleTickerProviderStateMixin {
  List<_Item> _screenshots = [];
  List<_Item> _candidates = [];
  List<_Item> _suspects = [];
  final _selected = <String>{};
  final _sizeCache = <String, int>{};
  bool _loading = true;
  late final TabController _tabController;
  int _lastTabIndex = 0;

  static const _tabNames = ['截图', '屏摄图', '疑似'];

  int get _actionableCount =>
      _screenshots.length + _candidates.length + _suspects.length;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _tabController.addListener(_onTabChanged);
    _load();
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _tabController.dispose();
    super.dispose();
  }

  void _onTabChanged() {
    if (_tabController.index == _lastTabIndex) return;
    _lastTabIndex = _tabController.index;
    if (mounted) {
      setState(() {});
      _updateSize();
    }
  }

  Future<void> _load() async {
    final rows = await widget.db.activeRows();
    final screenshots = <_Item>[];
    final candidates = <_Item>[];
    final suspects = <_Item>[];
    final missing = <String>[];

    for (final row in rows) {
      // 分桶规则见 domain/results_grouper.dart（模型截图不展示、<0.35 过滤等）。
      final bucket = resultBucket(row);
      if (bucket == ResultBucket.hidden) continue;
      final entity = await widget.repo.loadAsset(row.platformId);
      if (entity == null) {
        missing.add(row.platformId);
        continue;
      }
      final item = _Item(row, entity);
      switch (bucket) {
        case ResultBucket.screenshot:
          screenshots.add(item);
        case ResultBucket.candidate:
          candidates.add(item);
        case ResultBucket.suspect:
          suspects.add(item);
        case ResultBucket.hidden:
          break;
      }
    }
    if (missing.isNotEmpty) {
      await widget.db.markState(missing, RecognitionConfig.stateDeleted);
    }
    screenshots.sort((a, b) => b.row.takenAtMs.compareTo(a.row.takenAtMs));
    candidates.sort((a, b) => b.row.takenAtMs.compareTo(a.row.takenAtMs));
    suspects.sort((a, b) => b.row.takenAtMs.compareTo(a.row.takenAtMs));

    // 不做任何默认勾选：勾选和全选都由用户主动完成（包括截图）。
    _selected.clear();

    if (!mounted) return;
    setState(() {
      _screenshots = screenshots;
      _candidates = candidates;
      _suspects = suspects;
      _loading = false;
    });
    _updateSize();
  }

  /// 当前 Tab 的选中项：底栏统计与删除都只作用于当前 Tab。
  List<_Item> get _tabSelected =>
      _tabItems.where((i) => _selected.contains(i.id)).toList();

  int get _tabSelectedBytes => _tabSelected.fold(
    0,
    (sum, i) => sum + (_sizeCache[i.id] ?? 0),
  );

  Future<void> _updateSize() async {
    final pending = _tabSelected
        .where((i) => !_sizeCache.containsKey(i.id))
        .toList();
    for (final item in pending) {
      try {
        _sizeCache[item.id] = await item.entity.fileSize;
      } catch (_) {
        _sizeCache[item.id] = 0;
      }
    }
    if (pending.isNotEmpty && mounted) setState(() {});
  }

  void _toggle(_Item item) {
    setState(() {
      if (_selected.contains(item.id)) {
        _selected.remove(item.id);
      } else {
        _selected.add(item.id);
      }
    });
    _updateSize();
  }

  List<_Item> get _tabItems => switch (_tabController.index) {
    0 => _screenshots,
    1 => _candidates,
    _ => _suspects,
  };

  bool get _allTabSelected {
    final items = _tabItems;
    return items.isNotEmpty && items.every((i) => _selected.contains(i.id));
  }

  // 全选作用于当前 Tab（截图/屏摄图/疑似）。这是用户的显式操作，
  // 允许批量勾选模型结果；页面加载时不做任何默认勾选。
  void _toggleSelectAll() {
    final items = _tabItems;
    final allSelected = _allTabSelected;
    setState(() {
      for (final item in items) {
        if (allSelected) {
          _selected.remove(item.id);
        } else {
          _selected.add(item.id);
        }
      }
    });
    _updateSize();
  }

  String _formatBytes(int bytes) {
    if (bytes >= 1024 * 1024 * 1024) {
      return '${(bytes / 1024 / 1024 / 1024).toStringAsFixed(1)} GB';
    }
    if (bytes >= 1024 * 1024) {
      return '${(bytes / 1024 / 1024).toStringAsFixed(1)} MB';
    }
    return '${(bytes / 1024).toStringAsFixed(0)} KB';
  }

  Future<void> _deleteSelected() async {
    final targets = _tabSelected;
    if (targets.isEmpty) return;

    try {
      // 只保留系统删除确认弹窗（Android createDeleteRequest / iOS 系统删除），
      // App 内不再加一层确认。
      final deletedIds = await widget.repo.delete(
        targets.map((i) => i.entity).toList(),
      );
      if (deletedIds.isEmpty) {
        if (mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('未删除任何照片')));
        }
        return;
      }
      await widget.db.markState(deletedIds, RecognitionConfig.stateDeleted);
      _removeItems(deletedIds.toSet());
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('已删除'),
          content: Text(
            '本次删除 ${deletedIds.length} 张。\n'
            '照片已进入系统「最近删除」/回收站，30 天内可恢复；'
            '到系统相册清空后才能释放空间。',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('完成'),
            ),
          ],
        ),
      );
      if (mounted && _actionableCount == 0) Navigator.pop(context);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('删除失败：$e')));
      }
    }
  }

  Future<void> _correct(_Item item) async {
    await widget.db.recordCorrection(
      row: item.row,
      correctedLabel: RecognitionConfig.categoryOther,
    );
    _removeItems({item.id});
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('已记录：这张不是${item.categoryLabel}')));
  }

  Future<void> _keep(_Item item) async {
    await widget.db.markState([item.id], RecognitionConfig.stateKept);
    _removeItems({item.id});
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('已保留，以后不再推荐')));
  }

  void _removeItems(Set<String> ids) {
    if (ids.isEmpty) return;
    setState(() {
      _screenshots.removeWhere((i) => ids.contains(i.id));
      _candidates.removeWhere((i) => ids.contains(i.id));
      _suspects.removeWhere((i) => ids.contains(i.id));
      _selected.removeAll(ids);
    });
    _updateSize();
  }

  /// 长按任意图片：大图预览 + 保留/纠错两选项（点选高亮）+ 右侧确认生效。
  Future<void> _openPreview(_Item item) async {
    final title = item.row.category == RecognitionConfig.categoryScreenshot
        ? '截图'
        : item.isConfirmed
        ? '屏摄图'
        : '疑似屏摄图';
    const keepDesc = '移出列表，以后不再推荐';
    final correctDesc = '移出列表并记录纠错，帮助模型改进';
    String? choice;

    final action = await showDialog<String>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => Dialog(
          insetPadding: const EdgeInsets.symmetric(
            horizontal: 20,
            vertical: 24,
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    Text(
                      '${item.confidencePercent}%',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: Theme.of(context).colorScheme.tertiary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      maxHeight: MediaQuery.of(context).size.height * 0.5,
                    ),
                    child: FutureBuilder<Uint8List?>(
                      future: item.preview,
                      builder: (context, snapshot) {
                        final data = snapshot.data;
                        if (data == null) {
                          return const AspectRatio(
                            aspectRatio: 1,
                            child: ColoredBox(color: Color(0xFFE0E0E0)),
                          );
                        }
                        return Image.memory(data, fit: BoxFit.contain);
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 6),
                const Divider(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Flexible(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: _previewOption(
                          context,
                          label: '保留这张',
                          value: 'keep',
                          groupValue: choice,
                          onSelected: (v) =>
                              setDialogState(() => choice = v),
                        ),
                      ),
                    ),
                    Flexible(
                      child: FittedBox(
                        fit: BoxFit.scaleDown,
                        child: _previewOption(
                          context,
                          label: '不是${item.categoryLabel}',
                          value: 'correct',
                          groupValue: choice,
                          onSelected: (v) =>
                              setDialogState(() => choice = v),
                        ),
                      ),
                    ),
                    FilledButton(
                      onPressed: choice == null
                          ? null
                          : () => Navigator.pop(context, choice),
                      child: const Text('确认'),
                    ),
                  ],
                ),
                SizedBox(
                  height: 20,
                  child: Text(
                    switch (choice) {
                      'keep' => keepDesc,
                      'correct' => correctDesc,
                      _ => '',
                    },
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
    if (action == 'correct') {
      await _correct(item);
    } else if (action == 'keep') {
      await _keep(item);
    }
  }

  /// 预览弹窗选项：选中与未选中使用同一几何（同一 TextButton），
  /// 只切换底色/前景色，避免按钮大小或位置跳动。
  Widget _previewOption(
    BuildContext context, {
    required String label,
    required String value,
    required String? groupValue,
    required ValueChanged<String> onSelected,
  }) {
    final selected = value == groupValue;
    final scheme = Theme.of(context).colorScheme;
    return TextButton(
      onPressed: () => onSelected(value),
      style: TextButton.styleFrom(
        backgroundColor: selected ? scheme.primary : null,
        foregroundColor: selected ? scheme.onPrimary : scheme.primary,
      ),
      child: Text(label),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('待清理'),
        actions: [
          TextButton(
            onPressed: _loading || _tabItems.isEmpty ? null : _toggleSelectAll,
            child: Text(
              _allTabSelected
                  ? '取消全选'
                  : '全选${_tabNames[_tabController.index]}',
            ),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          tabs: [
            Tab(text: '截图 ${_screenshots.length}'),
            Tab(text: '屏摄图 ${_candidates.length}'),
            Tab(text: '疑似 ${_suspects.length}'),
          ],
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildScreenshotsTab(),
                _buildCandidatesTab(),
                _buildSuspectsTab(),
              ],
            ),
      bottomNavigationBar: _tabSelected.isEmpty
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: FilledButton.icon(
                  onPressed: _deleteSelected,
                  icon: const Icon(Icons.delete_outline),
                  label: Text(
                    '删除所选 ${_tabSelected.length} 张 · 约 ${_formatBytes(_tabSelectedBytes)}',
                  ),
                ),
              ),
            ),
    );
  }

  Widget _buildScreenshotsTab() {
    final selectedCount = _screenshots
        .where((i) => _selected.contains(i.id))
        .length;
    return _buildTab(
      items: _screenshots,
      emptyText: '没有待清理的截图 🎉',
      title: '确定',
      subtitle: selectedCount > 0
          ? '已勾选 $selectedCount 张'
          : '系统元数据识别，点按勾选或右上角全选',
      color: Theme.of(context).colorScheme.primary,
    );
  }

  Widget _buildCandidatesTab() {
    return _buildTab(
      items: _candidates,
      emptyText: '没有发现屏摄图 🎉',
      title: '模型候选',
      subtitle: '点击勾选，长按可预览大图，请逐张确认后再删除',
      color: Theme.of(context).colorScheme.primary,
    );
  }

  Widget _buildSuspectsTab() {
    return _buildTab(
      items: _suspects,
      emptyText: '没有疑似屏摄图 🎉',
      title: '疑似',
      subtitle: '点击勾选，长按可预览大图，请逐张确认后再删除',
      color: Theme.of(context).colorScheme.tertiary,
    );
  }

  Widget _buildTab({
    required List<_Item> items,
    required String emptyText,
    required String title,
    required String subtitle,
    required Color color,
  }) {
    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle_outline, size: 56),
            const SizedBox(height: 12),
            Text(emptyText),
          ],
        ),
      );
    }
    return CustomScrollView(
      slivers: [
        ..._buildTier(title: title, subtitle: subtitle, items: items, color: color),
        const SliverToBoxAdapter(child: SizedBox(height: 24)),
      ],
    );
  }

  List<Widget> _buildTier({
    required String title,
    required String subtitle,
    required List<_Item> items,
    required Color color,
  }) {
    final groups = _groupByMonth(items);
    return [
      SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                title == '疑似' ? Icons.help_outline : Icons.verified_outlined,
                size: 20,
                color: color,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$title · ${items.length} 张',
                      style: Theme.of(
                        context,
                      ).textTheme.titleMedium?.copyWith(color: color),
                    ),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
      for (final group in groups) ...[
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
            child: Text(
              '${group.key.year}年${group.key.month}月 · ${group.items.length} 张',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ),
        SliverGrid(
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 4,
            mainAxisSpacing: 4,
            crossAxisSpacing: 4,
          ),
          delegate: SliverChildBuilderDelegate(
            (context, index) => _tile(group.items[index]),
            childCount: group.items.length,
          ),
        ),
      ],
    ];
  }

  List<_MonthGroup> _groupByMonth(List<_Item> items) {
    final groups = <_MonthGroup>[];
    for (final item in items) {
      final d = DateTime.fromMillisecondsSinceEpoch(item.row.takenAtMs);
      final key = DateTime(d.year, d.month);
      final last = groups.isEmpty ? null : groups.last;
      if (last != null && last.key == key) {
        last.items.add(item);
      } else {
        groups.add(_MonthGroup(key, [item]));
      }
    }
    return groups;
  }

  Widget _tile(_Item item) {
    final selected = _selected.contains(item.id);
    return GestureDetector(
      // 点按一律勾选/取消；长按看大图（含纠错/保留）。
      onTap: () => _toggle(item),
      onLongPress: () => _openPreview(item),
      child: Stack(
        fit: StackFit.expand,
        children: [
          FutureBuilder<Uint8List?>(
            future: item.thumbnail,
            builder: (context, snapshot) {
              final data = snapshot.data;
              if (data == null) {
                return const ColoredBox(color: Color(0xFFE0E0E0));
              }
              return Image.memory(data, fit: BoxFit.cover);
            },
          ),
          if (selected)
            const DecoratedBox(
              decoration: BoxDecoration(color: Color(0x66000000)),
              child: Center(
                child: SizedBox(
                  width: 30,
                  height: 30,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: Color(0xFF8BFFE0),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.check, size: 22, color: Color(0xFF10263C)),
                  ),
                ),
              ),
            ),
          if (!item.isConfirmed)
            Positioned(
              right: 4,
              bottom: 4,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 5,
                    vertical: 2,
                  ),
                  child: Text(
                    '${item.confidencePercent}%',
                    style: const TextStyle(color: Colors.white, fontSize: 10),
                  ),
                ),
              ),
            ),
          if (item.isConfirmed && !item.isMetadata)
            const Positioned(
              left: 4,
              top: 4,
              child: Icon(Icons.auto_awesome, size: 14, color: Colors.white70),
            ),
        ],
      ),
    );
  }
}
