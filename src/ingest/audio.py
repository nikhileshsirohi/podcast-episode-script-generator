from typing import Optional, List, Tuple
from fastapi import UploadFile
from faster_whisper import WhisperModel
import tempfile
import os

# Lazy singleton model
_model: Optional[WhisperModel] = None

def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        # "base" + int8 is a good CPU default. Try "small" or "medium" for higher quality.
        _model = WhisperModel("base", compute_type="int8")
    return _model

async def transcribe_audio(file: UploadFile, language: Optional[str] = None):
    """
    Returns:
      {
        "text": str,
        "duration": float (sec),
        "words": List[Tuple[str, float]]  # (word_lower, start_time_sec)
      }
    """
    model = _get_model()

    # Save to a temp file because faster-whisper expects a path/stream
    suffix = os.path.splitext(file.filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        data = await file.read()
        tmp.write(data)
        temp_path = tmp.name

    # sanitize language input
    lang = (language or "").strip().lower() or None
    # quick friendly mappings
    human_map = {
        "english": "en", "hindi": "hi", "hin": "hi",
        "en-us": "en", "en-gb": "en", "en-in": "en",
    }
    if lang in human_map:
        lang = human_map[lang]

    try:
        try:
            segments, info = model.transcribe(
                temp_path,
                word_timestamps=True,
                language=lang,   # e.g., "en", "hi"; or None to auto-detect
                vad_filter=True,
            )
        except ValueError:
            # invalid language code → retry with auto-detect
            segments, info = model.transcribe(
                temp_path,
                word_timestamps=True,
                language=None,
                vad_filter=True,
            )

        words: List[Tuple[str, float]] = []
        full_text_parts: List[str] = []

        for seg in segments:
            txt = (seg.text or "").strip()
            if txt:
                full_text_parts.append(txt)
            if seg.words:
                for w in seg.words:
                    if w.start is not None and w.word.strip():
                        words.append((w.word.strip().lower(), float(w.start)))

        transcript_text = " ".join(full_text_parts).strip()
        duration = float(getattr(info, "duration", 0.0) or 0.0)

        # Fallback: if no word-level timings, approximate with segment starts
        if not words:
            for seg in segments:
                first = (seg.text or "").strip().split()
                words.append(((first[0].lower() if first else ""), float(seg.start)))

        return {
            "text": transcript_text,
            "duration": duration,
            "words": words,
        }
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass