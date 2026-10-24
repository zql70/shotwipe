import 'package:flutter/material.dart';

import 'data/app_database.dart';
import 'data/media_repository.dart';
import 'domain/scan_service.dart';
import 'inference/screen_photo_classifier.dart';
import 'ui/home_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final db = AppDatabase();
  final repo = MediaRepository();
  final classifier = ScreenPhotoClassifier();
  final scanner = ScanService(repo, db, classifier);
  runApp(ShotWipeApp(db: db, repo: repo, scanner: scanner));
}

class ShotWipeApp extends StatelessWidget {
  const ShotWipeApp({
    super.key,
    required this.db,
    required this.repo,
    required this.scanner,
  });

  final AppDatabase db;
  final MediaRepository repo;
  final ScanService scanner;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ShotWipe',
      // 品牌色（与 App 图标一致）：主色深海蓝 #10263C，
      // 点缀薄荷绿——浅色模式用加深版保证对比度，深色模式用原色 #8BFFE0。
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF10263C),
        ).copyWith(tertiary: const Color(0xFF0FA98A)),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF10263C),
          brightness: Brightness.dark,
        ).copyWith(tertiary: const Color(0xFF8BFFE0)),
        useMaterial3: true,
      ),
      home: HomePage(db: db, repo: repo, scanner: scanner),
    );
  }
}
