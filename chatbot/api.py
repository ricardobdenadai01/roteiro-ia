from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from chatbot.models import ChatRequest, ChatResponse, Message
from chatbot import rag

app = FastAPI(
    title="Roteiro IA — Chatbot",
    description="Chatbot RAG para criação e lapidação de roteiros de vídeo com base em anúncios de sucesso.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memória de sessão em memória (por session_id)
_sessions: dict[str, list[Message]] = {}


@app.get("/")
def health():
    return {"status": "ok", "message": "Roteiro IA Chatbot está rodando."}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="A mensagem não pode estar vazia.")

    session_id = request.session_id

    # Usa histórico do servidor se existir, senão usa o enviado pelo cliente
    history = _sessions.get(session_id, request.history)

    try:
        reply, campaigns_used = rag.chat(request.message, history)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao processar resposta: {str(e)}")

    # Atualiza memória da sessão
    history.append(Message(role="user", content=request.message))
    history.append(Message(role="assistant", content=reply))
    _sessions[session_id] = history

    return ChatResponse(reply=reply, session_id=session_id, campaigns_used=campaigns_used)


@app.delete("/session/{session_id}")
def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    return {"message": f"Sessão '{session_id}' apagada."}
