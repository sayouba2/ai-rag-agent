import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import (
    ALLOWED_EXTENSIONS,
    CHROMA_DIR,
    CORS_ORIGINS,
    DATA_DIR,
    MAX_FILE_SIZE_BYTES,
    OPENAI_API_KEY,
)
from app.ingest import ingest_documents, sanitize_filename
from app.rag_chain import (
    ask_rag,
    ask_rag_stream,
    build_rag_chain,
    clear_session,
    get_all_messages,
)
from app.schemas import (
    AskRequest,
    AskResponse,
    HistoryMessage,
    HistoryResponse,
    IngestResponse,
    Source,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise les objets coûteux une seule fois au démarrage du serveur :
    embeddings, base vectorielle et LLM sont partagés entre toutes les requêtes.
    """
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
    vectordb = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini", temperature=0)

    app.state.vectordb = vectordb
    app.state.chain = build_rag_chain(vectordb, llm)

    yield
    # Pas de ressources à libérer explicitement pour ChromaDB / OpenAI


app = FastAPI(title="AI RAG Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Upload & Ingest
# ---------------------------------------------------------------------------


@app.post("/upload", response_model=IngestResponse)
async def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
):
    os.makedirs(DATA_DIR, exist_ok=True)

    for file in files:
        # Validation de l'extension côté serveur
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Extension '{ext}' non autorisée. "
                    f"Extensions acceptées : {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
            )

        content = await file.read()

        # Validation de la taille
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Le fichier '{file.filename}' dépasse la limite de "
                    f"{MAX_FILE_SIZE_BYTES // (1024 * 1024)} Mo."
                ),
            )

        safe_name = sanitize_filename(file.filename)
        filepath = os.path.join(DATA_DIR, safe_name)
        with open(filepath, "wb") as f:
            f.write(content)

    chunks_added, files_skipped = ingest_documents(request.app.state.vectordb)

    return IngestResponse(
        message="Fichiers uploadés et indexés avec succès.",
        chunks_added=chunks_added,
        files_skipped=files_skipped,
    )


@app.post("/ingest", response_model=IngestResponse)
def ingest(request: Request):
    """Ré-indexe les documents déjà présents dans DATA_DIR."""
    chunks_added, files_skipped = ingest_documents(request.app.state.vectordb)
    return IngestResponse(
        message="Documents indexés avec succès.",
        chunks_added=chunks_added,
        files_skipped=files_skipped,
    )


# ---------------------------------------------------------------------------
# Ask (synchrone)
# ---------------------------------------------------------------------------


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request):
    session_id = body.session_id or str(uuid.uuid4())
    answer, sources = ask_rag(request.app.state.chain, body.question, session_id)

    return AskResponse(
        answer=answer,
        sources=[Source(**s) for s in sources],
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# Ask (streaming SSE)
# ---------------------------------------------------------------------------


@app.post("/ask/stream")
def ask_stream(body: AskRequest, request: Request):
    """
    Endpoint streaming (Server-Sent Events).

    Émet successivement :
    1. {"type": "session_id", "session_id": "..."}
    2. {"type": "sources",    "sources": [...]}
    3. {"type": "token",      "content": "..."}  (répété)
    4. [DONE]
    """
    session_id = body.session_id or str(uuid.uuid4())

    def generate():
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
        yield from ask_rag_stream(request.app.state.chain, body.question, session_id)

    return StreamingResponse(generate(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Historique de conversation
# ---------------------------------------------------------------------------


@app.get("/history/{session_id}", response_model=HistoryResponse)
def get_history(session_id: str):
    messages = get_all_messages(session_id)
    return HistoryResponse(
        session_id=session_id,
        messages=[HistoryMessage(**m) for m in messages],
    )


@app.delete("/history/{session_id}")
def delete_history(session_id: str):
    clear_session(session_id)
    return {"message": f"Session '{session_id}' supprimée."}
