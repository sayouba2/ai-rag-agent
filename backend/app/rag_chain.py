from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate

from app.config import OPENAI_API_KEY, CHROMA_DIR


PROMPT_TEMPLATE = """
You are a helpful AI assistant.
Answer the user's question using ONLY the context below.
If the answer is not in the context, say clearly that the information was not found in the documents.

Context:
{context}

Question:
{question}
"""


def ask_rag(question: str) -> str:
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    vectordb = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )

    retriever = vectordb.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(question)

    if not docs:
        return "I could not find relevant information in the indexed documents."

    context = "\n\n".join([doc.page_content for doc in docs])

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    formatted_prompt = prompt.format(context=context, question=question)

    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model="gpt-4.1-mini",
        temperature=0
    )

    response = llm.invoke(formatted_prompt)
    return response.content