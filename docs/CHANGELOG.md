# 変更履歴

このプロジェクトのすべての重要な変更は、このファイルに記録されています。
このファイルは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づいており、
[セマンティック バージョニング](https://semver.org/lang/ja/) を使用しています。

## [Unreleased]

### 追加
- docs/README.md を新規追加し、プロジェクト概要と使用方法を文書化

### 変更
- APIプロバイダーの取得処理を削除し、ElevenLabs APIへの統一を完了
- recording_controller でUIコールバックを直接実行するように変更
- 設定ファイルのAPIセクションを削除し、設定を整理
- バージョンを 0.0.0 から 0.0.1 に更新

### 削除
- 設定ファイル内の不要なAPIセクションを削除

## [0.0.0] - 2025-12-03

### 追加
- VoiceScribe プロジェクトを初期化
- ElevenLabs Speech-to-Text APIのサポートを追加
- Windows での音声入力と自動テキスト貼り付け機能を実装

[Unreleased]: https://github.com/yourusername/VoiceScribe/compare/v0.0.0...HEAD
[0.0.0]: https://github.com/yourusername/VoiceScribe/releases/tag/v0.0.0
