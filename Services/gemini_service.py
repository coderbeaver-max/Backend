
from google import genai
from langsmith import traceable

from prompts.system_prompt import SYSTEM_PROMPT
from config.settings import GEMINI_API_KEY


client = genai.Client(api_key=GEMINI_API_KEY)


@traceable(
    name="JARVIS Build Conversation Context",
    run_type="chain",
    tags=["jarvis", "memory", "conversation-context"],
)
def build_conversation_context(previous_messages):
    conversation_context = ""

    for role, content in previous_messages or []:
        conversation_context += f"{role}: {content}\n"

    return conversation_context


@traceable(
    name="JARVIS Build Gemini Prompt",
    run_type="chain",
    tags=["jarvis", "prompt-construction"],
)
def build_full_prompt(question: str, previous_messages=None) -> str:
    conversation_context = build_conversation_context(
        previous_messages
    )

    return f"""
{SYSTEM_PROMPT}

Previous Conversation:
{conversation_context}

Current User Question:
{question}
"""


@traceable(
    name="JARVIS Gemini Generation",
    run_type="llm",
    tags=["jarvis", "gemini", "generation"],
)
def generate_gemini_response(
    question: str,
    model_name: str,
    previous_messages=None,
):
    full_prompt = build_full_prompt(
        question=question,
        previous_messages=previous_messages,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
    )

    return response.text


@traceable(
    name="JARVIS Gemini Streaming",
    run_type="llm",
    tags=["jarvis", "gemini", "streaming"],
    reduce_fn=lambda chunks: "".join(chunks),
)
def stream_gemini_response(
    question: str,
    model_name: str,
    previous_messages=None,
):
    full_prompt = build_full_prompt(
        question=question,
        previous_messages=previous_messages,
    )

    stream_response = client.models.generate_content_stream(
        model=model_name,
        contents=full_prompt,
    )

    for chunk in stream_response:
        if hasattr(chunk, "text") and chunk.text:
            yield chunk.text
