from typing import Optional
import trafilatura

def fetch_text_from_url(url: str, *, include_comments: bool = False) -> Optional[str]:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    return trafilatura.extract(downloaded, include_comments=include_comments, favor_recall=True)

def clean_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return text
    return " ".join(text.split())