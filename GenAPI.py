from fastapi import FastAPI, Response, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import json
import time

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
# xAI CONFIG
# =========================
import os

XAI_API_KEY = os.getenv("XAI_API_KEY")

XAI_URL = "https://api.x.ai/v1/responses"

# =========================
# REQUEST MODEL
# =========================
class Model(BaseModel):
    user_id: str
    question: str
    model: str = "grok-4.20-reasoning"

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
# PREFLIGHT (CORS)
# =========================
@app.options("/api/ask")
def options_ask():
    return Response(status_code=200)

@app.options("/api/stream")
def options_stream():
    return Response(status_code=200)

# =========================
# NON-STREAM API
# =========================
@app.post("/api/ask")
def ask_question(model: Model):

    try:

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {XAI_API_KEY}"
        }

        payload = {
            "model": model.model,
            "input": model.question
        }

        response = requests.post(
            XAI_URL,
            headers=headers,
            json=payload,
            timeout=120
        )

        # if API returns error
        if response.status_code != 200:
            return {
                "status": "error",
                "code": response.status_code,
                "details": response.text
            }

        data = response.json()

        return {
            "status": "success",
            "user_id": model.user_id,
            "question": model.question,
            "response": data
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

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {XAI_API_KEY}"
            }

            payload = {
                "model": model.model,
                "input": model.question
            }

            response = requests.post(
                XAI_URL,
                headers=headers,
                json=payload,
                timeout=120
            )

            if response.status_code != 200:
                yield f"ERROR: {response.text}"
                return

            data = response.json()

            # convert response to pretty text
            text = json.dumps(data, indent=2)

            # stream response
            for char in text:
                yield char
                time.sleep(0.003)

        except Exception as e:

            yield f"ERROR: {str(e)}"

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )