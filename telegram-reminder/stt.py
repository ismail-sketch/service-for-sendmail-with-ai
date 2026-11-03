"""Локальное распознавание речи (Speech-to-Text) через faster-whisper."""
import logging

from faster_whisper import WhisperModel

import config

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info(
            "Загружаю модель STT '%s' (device=%s, compute_type=%s)…",
            config.WHISPER_MODEL,
            config.WHISPER_DEVICE,
            config.WHISPER_COMPUTE_TYPE,
        )
        _model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
    return _model


def transcribe(audio_path: str) -> str:
    """Принимает путь к аудио (ogg/wav/mp3 и т.п.), возвращает текст."""
    model = _get_model()
    segments, _info = model.transcribe(
        audio_path,
        language=config.WHISPER_LANGUAGE or None,
        beam_size=5,
    )
    return "".join(seg.text for seg in segments).strip()