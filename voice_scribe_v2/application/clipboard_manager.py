"""クリップボード管理 - スレッドセーフな操作"""

import logging
import time

import pyperclip
from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import AppSettings
from domain.exceptions import ClipboardError

logger = logging.getLogger(__name__)


class ClipboardManager(QObject):
    """クリップボード操作管理"""

    # Signal定義
    paste_completed = pyqtSignal()
    paste_failed = pyqtSignal(str)

    def __init__(self, settings: AppSettings):
        super().__init__()
        self._settings = settings
        self._paste_delay_ms = settings.recording.paste_delay_ms

        logger.info("ClipboardManager 初期化完了")

    def copy_and_paste(self, text: str):
        """クリップボードにコピーして貼り付け"""
        try:
            # クリップボードにコピー
            if not self.copy_only(text):
                self.paste_failed.emit("クリップボードへのコピーに失敗しました")
                return

            # 遅延
            time.sleep(self._paste_delay_ms / 1000.0)

            # 貼り付け
            if self._safe_paste():
                self.paste_completed.emit()
                logger.info(f"貼り付け完了: {len(text)}文字")
            else:
                self.paste_failed.emit("貼り付けに失敗しました")

        except Exception as e:
            logger.error(f"コピー&貼り付けエラー: {e}", exc_info=True)
            self.paste_failed.emit(str(e))

    def copy_only(self, text: str) -> bool:
        """クリップボードにコピーのみ"""
        try:
            return self._safe_copy(text)
        except Exception as e:
            logger.error(f"コピーエラー: {e}", exc_info=True)
            raise ClipboardError(f"コピー失敗: {e}")

    def _safe_copy(self, text: str) -> bool:
        """スレッドセーフなクリップボードコピー"""
        try:
            pyperclip.copy(text)

            # コピーの検証
            if self._verify_clipboard(text):
                logger.debug(f"クリップボードコピー成功: {len(text)}文字")
                return True
            else:
                logger.error("クリップボード検証失敗")
                return False

        except Exception as e:
            logger.error(f"クリップボードコピーエラー: {e}")
            return False

    def _safe_paste(self) -> bool:
        """スレッドセーフな貼り付け (Windows SendInput使用)"""
        if not self._is_windows():
            logger.warning("Windows以外では貼り付け機能は未サポート")
            return False

        try:
            # Windows SendInput API を使用
            import ctypes

            # Ctrl+V を送信
            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002

            # SendInput構造体
            class INPUT(ctypes.Structure):
                class _INPUT(ctypes.Union):
                    class KEYBDINPUT(ctypes.Structure):
                        _fields_ = [
                            ("wVk", ctypes.c_ushort),
                            ("wScan", ctypes.c_ushort),
                            ("dwFlags", ctypes.c_ulong),
                            ("time", ctypes.c_ulong),
                            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
                        ]

                    _fields_ = [("ki", KEYBDINPUT)]

                _fields_ = [("type", ctypes.c_ulong), ("ii", _INPUT)]

            # Ctrl キーダウン
            ctrl_down = INPUT()
            ctrl_down.type = 1  # INPUT_KEYBOARD
            ctrl_down.ii.ki.wVk = VK_CONTROL
            ctrl_down.ii.ki.dwFlags = 0

            # V キーダウン
            v_down = INPUT()
            v_down.type = 1
            v_down.ii.ki.wVk = VK_V
            v_down.ii.ki.dwFlags = 0

            # V キーアップ
            v_up = INPUT()
            v_up.type = 1
            v_up.ii.ki.wVk = VK_V
            v_up.ii.ki.dwFlags = KEYEVENTF_KEYUP

            # Ctrl キーアップ
            ctrl_up = INPUT()
            ctrl_up.type = 1
            ctrl_up.ii.ki.wVk = VK_CONTROL
            ctrl_up.ii.ki.dwFlags = KEYEVENTF_KEYUP

            # SendInput 実行
            inputs = (INPUT * 4)(ctrl_down, v_down, v_up, ctrl_up)
            ctypes.windll.user32.SendInput(
                4, ctypes.byref(inputs), ctypes.sizeof(INPUT)
            )

            logger.debug("SendInput で貼り付け実行")
            return True

        except Exception as e:
            logger.error(f"貼り付けエラー: {e}", exc_info=True)
            return False

    def _verify_clipboard(self, expected: str) -> bool:
        """クリップボードの内容を検証"""
        try:
            actual = pyperclip.paste()
            return actual == expected
        except Exception as e:
            logger.error(f"クリップボード検証エラー: {e}")
            return False

    def _is_windows(self) -> bool:
        """Windows環境かどうか"""
        import sys

        return sys.platform == "win32"
