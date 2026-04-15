import asyncio
import time
import traceback
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from chatbot.models import ChatRequest, ChatResponse, Message
from chatbot.sessions import load_history, save_history, delete_history
from chatbot import rag

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="Roteiro IA — Chatbot",
    description="Chatbot RAG para criação e lapidação de roteiros de vídeo com base em anúncios de sucesso.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno: {str(exc)}"},
    )

# ── Rate limiting (in-memory, per-IP) ────────────────────────────
_RATE_LIMIT = 30  # requests
_RATE_WINDOW = 60  # seconds
_hits: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    skip = ("/", "/docs", "/openapi.json", "/app")
    if request.url.path in skip or request.url.path.startswith("/static"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_WINDOW
    _hits[client_ip] = [t for t in _hits[client_ip] if t > window_start]

    if len(_hits[client_ip]) >= _RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit excedido. Tente novamente em breve."},
        )

    _hits[client_ip].append(now)
    return await call_next(request)


# ── Auth dependency ──────────────────────────────────────────────
def _check_api_key(request: Request) -> None:
    if not settings.CHATBOT_API_KEY:
        return
    key = request.headers.get("x-api-key", "")
    if key != settings.CHATBOT_API_KEY:
        raise HTTPException(status_code=401, detail="API key inválida ou ausente.")


# ── Routes ───────────────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "ok", "message": "Roteiro IA Chatbot está rodando."}


@app.get("/app")
def serve_frontend():
    return FileResponse(_FRONTEND_DIR / "index.html")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, raw_request: Request):
    _check_api_key(raw_request)

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")

    session_id = request.session_id
    loop = asyncio.get_event_loop()

    history = await loop.run_in_executor(None, load_history, session_id) or request.history

    try:
        reply, campaigns_used = await loop.run_in_executor(
            None, rag.chat, request.message, history
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao processar resposta: {str(e)}")

    history.append(Message(role="user", content=request.message))
    history.append(Message(role="assistant", content=reply))

    try:
        await loop.run_in_executor(None, save_history, session_id, history)
    except Exception:
        traceback.print_exc()

    return ChatResponse(reply=reply, session_id=session_id, campaigns_used=campaigns_used)


@app.delete("/session/{session_id}")
async def clear_session(session_id: str, request: Request):
    _check_api_key(request)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, delete_history, session_id)
    return {"message": f"Sessão '{session_id}' apagada."}
