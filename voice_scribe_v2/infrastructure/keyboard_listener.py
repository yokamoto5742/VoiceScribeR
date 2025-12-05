"""グローバルホットキー管理 - PyQt6対応"""

import logging
from typing import Dict, Optional

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import HotkeySettings
from domain.exceptions import HotkeyRegistrationError

logger = logging.getLogger(__name__)


class GlobalHotkeyManager(QObject):
    """グローバルホットキー管理"""

    # Signal定義
    toggle_recording_pressed = pyqtSignal()
    toggle_punctuation_pressed = pyqtSignal()
    exit_app_pressed = pyqtSignal()
    reload_replacements_pressed = pyqtSignal()

    def __init__(self, settings: HotkeySettings):
        super().__init__()
        self._settings = settings
        self._registered_hotkeys: Dict[str, keyboard.KeyboardEvent] = {}
        self._is_active = False

    def register_hotkeys(self):
        """ホットキーを登録"""
        if self._is_active:
            logger.warning("ホットキーは既に登録されています")
            return

        try:
            logger.info("ホットキー登録開始")

            # 録音トグル
            self._register_hotkey(
                "toggle_recording",
                self._settings.toggle_recording,
                self._on_toggle_recording,
            )

            # 句読点トグル
            self._register_hotkey(
                "toggle_punctuation",
                self._settings.toggle_punctuation,
                self._on_toggle_punctuation,
            )

            # アプリ終了
            self._register_hotkey(
                "exit_app", self._settings.exit_app, self._on_exit_app
            )

            # 置換ルール再読込
            self._register_hotkey(
                "reload_replacements",
                self._settings.reload_replacements,
                self._on_reload_replacements,
            )

            self._is_active = True
            logger.info("ホットキー登録完了")

        except Exception as e:
            logger.error(f"ホットキー登録失敗: {e}")
            raise HotkeyRegistrationError(f"登録失敗: {e}")

    def unregister_all(self):
        """全ホットキーを解除"""
        if not self._is_active:
            logger.warning("ホットキーは登録されていません")
            return

        try:
            logger.info("ホットキー解除開始")

            for action, key_combo in self._registered_hotkeys.items():
                try:
                    keyboard.unhook_key(key_combo)
                    logger.debug(f"解除: {action} ({key_combo})")
                except Exception as e:
                    logger.error(f"解除失敗: {action} - {e}")

            self._registered_hotkeys.clear()
            self._is_active = False
            logger.info("ホットキー解除完了")

        except Exception as e:
            logger.error(f"ホットキー解除エラー: {e}")

    def update_hotkey(self, action: str, new_key: str):
        """ホットキーを動的に変更"""
        if action not in ["toggle_recording", "toggle_punctuation", "exit_app", "reload_replacements"]:
            logger.error(f"未知のアクション: {action}")
            return

        try:
            # 既存のホットキーを解除
            if action in self._registered_hotkeys:
                old_key = self._registered_hotkeys[action]
                keyboard.unhook_key(old_key)
                logger.debug(f"解除: {action} ({old_key})")

            # 新しいホットキーを登録
            callback = getattr(self, f"_on_{action}")
            self._register_hotkey(action, new_key, callback)

            logger.info(f"ホットキー更新: {action} -> {new_key}")

        except Exception as e:
            logger.error(f"ホットキー更新失敗: {e}")
            raise HotkeyRegistrationError(f"更新失敗: {e}")

    def _register_hotkey(self, action: str, key_combo: str, callback):
        """個別ホットキーを登録"""
        try:
            # keyboard.on_press_key を使用
            keyboard.on_press_key(key_combo, callback, suppress=False)
            self._registered_hotkeys[action] = key_combo
            logger.debug(f"登録: {action} ({key_combo})")

        except Exception as e:
            logger.error(f"ホットキー登録エラー: {action} - {e}")
            raise

    def _on_toggle_recording(self, event: Optional[keyboard.KeyboardEvent] = None):
        """録音トグル時のコールバック"""
        logger.debug("録音トグルキーが押されました")
        self.toggle_recording_pressed.emit()

    def _on_toggle_punctuation(self, event: Optional[keyboard.KeyboardEvent] = None):
        """句読点トグル時のコールバック"""
        logger.debug("句読点トグルキーが押されました")
        self.toggle_punctuation_pressed.emit()

    def _on_exit_app(self, event: Optional[keyboard.KeyboardEvent] = None):
        """アプリ終了時のコールバック"""
        logger.debug("終了キーが押されました")
        self.exit_app_pressed.emit()

    def _on_reload_replacements(self, event: Optional[keyboard.KeyboardEvent] = None):
        """置換ルール再読込時のコールバック"""
        logger.debug("再読込キーが押されました")
        self.reload_replacements_pressed.emit()

    @property
    def is_active(self) -> bool:
        """ホットキーが有効かどうか"""
        return self._is_active

    def __del__(self):
        """デストラクタ - クリーンアップ"""
        self.unregister_all()
