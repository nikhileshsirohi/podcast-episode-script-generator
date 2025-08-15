# src/main.py
from fastapi import FastAPI, HTTPException
from src.schemas import GenerateRequest, GenerateResponse, Segment, ShowNote
from src.ingest.fetch import fetch_text_from_url, clean_text
from src.generation.gemini_client import generate_structured_script
from src.utils.timestamps import (
    estimate_segment_durations,
    cumulative_timestamps,
    hhmmss,
    snap_notes_to_segments
)

app = FastAPI(title="Podcast Episode Script Generator")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest):
    if not payload.text and not payload.url:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'text'.")

    source_text = payload.text
    if payload.url:
        extracted = fetch_text_from_url(payload.url)
        if not extracted:
            raise HTTPException(status_code=422, detail="Failed to extract text from the given URL.")
        source_text = extracted
    source_text = clean_text(source_text)

    MIN_WORDS = 40
    if not source_text or len(source_text.split()) < MIN_WORDS:
        raise HTTPException(status_code=422, detail=f"Source text is too short after cleaning (need at least {MIN_WORDS} words).")

    data = generate_structured_script(source_text, payload.model, payload.max_words)

    # Normalize segments
    segments = [Segment(**s) for s in data.get("segments", [])]
    title = data.get("title", "Podcast Episode")
    intro = data.get("intro", "")
    outro = data.get("outro", "")

    # Base show notes as bullets (strings) from model; convert to ShowNote
    raw_notes = data.get("show_notes", [])
    show_notes = [ShowNote(note=str(n)) for n in raw_notes]

    # Optionally compute timestamps
    if payload.include_timestamps and segments:
        # Estimate durations per segment based on speaking rate
        seg_texts = [s.content for s in segments]
        dur_secs = estimate_segment_durations(seg_texts, wpm=payload.speaking_wpm)

        # Assume intro takes some time too
        intro_seconds = int(round(len(intro.split()) * (60.0 / max(payload.speaking_wpm, 1))))
        seg_starts = cumulative_timestamps(dur_secs, intro_pad=intro_seconds)

        # Prepend an intro note with 00:00:00
        show_notes = [ShowNote(time="00:00:00", note="Intro")] + show_notes

        # Also add per-segment “chapter” notes at their start times
        for stamp, seg in zip(seg_starts, segments):
            show_notes.append(ShowNote(time=stamp, note=f"{seg.heading}"))

        # Add an outro timestamp at the end
        total_secs = intro_seconds + sum(dur_secs)
        show_notes.append(ShowNote(time=hhmmss(total_secs), note="Outro"))

        # ---- NEW: snap null-time bullets to nearest segment start (incl. intro) ----
        seg_start_list = ["00:00:00"] + seg_starts
        notes_dicts = [{"time": n.time, "note": n.note} for n in show_notes]
        notes_dicts = snap_notes_to_segments(notes_dicts, seg_start_list)
        show_notes = [ShowNote(time=n["time"], note=n["note"]) for n in notes_dicts]
        # ---------------------------------------------------------------------------

    resp = GenerateResponse(
        title=title,
        intro=intro,
        segments=segments,
        outro=outro,
        show_notes=show_notes,
    )
    return resp