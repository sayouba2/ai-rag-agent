import os
import shutil
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_chroma import Chroma

from app.config import OPENAI_API_KEY, CHROMA_DIR, DATA_DIR


def load_documents():
    documents = []

    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
        return documents

    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)

        if filename.lower().endswith(".pdf"):
            loader = PyPDFLoader(filepath)
            documents.extend(loader.load())

        elif filename.lower().endswith(".txt"):
            loader = TextLoader(filepath, encoding="utf-8")
            documents.extend(loader.load())

    return documents


def ingest_documents():
    docs = load_documents()

    if not docs:
        return 0

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150
    )
    split_docs = splitter.split_documents(docs)

    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    # Supprime complètement l'ancienne DB seulement si elle existe
    # et avant toute nouvelle ouverture de Chroma dans cette fonction
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)

    vectordb = Chroma.from_documents(
        documents=split_docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )

    return len(split_docs)