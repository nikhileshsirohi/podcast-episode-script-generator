from typing import List, Dict, Tuple
import re

def hhmmss(seconds: float) -> str:
    """
    Convert seconds (int/float) to HH:MM:SS string, rounding to nearest second.
    """
    secs = int(round(seconds))
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def estimate_segment_durations(segments_text: List[str], wpm: int = 150) -> List[int]:
    """
    Estimate speaking duration per segment in seconds based on words-per-minute.
    seconds = words * (60 / wpm)
    """
    seconds_per_word = 60.0 / max(wpm, 1)
    durations = []
    for text in segments_text:
        word_count = max(len(text.split()), 1)
        durations.append(int(round(word_count * seconds_per_word)))
    return durations

def cumulative_timestamps(durations: List[int], intro_pad: int = 0) -> List[str]:
    """
    Given a list of segment durations (in seconds), return start timestamps for each segment,
    accounting for an intro padding in seconds (intro_pad).
    Example: durations [30, 40], intro_pad=10 -> starts ["00:00:10", "00:00:40"]
    """
    stamps = []
    elapsed = int(round(intro_pad))
    for d in durations:
        stamps.append(hhmmss(elapsed))
        elapsed += int(d)
    return stamps

def snap_notes_to_segments(
    notes: List[Dict],
    seg_starts_hhmmss: List[str],
) -> List[Dict]:
    """
    For any note with time==None, set time to the closest *earlier* segment start.
    If nothing earlier, fallback to "00:00:00".
    """
    def to_secs(hms: str) -> int:
        h, m, s = map(int, hms.split(":"))
        return h * 3600 + m * 60 + s

    if not seg_starts_hhmmss:
        seg_starts_hhmmss = ["00:00:00"]

    seg_starts_secs = [to_secs(t) for t in seg_starts_hhmmss]

    current_idx = 0
    for n in notes:
        t = n.get("time")
        if t is None:
            n["time"] = seg_starts_hhmmss[current_idx]
        else:
            try:
                ts = to_secs(t)
                while current_idx + 1 < len(seg_starts_secs) and ts >= seg_starts_secs[current_idx + 1]:
                    current_idx += 1
            except Exception:
                n["time"] = seg_starts_hhmmss[current_idx]
    return notes

# ---------- Audio alignment helpers ----------

def _flatten_words(text: str) -> List[str]:
    # Simple tokenizer: split on alphanumerics/apostrophes
    return re.findall(r"[A-Za-z0-9']+", text.lower())

def map_segments_to_audio_starts(
    transcript_words_with_time: List[Tuple[str, float]],  # [(word_lower, start_sec), ...]
    segments_text: List[str],
    intro_text: str = "",
) -> List[str]:
    """
    Returns HH:MM:SS start time for each generated segment using *actual* audio timestamps.
    Method: proportional alignment by cumulative word counts.
    """
    # Transcript word timeline
    t_words = [w for (w, _) in transcript_words_with_time]
    t_times = [t for (_, t) in transcript_words_with_time]
    total_transcript_words = max(len(t_words), 1)

    # Compute cumulative word counts for intro + segments
    intro_wc = len(_flatten_words(intro_text))
    seg_wcs = [len(_flatten_words(s or "")) for s in segments_text]
    cum_wcs = []
    run = intro_wc
    for wc in seg_wcs:
        cum_wcs.append(run)   # segment start = words BEFORE this segment
        run += wc

    # Map each cumulative count to a transcript index/time
    starts_hms: List[str] = []
    for cum in cum_wcs:
        idx = min(max(cum, 0), total_transcript_words - 1)
        ts = t_times[idx] if 0 <= idx < len(t_times) else t_times[-1]
        starts_hms.append(hhmmss(ts))
    return starts_hms

def outro_time_from_audio(
    transcript_words_with_time: List[Tuple[str, float]],
    total_duration_fallback: float = 0.0,
) -> str:
    if transcript_words_with_time:
        return hhmmss(transcript_words_with_time[-1][1])
    return hhmmss(total_duration_fallback)

def distribute_bullets_over_segments(bullets: List[Dict], seg_starts: List[str]) -> List[Dict]:
    """
    Evenly assign bullet notes (dicts with 'note'/'time') to segment starts.
    Returns new list where each bullet has time set to the start of its assigned segment.
    """
    if not bullets:
        return []
    if not seg_starts:
        # fallback to intro
        return [{"time": "00:00:00", "note": b.get("note", "")} for b in bullets]

    B, S = len(bullets), len(seg_starts)
    out = []
    # Proportionally divide B bullets into S buckets using rounding
    def bucket_end(i):  # bullets count up to segment i (exclusive)
        return round((i * B) / S)

    start_idx = 0
    for i in range(S):
        end_idx = bucket_end(i + 1)
        for j in range(start_idx, min(end_idx, B)):
            out.append({"time": seg_starts[i], "note": bullets[j].get("note", "")})
        start_idx = end_idx
    # Any leftovers (due to rounding) go to last segment
    for j in range(start_idx, B):
        out.append({"time": seg_starts[-1], "note": bullets[j].get("note", "")})
    return out