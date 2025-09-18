from fastapi import FastAPI
from pydantic import BaseModel
import os
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Milvus
from langchain.chains import RetrievalQA
from langchain.llms.base import LLM
from langchain.schema import Document
import requests
from typing import List, Dict, Any


MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://localhost:5001/generate")

app = FastAPI(title="RAG API", description="RAG system")


# Minimal remote LLM wrapper for LangChain
class RemoteLLM(LLM):
    def __init__(self, url):
        self.url = url

    def _call(self, prompt, stop=None):
        r = requests.post(self.url, json={"prompt": prompt, "max_tokens": 512})
        return r.json()["text"]

    @property
    def _identifying_params(self):
        return {"url": self.url}

    @property
    def _llm_type(self):
        return "remote_llm"


# initialize embeddings + vectorstore lazily
emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


# connect Milvus via LangChain wrapper
vs = Milvus(
    collection_name="docs",
    connection_args={"host": MILVUS_HOST, "port": MILVUS_PORT},
    embedding_function=emb,
)
llm = RemoteLLM(LLM_SERVER_URL)
qa = RetrievalQA.from_chain_type(
    llm=llm, chain_type="stuff", retriever=vs.as_retriever(search_kwargs={"k": 6})
)


class QReq(BaseModel):
    question: str
    include_metadata: bool = True


class QAResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]] = []
    ticket_info: Dict[str, Any] = {}


def get_enhanced_context(docs: List[Document]) -> List[Dict[str, Any]]:
    """Extract enhanced metadata from retrieved documents"""
    sources = []
    for doc in docs:
        source_info = {
            "content": (
                doc.page_content[:200] + "..."
                if len(doc.page_content) > 200
                else doc.page_content
            ),
            "source_file": doc.metadata.get("source", "Unknown"),
            "ticket_id": doc.metadata.get("ticket_id", "Unknown"),
        }
        sources.append(source_info)
    return sources


def get_ticket_summary(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary of relevant tickets"""
    if not sources:
        return {}

    ticket_ids = list(set([s["ticket_id"] for s in sources]))

    return {
        "relevant_tickets": ticket_ids,
        "total_tickets": len(ticket_ids),
    }


@app.post("/qa", response_model=QAResponse)
async def qa_endpoint(req: QReq):
    """Query the RAG system with enhanced metadata"""
    try:
        # Get the answer using LangChain
        resp = qa.run(req.question)

        # Get source documents with metadata
        if req.include_metadata:
            # Retrieve documents with metadata
            docs = vs.similarity_search(req.question, k=6)
            sources = get_enhanced_context(docs)
            ticket_info = get_ticket_summary(sources)
        else:
            sources = []
            ticket_info = {}

        return QAResponse(answer=resp, sources=sources, ticket_info=ticket_info)

    except Exception as e:
        return QAResponse(
            answer=f"Error processing query: {str(e)}", sources=[], ticket_info={}
        )


@app.get("/search")
async def search_tickets(query: str, limit: int = 5):
    """Search for JIRA tickets by content"""
    try:
        docs = vs.similarity_search(query, k=limit)
        results = []

        for doc in docs:
            result = {
                "content": doc.page_content,
                "ticket_id": doc.metadata.get("ticket_id", "Unknown"),
                "source_file": doc.metadata.get("source", "Unknown"),
            }
            results.append(result)

        return {"query": query, "results": results, "count": len(results)}

    except Exception as e:
        return {"error": str(e), "results": [], "count": 0}


@app.get("/tickets")
async def list_tickets():
    """List all available JIRA tickets"""
    try:
        # This is a simplified version - in production you'd want to query the collection directly
        docs = vs.similarity_search("", k=100)  # Get a sample
        tickets = {}

        for doc in docs:
            ticket_id = doc.metadata.get("ticket_id", "Unknown")
            if ticket_id not in tickets:
                tickets[ticket_id] = {
                    "ticket_id": ticket_id,
                    "source_file": doc.metadata.get("source", "Unknown"),
                }

        return {"tickets": list(tickets.values()), "count": len(tickets)}

    except Exception as e:
        return {"error": str(e), "tickets": [], "count": 0}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "RAG API"}


@app.get("/")
async def root():
    return {
        "message": "RAG API",
        "endpoints": {
            "qa": "POST /qa - Ask questions about JIRA tickets",
            "search": "GET /search?query=... - Search tickets by content",
            "tickets": "GET /tickets - List all available tickets",
            "health": "GET /health - Health check",
        },
    }
