import configparser
import logging
import os
import sys
import threading
import time
from typing import Dict

import pyperclip

from service.safe_paste_sendinput import safe_paste_text, safe_clipboard_copy, is_paste_available
from utils.config_manager import get_config_value

logger = logging.getLogger(__name__)

_clipboard_lock = threading.Lock()


def process_punctuation(text: str, use_punctuation: bool) -> str:
    if use_punctuation:
        return text

    try:
        result = text.replace('。', '').replace('、', '')
        return result
    except (AttributeError, TypeError) as e:
        logging.error(f"句読点処理中にタイプエラー: {str(e)}")
        return text
    except Exception as e:
        logging.error(f"句読点処理中に予期しないエラー: {str(e)}")
        return text


def get_replacements_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, 'replacements.txt')


def load_replacements() -> Dict[str, str]:
    replacements = {}
    file_path = get_replacements_path()
    logging.info(f"置換ルールファイルのパス: {file_path}")

    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()

            for line_number, line in enumerate(lines, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    old, new = line.split(',')
                    replacements[old.strip()] = new.strip()
                    logging.debug(f"置換ルール読み込み - {line_number}行目: '{old.strip()}' → '{new.strip()}'")
                except ValueError:
                    logging.error(f"置換ファイルの{line_number}行目に無効な行があります: {line}")
                    continue

            logging.info(f"置換ルールの総数: {len(replacements)}")
            if len(replacements) > 0:
                logging.debug("読み込んだ置換ルール:")
                for old, new in replacements.items():
                    logging.debug(f"  '{old}' → '{new}'")

    except IOError as e:
        logging.error(f"置換ファイルの読み込み中にエラーが発生しました: {e}")
        return {}
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)
        return {}

    return replacements


def replace_text(text: str, replacements: Dict[str, str]) -> str:
    if not text:
        logging.error("入力テキストが空です")
        return ""

    if not replacements:
        logging.warning("置換ルールが空です")
        return text

    try:
        result = text
        logging.info(f"テキスト置換開始 - 文字数: {len(text)}")

        for old, new in replacements.items():
            if old in result:
                before_replace = result
                result = result.replace(old, new)
                if before_replace != result:
                    logging.debug(f"置換実行: '{old}' → '{new}'")

        logging.info("テキスト置換完了")
        return result

    except Exception as e:
        logging.error(f"テキスト置換中にエラーが発生: {str(e)}", exc_info=True)
        return text


def copy_and_paste_transcription(
        text: str,
        replacements: Dict[str, str],
        config: configparser.ConfigParser
):
    if not text:
        logging.warning("空のテキスト")
        return

    try:
        replaced_text = replace_text(text, replacements)
        if not replaced_text:
            logging.error("テキスト置換結果が空です")
            return

        if not safe_clipboard_copy(replaced_text):
            raise Exception("クリップボードへのコピーに失敗しました")

        paste_delay = get_config_value(config, 'CLIPBOARD', 'paste_delay', 0.2)

        def delayed_paste():
            try:
                time.sleep(paste_delay)
                if not safe_paste_text():
                    logging.error("貼り付け実行に失敗しました")
            except Exception as paste_error:
                logging.error(f"遅延ペースト中にエラー: {str(paste_error)}", exc_info=True)

        paste_thread = threading.Thread(target=delayed_paste, daemon=True)
        paste_thread.start()

    except Exception as e:
        logging.error(f"コピー&ペースト処理でエラー: {str(e)}", exc_info=True)
        raise


def emergency_clipboard_recovery():
    try:
        with _clipboard_lock:
            pyperclip.copy("")
            time.sleep(0.1)

            test_text = "test"
            pyperclip.copy(test_text)
            time.sleep(0.1)

            if pyperclip.paste() == test_text:
                return True
            else:
                logging.error("クリップボード復旧失敗")
                return False

    except Exception as e:
        logging.error(f"クリップボード復旧中にエラー: {str(e)}")
        return False


def initialize_text_processing():
    try:
        if is_paste_available():
            pass
        else:
            logging.error("貼り付け機能初期化失敗")

        test_result = emergency_clipboard_recovery()
        if not test_result:
            logging.warning("クリップボード初期化テストに失敗しました")

    except Exception as e:
        logging.error(f"モジュール初期化中にエラー: {str(e)}")
