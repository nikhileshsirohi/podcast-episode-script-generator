from typing import Optional
import trafilatura

def fetch_text_from_url(url: str, *, include_comments: bool = False) -> Optional[str]:
    """
    Downloads and extracts main article text from a URL.
    Returns None if extraction fails.
    """
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    return trafilatura.extract(downloaded, include_comments=include_comments, favor_recall=True)
