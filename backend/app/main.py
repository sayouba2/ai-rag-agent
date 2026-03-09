from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os

from app.schemas import AskRequest, AskResponse, IngestResponse
from app.ingest import ingest_documents
from app.rag_chain import ask_rag
from app.config import DATA_DIR

app = FastAPI(title="AI RAG Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # pour dev seulement
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload", response_model=IngestResponse)
async def upload_files(files: list[UploadFile] = File(...)):
    os.makedirs(DATA_DIR, exist_ok=True)

    saved_count = 0
    for file in files:
        filepath = os.path.join(DATA_DIR, file.filename)
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        saved_count += 1

    chunks = ingest_documents()

    return IngestResponse(
        message="Files uploaded and indexed successfully.",
        files_indexed=chunks
    )


@app.post("/ingest", response_model=IngestResponse)
def ingest():
    chunks = ingest_documents()
    return IngestResponse(
        message="Documents indexed successfully.",
        files_indexed=chunks
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    answer = ask_rag(request.question)
    return AskResponse(answer=answer)