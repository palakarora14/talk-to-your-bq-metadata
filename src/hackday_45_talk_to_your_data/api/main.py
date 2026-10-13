"""FastAPI application entry-point."""

from fastapi import FastAPI

from hackday_45_talk_to_your_data.api import session as sessions
from hackday_45_talk_to_your_data.api.models import ChatRequest, ChatResponse
from hackday_45_talk_to_your_data.chains.base import ChromaRetriever
from hackday_45_talk_to_your_data.chains.chains import detect_intent, run_chain
from hackday_45_talk_to_your_data.chains.reranker import rerank

app = FastAPI(title="Talk to Your Data", version="0.1.0")
_retriever = ChromaRetriever()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    history = sessions.get_history(req.session_id)

    intent = detect_intent(req.message)
    raw_chunks = _retriever.retrieve(req.message, intent, req.project, req.dataset, req.time_range, req.user_email)
    context_chunks = rerank(req.message, raw_chunks)

    reply = run_chain(req.message, context_chunks, history, req.model)

    sessions.append(req.session_id, "user", req.message)
    sessions.append(req.session_id, "assistant", reply)

    return ChatResponse(
        session_id=req.session_id,
        reply=reply,
        sources=context_chunks,
    )


@app.delete("/chat/{session_id}")
def clear_session(session_id: str) -> dict[str, str]:
    sessions.clear(session_id)
    return {"status": "cleared"}
