
import os
import re

from dotenv import load_dotenv
from sarvamai import SarvamAI


load_dotenv()


SUPPORTED_LANGUAGES = {
    "Assamese": "as-IN",
    "Bengali": "bn-IN",
    "Bodo": "brx-IN",
    "Dogri": "doi-IN",
    "English": "en-IN",
    "Gujarati": "gu-IN",
    "Hindi": "hi-IN",
    "Kannada": "kn-IN",
    "Kashmiri": "ks-IN",
    "Konkani": "kok-IN",
    "Maithili": "mai-IN",
    "Malayalam": "ml-IN",
    "Manipuri": "mni-IN",
    "Marathi": "mr-IN",
    "Nepali": "ne-IN",
    "Odia": "od-IN",
    "Punjabi": "pa-IN",
    "Sanskrit": "sa-IN",
    "Santali": "sat-IN",
    "Sindhi": "sd-IN",
    "Tamil": "ta-IN",
    "Telugu": "te-IN",
    "Urdu": "ur-IN"
}


MAX_CHUNK_SIZE = 1800


def get_translation_client():

    api_key = os.getenv("SARVAM_API_KEY")

    if not api_key:
        raise ValueError("SARVAM_API_KEY is missing from .env file")

    return SarvamAI(
        api_subscription_key=api_key
    )


def split_long_sentence(sentence, max_length=MAX_CHUNK_SIZE):

    words = sentence.split()

    chunks = []
    current_chunk = ""

    for word in words:

        if len(word) > max_length:
            raise ValueError(
                "A single word exceeds the translation API limit"
            )

        if not current_chunk:
            current_chunk = word

        elif len(current_chunk) + len(word) + 1 <= max_length:
            current_chunk += " " + word

        else:
            chunks.append(current_chunk)
            current_chunk = word

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def split_text_into_chunks(text, max_length=MAX_CHUNK_SIZE):

    if not text:
        return []

    paragraphs = re.split(r"\n+", text)

    chunks = []

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            continue

        sentences = re.split(
            r"(?<=[.!?।॥])\s+",
            paragraph
        )

        current_chunk = ""

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            if len(sentence) > max_length:

                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                long_parts = split_long_sentence(
                    sentence,
                    max_length
                )

                chunks.extend(long_parts)
                continue

            if not current_chunk:
                current_chunk = sentence

            elif len(current_chunk) + len(sentence) + 1 <= max_length:
                current_chunk += " " + sentence

            else:
                chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

    return chunks


def translate_text(
    text,
    target_language,
    source_language="en-IN"
):

    if not text or not text.strip():
        return ""

    if target_language not in SUPPORTED_LANGUAGES.values():
        raise ValueError("Unsupported target language")

    if source_language not in SUPPORTED_LANGUAGES.values():
        raise ValueError("Unsupported source language")

    if source_language == target_language:
        return text

    client = get_translation_client()

    chunks = split_text_into_chunks(text)

    translated_chunks = []

    for chunk in chunks:

        response = client.text.translate(
            input=chunk,
            source_language_code=source_language,
            target_language_code=target_language,
            model="sarvam-translate:v1"
        )

        translated_chunks.append(
            response.translated_text
        )

    return "\n\n".join(translated_chunks)


def translate_article(article, target_language):

    if target_language not in SUPPORTED_LANGUAGES.values():
        raise ValueError("Unsupported target language")

    source_language = "en-IN"

    if target_language == source_language:

        return {
            "title": article.title or "",
            "description": article.description or "",
            "content": article.content or "",
            "target_language": target_language
        }

    translated_title = translate_text(
        text=article.title or "",
        source_language=source_language,
        target_language=target_language
    )

    translated_description = translate_text(
        text=article.description or "",
        source_language=source_language,
        target_language=target_language
    )

    translated_content = translate_text(
        text=article.content or "",
        source_language=source_language,
        target_language=target_language
    )

    return {
        "title": translated_title,
        "description": translated_description,
        "content": translated_content,
        "target_language": target_language
    }
