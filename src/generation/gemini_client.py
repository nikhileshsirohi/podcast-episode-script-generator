import os
from typing import Dict, Any
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

def configure_gemini():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not set. Put it in your .env file.")
    genai.configure(api_key=api_key)

PROMPT_TEMPLATE = """
You are a senior podcast script writer.
Transform the SOURCE TEXT into a polished episode with the following JSON schema:

{{
  "title": "string",
  "intro": "2-4 sentences hook",
  "segments": [
    {{"heading": "string", "content": "150-250 words"}},
    {{"heading": "string", "content": "150-250 words"}}
  ],
  "outro": "2-3 sentences wrap-up with CTA to subscribe",
  "show_notes": ["5-8 concise bullets with key points, names, dates, links if present"]
}}

Rules:
- Keep language clear, engaging, and non-repetitive.
- Maintain neutral tone unless the text clearly expresses a stance.
- If the source contains events, include dates and names accurately.
- No markdown, ONLY valid JSON in the final output.

TARGET_MAX_WORDS = {max_words}

SOURCE TEXT:
\"\"\"{source_text}\"\"\"
"""

def generate_structured_script(source_text: str, model_name: str, max_words: int) -> Dict[str, Any]:
    if not source_text or not source_text.strip():
        raise ValueError("Empty source_text")

    configure_gemini()
    model = genai.GenerativeModel(model_name)
    prompt = PROMPT_TEMPLATE.format(source_text=source_text[:20000], max_words=max_words)
    resp = model.generate_content(prompt)
    # Gemini often returns code fences or stray text; try to parse robustly
    txt = resp.text.strip()
    # strip code fences if any
    if txt.startswith("```"):
        txt = txt.strip("`")
        # remove "json" hint if present
        txt = txt.replace("json\n", "").replace("json\r\n", "")
    # Minimal safety: fall back to a lightweight scaffold on parse error
    import json
    try:
        data = json.loads(txt)
    except Exception:
        data = {
            "title": "Podcast Episode",
            "intro": "Welcome to our show! Here's what we're covering today.",
            "segments": [{"heading": "Main Discussion", "content": source_text[:600]}],
            "outro": "Thanks for listening! Subscribe for more.",
            "show_notes": []
        }
    return data