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
    openapi_url="/api/openapi.json"
)

# =========================
# ROUTER REGISTRATION
# =========================
app.include_router(ask_router)
app.include_router(stream_router)


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
        "allowed_models": list(ALLOWED_MODELS)
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
        reload=True
    )