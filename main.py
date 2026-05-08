"""
FastAPI application for SHL Assessment Recommender.
Provides /health and /chat endpoints.
"""

import os
import sys
from contextlib import asynccontextmanager
from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Import local modules
from retriever import get_retriever
from agent import SHLAgent

# Global agent instance
agent = None

# Get port from environment (Render sets this)
# Default to 10000 for Render Docker, or 8080 for local
PORT = int(os.environ.get("PORT", 10000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load resources at startup."""
    global agent

    print("=" * 50)
    print("Starting SHL Assessment Recommender...")
    print(f"Port: {PORT}")
    print("Loading FAISS index and model...")

    try:
        # Pre-load the retriever
        get_retriever()
        print("Retriever loaded successfully")

        # Initialize agent
        agent = SHLAgent()
        print("Agent initialized")

        print("Ready!")
        print("=" * 50)

    except Exception as e:
        print(f"Error during startup: {e}")
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    """Single message in conversation history."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Request body for /chat endpoint."""
    messages: List[Message] = Field(..., min_length=1)

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {"role": "user", "content": "I need an assessment for hiring software engineers"}
                ]
            }
        }


class Recommendation(BaseModel):
    """Single assessment recommendation."""
    name: str
    url: str
    test_type: str


class ChatResponse(BaseModel):
    """Response body for /chat endpoint."""
    reply: str
    recommendations: List[Recommendation]
    end_of_conversation: bool

    class Config:
        json_schema_extra = {
            "example": {
                "reply": "Based on your needs, I recommend these assessments",
                "recommendations": [
                    {"name": "SHL Verify Cognitive Assessment", "url": "https://www.shl.com/products/assessments/cognitive-assessments/", "test_type": "A"}
                ],
                "end_of_conversation": False
            }
        }


@app.get("/health")
async def health():
    """Health check endpoint - returns status within 500ms."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint for SHL Assessment Recommender.

    Accepts conversation history and returns agent response with recommendations.
    """
    global agent

    if agent is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Convert messages to dict format for agent
    messages = [m.model_dump() for m in request.messages]

    try:
        response = await agent.process(messages)

        # Ensure response matches schema
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
        print(f"Error processing chat: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)