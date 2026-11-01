
import os
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

from backend.app.translation_service import SUPPORTED_LANGUAGES

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def get_client():
    # Created on first use, so the rest of the app still starts
    # when this key is missing.
    api_key = os.getenv("SARVAM_CHAT_API_KEY")

    if not api_key:
        raise ValueError("SARVAM_CHAT_API_KEY not found in .env file")

    return SarvamAI(api_subscription_key=api_key)

MODEL_NAME = "sarvam-105b"

LANGUAGE_NAMES = {
    code: name
    for name, code in SUPPORTED_LANGUAGES.items()
}


def generate_chat_response(message, language_code):

    if not message or not message.strip():
        raise ValueError("Message cannot be empty")

    language_name = LANGUAGE_NAMES.get(language_code)

    if not language_name:
        raise ValueError("Unsupported language")

    messages = [
        {
            "role": "system",
            "content": (
                "You are Bharat Brief AI Assistant. "
                "You are a helpful general-purpose AI assistant. "
                "Answer questions about education, coding, science, "
                "technology, history, news and general knowledge. "
                f"Always respond in {language_name}. "
                "Give clear, accurate and helpful answers."
            )
        },
        {
            "role": "user",
            "content": message.strip()
        }
    ]

    response = get_client().chat.completions(
        model=MODEL_NAME,
        messages=messages,
        max_tokens=1000,
        reasoning_effort=None
    )

    return response.choices[0].message.content
