# RAG System

A RAG (Retrieval-Augmented Generation) system built with LLaMA 3, LangChain, and Milvus.

## Architecture

```
Documents → Ingestion → Milvus → LangChain → LLaMA 3 → Response
```

## Features

- Document ingestion with metadata extraction
- Vector search and retrieval
- Question answering with source attribution
- REST API for queries

## Quick Start

### 1. Download a Model
Choose one of these models:

**Mistral 7B (Recommended - 4.1GB)**
```bash
cd models
wget -O small-model.ggml https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGML/resolve/main/mistral-7b-instruct-v0.1.Q4_0.bin
```

**CodeLlama 7B (Best for technical docs - 3.8GB)**
```bash
cd models
wget -O small-model.ggml https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGML/resolve/main/codellama-7b-instruct.Q4_0.bin
```

**Phi-3 Mini (Most efficient - 2.3GB)**
```bash
cd models
wget -O small-model.ggml https://huggingface.co/TheBloke/Phi-3-mini-4k-instruct-GGML/resolve/main/Phi-3-mini-4k-instruct-q4.gguf
```

### 2. Start Services
```bash
docker compose up --build -d
```

### 3. Ingest Documents
```bash
docker compose run --rm ingest
```

### 4. Test API
```bash
curl -X POST "http://localhost:8000/qa" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the main content?"}'
```

## Adding Documents

1. Place `.txt` files in `data/jira/` directory
2. Run: `docker compose run --rm ingest`

## Troubleshooting

- **Model not found**: Check `./models/small-model.ggml` exists
- **Out of memory**: Use Phi-3 Mini (2.3GB) or increase Docker memory
- **Download fails**: Try `curl -L -o small-model.ggml "URL"`
- **Service errors**: Check logs with `docker compose logs`
