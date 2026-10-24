import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:photo_manager/photo_manager.dart';

import '../core/recognition_config.dart';
import '../data/app_database.dart';
import '../data/media_repository.dart';
import '../domain/protect_rules.dart';

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

class _ResultsPageState extends State<ResultsPage> {
  List<_Item> _screenshots = [];
  List<_Item> _screenPhotos = [];
  final _selected = <String>{};
  final _sizeCache = <String, int>{};
  int _selectedBytes = 0;
  bool _loading = true;

  int get _actionableCount => _screenshots.length + _screenPhotos.length;

  List<_Item> get _allItems => [..._screenshots, ..._screenPhotos];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final rows = await widget.db.activeRows();
    final screenshots = <_Item>[];
    final screenPhotos = <_Item>[];
    final missing = <String>[];

    for (final row in rows) {
      if (!RecognitionConfig.isActionableCategory(row.category)) continue;
      // 模型判出的「截图」不可信（实测会把山景/普通照片当成截图），
      // 截图 Tab 只展示系统元数据命中；屏幕类结果只在屏摄 Tab 展示。
      if (row.category == RecognitionConfig.categoryScreenshot &&
          row.source != RecognitionConfig.sourceMetadata) {
        continue;
      }
      if (row.category == RecognitionConfig.categoryScreenPhoto &&
          row.source != RecognitionConfig.sourceModel) {
        continue;
      }
      if (row.source != RecognitionConfig.sourceMetadata &&
          row.confidence < RecognitionConfig.suspiciousThreshold) {
        continue;
      }
      final entity = await widget.repo.loadAsset(row.platformId);
      if (entity == null) {
        missing.add(row.platformId);
        continue;
      }
      final item = _Item(row, entity);
      if (row.category == RecognitionConfig.categoryScreenshot) {
        screenshots.add(item);
      } else {
        screenPhotos.add(item);
      }
    }
    if (missing.isNotEmpty) {
      await widget.db.markState(missing, RecognitionConfig.stateDeleted);
    }
    screenshots.sort((a, b) => b.row.takenAtMs.compareTo(a.row.takenAtMs));
    screenPhotos.sort((a, b) => b.row.takenAtMs.compareTo(a.row.takenAtMs));

    final now = DateTime.now();
    for (final item in [...screenshots, ...screenPhotos]) {
      if (item.isConfirmed &&
          ProtectRules.shouldAutoSelect(item.row, item.entity, now)) {
        _selected.add(item.id);
      }
    }

