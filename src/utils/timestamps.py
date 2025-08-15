# src/utils/timestamps.py
from typing import List, Dict

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

    # Ensure at least intro exists
    if not seg_starts_hhmmss:
        seg_starts_hhmmss = ["00:00:00"]

    seg_starts_secs = [to_secs(t) for t in seg_starts_hhmmss]

    current_idx = 0
    for n in notes:
        t = n.get("time")
        if t is None:
            # assign current segment start
            n["time"] = seg_starts_hhmmss[current_idx]
        else:
            # advance current_idx if time passes next segment boundary
            try:
                ts = to_secs(t)
                while current_idx + 1 < len(seg_starts_secs) and ts >= seg_starts_secs[current_idx + 1]:
                    current_idx += 1
            except Exception:
                n["time"] = seg_starts_hhmmss[current_idx]
    return notes