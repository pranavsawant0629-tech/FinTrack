from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config.settings import settings
from app.llm.llm_client import llm_client
from app.rag.retriever import rag_retriever, RetrievalResponse
from app.api.equity import router as equity_router
from app.api.crypto import router as crypto_router
from app.api.personal_finance import router as personal_finance_router
from app.api.derivatives import router as derivatives_router
from app.api.portfolio import router as portfolio_router
from app.api.news import router as news_router
from app.api.quiz import router as quiz_router
from app.api.onboarding import router as onboarding_router
from app.api.chat import router as chat_router
from app.api.memory import router as memory_router
from app.api.conversations import router as conversations_router

app = FastAPI(title="Finova AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(equity_router, prefix="/agents/equity", tags=["Equity Agent"])
app.include_router(crypto_router, prefix="/agents/crypto", tags=["Crypto Agent"])
app.include_router(personal_finance_router, prefix="/agents/personal-finance", tags=["Personal Finance Agent"])
app.include_router(derivatives_router, prefix="/agents/derivatives", tags=["Derivatives Agent"])
app.include_router(portfolio_router, prefix="/agents/portfolio", tags=["Portfolio Agent"])
app.include_router(news_router, prefix="/agents/news", tags=["News Agent"])
app.include_router(quiz_router, prefix="/agents/quiz", tags=["Quiz Agent"])
app.include_router(onboarding_router, prefix="/agents/onboarding", tags=["Onboarding Agent"])
app.include_router(chat_router, tags=["Central Orchestrator"])
app.include_router(memory_router)
app.include_router(conversations_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "ollama_model": settings.ollama_model,
    }


class TestLLMRequest(BaseModel):
    message: str


@app.post("/test-llm")
def test_llm(payload: TestLLMRequest):
    reply = llm_client.chat(payload.message)
    return {"reply": reply}


class RetrieveRequest(BaseModel):
    query: str
    top_k: int | None = None
    score_threshold: float | None = None
    topic: str | None = None
    authority_level: str | None = None


@app.post("/rag/retrieve", response_model=RetrievalResponse)
def retrieve(payload: RetrieveRequest):
    """
    RAG Core endpoint: Returns raw retrieved chunks, similarity scores,
    and citation/provenance metadata. Does NOT invoke any LLM.
    """
    return rag_retriever.retrieve(
        query=payload.query,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
        topic=payload.topic,
        authority_level=payload.authority_level,
    )