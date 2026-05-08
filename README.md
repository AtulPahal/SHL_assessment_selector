# SHL Assessment Recommender

A production-grade Conversational SHL Assessment Recommender built with FastAPI, FAISS, and Gemini.

## Overview

This service helps hiring managers find the right SHL assessments through multi-turn dialogue. The agent takes a user from vague hiring intent to a grounded shortlist of real SHL assessments.

## Architecture

```
Scraper (scrape_catalog.py)
    ↓
catalog.json (SHL Individual Test Solutions)
    ↓
build_index.py → FAISS Index + Metadata
    ↓
FastAPI Service (main.py)
    ├── /health (health check)
    └── /chat (conversational agent)
         ↓
    Agent Logic (agent.py)
         ├── CLARIFY: Ask clarifying questions
         ├── RECOMMEND: Return catalog-based recommendations
         ├── REFINE: Update shortlist based on user feedback
         └── COMPARE: Compare specific assessments
         ↓
    Retriever (retriever.py) → FAISS vector search
         ↓
    LLM (Gemini 1.5 Flash) → Natural language response
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey).

### 3. Build the Index

```bash
python3 build_index.py
```

### 4. Run the Service

```bash
python3 main.py
```

The service will start at `http://localhost:8080`.

### 5. Test the Endpoint

```bash
# Health check
curl http://localhost:8080/health

# Chat
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need an assessment for senior software engineers"}]}'
```

## API Endpoints

### GET /health

Returns service health status.

```json
{"status": "ok"}
```

### POST /chat

Conversational agent endpoint.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "I need an assessment"},
    {"role": "assistant", "content": "What job role?"},
    {"role": "user", "content": "Software engineer"}
  ]
}
```

**Response:**
```json
{
  "reply": "Based on your needs, I recommend these assessments:",
  "recommendations": [
    {"name": "SHL Verify Cognitive Assessment", "url": "https://www.shl.com/...", "test_type": "A"}
  ],
  "end_of_conversation": false
}
```

## Test Suite

```bash
python3 test_agent.py
```

## Deployment

### Docker

```bash
docker build -t shl-recommender .
docker run -p 8080:8080 --env-file .env shl-recommender
```

### Render.com (Free Tier)

1. Push to GitHub
2. Connect to Render.com
3. Create Web Service with:
   - Build Command: `pip install -r requirements.txt && python build_index.py`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port 8080`
4. Set environment variable: `GEMINI_API_KEY`

## Project Structure

```
project/
├── scrape_catalog.py       # Standalone scraper
├── build_index.py          # Embeds catalog, saves FAISS index
├── catalog.json           # Scraped catalog data
├── catalog.index          # FAISS vector index
├── catalog_meta.json     # Index metadata
├── main.py                # FastAPI app
├── agent.py               # Agent logic
├── retriever.py          # FAISS retrieval wrapper
├── prompts.py             # System prompts
├── test_agent.py          # Test suite
├── requirements.txt
├── Dockerfile
├── .env.example
├── README.md
└── approach.md
```

## Deployed Endpoint

**Live URL:** `https://shl-recommender.onrender.com`

- Health: `https://shl-recommender.onrender.com/health`
- Chat: `https://shl-recommender.onrender.com/chat`

## License

Proprietary - SHL Assessment Recommender
