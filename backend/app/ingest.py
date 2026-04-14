import os
import json
import hashlib
import unicodedata
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    CSVLoader,
)
from langchain_chroma import Chroma

from app.config import DATA_DIR, ALLOWED_EXTENSIONS

# Chemin du fichier manifest qui trace les fichiers déjà indexés
MANIFEST_PATH = os.path.join(DATA_DIR, ".manifest.json")


def sanitize_filename(filename: str) -> str:
    """Prévient les attaques par traversée de chemin et sanitise le nom de fichier."""
    filename = unicodedata.normalize("NFKD", filename)
    # Garde uniquement les caractères alphanumériques, tirets, underscores et points
    filename = re.sub(r"[^\w\-. ]", "_", filename)
    # Supprime toute composante de chemin (ex: ../../etc/passwd -> passwd)
    filename = os.path.basename(filename)
    if not filename or filename.startswith("."):
        filename = "unnamed_file"
    return filename


def file_hash(filepath: str) -> str:
    """Calcule le SHA-256 d'un fichier pour détecter les modifications."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict:
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: dict) -> None:
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def _get_loader(filepath: str):
    """Retourne le loader LangChain adapté à l'extension du fichier."""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        return PyPDFLoader(filepath)
    elif ext in (".txt", ".md"):
        # Le Markdown est du texte brut, TextLoader suffit
        return TextLoader(filepath, encoding="utf-8")
    elif ext == ".csv":
        return CSVLoader(filepath, encoding="utf-8")
    elif ext == ".docx":
        # Import optionnel : nécessite le package docx2txt
        from langchain_community.document_loaders import Docx2txtLoader
        return Docx2txtLoader(filepath)
    return None


def ingest_documents(vectordb: Chroma) -> tuple[int, int]:
    """
    Indexe de façon incrémentale les documents du DATA_DIR.

    - Les fichiers déjà indexés (même hash SHA-256) sont ignorés.
    - Les fichiers modifiés voient leurs anciens chunks supprimés puis réindexés.
    - Les nouveaux fichiers sont indexés directement.

    Retourne (chunks_ajoutés, fichiers_ignorés).
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    manifest = load_manifest()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )

    chunks_added = 0
    files_skipped = 0

    for filename in sorted(os.listdir(DATA_DIR)):
        # Ignore les fichiers cachés (manifest, etc.)
        if filename.startswith("."):
            continue

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue

        filepath = os.path.join(DATA_DIR, filename)
        current_hash = file_hash(filepath)

        # Fichier déjà indexé avec le même contenu → on saute
        if manifest.get(filename, {}).get("hash") == current_hash:
            files_skipped += 1
            continue

        # Fichier modifié → suppression des anciens chunks
        if filename in manifest:
            old_ids = manifest[filename].get("ids", [])
            if old_ids:
                vectordb.delete(ids=old_ids)

        loader = _get_loader(filepath)
        if loader is None:
            continue

        try:
            docs = loader.load()
        except Exception as exc:
            print(f"[ingest] Impossible de charger '{filename}': {exc}")
            continue

        if not docs:
            continue

        split_docs = splitter.split_documents(docs)

        # IDs stables basés sur le nom de fichier + index de chunk
        chunk_ids = [f"{filename}__{i}" for i in range(len(split_docs))]

        vectordb.add_documents(documents=split_docs, ids=chunk_ids)

        manifest[filename] = {"hash": current_hash, "ids": chunk_ids}
        chunks_added += len(split_docs)

    save_manifest(manifest)
    return chunks_added, files_skipped
