from sentence_transformers import SentenceTransformer
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection
import os
import re
import yaml
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


def parse_jira_yaml(yaml_data, filename):
    """Parse JIRA YAML data and extract metadata"""
    try:
        # Extract ticket metadata from YAML
        ticket_id = yaml_data.get("id", filename.replace(".yml", ""))
        title = yaml_data.get("title", "No title")
        ticket_type = yaml_data.get("type", "Unknown")
        description = yaml_data.get("description", "")

        return {
            "ticket_id": ticket_id,
            "title": title,
            "ticket_type": ticket_type,
            "description": description,
            "source": "jira",
        }
    except Exception as e:
        print(f"Error parsing YAML for {filename}: {str(e)}")
        return None


def create_jira_content(title, description):
    """Create content string from title and description"""
    if not description or len(description.strip()) < 50:
        return None

    # Clean up description - remove markdown formatting and extra whitespace
    clean_description = re.sub(r"#+\s*", "", description)  # Remove markdown headers
    clean_description = re.sub(
        r"\n\s*\n", "\n", clean_description
    )  # Remove extra newlines
    clean_description = clean_description.strip()

    # Combine title and description
    content = f"{title}\n{clean_description}"
    return content


def chunk_jira_content(content, max_tokens=800, overlap=150):
    """Enhanced chunking for JIRA content"""
    if not content:
        return []

    # If content is small enough, keep as is
    if len(content) <= max_tokens * 4:  # Rough character to token ratio
        return [content]

    # Use regular chunking for larger content
    chunks = chunk_text(content, max_tokens, overlap)
    return [chunk for chunk in chunks if chunk.strip()]


def ingest_folder_jira(path: str):
    print("🚀 Starting JIRA ticket ingestion...")

    # Use a better embedding model for technical content
    model = SentenceTransformer("all-MiniLM-L6-v2")
    dim = model.get_sentence_embedding_dimension()
    col = create_collection(dim=dim)

    total_chunks = 0
    processed_files = 0
    skipped_files = 0

    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        if not fpath.endswith(".yml"):
            continue

        print(f"📄 Processing {fname}...")

        try:
            # Read and parse YAML file
            with open(fpath, "r", encoding="utf-8") as file:
                yaml_data = yaml.safe_load(file)

            # Parse JIRA ticket metadata
            metadata = parse_jira_yaml(yaml_data, fname)
            if not metadata:
                print(f"⚠️  Failed to parse metadata for {fname}")
                skipped_files += 1
                continue

            # Filter by type: only Task and Story
            if metadata["ticket_type"] not in ["Task", "Story"]:
                print(
                    f"⏭️  Skipping {fname}: type '{metadata['ticket_type']}' not in [Task, Story]"
                )
                skipped_files += 1
                continue

            # Create content from title and description
            content = create_jira_content(metadata["title"], metadata["description"])
            if not content:
                print(
                    f"⏭️  Skipping {fname}: no description or description too short (< 50 chars)"
                )
                skipped_files += 1
                continue

            # Chunk the content
            chunks = chunk_jira_content(content, max_tokens=800, overlap=150)

            if not chunks:
                print(f"⚠️  No chunks generated for {fname}")
                skipped_files += 1
                continue

            # Generate embeddings
            embeddings = model.encode(chunks, show_progress_bar=True).tolist()

            # Prepare records with metadata
            sources = [fname] * len(chunks)
            ticket_ids = [metadata["ticket_id"]] * len(chunks)

            # Insert into collection
            col.insert(
                [
                    embeddings,
                    chunks,
                    sources,
                    ticket_ids,
                ]
            )

            total_chunks += len(chunks)
            processed_files += 1

            print(f"✅ {fname}: {len(chunks)} chunks processed")
            print(f"   Ticket: {metadata['ticket_id']} - {metadata['title']}")
            print(f"   Type: {metadata['ticket_type']}")

        except Exception as e:
            print(f"❌ Error processing {fname}: {str(e)}")
            skipped_files += 1
            continue

    col.flush()
    print(f"\n🎉 Ingestion completed!")
    print(f"   Files processed: {processed_files}")
    print(f"   Files skipped: {skipped_files}")
    print(f"   Total chunks: {total_chunks}")
    print(f"   Collection: {collection_name}")


if __name__ == "__main__":
    ingest_folder_jira("/app/data/jira/data")
