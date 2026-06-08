import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_openai import OpenAIEmbeddings

# Load environment variables from .env file
load_dotenv()

# Verify that OPENAI_API_KEY is present
if not os.environ.get("OPENAI_API_KEY"):
    raise ValueError(
        "ERROR: OPENAI_API_KEY is not set. Please copy .env.example to .env, "
        "add your OpenAI API key to .env, and try again."
    )

# Redis configuration for Celery
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Watchdog folder directory to monitor
WATCHED_DIR = os.environ.get("WATCHED_DIR", "./watched_documents")

# Local directory where Chroma DB vectors will be saved
CHROMA_DB_DIR = os.environ.get("CHROMA_DB_DIR", "./chroma_db")

def get_llm(model_name: str = "gpt-4o-mini", temperature: float = 0.0):
    """Initialize and return a chat model using init_chat_model."""
    return init_chat_model(model_name, temperature=temperature)

def get_embeddings():
    """Initialize and return OpenAIEmbeddings."""
    return OpenAIEmbeddings()
