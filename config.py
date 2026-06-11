import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# Load environment variables from .env file
load_dotenv()

# Verify that OPENROUTER_API_KEY is present
if not os.environ.get("OPENROUTER_API_KEY"):
    raise ValueError(
        "ERROR: OPENROUTER_API_KEY is not set. Please copy .env.example to .env, "
        "add your OpenRouter API key to .env, and try again."
    )

# Redis configuration for Celery
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Watchdog folder directory to monitor
WATCHED_DIR = os.environ.get("WATCHED_DIR", "./watched_documents")

# Local directory where Chroma DB vectors will be saved
CHROMA_DB_DIR = os.environ.get("CHROMA_DB_DIR", "./chroma_db")

# Default Models from OpenRouter (Llama-3-8b-instruct free version)
DEFAULT_LLM_MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct:free")
DEFAULT_EMBEDDING_MODEL = os.environ.get("OPENROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")

def get_llm(model_name: str | None = None, temperature: float = 0.0, streaming: bool = False):
    """Initialize and return a chat model pointing to LM Studio."""
    # We ignore the model_name from OpenRouter and let LM Studio use whatever is loaded
    print(f"[Config] Initializing Chat Model (via LM Studio, streaming={streaming})")
    return ChatOpenAI(
        model="local-model", # LM studio doesn't care about the name, uses whatever is loaded
        temperature=temperature,
        api_key="lm-studio",
        base_url="http://localhost:1234/v1",
        streaming=streaming,
    )

def get_embeddings(model_name: str | None = None):
    """Initialize and return an embedding model pointing to OpenRouter."""
    # Safety adapter: redirect standard embedding names to the configured model
    if model_name is None or "text-embedding" in model_name:
        model_name = DEFAULT_EMBEDDING_MODEL
        
    print(f"[Config] Initializing Embeddings: {model_name} (via OpenRouter)")
    return OpenAIEmbeddings(
        model=model_name,
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )
