
import os
import base64
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def get_client():
    # Created on first use, so the rest of the app still starts
    # when this key is missing.
    api_key = os.getenv("SARVAM_PODCAST_API_KEY")

    if not api_key:
        raise ValueError("SARVAM_PODCAST_API_KEY not found in .env file")

    return SarvamAI(api_subscription_key=api_key)

CHAT_MODEL = "sarvam-105b"
TTS_MODEL = "bulbul:v4-flash"

SUPPORTED_PODCAST_LANGUAGES = {
    "hi-IN",
    "en-IN",
    "bn-IN",
    "gu-IN",
    "kn-IN",
    "mr-IN",
    "pa-IN",
    "ta-IN",
    "te-IN"
}


def generate_podcast_script(articles, language_code, duration):

    if not articles:
        raise ValueError("No news articles provided")

    if language_code not in SUPPORTED_PODCAST_LANGUAGES:
        raise ValueError("Podcast voice is not available for this language yet")

    news_text = ""

    for i, article in enumerate(articles, start=1):
        news_text += f"""
News {i}
Title: {article.get('title', '')}
Description: {article.get('description', '')}
Content: {article.get('content', '')}
"""

    prompt = f"""
You are a professional Indian news podcast presenter.

Create a natural and engaging news podcast script.

Language code: {language_code}
Target duration: {duration} minutes.

Use only the information provided in the news articles.
Do not invent facts, dates, quotes or statistics.
Combine duplicate reports about the same event.
Cover the most important information first.
Use smooth transitions between stories.
Start with a welcome introduction.
End with a short closing statement.

Write a script suitable for spoken narration.
Do not include headings, bullet points or production instructions.

News articles:
{news_text}
"""

    response = get_client().chat.completions(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        reasoning_effort=None,
        max_tokens=4000
    )

    script = response.choices[0].message.content

    if not script:
        raise ValueError("Podcast script generation failed")

    return script.strip()


def split_text_into_chunks(text, max_size=2300):

    words = text.split()
    chunks = []
    current_chunk = ""

    for word in words:

        if len(current_chunk) + len(word) + 1 <= max_size:
            current_chunk += (" " if current_chunk else "") + word

        else:
            if current_chunk:
                chunks.append(current_chunk)

            current_chunk = word

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def generate_podcast_audio(script, language_code):

    if language_code not in SUPPORTED_PODCAST_LANGUAGES:
        raise ValueError("Podcast voice is not available for this language yet")

    chunks = split_text_into_chunks(script)

    audio_parts = []

    for i, chunk in enumerate(chunks, start=1):

        print(f"Generating podcast audio chunk {i}/{len(chunks)}")

        response = get_client().text_to_speech.convert(
            model=TTS_MODEL,
            text=chunk,
            language_code=language_code
        )

        if not response.audios:
            raise ValueError("Audio generation failed")

        audio_bytes = base64.b64decode(response.audios[0])
        audio_parts.append(audio_bytes)

    return b"".join(audio_parts)
