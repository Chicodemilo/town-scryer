# ==============================================================================
# File:      api/app/services/transcription_service.py
# Purpose:   Transcribe an audio chunk to text using a self-hosted Whisper
#            model (faster-whisper / CTranslate2). No external API call, no
#            third-party data path — runs entirely inside the api container.
# Callers:   routes/sessions.py (process_audio_chunk)
# Callees:   faster_whisper, tempfile, logging
# Modified:  2026-06-06
# ==============================================================================
import logging
import os
import tempfile
import threading

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

# small.en hits a good balance: ~250MB, ~1.5-3x real-time on CPU, much
# better at noisy room audio than base.en. Pre-downloaded at image build
# time so first transcription is fast.
WHISPER_MODEL_NAME = os.getenv('WHISPER_MODEL', 'small.en')
WHISPER_DEVICE = os.getenv('WHISPER_DEVICE', 'cpu')
WHISPER_COMPUTE_TYPE = os.getenv('WHISPER_COMPUTE_TYPE', 'int8')
WHISPER_DOWNLOAD_ROOT = os.getenv('WHISPER_DOWNLOAD_ROOT', '/opt/whisper-models')

_model = None
_model_lock = threading.Lock()


def _get_model() -> WhisperModel:
    """Lazy-load the Whisper model once per process and reuse it."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info(
                    f'Loading Whisper model {WHISPER_MODEL_NAME} '
                    f'(device={WHISPER_DEVICE}, compute_type={WHISPER_COMPUTE_TYPE})'
                )
                _model = WhisperModel(
                    WHISPER_MODEL_NAME,
                    device=WHISPER_DEVICE,
                    compute_type=WHISPER_COMPUTE_TYPE,
                    download_root=WHISPER_DOWNLOAD_ROOT,
                )
    return _model


def transcribe_audio(audio_bytes: bytes, filename: str = 'chunk.webm') -> str:
    """Run an audio chunk through the local Whisper model. Returns the
    transcript string (may be empty if no speech is detected)."""
    model = _get_model()

    # faster-whisper's transcribe() wants a file path or numpy array. The
    # browser sends webm/opus; ffmpeg (bundled in the container) decodes it.
    suffix = os.path.splitext(filename)[1] or '.webm'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, _info = model.transcribe(
            tmp_path,
            language='en',
            # vad_filter trims silence — Critical Role pauses, table chatter
            # between encounters, etc. — so empty stretches don't generate
            # garbage hallucinations.
            vad_filter=True,
        )
        parts = [seg.text for seg in segments]
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return ' '.join(parts).strip()
