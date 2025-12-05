"""PyAudio音声録音モジュール - QThread対応"""

import logging
from typing import Optional

import pyaudio
from PyQt6.QtCore import QThread, pyqtSignal

from config.settings import AudioSettings
from domain.exceptions import (
    AudioDeviceNotFoundError,
    AudioRecordingError,
    AudioStreamError,
)

logger = logging.getLogger(__name__)


class AudioRecorderWorker(QThread):
    """音声録音ワーカースレッド"""

    # Signal定義
    audio_chunk_ready = pyqtSignal(bytes)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    error_occurred = pyqtSignal(Exception)

    def __init__(self, settings: AudioSettings):
        super().__init__()
        self._settings = settings
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._is_recording = False

    def run(self):
        """QThread のメインループ"""
        try:
            self._initialize_pyaudio()

            while self._is_recording:
                try:
                    chunk_data = self._read_audio_chunk()
                    if chunk_data:
                        self.audio_chunk_ready.emit(chunk_data)
                except Exception as e:
                    logger.error(f"音声チャンク読み取りエラー: {e}")
                    self.error_occurred.emit(AudioStreamError(str(e)))
                    break

        except Exception as e:
            logger.error(f"録音スレッドエラー: {e}", exc_info=True)
            self.error_occurred.emit(AudioRecordingError(str(e)))

        finally:
            self._cleanup()

    def start_recording(self):
        """録音を開始"""
        if self._is_recording:
            logger.warning("既に録音中です")
            return

        logger.info("録音開始")
        self._is_recording = True
        self.start()  # QThread を開始
        self.recording_started.emit()

    def stop_recording(self):
        """録音を停止"""
        if not self._is_recording:
            logger.warning("録音していません")
            return

        logger.info("録音停止")
        self._is_recording = False
        self.wait()  # スレッド終了を待つ
        self.recording_stopped.emit()

    def _initialize_pyaudio(self):
        """PyAudio を初期化"""
        try:
            self._pyaudio = pyaudio.PyAudio()

            # デバイス情報をログ出力
            device_info = self._pyaudio.get_default_input_device_info()
            logger.info(f"録音デバイス: {device_info['name']}")

            # ストリームを開く
            self._stream = self._pyaudio.open(
                format=self._get_audio_format(),
                channels=self._settings.channels,
                rate=self._settings.sample_rate,
                input=True,
                frames_per_buffer=self._settings.chunk_size,
            )

            logger.info(
                f"PyAudio初期化完了: {self._settings.sample_rate}Hz, "
                f"{self._settings.channels}ch, {self._settings.chunk_size} samples/chunk"
            )

        except OSError as e:
            logger.error(f"音声デバイスが見つかりません: {e}")
            raise AudioDeviceNotFoundError(str(e))

        except Exception as e:
            logger.error(f"PyAudio初期化エラー: {e}")
            raise AudioRecordingError(f"録音初期化失敗: {e}")

    def _read_audio_chunk(self) -> Optional[bytes]:
        """音声チャンクを読み取り"""
        if not self._stream or not self._stream.is_active():
            return None

        try:
            data = self._stream.read(
                self._settings.chunk_size, exception_on_overflow=False
            )
            return data

        except Exception as e:
            logger.error(f"音声読み取りエラー: {e}")
            raise AudioStreamError(str(e))

    def _cleanup(self):
        """リソースをクリーンアップ"""
        logger.info("録音リソースをクリーンアップ中")

        if self._stream:
            try:
                if self._stream.is_active():
                    self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.error(f"ストリーム終了エラー: {e}")
            finally:
                self._stream = None

        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception as e:
                logger.error(f"PyAudio終了エラー: {e}")
            finally:
                self._pyaudio = None

        logger.info("クリーンアップ完了")

    def _get_audio_format(self) -> int:
        """PyAudio フォーマットを取得"""
        if self._settings.format_bits == 16:
            return pyaudio.paInt16
        elif self._settings.format_bits == 24:
            return pyaudio.paInt24
        elif self._settings.format_bits == 32:
            return pyaudio.paInt32
        else:
            logger.warning(
                f"未対応のビット深度: {self._settings.format_bits}, 16bitを使用"
            )
            return pyaudio.paInt16

    @property
    def is_recording(self) -> bool:
        """録音中かどうか"""
        return self._is_recording
