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
      // 品牌色试验中：以薄荷绿 #8BFFE0 为种子生成整套配色；
      // 选中角标等处仍直接使用 #8BFFE0 / #10263C 品牌常量。
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF8BFFE0)),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF8BFFE0),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: HomePage(db: db, repo: repo, scanner: scanner),
    );
  }
}
