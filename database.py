import os
import bs4
import requests
import subprocess
import tempfile
import pathlib
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from typing import List, Dict
from config import get_embeddings, CHROMA_DB_DIR
import pickle

class CustomEnsembleRetriever(BaseRetriever):
    retrievers: List[BaseRetriever]
    weights: List[float]
    
    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        all_docs_results = [r.invoke(query) for r in self.retrievers]
        
        c = 60
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Document] = {}
        
        for i, docs in enumerate(all_docs_results):
            weight = self.weights[i]
            for rank, doc in enumerate(docs):
                key = doc.page_content
                if key not in rrf_scores:
                    rrf_scores[key] = 0.0
                    doc_map[key] = doc
                rrf_scores[key] += weight * (1 / (rank + c))
                
        sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        return [doc_map[k] for k in sorted_keys][:10]

BM25_DOCS_PATH = os.path.abspath("bm25_docs.pkl")

def _load_bm25_docs():
    if os.path.exists(BM25_DOCS_PATH):
        try:
            with open(BM25_DOCS_PATH, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading BM25 docs: {e}")
    return []

def _save_bm25_docs(docs):
    try:
        with open(BM25_DOCS_PATH, "wb") as f:
            pickle.dump(docs, f)
    except Exception as e:
        print(f"Error saving BM25 docs: {e}")

_vectorstore = None
_retriever = None



def extract_pdf_with_mineru(file_path: str) -> list[Document]:
    """Tries to extract PDF text using MinerU's CLI via Docker."""
    try:
        # Create a persistent directory for MinerU output
        out_dir = os.path.abspath("mineru_extractions")
        os.makedirs(out_dir, exist_ok=True)
        
        abs_file_path = os.path.abspath(file_path)
        file_dir = os.path.dirname(abs_file_path)
        file_name = os.path.basename(abs_file_path)
        
        print(f"Running MinerU (Docker) on {file_path}...")
        
        # We mount the directory containing the PDF and the output directory into the container
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{file_dir}:/input",
            "-v", f"{out_dir}:/output",
            "mineru:latest",
            "mineru", "-b", "pipeline", "-p", f"/input/{file_name}", "-o", "/output"
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        base_name = os.path.splitext(file_name)[0]
        pdf_out_dir = pathlib.Path(out_dir) / base_name
        
        if pdf_out_dir.exists():
            md_files = list(pdf_out_dir.glob("**/*.md"))
        else:
            md_files = list(pathlib.Path(out_dir).glob("**/*.md"))

        if md_files:
            # Use the most recently modified markdown file to ensure we get the latest extraction
            md_file = max(md_files, key=os.path.getmtime)
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            return [Document(page_content=content, metadata={"source": file_path})]
    except Exception as e:
        print(f"MinerU Docker extraction failed. Error: {e}")
    return []

def extract_text_from_file(file_path: str) -> list[Document]:
    """Extracts text from files. Integrates MinerU for PDFs with fallback loaders."""
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Try MinerU for PDFs
    if ext == ".pdf":
        docs = extract_pdf_with_mineru(file_path)
        if docs:
            return docs
            
        # Fallback to standard PDF loaders
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            return loader.load()
        except ImportError:
            print("WARNING: 'pypdf' is not installed. PDF fallback loader skipped. Run `poetry add pypdf` to parse PDFs without MinerU.")
            return []
        except Exception as e:
            print(f"PDF fallback loader error: {e}")
            return []

    # 2. Text or Markdown files
    if ext in [".txt", ".md", ".markdown"]:
        try:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path, encoding="utf-8")
            return loader.load()
        except Exception as e:
            print(f"TextLoader error: {e}")

    # 3. HTML files
    if ext in [".html", ".htm"]:
        try:
            from langchain_community.document_loaders import BSHTMLLoader
            loader = BSHTMLLoader(file_path)
            return loader.load()
        except Exception as e:
            print(f"BSHTMLLoader error: {e}")

    # 4. Fallback to basic file read
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": file_path})]
    except Exception as e:
        print(f"Generic file read error for {file_path}: {e}")
    return []

def get_vectorstore():
    """Returns the Chroma vector store instance, initializing it if necessary."""
    global _vectorstore
    if _vectorstore is None:
        embeddings = get_embeddings()
        _vectorstore = Chroma(
            persist_directory=CHROMA_DB_DIR,
            embedding_function=embeddings
        )
    return _vectorstore



