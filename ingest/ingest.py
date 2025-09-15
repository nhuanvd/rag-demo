from sentence_transformers import SentenceTransformer
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
import os
import re
from utils.chunker import chunk_text


MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", 19530))


connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)


collection_name = "docs"


def create_collection(dim=384):
    if Collection.exists(collection_name):
        print(
            f"Collection '{collection_name}' already exists, using existing collection"
        )
        return Collection(collection_name)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
        FieldSchema(name="ticket_id", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="ticket_type", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="priority", dtype=DataType.VARCHAR, max_length=20),
        FieldSchema(name="status", dtype=DataType.VARCHAR, max_length=20),
    ]
    schema = CollectionSchema(fields, description="JIRA RAG docs")
    col = Collection(collection_name, schema)
    col.create_index(
        "embedding",
        {
            "index_type": "HNSW",
            "metric_type": "COSINE",
            "params": {"M": 16, "efConstruction": 200},
        },
    )
    col.load()
    print(f"Created new collection '{collection_name}' with enhanced schema")
    return col


def parse_jira_ticket(text, filename):
    """Parse JIRA ticket content and extract metadata"""
    lines = text.split("\n")

    # Extract ticket metadata
    ticket_id = None
    title = None
    ticket_type = None
    status = None
    priority = None
    assignee = None
    reporter = None

    for line in lines:
        if line.startswith("JIRA TICKET:"):
            ticket_id = line.replace("JIRA TICKET:", "").strip()
        elif line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("TYPE:"):
            ticket_type = line.replace("TYPE:", "").strip()
        elif line.startswith("STATUS:"):
            status = line.replace("STATUS:", "").strip()
        elif line.startswith("PRIORITY:"):
            priority = line.replace("PRIORITY:", "").strip()
        elif line.startswith("ASSIGNEE:"):
            assignee = line.replace("ASSIGNEE:", "").strip()
        elif line.startswith("REPORTER:"):
            reporter = line.replace("REPORTER:", "").strip()

    return {
        "ticket_id": ticket_id or filename.replace(".txt", ""),
        "title": title or "No title",
        "ticket_type": ticket_type or "Unknown",
        "status": status or "Unknown",
        "priority": priority or "Unknown",
        "assignee": assignee or "Unknown",
        "reporter": reporter or "Unknown",
    }


def chunk_jira_ticket(text, max_tokens=800, overlap=150):
    """Enhanced chunking for JIRA tickets with better context preservation"""
    # Split by major sections first
    sections = re.split(r"\n(?:DESCRIPTION:|COMMENTS:|###|##)", text)

    chunks = []
    for section in sections:
        if not section.strip():
            continue

        # If section is small enough, keep as is
        if len(section) <= max_tokens * 4:  # Rough character to token ratio
            if section.strip():
                chunks.append(section.strip())
        else:
            # Further chunk large sections
            sub_chunks = chunk_text(section, max_tokens, overlap)
            chunks.extend(sub_chunks)

    # If no sections found, fall back to regular chunking
    if not chunks:
        chunks = chunk_text(text, max_tokens, overlap)

    return [chunk for chunk in chunks if chunk.strip()]


def ingest_folder_jira(path: str):
    print("🚀 Starting JIRA ticket ingestion...")

    # Use a better embedding model for technical content
    model = SentenceTransformer("all-MiniLM-L6-v2")
    dim = model.get_sentence_embedding_dimension()
    col = create_collection(dim=dim)

    total_chunks = 0
    processed_files = 0

    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        if not fpath.endswith(".txt"):
            continue

        print(f"📄 Processing {fname}...")

        try:
            text = open(fpath, "r", encoding="utf-8").read()

            # Parse JIRA ticket metadata
            metadata = parse_jira_ticket(text, fname)

            # Enhanced chunking for JIRA tickets
            chunks = chunk_jira_ticket(text, max_tokens=800, overlap=150)

            if not chunks:
                print(f"⚠️  No chunks generated for {fname}")
                continue

            # Generate embeddings
            embeddings = model.encode(chunks, show_progress_bar=True).tolist()

            # Prepare records with enhanced metadata
            sources = [fname] * len(chunks)
            ticket_ids = [metadata["ticket_id"]] * len(chunks)
            ticket_types = [metadata["ticket_type"]] * len(chunks)
            priorities = [metadata["priority"]] * len(chunks)
            statuses = [metadata["status"]] * len(chunks)

            # Insert into collection
            col.insert(
                [
                    embeddings,
                    chunks,
                    sources,
                    ticket_ids,
                    ticket_types,
                    priorities,
                    statuses,
                ]
            )

            total_chunks += len(chunks)
            processed_files += 1

            print(f"✅ {fname}: {len(chunks)} chunks processed")
            print(f"   Ticket: {metadata['ticket_id']} - {metadata['title']}")
            print(
                f"   Type: {metadata['ticket_type']}, Priority: {metadata['priority']}, Status: {metadata['status']}"
            )

        except Exception as e:
            print(f"❌ Error processing {fname}: {str(e)}")
            continue

    col.flush()
    print(f"\n🎉 Ingestion completed!")
    print(f"   Files processed: {processed_files}")
    print(f"   Total chunks: {total_chunks}")
    print(f"   Collection: {collection_name}")


if __name__ == "__main__":
    ingest_folder_jira("/app/data/jira")
