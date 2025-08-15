# src/ingest/youtube.py
from typing import Optional, List
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)

def _extract_video_id(url: str) -> Optional[str]:
    try:
        u = urlparse(url.strip())
        host = (u.hostname or "").lower()

        # youtu.be/<id>
        if host.endswith("youtu.be"):
            vid = u.path.strip("/").split("/")[0]
            return vid[:11] if vid else None

        # youtube.com / m.youtube.com / youtube-nocookie.com
        if "youtube" in host:
            if u.path == "/watch":
                vid = parse_qs(u.query).get("v", [None])[0]
                return vid[:11] if vid else None
            if u.path.startswith("/shorts/"):
                vid = u.path.split("/shorts/")[1].split("/")[0]
                return vid[:11] if vid else None

        # last resort: 11-char id in the string
        m = re.search(r"(?P<id>[A-Za-z0-9_-]{11})", url)
        if m:
            return m.group("id")
    except Exception:
        pass
    return None

def _join(items: List[dict]) -> str:
    return " ".join([d.get("text", "") for d in items if d.get("text")]).strip()

def fetch_youtube_transcript(
    url: str,
    *,
    lang_priority = ("en", "en-US", "en-GB", "en-IN", "hi")
) -> Optional[str]:
    """
    Strategy:
    1) Direct get_transcript with preferred languages (manual or auto).
    2) list_transcripts(): manual -> generated in preferred languages.
    3) If a transcript exists in another language, try translate('en').
    4) Finally, any transcript of any type/language.
    """
    vid = _extract_video_id(url)
    if not vid:
        return None

    # 1) Direct attempt
    try:
        items = YouTubeTranscriptApi.get_transcript(vid, languages=list(lang_priority))
        text = _join(items)
        if text:
            return text
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        pass
    except Exception:
        pass

    # 2/3/4) Explore transcript objects for more options
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(vid)

        # Prefer manual in priority languages
        for langs in [list(lang_priority), ["en"], ["hi"]]:
            try:
                t = transcripts.find_transcript(langs)
                text = _join(t.fetch())
                if text:
                    return text
            except Exception:
                pass

        # Then auto-generated in priority languages
        for langs in [list(lang_priority), ["en"], ["hi"]]:
            try:
                t = transcripts.find_generated_transcript(langs)
                text = _join(t.fetch())
                if text:
                    return text
            except Exception:
                pass

        # Try translating any available transcript to English
        for t in transcripts:
            try:
                tr_en = t.translate("en")
                text = _join(tr_en.fetch())
                if text:
                    return text
            except Exception:
                continue

        # Finally: first available transcript of any kind/language
        for t in transcripts:
            try:
                text = _join(t.fetch())
                if text:
                    return text
            except Exception:
                continue

    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable):
        return None
    except Exception:
        return None

    return None