from google import genai
from prompts.system_prompt import SYSTEM_PROMPT
from config.settings import GEMINI_API_KEY


# =========================
# GEMINI CLIENT
# =========================
client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================
# GENERATE RESPONSE
# =========================
def generate_gemini_response(
    question: str,
    model_name: str
):
    full_prompt = f"""
{SYSTEM_PROMPT}

User Question:
{question}
"""

    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt
    )

    return response.text


# =========================
# STREAM RESPONSE
# =========================
def stream_gemini_response(
    question: str,
    model_name: str
):
    full_prompt = f"""
{SYSTEM_PROMPT}

User Question:
{question}
"""

    stream_response = client.models.generate_content_stream(
        model=model_name,
        contents=full_prompt
    )

    for chunk in stream_response:
        if hasattr(chunk, "text") and chunk.text:
            yield chunk.text