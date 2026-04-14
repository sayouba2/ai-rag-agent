"""
Tests des endpoints FastAPI.

Les appels OpenAI et ChromaDB sont mockés pour ne pas nécessiter
de vraies clés API ni de base vectorielle.
"""
import io
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Fixture : app avec lifespan mocké
# ---------------------------------------------------------------------------


@pytest.fixture()
async def client():
    """
    Crée un AsyncClient pour l'app FastAPI.
    OpenAIEmbeddings, Chroma et ChatOpenAI sont mockés afin que le lifespan
    ne tente pas de connexions réseau réelles.
    """
    with (
        patch("app.main.OpenAIEmbeddings", return_value=MagicMock()),
        patch("app.main.Chroma", return_value=MagicMock()),
        patch("app.main.ChatOpenAI", return_value=MagicMock()),
        patch("app.main.build_rag_chain", return_value=MagicMock()),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /ask
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_returns_answer_and_session(client):
    with patch("app.main.ask_rag", return_value=("Réponse test", [])):
        res = await client.post("/ask", json={"question": "Qu'est-ce que ce document ?"})

    assert res.status_code == 200
    body = res.json()
    assert body["answer"] == "Réponse test"
    assert "session_id" in body
    assert isinstance(body["sources"], list)


@pytest.mark.asyncio
async def test_ask_reuses_session_id(client):
    with patch("app.main.ask_rag", return_value=("ok", [])):
        res = await client.post(
            "/ask",
            json={"question": "Question 2", "session_id": "my-session-123"},
        )

    assert res.status_code == 200
    assert res.json()["session_id"] == "my-session-123"


# ---------------------------------------------------------------------------
# /upload — validation extension
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_rejects_invalid_extension(client):
    res = await client.post(
        "/upload",
        files={"files": ("malware.exe", io.BytesIO(b"bad"), "application/octet-stream")},
    )
    assert res.status_code == 400
    assert ".exe" in res.json()["detail"]


# ---------------------------------------------------------------------------
# /upload — validation taille
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client):
    from app.config import MAX_FILE_SIZE_BYTES

    large = io.BytesIO(b"x" * (MAX_FILE_SIZE_BYTES + 1))
    res = await client.post(
        "/upload",
        files={"files": ("big.txt", large, "text/plain")},
    )
    assert res.status_code == 413


# ---------------------------------------------------------------------------
# /upload — fichier valide (sauvegarde + ingest mockés)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_valid_file(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))

    with (
        patch("app.main.ingest_documents", return_value=(5, 0)),
        patch("app.main.DATA_DIR", str(tmp_path)),
    ):
        res = await client.post(
            "/upload",
            files={"files": ("rapport.txt", io.BytesIO(b"contenu test"), "text/plain")},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["chunks_added"] == 5
    assert body["files_skipped"] == 0


# ---------------------------------------------------------------------------
# /history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_empty_session(client):
    res = await client.get("/history/session-inexistante")
    assert res.status_code == 200
    body = res.json()
    assert body["session_id"] == "session-inexistante"
    assert body["messages"] == []


@pytest.mark.asyncio
async def test_delete_history(client):
    with patch("app.main.clear_session") as mock_clear:
        res = await client.delete("/history/abc-123")
    assert res.status_code == 200
    mock_clear.assert_called_once_with("abc-123")
