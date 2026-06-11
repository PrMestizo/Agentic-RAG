import os
from langchain.tools import tool
from database import get_retriever, get_vectorstore

@tool
def retrieve_documents(query: str) -> str:
    """Search and return information from the user's ingested documents to answer questions."""
    retriever = get_retriever()
    docs = retriever.invoke(query)
    
    formatted_docs = []
    total_chars = 0
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "Unknown source")
        # Extract filename if it is a path to keep context clean
        if os.path.isabs(source) or "/" in source or "\\" in source:
            source = os.path.basename(source)
        
        chunk_text = f"Document {i+1} (Source: {source}):\n{doc.page_content}"
        
        # Enforce maximum text context limit to prevent LM Studio / local LLM crash/truncation (16k chars/4k tokens is safe and fast for local GPUs)
        if total_chars + len(chunk_text) > 16000:
            print("[Tools] Warning: Context limit reached (16k chars). Truncating further documents.")
            break
            
        formatted_docs.append(chunk_text)
        total_chars += len(chunk_text)
        
    return "\n\n".join(formatted_docs)

@tool
def list_ingested_documents() -> str:
    """List all unique source documents currently ingested in the RAG database, including their title, author/company, and main topic."""
    vectorstore = get_vectorstore()
    try:
        # Get all documents and their metadata
        db_data = vectorstore.get(include=["metadatas", "documents"])
        
        unique_docs = {}
        for doc_text, meta in zip(db_data.get("documents", []), db_data.get("metadatas", [])):
            source = meta.get("source", "Unknown source")
            if os.path.isabs(source) or "/" in source or "\\" in source:
                source = os.path.basename(source)
            
            # Save the chunk that contains the Context header (first page / metadata header)
            if source not in unique_docs:
                unique_docs[source] = doc_text
            elif "Context:" in doc_text and "Context:" not in unique_docs[source]:
                unique_docs[source] = doc_text
                
        if not unique_docs:
            return "No documents are currently ingested in the database."
            
        formatted_list = []
        for filename, content in sorted(unique_docs.items()):
            header = "No metadata extracted."
            if "Context:" in content:
                parts = content.split("Original Text:")
                header = parts[0].replace("Context:", "").strip()
            
            formatted_list.append(f"File: {filename}\n{header}\n" + "-"*40)
            
        return "Ingested documents catalog:\n\n" + "\n\n".join(formatted_list)
    except Exception as e:
        return f"Error retrieving document metadata: {e}"

retriever_tool = retrieve_documents
