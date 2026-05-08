from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.generativeai as genai
from dotenv import load_dotenv

import os
import time

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# GEMINI CONFIG
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print("KEY:", GEMINI_API_KEY[:10])

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing")

genai.configure(api_key=GEMINI_API_KEY)

# =========================
# APP INIT
# =========================
app = FastAPI(
    title="GenAI Tutor API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# REQUEST MODEL
# =========================
class Model(BaseModel):
    user_id: str
    question: str
    model: str = "gemini-2.5-flash"

# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def root():
    return {"status": "Backend running 🚀"}

@app.get("/api/health")
def health():
    return {"message": "API healthy ✅"}

# =========================
# PREFLIGHT
# =========================
@app.options("/api/ask")
def options_ask():
    return Response(status_code=200)

@app.options("/api/stream")
def options_stream():
    return Response(status_code=200)

# =========================
# NORMAL RESPONSE API
# =========================
@app.post("/api/ask")
def ask_question(model: Model):

    try:

        ai_model = genai.GenerativeModel(model.model)

        response = ai_model.generate_content(
            model.question
        )

        return {
            "status": "success",
            "user_id": model.user_id,
            "question": model.question,
            "response": response.text
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================
# STREAMING API
# =========================
@app.post("/api/stream")
def stream_answer(model: Model):

    def generate():

        try:

            ai_model = genai.GenerativeModel(model.model)

            response = ai_model.generate_content(
                model.question,
                stream=True
            )

            for chunk in response:

                if hasattr(chunk, "text") and chunk.text:
                    yield chunk.text
                    time.sleep(0.01)

        except Exception as e:
            yield f"ERROR: {str(e)}"

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )

# =========================
# LOCAL RUN
# =========================
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "GenAPI:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )