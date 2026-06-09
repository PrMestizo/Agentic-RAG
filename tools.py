from langchain.tools import tool
from database import get_retriever

@tool
def retrieve_documents(query: str) -> str:
    """Search and return information from the user's ingested documents to answer questions."""
    retriever = get_retriever()
    docs = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])

retriever_tool = retrieve_documents
