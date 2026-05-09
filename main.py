"""
FastAPI application for SHL Assessment Recommender.
Provides /health and /chat endpoints.
"""

import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from contextlib import asynccontextmanager

# Import local modules
from retriever import get_retriever
from agent import SHLAgent

# Global agent instance
agent = None

# Get port - Render sets PORT env, default to 10000
PORT = int(os.environ.get("PORT", 10000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load resources at startup."""
    global agent
    print(f"Starting SHL Assessment Recommender on port {PORT}...")
    print("Loading FAISS index and model...")

    try:
        get_retriever()
        print("✓ Retriever loaded")
        agent = SHLAgent()
        print("✓ Agent initialized")
        print("Ready!")
    except Exception as e:
        print(f"✗ Startup error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    yield
    print("Shutting down...")


app = FastAPI(
    title="SHL Assessment Recommender",
    description="Conversational agent for finding the right SHL assessments",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    reply: str
    recommendations: List[Recommendation]
    end_of_conversation: bool


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    messages = [m.model_dump() for m in request.messages]

    try:
        response = await agent.process(messages)
        return ChatResponse(
            reply=response.get("reply", ""),
            recommendations=[
                Recommendation(
                    name=r.get("name", ""),
                    url=r.get("url", ""),
                    test_type=r.get("test_type", "")
                )
                for r in response.get("recommendations", [])
            ],
            end_of_conversation=response.get("end_of_conversation", False)
        )
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)