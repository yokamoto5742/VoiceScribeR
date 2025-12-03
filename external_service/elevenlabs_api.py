import configparser
import logging
import os
import traceback
from typing import Optional

from elevenlabs.client import ElevenLabs

from utils.env_loader import load_env_variables


def setup_elevenlabs_client() -> ElevenLabs:
    env_vars = load_env_variables()
    api_key = env_vars.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEYが未設定です")
    return ElevenLabs(api_key=api_key)


def validate_audio_file(file_path: str) -> tuple[bool, Optional[str]]:
    """音声ファイルの存在と有効性を検証

    Returns:
        tuple[bool, Optional[str]]: (検証成功, エラーメッセージ)
    """
    if not file_path:
        return False, "音声ファイルパスが未指定です"

    if not os.path.exists(file_path):
        return False, f"音声ファイルが存在しません: {file_path}"

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, "音声ファイルサイズが0バイトです"

    return True, None


def convert_response_to_text(response) -> Optional[str]:
    """APIレスポンスをテキストに変換"""
    if response is None:
        logging.error("APIからのレスポンスが空です")
        return None

    try:
        if isinstance(response, str):
            return response
        elif hasattr(response, 'text') and response.text is not None:
            return str(response.text)
        elif hasattr(response, '__str__'):
            return str(response)
        else:
            logging.error(f"予期しないレスポンス形式: {type(response)}")
            return None
    except Exception as e:
        logging.error(f"レスポンス変換中の予期しないエラー: {str(e)}")
        logging.debug(f"レスポンス変換エラー詳細: {traceback.format_exc()}")
        return None


def transcribe_audio(
        audio_file_path: str,
        config: configparser.ConfigParser,
        client: ElevenLabs
) -> Optional[str]:
    is_valid, error_msg = validate_audio_file(audio_file_path)
    if not is_valid:
        logging.warning(error_msg) if "未指定" in error_msg else logging.error(error_msg)
        return None

    try:
        logging.info("ファイル読み込み開始")
        with open(audio_file_path, "rb") as file:
            file_content = file.read()
            logging.info(f"ファイル読み込み完了: {len(file_content)} bytes")

            transcription = client.speech_to_text.convert(
                file=(os.path.basename(audio_file_path), file_content),
                model_id=config['ELEVENLABS']['MODEL'],
                language_code=config['ELEVENLABS']['LANGUAGE']
            )

        text_result = convert_response_to_text(transcription)
        if text_result is None:
            return None

        if len(text_result) == 0:
            logging.warning("文字起こし結果が空です")
            return ""

        logging.info(f"文字起こし完了: {len(text_result)}文字")
        return text_result

    except FileNotFoundError as e:
        logging.error(f"ファイルが見つかりません: {str(e)}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None
    except PermissionError as e:
        logging.error(f"ファイルアクセス権限エラー: {str(e)}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None
    except OSError as e:
        logging.error(f"OS関連エラー: {str(e)}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None

    except Exception as e:
        logging.error(f"文字起こしエラー: {str(e)}")
        logging.error(f"エラーのタイプ: {type(e).__name__}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None
