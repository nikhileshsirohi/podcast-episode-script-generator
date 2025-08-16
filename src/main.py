from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from src.schemas import GenerateRequest, GenerateResponse, Segment, ShowNote
from src.ingest.fetch import fetch_text_from_url, clean_text
from src.ingest.youtube import fetch_youtube_transcript
from src.ingest.files import read_any
from src.generation.gemini_client import generate_structured_script
from src.utils.cache import ingest_cache
from src.ingest.audio import transcribe_audio
from src.utils.timestamps import (
    estimate_segment_durations,
    cumulative_timestamps,
    hhmmss,
    snap_notes_to_segments,
    map_segments_to_audio_starts,
    outro_time_from_audio,
    distribute_bullets_over_segments
)

app = FastAPI(title="Podcast Episode Script Generator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Helper: NOT a route ----------
def _generate_from_source_text(source_text: str, payload: GenerateRequest) -> GenerateResponse:
    MIN_WORDS = 40
    source_text = clean_text(source_text)
    if not source_text or len(source_text.split()) < MIN_WORDS:
        raise HTTPException(
            status_code=422,
            detail=f"Source text is too short after cleaning (need at least {MIN_WORDS} words)."
        )

    data = generate_structured_script(source_text, payload.model, payload.max_words)

    segments = [Segment(**s) for s in data.get("segments", [])]
    title = data.get("title", "Podcast Episode")
    intro = data.get("intro", "")
    outro = data.get("outro", "")

    raw_notes = data.get("show_notes", [])
    show_notes = [ShowNote(note=str(n)) for n in raw_notes]

    if payload.include_timestamps and segments:
        # Estimate segment start times (text/URL/file text path)
        seg_texts = [s.content for s in segments]
        dur_secs = estimate_segment_durations(seg_texts, wpm=payload.speaking_wpm)
        intro_seconds = int(round(len(intro.split()) * (60.0 / max(payload.speaking_wpm, 1))))
        seg_starts = cumulative_timestamps(dur_secs, intro_pad=intro_seconds)

        # Intro + per-segment markers + outro
        show_notes = [ShowNote(time="00:00:00", note="Intro")] + show_notes
        for stamp, seg in zip(seg_starts, segments):
            show_notes.append(ShowNote(time=stamp, note=f"{seg.heading}"))
        total_secs = intro_seconds + sum(dur_secs)
        show_notes.append(ShowNote(time=hhmmss(total_secs), note="Outro"))

        # Snap model bullets with null time to nearest segment start (incl. Intro)
        seg_start_list = ["00:00:00"] + seg_starts
        notes_dicts = [{"time": n.time, "note": n.note} for n in show_notes]
        notes_dicts = snap_notes_to_segments(notes_dicts, seg_start_list)
        show_notes = [ShowNote(time=n["time"], note=n["note"]) for n in notes_dicts]

    return GenerateResponse(
        title=title,
        intro=intro,
        segments=segments,
        outro=outro,
        show_notes=show_notes,
    )


# ---------- Public routes ----------
@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest):
    if not payload.text and not payload.url:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'text'.")

    # Ingest by URL or use supplied text
    source_text = payload.text
    if payload.url:
        extracted = fetch_text_from_url(payload.url)
        if not extracted:
            raise HTTPException(status_code=422, detail="Failed to extract text from the given URL.")
        source_text = extracted

    return _generate_from_source_text(source_text, payload)


@app.post("/generate/youtube", response_model=GenerateResponse)
def generate_from_youtube(payload: GenerateRequest):
    if not payload.url:
        raise HTTPException(status_code=400, detail="Provide 'url' of a YouTube video.")
    key = f"yt::{payload.url}"
    if key in ingest_cache:
        source_text = ingest_cache[key]
    else:
        source_text = fetch_youtube_transcript(payload.url)
        if not source_text:
            raise HTTPException(status_code=422, detail="Failed to fetch YouTube transcript (disabled/unavailable).")
        ingest_cache[key] = source_text
    return _generate_from_source_text(source_text, payload)


@app.post("/generate/file", response_model=GenerateResponse)
async def generate_from_file(
    file: UploadFile = File(...),
    model: str = Form("gemini-1.5-flash"),
    max_words: int = Form(1200),
    speaking_wpm: int = Form(150),
    include_timestamps: bool = Form(True),
    language: str = Form(None),   # optional: "en", "hi", etc.
):
    name = (file.filename or "").lower()
    ct = (file.content_type or "").lower()

    def is_audio() -> bool:
        if ct.startswith("audio/"):
            return True
        for ext in (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".wma"):
            if name.endswith(ext):
                return True
        return False

    # -------------------- AUDIO PATH --------------------
    if is_audio():
        lang = (language or "").strip().lower()
        if lang in {"", "string", "none", "null"}:
            lang = None
        alias = {"english": "en", "hindi": "hi", "hin": "hi", "en-us": "en", "en-gb": "en", "en-in": "en"}
        lang = alias.get(lang, lang) or None

        tx = await transcribe_audio(file, language=lang)
        source_text = tx["text"]
        words_timeline = tx["words"]      # [(word_lower, start_sec), ...]
        duration = tx["duration"]

        # Disable timestamps in helper to avoid duplicates; we add audio-true stamps below
        payload = GenerateRequest(
            url=None,
            text=source_text,
            model=model,
            max_words=max_words,
            speaking_wpm=speaking_wpm,
            include_timestamps=False,
        )

        resp = _generate_from_source_text(source_text, payload)

        if include_timestamps and resp.segments and words_timeline:
            # Audio-true chapter markers
            seg_texts = [s.content for s in resp.segments]
            audio_starts = map_segments_to_audio_starts(
                words_timeline, seg_texts, intro_text=resp.intro
            )

            # 1) Chapter markers from *audio*
            chapter_notes = [ShowNote(time=t, note=seg.heading) for t, seg in zip(audio_starts, resp.segments)]

            # 2) Evenly distribute model bullets across segments (at their start times)
            raw_bullets = [{"note": n.note} for n in resp.show_notes]  # model bullets have no time
            distributed = distribute_bullets_over_segments(raw_bullets, audio_starts)
            bullet_notes = [ShowNote(time=d["time"], note=d["note"]) for d in distributed]

            # 3) Build final notes: Intro, bullets (now timed), chapters, Outro
            final_notes = [ShowNote(time="00:00:00", note="Intro")] + bullet_notes + chapter_notes
            final_notes.append(
                ShowNote(
                    time=outro_time_from_audio(words_timeline, total_duration_fallback=duration),
                    note="Outro",
                )
            )

            resp.show_notes = final_notes

        return resp

    # -------------------- NON-AUDIO PATH (txt/pdf) --------------------
    content = await read_any(file)
    if not content:
        raise HTTPException(
            status_code=422,
            detail="Unsupported or unreadable file. Try .txt/.pdf (or audio formats: .mp3/.wav/.m4a).",
        )

    # Small cache by name+size
    cache_key = f"file::{file.filename}::{len(content)}"
    if cache_key in ingest_cache:
        content = ingest_cache[cache_key]
    else:
        ingest_cache[cache_key] = content

    payload = GenerateRequest(
        url=None,
        text=content,
        model=model,
        max_words=max_words,
        speaking_wpm=speaking_wpm,
        include_timestamps=include_timestamps,
    )
    return _generate_from_source_text(content, payload)

    # uvicorn src.main:app --reload
    # python -m http.server 5500 -> http://127.0.0.1:5500