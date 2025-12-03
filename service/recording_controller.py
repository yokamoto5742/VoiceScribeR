import configparser
import glob
import logging
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from external_service.elevenlabs_api import transcribe_audio
from service.audio_recorder import save_audio
from service.text_processing import copy_and_paste_transcription, process_punctuation
from utils.config_manager import get_config_value


class RecordingController:
    def __init__(
            self,
            master: tk.Tk,
            config: configparser.ConfigParser,
            recorder: Any,
            client: Any,
            replacements: Dict[str, str],
            ui_callbacks: Dict[str, Callable],
            notification_callback: Callable
    ):
        self.cancel_processing = False
        self.master = master
        self.config = config
        self.recorder = recorder
        self.client = client
        self.replacements = replacements
        self.ui_callbacks = ui_callbacks
        self.show_notification = notification_callback

        self.recording_timer: Optional[threading.Timer] = None
        self.five_second_timer: Optional[str] = None
        self.paste_timer = None
        self.five_second_notification_shown: bool = False
        self.processing_thread: Optional[threading.Thread] = None

        self.use_punctuation: bool = get_config_value(config, 'WHISPER', 'USE_PUNCTUATION', True)

        self.transcribe_audio_func = transcribe_audio

        self.temp_dir = config['PATHS']['TEMP_DIR']
        self.cleanup_minutes = int(config['PATHS']['CLEANUP_MINUTES'])

        # スレッドセーフなUI更新用キュー
        self._ui_queue: queue.Queue = queue.Queue()
        self._ui_lock = threading.Lock()
        self._is_shutting_down = False

        os.makedirs(self.temp_dir, exist_ok=True)
        self._cleanup_temp_files()

        self._start_ui_queue_processor()

    def _start_ui_queue_processor(self):

        def process_queue():
            if self._is_shutting_down:
                return

            try:
                for _ in range(10):
                    try:
                        callback, args = self._ui_queue.get_nowait()
                        try:
                            callback(*args)
                        except tk.TclError as e:
                            logging.warning(f"UIコールバック実行中にTclError: {str(e)}")
                        except Exception as e:
                            logging.error(f"UIコールバック実行中にエラー: {str(e)}")
                    except queue.Empty:
                        break
            except Exception as e:
                logging.error(f"UIキュー処理中にエラー: {str(e)}")
            finally:
                if not self._is_shutting_down and self._is_ui_valid():
                    try:
                        self.master.after(50, process_queue)
                    except tk.TclError:
                        pass

        if self._is_ui_valid():
            try:
                self.master.after(50, process_queue)
            except tk.TclError as e:
                logging.error(f"UIキュー処理開始に失敗: {str(e)}")

    def _schedule_ui_callback(self, callback: Callable, *args):
        """スレッドセーフにUIコールバックをスケジュール"""
        if self._is_shutting_down:
            logging.debug("シャットダウン中のためUIコールバックをスキップ")
            return

        try:
            self._ui_queue.put_nowait((callback, args))
        except Exception as e:
            logging.error(f"UIコールバックのキューイングに失敗: {str(e)}")

    def _is_ui_valid(self) -> bool:
        if self._is_shutting_down:
            return False

        try:
            with self._ui_lock:
                return (self.master is not None and
                        hasattr(self.master, 'winfo_exists') and
                        self.master.winfo_exists())
        except tk.TclError:
            return False
        except Exception:
            return False

    def _cleanup_temp_files(self):
        try:
            current_time = datetime.now()
            pattern = os.path.join(self.temp_dir, "*.wav")

            for file_path in glob.glob(pattern):
                file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                if current_time - file_modified > timedelta(minutes=self.cleanup_minutes):
                    try:
                        os.remove(file_path)
                        logging.info(f"古い音声ファイルを削除しました: {file_path}")
                    except Exception as e:
                        logging.error(f"ファイル削除中にエラーが発生しました: {file_path}, {e}")
        except Exception as e:
            logging.error(f"クリーンアップ処理中にエラーが発生しました: {e}")

    def _handle_error(self, error_msg: str):
        try:
            if self._is_ui_valid():
                self.show_notification("エラー", error_msg)
                self.ui_callbacks['update_status_label'](
                    f"{self.config['KEYS']['TOGGLE_RECORDING']}キーで音声入力開始/停止"
                )
                self.ui_callbacks['update_record_button'](False)
                if self.recorder.is_recording:
                    self.recorder.stop_recording()
        except Exception as e:
            logging.error(f"エラーハンドリング中にエラー: {str(e)}")

    def toggle_recording(self):
        if not self.recorder.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if self.processing_thread and self.processing_thread.is_alive():
            raise RuntimeError("前回の処理が完了していません")

        self.cancel_processing = False
        self.recorder.start_recording()
        self.ui_callbacks['update_record_button'](True)
        self.ui_callbacks['update_status_label'](
            f"音声入力中... ({self.config['KEYS']['TOGGLE_RECORDING']}キーで停止)"
        )

        recording_thread = threading.Thread(target=self._safe_record, daemon=False)
        recording_thread.start()

        auto_stop_timer = int(self.config['RECORDING']['AUTO_STOP_TIMER'])
        self.recording_timer = threading.Timer(auto_stop_timer, self.auto_stop_recording)
        self.recording_timer.start()

        self.five_second_notification_shown = False
        if self._is_ui_valid():
            self.five_second_timer = self.master.after(
                (auto_stop_timer - 5) * 1000,
                self.show_five_second_notification
            )

    def _safe_record(self):
        try:
            self.recorder.record()
        except Exception as e:
            logging.error(f"録音中にエラーが発生しました: {str(e)}")
            try:
                self.master.after(0, self._safe_error_handler, f"録音中にエラーが発生しました: {str(e)}")
            except Exception:
                pass

    def stop_recording(self):
        try:
            if self.recording_timer and self.recording_timer.is_alive():
                self.recording_timer.cancel()

            if self.five_second_timer:
                try:
                    if self._is_ui_valid():
                        self.master.after_cancel(self.five_second_timer)
                except Exception:
                    pass
                self.five_second_timer = None

            self._stop_recording_process()
        except Exception as e:
            self._safe_error_handler(f"録音の停止中にエラーが発生しました: {str(e)}")

    def auto_stop_recording(self):
        self._schedule_ui_callback(self._auto_stop_recording_ui)

    def _auto_stop_recording_ui(self):
        try:
            self.show_notification("自動停止", "アプリケーションを終了します")
            self._stop_recording_process()
            if self._is_ui_valid():
                self.master.after(1000, self.master.quit)
        except Exception as e:
            logging.error(f"自動停止処理中にエラー: {str(e)}")

    def _stop_recording_process(self):
        try:
            frames, sample_rate = self.recorder.stop_recording()
            logging.info(f"音声データを取得しました")

            self.ui_callbacks['update_record_button'](False)
            self.ui_callbacks['update_status_label']("テキスト出力中...")

            self.processing_thread = threading.Thread(
                target=self.transcribe_audio_frames,
                args=(frames, sample_rate),
                daemon=False
            )
            self.processing_thread.start()

            if self._is_ui_valid():
                self.master.after(100, self._check_process_thread, self.processing_thread)
        except Exception as e:
            logging.error(f"録音停止処理中にエラー: {str(e)}")
            self._safe_error_handler(f"録音停止処理中にエラー: {str(e)}")

    def _check_process_thread(self, thread: threading.Thread):
        try:
            if not thread.is_alive():
                self.ui_callbacks['update_status_label'](
                    f"{self.config['KEYS']['TOGGLE_RECORDING']}キーで音声入力開始/停止"
                )
                self.processing_thread = None
                return

            self.ui_callbacks['update_status_label']("テキスト出力中...")
            if self._is_ui_valid():
                self.master.after(100, self._check_process_thread, thread)
        except Exception as e:
            logging.error(f"処理スレッドチェック中にエラー: {str(e)}")

    def show_five_second_notification(self):
        try:
            if self.recorder.is_recording and not self.five_second_notification_shown:
                if self._is_ui_valid():
                    self.master.lift()
                    self.master.attributes('-topmost', True)
                    self.master.attributes('-topmost', False)
                    self.show_notification("自動停止", "あと5秒で音声入力を停止します")
                    self.five_second_notification_shown = True
        except Exception as e:
            logging.error(f"通知表示中にエラー: {str(e)}")

    def handle_audio_file(self, event):
        try:
            file_path = self.master.clipboard_get()
            if not os.path.exists(file_path):
                self.show_notification('エラー', '音声ファイルが見つかりません')
                return

            self.ui_callbacks['update_status_label']('音声ファイル処理中...')

            transcription = self.transcribe_audio_func(
                file_path,
                self.config,
                self.client
            )
            if transcription:
                transcription = process_punctuation(transcription, self.use_punctuation)
                self._safe_ui_update(transcription)
            else:
                raise ValueError('音声ファイルの処理に失敗しました')

        except Exception as e:
            self.show_notification('エラー', str(e))
        finally:
            self.ui_callbacks['update_status_label'](
                f"{self.config['KEYS']['TOGGLE_RECORDING']}キーで音声入力開始/停止"
            )

    def transcribe_audio_frames(self, frames: List[bytes], sample_rate: int):
        try:
            logging.info("音声フレーム処理開始")

            if self.cancel_processing:
                logging.info("処理がキャンセルされました")
                return

            temp_audio_file = save_audio(frames, sample_rate, self.config)
            if not temp_audio_file:
                raise ValueError("音声ファイルの保存に失敗しました")

            if self.cancel_processing:
                logging.info("処理がキャンセルされました")
                return

            logging.info("文字起こし開始")
            transcription = self.transcribe_audio_func(
                temp_audio_file,
                self.config,
                self.client
            )

            if not transcription:
                raise ValueError("音声ファイルの文字起こしに失敗しました")

            logging.debug(f"句読点処理開始: use_punctuation={self.use_punctuation}")
            transcription = process_punctuation(transcription, self.use_punctuation)
            logging.debug("句読点処理完了")

            if self.cancel_processing:
                logging.info("処理がキャンセルされました")
                return

            logging.debug("UI更新をスケジュール")
            try:
                self.master.after(0, self._safe_ui_update, transcription)
            except Exception:
                pass
            logging.debug("UI更新スケジュール完了")

        except Exception as e:
            logging.error(f"文字起こし処理中にエラー: {str(e)}")
            import traceback
            logging.debug(f"詳細: {traceback.format_exc()}")
            try:
                self.master.after(0, self._safe_error_handler, str(e))
            except Exception:
                pass

    def _safe_ui_update(self, text: str):
        try:
            logging.debug(f"_safe_ui_update開始: text長={len(text)}")
            if self._is_ui_valid():
                self.ui_update(text)
            else:
                logging.warning("UIが無効なため、UI更新をスキップします")
        except Exception as e:
            logging.error(f"UI更新中にエラー: {str(e)}")
            import traceback
            logging.debug(f"詳細: {traceback.format_exc()}")

    def _safe_error_handler(self, error_msg: str):
        try:
            if self._is_ui_valid():
                self._handle_error(error_msg)
            else:
                logging.error(f"UI無効時のエラー: {error_msg}")
        except Exception as e:
            logging.error(f"エラーハンドリング中にエラー: {str(e)}")

    def ui_update(self, text: str):
        try:
            logging.debug(f"ui_update開始: text長={len(text)}")
            paste_delay = int(float(self.config['CLIPBOARD'].get('PASTE_DELAY', 0.1)) * 1000)
            if self._is_ui_valid():
                self.master.after(paste_delay, self.copy_and_paste, text)
                logging.debug(f"copy_and_pasteをスケジュール: delay={paste_delay}ms")
        except Exception as e:
            logging.error(f"UI更新中にエラー: {str(e)}")
            import traceback
            logging.debug(f"詳細: {traceback.format_exc()}")

    def copy_and_paste(self, text: str):
        try:
            logging.debug(f"copy_and_paste開始: text長={len(text)}")
            threading.Thread(
                target=self._safe_copy_and_paste,
                args=(text,),
                daemon=True
            ).start()
        except Exception as e:
            logging.error(f"コピー&ペースト開始中にエラー: {str(e)}")

    def _safe_copy_and_paste(self, text: str):
        try:
            logging.debug("_safe_copy_and_paste開始")
            copy_and_paste_transcription(text, self.replacements, self.config)
            logging.debug("_safe_copy_and_paste完了")
        except Exception as e:
            logging.error(f"コピー&ペースト実行中にエラー: {str(e)}")
            import traceback
            logging.debug(f"詳細: {traceback.format_exc()}")
            self._schedule_ui_callback(self._safe_error_handler, f"コピー&ペースト中にエラー: {str(e)}")

    def cleanup(self):
        try:
            logging.info("RecordingController クリーンアップ開始")
            self._is_shutting_down = True
            self.cancel_processing = True

            if self.recorder.is_recording:
                self.stop_recording()

            if self.processing_thread and self.processing_thread.is_alive():
                logging.info("処理スレッドの完了を待機中...")
                for _ in range(50):  # 5秒間待機
                    if not self.processing_thread.is_alive():
                        break
                    time.sleep(0.1)

                if self.processing_thread.is_alive():
                    logging.warning("処理スレッドが強制終了されました")
                    self.processing_thread.join(1.0)

            if self.recording_timer and self.recording_timer.is_alive():
                self.recording_timer.cancel()

            if self.five_second_timer:
                try:
                    if self._is_ui_valid():
                        self.master.after_cancel(self.five_second_timer)
                except Exception:
                    pass

            self._cleanup_temp_files()

        except Exception as e:
            logging.error(f"クリーンアップ処理中にエラーが発生しました: {str(e)}")

    def _wait_for_processing(self):
        if self.processing_thread and self.processing_thread.is_alive():
            logging.info("処理スレッドの完了を待機中...")
            self.ui_callbacks['update_status_label']("処理完了待機中...")
            self.processing_thread.join(timeout=5.0)

            if self.processing_thread.is_alive():
                logging.warning("処理スレッドの待機がタイムアウトしました")
            else:
                logging.info("処理スレッドの待機が完了しました")
