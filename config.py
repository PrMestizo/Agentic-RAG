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

def get_llm(model_name: str = "gpt-4o-mini", temperature: float = 0.0):
    """Initialize and return a chat model using init_chat_model."""
    return init_chat_model(model_name, temperature=temperature)

def get_embeddings():
    """Initialize and return OpenAIEmbeddings."""
    return OpenAIEmbeddings()
