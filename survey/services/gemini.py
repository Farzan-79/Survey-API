import logging

from django.conf import settings

from google import genai
from google.genai import errors, types
import httpx

from .exceptions import AIServiceUnavailable

logger = logging.getLogger(__name__) # logger for showing the error details in the terminal, not on the page  

client = genai.Client(
    api_key=settings.GOOGLE_API_KEY,
    http_options=types.HttpOptions(
        timeout=settings.GEMINI_TIMEOUT * 1000,
    ),
)

def generate_summary(prompt: str, model: str = settings.GEMINI_MODEL) -> str:
    try:
        response = client.models.generate_content(
                model = model,
                contents = prompt)

        return response.text
    except (
    errors.APIError,
    httpx.HTTPError,
    ) as exc:
        logger.exception(
            "-------------------- Gemini summary generation failed for model '%s'. ----------------------------",
            model
        )

        raise AIServiceUnavailable(
            "AI service unavailable."
        ) from exc # reises our own error instead of the google error