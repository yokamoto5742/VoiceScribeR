import configparser
import glob
import logging
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, Dict, Optional

from service.replacements_editor import ReplacementsEditor

class UIComponents:
    def __init__(
            self,
            master: tk.Tk,
            config: configparser.ConfigParser,
            callbacks: Dict[str, Callable]
    ):
        self.master = master
        self.config = config
        self.callbacks = callbacks
        self._toggle_recording = callbacks.get('toggle_recording', lambda: None)
        self._toggle_punctuation = callbacks.get('toggle_punctuation', lambda: None)
        self.status_label: Optional[tk.Label] = None
        self.punctuation_status_label: Optional[tk.Label] = None
        self.punctuation_button: Optional[tk.Button] = None
        self.record_button: Optional[tk.Button] = None
        self.reload_audio_button: Optional[tk.Button] = None
        self.load_audio_button: Optional[tk.Button] = None
        self.replace_button: Optional[tk.Button] = None
        self.close_button: Optional[tk.Button] = None

    def setup_ui(self, version: str):
        self.master.title(f'VoiceScribe v{version}')

        window_width = int(self.config['WINDOW'].get('width', 350))
        window_height = int(self.config['WINDOW'].get('height', 400))
        self.master.geometry(f"{window_width}x{window_height}")

        self.record_button = tk.Button(
            self.master,
            text=f'音声入力開始',
            command=self._toggle_recording,
            width=15
        )
        self.record_button.pack(pady=10)

        self.punctuation_button = tk.Button(
            self.master,
            text=f'句読点切替:{self.config["KEYS"]["TOGGLE_PUNCTUATION"]}',
            command=self._toggle_punctuation,
            width=15
        )
        self.punctuation_button.pack(pady=5)

        self.punctuation_status_label = tk.Label(
            self.master,
            text='【現在句読点あり】',
        )
        self.punctuation_status_label.pack(pady=5)

        self.reload_audio_button = tk.Button(
            self.master,
            text=f'音声再読込:{self.config["KEYS"]["RELOAD_AUDIO"]}',
            command=self.reload_latest_audio,
            width=15
        )
        self.reload_audio_button.pack(pady=5)

        self.load_audio_button = tk.Button(
            self.master,
            text='音声ファイル選択',
            command=self.open_audio_file,
            width=15
        )
        self.load_audio_button.pack(pady=5)

        self.replace_button = tk.Button(
            self.master,
            text='置換単語登録',
            command=self.open_replacements_editor,
            width=15
        )
        self.replace_button.pack(pady=5)

        self.close_button = tk.Button(
            self.master,
            text=f'閉じる:{self.config["KEYS"]["EXIT_APP"]}',
            command=self.master.quit,
            width=15
        )
        self.close_button.pack(pady=5)

        self.status_label = tk.Label(
            self.master,
            text=f"{self.config['KEYS']['TOGGLE_RECORDING']}キーで音声入力開始/停止"
        )
        self.status_label.pack(pady=10)

    def update_callbacks(self, callbacks: Dict[str, Callable]):
        self.callbacks = callbacks
        self._toggle_recording = callbacks.get('toggle_recording', self._toggle_recording)
        self._toggle_punctuation = callbacks.get('toggle_punctuation', self._toggle_punctuation)

    def update_record_button(self, is_recording: bool):
        assert self.record_button is not None
        self.record_button.config(
            text=f'音声入力{"停止" if is_recording else "開始"}:{self.config["KEYS"]["TOGGLE_RECORDING"]}'
        )

    def update_punctuation_button(self, use_punctuation: bool):
        assert self.punctuation_status_label is not None
        self.punctuation_status_label.config(
            text=f'【現在句読点{"あり】" if use_punctuation else "なし】"}'
        )

    def update_status_label(self, text: str):
        assert self.status_label is not None
        self.status_label.config(text=text)

    def reload_latest_audio(self):
        latest_file = self.get_latest_audio_file()
        if latest_file:
            self.master.clipboard_clear()
            self.master.clipboard_append(latest_file)
            self.master.event_generate('<<LoadAudioFile>>')
        else:
            messagebox.showwarning("警告", "音声ファイルが見つかりません")

    def get_latest_audio_file(self):
        try:
            files = glob.glob(os.path.join(self.config['PATHS']['TEMP_DIR'], "*.wav"))
            if not files:
                return None
            return max(files, key=os.path.getmtime)
        except Exception as e:
            logging.error(f"最新の音声ファイル取得中にエラー: {str(e)}")
            return None

    def open_audio_file(self):
        file_path = filedialog.askopenfilename(
            title='音声ファイルを選択',
            filetypes=[('Wave files', '*.wav')],
            initialdir=self.config['PATHS']['TEMP_DIR']
        )
        if file_path:
            self.master.clipboard_clear()
            self.master.clipboard_append(file_path)
            self.master.event_generate('<<LoadAudioFile>>')

    def open_replacements_editor(self):
        ReplacementsEditor(self.master, self.config)
