# src/schemas.py
from typing import List, Optional
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    url: Optional[str] = Field(None, description="Public article/speech URL")
    text: Optional[str] = Field(None, description="Raw source text")
    model: str = Field("gemini-1.5-flash", description="Gemini model name")
    max_words: int = Field(1200, description="Target max words for script body")
    speaking_wpm: int = Field(150, description="Speaking speed for timestamps")
    include_timestamps: bool = Field(True, description="Whether to include timestamps in show notes")

class Segment(BaseModel):
    heading: str
    content: str

class ShowNote(BaseModel):
    time: Optional[str] = None      # "00:01:23"
    note: str                       # bullet text

class GenerateResponse(BaseModel):
    title: str
    intro: str
    segments: List[Segment]
    outro: str
    show_notes: List[ShowNote]