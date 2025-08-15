# src/utils/timestamps.py
from typing import List, Optional
from dataclasses import dataclass

def snap_notes_to_segments(
    notes: List[dict],
    seg_starts_hhmmss: List[str],
) -> List[dict]:
    """
    For any note with time==None, assign the closest earlier segment start.
    If no segment start exists yet, fallback to 00:00:00.
    """
    def to_secs(hms: str) -> int:
        h, m, s = map(int, hms.split(":"))
        return h*3600 + m*60 + s

    # Precompute seconds
    seg_starts_secs = [to_secs(t) for t in seg_starts_hhmmss]
    if not seg_starts_secs:
        seg_starts_secs = [0]
        seg_starts_hhmmss = ["00:00:00"]

    last_start_idx = 0
    for n in notes:
        if n.get("time") is None:
            # use current "last" start
            n["time"] = seg_starts_hhmmss[last_start_idx]
        else:
            # advance last_start_idx if this explicit note time passes a segment start
            try:
                t = to_secs(n["time"])
                while last_start_idx + 1 < len(seg_starts_secs) and t >= seg_starts_secs[last_start_idx + 1]:
                    last_start_idx += 1
            except Exception:
                # if parsing fails, just set to current last start
                n["time"] = seg_starts_hhmmss[last_start_idx]
    return notes