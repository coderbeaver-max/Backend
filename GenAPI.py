
import os

from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from config.settings import ALLOWED_MODELS

from routes.ask import router as ask_router
from routes.straem import router as stream_router


# =========================
# APP INIT
# =========================
app = FastAPI(
    title="GenAI Tutor API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# =========================
# CORS CONFIGURATION
# =========================
default_frontend_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://tutor-five-tawny.vercel.app",
]

configured_frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

frontend_origins = list(
    dict.fromkeys(
        default_frontend_origins + configured_frontend_origins
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_origin_regex=(
        r"^https://tutor-[a-z0-9-]+-coderbeaver-maxs-projects\.vercel\.app$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# ROUTER REGISTRATION
# =========================
app.include_router(ask_router)
app.include_router(stream_router)


# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def root():
    return {
        "status": "Backend running 🚀"
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "gemini": "connected",
        "server": "running",
        "allowed_models": list(ALLOWED_MODELS),
    }


# =========================
# PREFLIGHT
# =========================
@app.options("/api/ask")
def options_ask():
    return Response(status_code=200)


# =========================
# LOCAL RUN
# =========================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "GenAPI:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
