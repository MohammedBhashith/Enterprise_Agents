from pathlib import Path
from typing import List, Dict

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from llm_config import get_llm
from rbac import can_access_document


DOCS_DIR = Path("data/documents")
CHROMA_DIR = Path("data/chroma_db")
COLLECTION_NAME = "enterprise_policy_docs"


def get_embeddings():
    """
    Local embedding model.
    This does not call Gemini/Groq, so it saves API usage.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )


def load_policy_documents() -> List[Document]:
    documents = []

    policy_files = [
        {
            "path": DOCS_DIR / "hr_policy.txt",
            "department": "HR",
            "source": "hr_policy.txt",
            "allowed_roles": "Employee,Manager,HR Team,Admin",
        },
        {
            "path": DOCS_DIR / "it_policy.txt",
            "department": "IT",
            "source": "it_policy.txt",
            "allowed_roles": "Employee,Manager,IT Team,Admin",
        },
    ]

    for file_info in policy_files:
        path = file_info["path"]

        if not path.exists():
            continue

        text = path.read_text(encoding="utf-8")

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "department": file_info["department"],
                    "source": file_info["source"],
                    "allowed_roles": file_info["allowed_roles"],
                },
            )
        )

    return documents


def build_vector_db():
    """
    Loads policy documents, chunks them, creates embeddings, and stores them in ChromaDB.
    Run this whenever documents are updated.
    """
    documents = load_policy_documents()

    if not documents:
        return "No documents found in data/documents."

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80
    )

    chunks = splitter.split_documents(documents)

    vector_db = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )

    vector_db.reset_collection()
    vector_db.add_documents(chunks)

    return f"Vector database created successfully with {len(chunks)} chunks."


def get_vector_db():
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(CHROMA_DIR),
    )


def retrieve_policy_docs(user_id: str, question: str, top_k: int = 3) -> List[Document]:
    """
    Retrieves top-K documents and filters them using RBAC.
    """
    vector_db = get_vector_db()

    docs = vector_db.similarity_search(question, k=top_k)

    allowed_docs = []

    for doc in docs:
        department = doc.metadata.get("department")

        if can_access_document(user_id, department):
            allowed_docs.append(doc)

    return allowed_docs


def answer_policy_question(user_id: str, question: str) -> str:
    """
    RAG answer:
    1. Retrieve relevant chunks.
    2. Apply RBAC filter.
    3. Use LLM only for final answer.
    """

    docs = retrieve_policy_docs(user_id, question)

    if not docs:
        return "I could not find any policy documents that you are allowed to access for this question."

    context = "\n\n".join(
        [
            f"Source: {doc.metadata.get('source')}\nContent: {doc.page_content}"
            for doc in docs
        ]
    )

    sources = sorted(set(doc.metadata.get("source") for doc in docs))

    prompt = f"""
You are an internal enterprise policy assistant.

Answer the user's question using only the provided policy context.
Keep the answer clear and short.
If the answer is not available in the context, say that it is not available in the internal policy documents.

User question:
{question}

Policy context:
{context}

Answer:
"""

    llm = get_llm(temperature=0.1)
    response = llm.invoke(prompt)

    answer = response.content if hasattr(response, "content") else str(response)

    return f"{answer}\n\nSources: {', '.join(sources)}"


if __name__ == "__main__":
    print(build_vector_db())