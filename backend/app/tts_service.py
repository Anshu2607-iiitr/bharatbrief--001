import os
import re
import base64
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def get_client():
    # Created on first use, so the rest of the app still starts
    # when this key is missing.
    api_key = os.getenv("SARVAM_API_KEY")

    if not api_key:
        raise ValueError("SARVAM_API_KEY not found in .env file")

    return SarvamAI(api_subscription_key=api_key)

MAX_CHUNK_SIZE = 1800


def split_text_into_chunks(text):
    text = text.strip()

    if not text:
        return []

    sentences = re.split(r'(?<=[.!?।])\s+', text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        if len(sentence) > MAX_CHUNK_SIZE:
            words = sentence.split()

            for word in words:
                if len(current_chunk) + len(word) + 1 <= MAX_CHUNK_SIZE:
                    current_chunk = (current_chunk + " " + word).strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = word

            continue

        if len(current_chunk) + len(sentence) + 1 <= MAX_CHUNK_SIZE:
            current_chunk = (current_chunk + " " + sentence).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def generate_speech(text, language_code):
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    if len(text) > 2500:
        raise ValueError("Text exceeds 2500 characters")

    response = get_client().text_to_speech.convert(
        text=text,
        model="bulbul:v4-flash",
        language_code=language_code,
        output_audio_codec="mp3"
    )

    return base64.b64decode(response.audios[0])


def generate_long_speech(text, language_code):
    chunks = split_text_into_chunks(text)

    if not chunks:
        raise ValueError("Text cannot be empty")

    audio_parts = []

    for index, chunk in enumerate(chunks):
        print(f"Generating chunk {index + 1}/{len(chunks)}")

        audio = generate_speech(
            text=chunk,
            language_code=language_code
        )

        audio_parts.append(audio)

    return b"".join(audio_parts)