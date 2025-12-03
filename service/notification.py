import configparser
import logging
import tkinter as tk
from typing import Optional


class NotificationManager:
    def __init__(self, master: tk.Tk, config: configparser.ConfigParser):
        self.master = master
        self.config = config
        self.current_popup: Optional[tk.Toplevel] = None

    def show_timed_message(self, title: str, message: str, duration: int = 2000):
        if self.current_popup:
            try:
                self.current_popup.destroy()
            except tk.TclError:
                pass

        try:
            self.current_popup = tk.Toplevel(self.master)
            self.current_popup.title(title)
            self.current_popup.attributes('-topmost', True)

            label = tk.Label(self.current_popup, text=message)
            label.pack(padx=20, pady=20)

            self.current_popup.after(duration, self._destroy_popup)

        except Exception as e:
            logging.error(f"通知中にエラーが発生しました: {str(e)}")

    def show_error_message(self, title: str, message: str):
        try:
            self.show_timed_message(f"エラー: {title}", message)
        except Exception as e:
            logging.error(f"通知中にエラーが発生しました: {str(e)}")

    def show_status_message(self, message: str):
        try:
            status_text = f"{self.config['KEYS']['TOGGLE_RECORDING']}キーで音声入力開始/停止 {message}"
            self.master.after(0, lambda: self._update_status_label(status_text))
        except Exception as e:
            logging.error(f"ステータス更新中にエラーが発生しました: {str(e)}")

    def _destroy_popup(self):
        try:
            if self.current_popup:
                self.current_popup.destroy()
        except tk.TclError:
            pass
        except Exception as e:
            logging.error(f"ポップアップの破棄中にエラーが発生しました: {str(e)}")
        finally:
            self.current_popup = None

    def _update_status_label(self, text: str):
        status_label = self.master.children.get('status_label')
        if status_label is not None and hasattr(status_label, 'config'):
            status_label.config(text=text)  # type: ignore[union-attr]

    def cleanup(self):
        if self.current_popup:
            try:
                self.current_popup.destroy()
            except tk.TclError:
                pass
