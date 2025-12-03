import configparser
import logging
import os
import wave
from datetime import datetime
from typing import List, Tuple, Optional

import pyaudio


class AudioRecorder:
    def __init__(self, config: configparser.ConfigParser):
        self.sample_rate = int(config['AUDIO']['SAMPLE_RATE'])
        self.channels = int(config['AUDIO']['CHANNELS'])
        self.chunk = int(config['AUDIO']['CHUNK'])
        self.temp_dir = config['PATHS']['TEMP_DIR']
        self.frames: List[bytes] = []
        self.is_recording = False
        self.p: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None

        os.makedirs(self.temp_dir, exist_ok=True)

        self.logger = logging.getLogger(__name__)

    def start_recording(self):
        self.is_recording = True
        self.frames = []
        try:
            self.p = pyaudio.PyAudio()
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk,
            )
            self.logger.info("音声入力を開始しました。")
        except Exception as e:
            self.logger.error(f"音声入力の開始中に予期せぬエラーが発生しました: {e}")

    def stop_recording(self) -> Tuple[List[bytes], int]:
        self.is_recording = False
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
        except Exception as e:
            self.logger.error(f"音声入力の停止中に予期せぬエラーが発生しました: {e}")

        try:
            if self.p:
                self.p.terminate()
        except Exception as e:
            self.logger.error(f"PyAudio終了中に予期せぬエラーが発生しました: {e}")

        self.logger.info("音声入力を停止しました。")
        return self.frames, self.sample_rate

    def record(self):
        while self.is_recording:
            try:
                if self.stream is None:
                    raise AttributeError("ストリームが初期化されていません")
                data = self.stream.read(self.chunk)
                self.frames.append(data)
            except AttributeError:
                self.logger.error(f"音声入力中にストリーム初期化エラーが発生しました")
                raise
            except Exception as e:
                self.logger.error(f"音声入力中に予期せぬエラーが発生しました: {e}")
                self.is_recording = False
                break


def save_audio(frames: List[bytes], sample_rate: int, config: configparser.ConfigParser) -> Optional[str]:
    try:
        temp_dir = config['PATHS']['TEMP_DIR']
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_filename = f"audio_{timestamp}.wav"
        temp_path = os.path.join(temp_dir, temp_filename)

        with wave.open(temp_path, "wb") as wf:
            channels = int(config['AUDIO']['CHANNELS'])
            wf.setnchannels(channels)
            wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(frames))

        logging.info(f"音声ファイル保存完了: {temp_path}")

        return temp_path

    except Exception as e:
        logging.error(f"音声ファイル保存エラー: {str(e)}")
        return None
