from celery import Celery
from config import REDIS_URL

# Initialize Celery app bound to Redis
app = Celery(
    "agentic_rag",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Celery Configurations
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@app.task
def process_file_task(file_path: str):
    """Asynchronous task to parse and index a document into Chroma."""
    # Delayed import to avoid circular imports during Celery worker startup
    from database import index_document
    try:
        index_document(file_path)
    except Exception as e:
        print(f"Failed to process file {file_path}: {e}")
        raise

@app.task
def delete_file_task(file_path: str):
    """Asynchronous task to delete document chunks from Chroma."""
    # Delayed import to avoid circular imports during Celery worker startup
    from database import delete_document
    try:
        delete_document(file_path)
    except Exception as e:
        print(f"Failed to delete file {file_path}: {e}")
        raise
