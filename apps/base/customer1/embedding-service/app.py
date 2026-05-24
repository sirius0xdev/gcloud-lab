"""
Lightweight embedding service wrapping nomic-embed-text-v1.5
OpenAI-compatible /v1/embeddings endpoint.
"""

import os
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# Model globals (loaded at startup)
_model = None
_tokenizer = None
_dimensions = 768  # nomic-embed-text-v1.5 output dimensions
_model_name = "nomic-embed-text-v1.5"


def load_model():
    """Load the embedding model at startup."""
    global _model, _tokenizer
    from sentence_transformers import SentenceTransformer

    model_path = os.getenv("MODEL_PATH", _model_name)
    print(f"Loading model: {model_path}")
    _model = SentenceTransformer(model_path, device="cpu")
    _model.max_seq_length = 8192  # nomic supports long contexts
    print(f"Model loaded. Dimensions: {_model.get_sentence_embedding_dimension()}")
    _dimensions = _model.get_sentence_embedding_dimension()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load model."""
    load_model()
    yield
    # Shutdown: no cleanup needed for CPU model


app = FastAPI(
    title="Embedding Service",
    description="OpenAI-compatible embedding service using nomic-embed-text-v1.5",
    version="1.0.0",
    lifespan=lifespan,
)


# --- Request/Response Models ---

class EmbeddingInput(BaseModel):
    input: str | list[str] = Field(..., description="Text to embed. Can be a string or list of strings.")
    model: str = Field(default=_model_name, description="Model name. Only nomic-embed-text-v1.5 is supported.")
    encoding_format: str = Field(default="float", description="Output format. Only 'float' is supported.")


class EmbeddingObject(BaseModel):
    object: str = "embedding"
    embedding: list[float]
    index: int


class UsageInfo(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingObject]
    model: str
    usage: UsageInfo


# --- Endpoints ---

@app.post("/v1/embeddings")
def create_embeddings(req: EmbeddingInput) -> EmbeddingResponse:
    """Create embeddings for input text(s). OpenAI-compatible."""
    # Normalize input to list
    if isinstance(req.input, str):
        texts = [req.input]
    else:
        texts = req.input

    if not texts:
        raise HTTPException(status_code=400, detail="Input must not be empty.")

    if len(texts) > 2048:
        raise HTTPException(status_code=400, detail="Input must have at most 2048 elements.")

    # Generate embeddings
    start = time.time()
    embeddings = _model.encode(
        texts,
        normalize_embeddings=True,  # cosine similarity ready
        show_progress_bar=False,
    ).tolist()

    elapsed = time.time() - start

    # Build response
    data = []
    total_tokens = 0
    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        tokens = len(text.split())  # rough token count
        total_tokens += tokens
        data.append(EmbeddingObject(
            object="embedding",
            embedding=emb,
            index=i,
        ))

    return EmbeddingResponse(
        object="list",
        data=data,
        model=req.model,
        usage=UsageInfo(
            prompt_tokens=total_tokens,
            total_tokens=total_tokens,
        ),
    )


@app.get("/v1/models")
def list_models():
    """List available models. OpenAI-compatible."""
    return {
        "object": "list",
        "data": [
            {
                "id": _model_name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "self",
            }
        ],
    }


@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "healthy",
        "model": _model_name,
        "dimensions": _dimensions,
        "ready": _model is not None,
    }
