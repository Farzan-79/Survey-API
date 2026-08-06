from google import genai
from django.conf import settings

client = genai.Client(
    api_key = settings.GOOGLE_API_KEY
)

def generate_summary(prompt: str, model: str = settings.GEMINI_MODEL) -> str:
    response = client.models.generate_content(
            model = model,
            contents = prompt)

    return response.text