    if (!mounted) return;
    setState(() {
      _screenshots = screenshots;
      _screenPhotos = screenPhotos;
      _loading = false;
    });
    _updateSize();
  }

  Future<void> _updateSize() async {
    var total = 0;
    for (final id in _selected) {
      var size = _sizeCache[id];
      if (size == null) {
        AssetEntity? entity;
        for (final item in _allItems) {
          if (item.id == id) {
            entity = item.entity;
            break;
          }
        }
        if (entity == null) continue;
        try {
          size = await entity.fileSize;
        } catch (_) {
          size = 0;
        }
        _sizeCache[id] = size;
      }
      total += size;
    }
    if (mounted) setState(() => _selectedBytes = total);
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

  void _toggleSelectAll() {
    // 只批量选择系统元数据截图；模型结果必须逐张人工确认。
    final selectable = _autoSelectableItems;
    final allSelected =
        selectable.isNotEmpty &&
        selectable.every((i) => _selected.contains(i.id));
    setState(() {
      for (final item in selectable) {
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
    final targets = _allItems.where((i) => _selected.contains(i.id)).toList();
    if (targets.isEmpty) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除所选照片？'),
        content: Text(
          '共 ${targets.length} 张 · 约 ${_formatBytes(_selectedBytes)}。\n'
          '下一步会弹出系统确认框。\n'
          '删除后照片会进入系统「最近删除」/回收站（通常保留 30 天），'
          '需要彻底释放空间时请到系统相册里清空。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text('删除 ${targets.length} 张'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
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

  Future<void> _showItemActions(_Item item) async {
    final action = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: Text('这张不是${item.categoryLabel}？'),
              subtitle: Text(
                '${item.isMetadata ? '系统元数据识别' : '端上模型识别'} · 置信度 ${item.confidencePercent}%',
              ),
            ),
            const Divider(height: 1),
            ListTile(
              leading: const Icon(Icons.block_outlined),
              title: Text('不是${item.categoryLabel}'),
              subtitle: const Text('移出列表并记录纠错，以后不再推荐'),
              onTap: () => Navigator.pop(context, 'correct'),
            ),
            ListTile(
              leading: const Icon(Icons.bookmark_border),
              title: const Text('保留这张'),
              subtitle: const Text('移出列表，以后不再推荐'),
              onTap: () => Navigator.pop(context, 'keep'),
            ),
          ],
        ),
      ),
    );
    if (action == 'correct') {
      await _correct(item);
    } else if (action == 'keep') {
      await _keep(item);
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
      _screenPhotos.removeWhere((i) => ids.contains(i.id));
      _selected.removeAll(ids);
    });
    _updateSize();
  }

  Future<void> _openPreview(_Item item) async {
    final action = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            const Expanded(child: Text('疑似屏摄图')),
            Text(
              '${item.confidencePercent}%',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Theme.of(context).colorScheme.tertiary,
              ),
            ),
          ],
        ),
        content: SizedBox(
          width: 260,
          height: 260,
          child: AspectRatio(
            aspectRatio: 1,
            child: FutureBuilder<Uint8List?>(
              future: item.entity.thumbnailDataWithSize(
                const ThumbnailSize(1024, 1024),
                quality: 90,
              ),
              builder: (context, snapshot) {
                final data = snapshot.data;
                if (data == null) {
                  return const ColoredBox(color: Color(0xFFE0E0E0));
                }
                return Image.memory(data, fit: BoxFit.contain);
              },
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('关闭'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, 'correct'),
            child: const Text('这不是屏摄图'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, 'select'),
            child: Text(_selected.contains(item.id) ? '取消选择' : '选入清理'),
          ),
        ],
      ),
    );
    if (action == 'select') {
      _toggle(item);
    } else if (action == 'correct') {
      await _correct(item);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('待清理'),
          actions: [
            TextButton(
              onPressed:
                  _loading || _autoSelectableItems.isEmpty ? null : _toggleSelectAll,
              child: Text(_allAutoSelectableSelected ? '取消全选' : '全选截图'),
            ),
          ],
          bottom: TabBar(
            tabs: [
              Tab(text: '截图 ${_screenshots.length}'),
              Tab(text: '屏摄图 ${_screenPhotos.length}'),
            ],
          ),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : TabBarView(
                children: [
                  _buildTab(
                    _screenshots,
                    category: RecognitionConfig.categoryScreenshot,
                  ),
                  _buildTab(
                    _screenPhotos,
                    category: RecognitionConfig.categoryScreenPhoto,
                  ),
                ],
              ),
        bottomNavigationBar: _selected.isEmpty
            ? null
            : SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: FilledButton.icon(
                    onPressed: _deleteSelected,
                    icon: const Icon(Icons.delete_outline),
                    label: Text(
                      '删除所选 ${_selected.length} 张 · 约 ${_formatBytes(_selectedBytes)}',
                    ),
                  ),
                ),
              ),
      ),
    );
  }

  List<_Item> get _autoSelectableItems => _allItems
      .where((i) => i.row.source == RecognitionConfig.sourceMetadata)
      .toList();

  bool get _allAutoSelectableSelected {
    final selectable = _autoSelectableItems;
    return selectable.isNotEmpty &&
        selectable.every((i) => _selected.contains(i.id));
  }

  Widget _buildTab(List<_Item> items, {required String category}) {
    if (items.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle_outline, size: 56),
            const SizedBox(height: 12),
            Text(
              category == RecognitionConfig.categoryScreenshot
                  ? '没有待清理的截图 🎉'
                  : '没有发现屏摄图 🎉',
            ),
          ],
        ),
      );
    }
    final confirmed = items.where((i) => i.isConfirmed).toList();
    final suspicious = items.where((i) => !i.isConfirmed).toList();
    final isScreenshotTab =
        category == RecognitionConfig.categoryScreenshot;
    final selectedCount =
        confirmed.where((i) => _selected.contains(i.id)).length;
    final confirmedTitle = isScreenshotTab ? '确定' : '模型候选';
    final confirmedSubtitle = isScreenshotTab
        ? (selectedCount > 0
            ? '系统截图已按保护规则自动勾选 $selectedCount 张'
            : '最近 7 天或收藏的截图不会自动勾选')
        : (selectedCount > 0
            ? '已手动勾选 $selectedCount 张，请确认无误'
            : '模型结果默认不勾选，请逐张确认后再删除');
    return CustomScrollView(
      slivers: [
        if (confirmed.isNotEmpty)
          ..._buildTier(
            title: confirmedTitle,
            subtitle: confirmedSubtitle,
            items: confirmed,
            color: Theme.of(context).colorScheme.primary,
          ),
        if (suspicious.isNotEmpty)
          ..._buildTier(
            title: '疑似',
            subtitle: '默认不勾选，点按查看大图后再决定',
            items: suspicious,
            color: Theme.of(context).colorScheme.tertiary,
          ),
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
      onTap: () => item.isConfirmed ? _toggle(item) : _openPreview(item),
      onLongPress: () => _showItemActions(item),
      child: Stack(
        fit: StackFit.expand,
        children: [
          FutureBuilder<Uint8List?>(
            future: item.entity.thumbnailDataWithSize(
              const ThumbnailSize.square(256),
              quality: 85,
            ),
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
                child: Icon(Icons.check_circle, color: Colors.white),
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