def get_retriever():
    """Exposes the hybrid retriever."""
    global _retriever
    if _retriever is not None:
        return _retriever

    vectorstore = get_vectorstore()
    chroma_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    
    bm25_docs = _load_bm25_docs()
    if not bm25_docs:
        print("WARNING: BM25 index is empty. Falling back to semantic search only.")
        _retriever = chroma_retriever
        return _retriever
        
    bm25_retriever = BM25Retriever.from_documents(bm25_docs)
    bm25_retriever.k = 10
    
    ensemble_retriever = CustomEnsembleRetriever(
        retrievers=[chroma_retriever, bm25_retriever],
        weights=[0.5, 0.5]
    )
    _retriever = ensemble_retriever
    return _retriever

def index_document(file_path: str):
    """Indexes a local file into Chroma DB."""
    global _retriever
    _retriever = None
    abs_path = os.path.abspath(file_path)
    print(f"Indexing document: {abs_path}")
    
    # Remove existing chunks first (for updating)
    delete_document(abs_path)
    
    # Extract
    docs = extract_text_from_file(abs_path)
    if not docs:
        print(f"No content extracted from {abs_path}. Skipping.")
        return
        
    # Split
    print("Applying Recursive Character Text Splitting...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    doc_splits = text_splitter.split_documents(docs)
    
    # Contextual Retrieval Injection
    print("Applying Contextual Retrieval (Chunk-level metadata injection)...")
    from config import get_llm
    llm = get_llm()
    
    # Step 1: Global Context
    global_context = "Unknown document context"
    try:
        first_page_content = docs[0].page_content[:2000] if docs else ""
        global_prompt = f"Extract the Title, Author/Company, and Main Topic of this document. Keep it extremely brief (max 2 sentences).\nDocument start: {first_page_content}"
        global_context = llm.invoke(global_prompt).content
        print(f"Global Context extracted: {global_context}")
    except Exception as e:
        print(f"Failed to extract Global Context: {e}")
        
    # Step 2: Chunk-level Context
    for i, chunk in enumerate(doc_splits):
        if i % 10 == 0:
            print(f"Injecting context into chunk {i+1}/{len(doc_splits)}...")
            
        chunk_summary = ""
        try:
            # Truncate chunk text to ~8000 characters to prevent LM Studio context overflow
            truncated_text = chunk.page_content[:8000]
            chunk_prompt = (
                f"Document context: {global_context}\n"
                f"Chunk text: {truncated_text}\n"
                "Given the document context, write a single concise sentence summarizing the specific topic, entities, or metrics discussed in this chunk. "
                "Reply ONLY with that single sentence."
            )
            chunk_summary = llm.invoke(chunk_prompt).content
        except Exception as e:
            print(f"Failed to summarize chunk {i+1}, using only global context. Error: {e}")
        
        # Prepend context to the text so the embedding model sees it
        if chunk_summary:
            chunk.page_content = f"Context: {global_context} - {chunk_summary}\n\nOriginal Text: {chunk.page_content}"
        else:
            chunk.page_content = f"Context: {global_context}\n\nOriginal Text: {chunk.page_content}"
    
    # Store
    vectorstore = get_vectorstore()
    batch_size = 5000
    for i in range(0, len(doc_splits), batch_size):
        batch = doc_splits[i:i+batch_size]
        vectorstore.add_documents(batch)
    print(f"Successfully indexed {abs_path} into Chroma DB.")
    
    # Store in BM25 list
    bm25_docs = _load_bm25_docs()
    bm25_docs.extend(doc_splits)
    _save_bm25_docs(bm25_docs)
    print(f"Successfully added {abs_path} to BM25 index. Split into {len(doc_splits)} chunks.")

def delete_document(file_path: str):
    """Deletes all chunks of a document from Chroma DB based on its source metadata."""
    global _retriever
    _retriever = None
    abs_path = os.path.abspath(file_path)
    vectorstore = get_vectorstore()
    try:
        db_data = vectorstore.get(where={"source": abs_path})
        ids = db_data.get("ids", [])
        if ids:
            print(f"Deleting {len(ids)} existing chunks from Chroma for: {abs_path}")
            vectorstore.delete(ids=ids)
            print(f"Deleted from Chroma successfully.")
        else:
            print(f"No existing chunks found in Chroma for: {abs_path}")
            
        # Delete from BM25 list
        bm25_docs = _load_bm25_docs()
        original_len = len(bm25_docs)
        bm25_docs = [doc for doc in bm25_docs if doc.metadata.get("source") != abs_path]
        if len(bm25_docs) < original_len:
            _save_bm25_docs(bm25_docs)
            print(f"Deleted {original_len - len(bm25_docs)} chunks from BM25 index.")
            
    except Exception as e:
        print(f"Error checking/deleting existing chunks for {abs_path}: {e}")
