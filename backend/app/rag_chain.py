import json
import os

from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_community.chat_message_histories import ChatMessageHistory

# Stockage en mémoire des historiques de session {session_id: ChatMessageHistory}
_session_store: dict[str, ChatMessageHistory] = {}


def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in _session_store:
        _session_store[session_id] = ChatMessageHistory()
    return _session_store[session_id]


def get_all_messages(session_id: str) -> list[dict]:
    """Retourne l'historique d'une session sous forme de liste de dicts."""
    history = _session_store.get(session_id)
    if not history:
        return []
    result = []
    for msg in history.messages:
        role = "human" if msg.type == "human" else "ai"
        result.append({"role": role, "content": msg.content})
    return result


def clear_session(session_id: str) -> None:
    _session_store.pop(session_id, None)


def build_rag_chain(vectordb: Chroma, llm: ChatOpenAI):
    """
    Construit la chaîne RAG avec historique de conversation.

    Utilise :
    - create_history_aware_retriever : reformule la question en tenant compte
      de l'historique pour améliorer la pertinence de la recherche vectorielle.
    - create_retrieval_chain + create_stuff_documents_chain : génère la réponse
      finale en injectant les documents récupérés dans le contexte.
    - RunnableWithMessageHistory : persiste automatiquement chaque échange dans
      le store de session.
    """
    retriever = vectordb.as_retriever(search_kwargs={"k": 4})

    # Prompt de reformulation : transforme une question de suivi en question autonome
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "Given a chat history and the latest user question which might reference "
            "context in the chat history, formulate a standalone question which can be "
            "understood without the chat history. "
            "Do NOT answer the question, just reformulate it if needed and otherwise "
            "return it as is."
        )),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )

    # Prompt de réponse finale
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a helpful AI assistant. "
            "Answer the user's question using ONLY the context below.\n"
            "If the answer is not in the context, say clearly that the information "
            "was not found in the documents.\n\n"
            "Context:\n{context}"
        )),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])

    qa_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, qa_chain)

    return RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer",
    )


def _extract_sources(context_docs: list) -> list[dict]:
    """Déduplique et formate les sources issues des documents récupérés."""
    sources = []
    seen: set[tuple] = set()
    for doc in context_docs:
        meta = doc.metadata
        filename = os.path.basename(meta.get("source", "unknown"))
        page = meta.get("page")
        excerpt = (
            doc.page_content[:200] + "..."
            if len(doc.page_content) > 200
            else doc.page_content
        )
        key = (filename, page, excerpt[:50])
        if key not in seen:
            seen.add(key)
            sources.append({"filename": filename, "page": page, "excerpt": excerpt})
    return sources


def ask_rag(chain, question: str, session_id: str) -> tuple[str, list[dict]]:
    """Appel synchrone : retourne (réponse, sources)."""
    result = chain.invoke(
        {"input": question},
        config={"configurable": {"session_id": session_id}},
    )
    answer = result["answer"]
    sources = _extract_sources(result.get("context", []))
    return answer, sources


def ask_rag_stream(chain, question: str, session_id: str):
    """
    Générateur SSE pour le streaming de la réponse.

    Émet des événements JSON de trois types :
    - {"type": "sources", "sources": [...]}   → liste des sources (émis en premier)
    - {"type": "token",   "content": "..."}   → token de réponse
    - "[DONE]"                                → fin du stream
    """
    sources_sent = False

    for chunk in chain.stream(
        {"input": question},
        config={"configurable": {"session_id": session_id}},
    ):
        if not sources_sent and "context" in chunk:
            sources = _extract_sources(chunk["context"])
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            sources_sent = True

        if "answer" in chunk and chunk["answer"]:
            yield f"data: {json.dumps({'type': 'token', 'content': chunk['answer']})}\n\n"

    yield "data: [DONE]\n\n"
