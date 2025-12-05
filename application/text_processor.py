"""テキスト後処理パイプライン"""

import logging
import re
from pathlib import Path
from typing import List

from config.settings import AppSettings
from domain.exceptions import TextProcessingError
from domain.models import ReplacementRule

logger = logging.getLogger(__name__)


class TextPostProcessor:
    """テキスト後処理パイプライン"""

    def __init__(self, settings: AppSettings):
        self._settings = settings
        self._use_punctuation = settings.recording.use_punctuation
        self._replacement_rules: List[ReplacementRule] = []

        # 置換ルールをロード
        self.reload_replacements()

        logger.info("TextPostProcessor 初期化完了")

    def process(self, text: str) -> str:
        """メイン処理パイプライン"""
        if not text:
            return text

        try:
            # 1. 句読点処理
            text = self._apply_punctuation_rules(text)

            # 2. 置換ルール適用
            text = self._apply_replacements(text)

            return text

        except Exception as e:
            logger.error(f"テキスト処理エラー: {e}", exc_info=True)
            raise TextProcessingError(f"処理失敗: {e}")

    def _apply_punctuation_rules(self, text: str) -> str:
        """句読点処理を適用"""
        if not self._use_punctuation:
            # 句読点を削除
            text = text.replace("。", "")
            text = text.replace("、", "")
            logger.debug("句読点を削除しました")

        return text

    def _apply_replacements(self, text: str) -> str:
        """置換ルールを適用"""
        if not self._replacement_rules:
            return text

        original_text = text

        for rule in self._replacement_rules:
            try:
                if rule.is_regex:
                    # 正規表現置換
                    text = re.sub(rule.pattern, rule.replacement, text)
                else:
                    # 完全一致置換
                    text = text.replace(rule.pattern, rule.replacement)

            except Exception as e:
                logger.error(f"置換ルール適用エラー: {rule} - {e}")
                continue

        if text != original_text:
            logger.debug(f"置換適用: '{original_text}' → '{text}'")

        return text

    def reload_replacements(self):
        """置換ルールを再読み込み"""
        replacements_file = self._settings.paths.replacements_file

        if not replacements_file.exists():
            logger.warning(f"置換ルールファイルが見つかりません: {replacements_file}")
            self._replacement_rules = []
            return

        try:
            self._replacement_rules = self._load_replacements_from_file(
                replacements_file
            )
            logger.info(f"置換ルール読み込み完了: {len(self._replacement_rules)}件")

        except Exception as e:
            logger.error(f"置換ルール読み込みエラー: {e}", exc_info=True)
            raise TextProcessingError(f"置換ルール読み込み失敗: {e}")

    def _load_replacements_from_file(self, file_path: Path) -> List[ReplacementRule]:
        """ファイルから置換ルールをロード"""
        rules = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()

                    # 空行とコメント行をスキップ
                    if not line or line.startswith("#"):
                        continue

                    # タブ区切りで分割
                    parts = line.split("\t")
                    if len(parts) < 2:
                        logger.warning(
                            f"無効な行をスキップ (行{line_num}): {line}"
                        )
                        continue

                    pattern = parts[0]
                    replacement = parts[1]

                    # 正規表現フラグ（オプション）
                    is_regex = len(parts) >= 3 and parts[2].lower() == "regex"

                    rule = ReplacementRule(
                        pattern=pattern, replacement=replacement, is_regex=is_regex
                    )
                    rules.append(rule)
                    logger.debug(f"ルール追加: {rule}")

            logger.info(f"{len(rules)}件の置換ルールを読み込みました")
            return rules

        except Exception as e:
            logger.error(f"ファイル読み込みエラー: {e}")
            raise

    def set_punctuation_enabled(self, enabled: bool):
        """句読点使用を設定"""
        self._use_punctuation = enabled
        logger.info(f"句読点使用: {enabled}")

    @property
    def use_punctuation(self) -> bool:
        """句読点を使用するか"""
        return self._use_punctuation

    @property
    def replacement_count(self) -> int:
        """登録されている置換ルール数"""
        return len(self._replacement_rules)
