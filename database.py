import os
import bs4
import requests
import subprocess
import tempfile
import pathlib
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from config import get_embeddings, CHROMA_DB_DIR

_vectorstore = None
_retriever = None

def load_web_page(url: str, bs_kwargs: dict | None = None) -> list[Document]:
    """Helper to download and parse a web page using BeautifulSoup."""
    response = requests.get(url)
    response.raise_for_status()
    soup = bs4.BeautifulSoup(response.text, "html.parser", **(bs_kwargs or {}))
    return [Document(page_content=soup.get_text(), metadata={"source": url})]

def extract_pdf_with_mineru(file_path: str) -> list[Document]:
    """Tries to extract PDF text using MinerU's CLI (magic-pdf)."""
    try:
        # Check if magic-pdf command exists in PATH
        subprocess.run(["magic-pdf", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Running MinerU (magic-pdf) on {file_path}...")
            cmd = ["magic-pdf", "-p", file_path, "-o", temp_dir]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            temp_path = pathlib.Path(temp_dir)
            md_files = list(temp_path.glob("**/*.md"))
            if md_files:
                md_file = md_files[0]
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                return [Document(page_content=content, metadata={"source": file_path})]
    except Exception as e:
        print(f"MinerU extraction failed or not installed (magic-pdf). Error: {e}")
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

def _build_default_database():
    """Fills the database with default Lilian Weng urls if empty."""
    urls = [
        "https://lilianweng.github.io/posts/2024-11-28-reward-hacking/",
        "https://lilianweng.github.io/posts/2024-07-07-hallucination/",
        "https://lilianweng.github.io/posts/2024-04-12-diffusion-video/",
    ]
    docs = [load_web_page(url) for url in urls]
    docs_list = [item for sublist in docs for item in sublist]

    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=100, chunk_overlap=50
    )
    doc_splits = text_splitter.split_documents(docs_list)
    
    vectorstore = get_vectorstore()
    vectorstore.add_documents(doc_splits)
    print(f"Indexed default Lilian Weng blog posts. Split into {len(doc_splits)} chunks.")

def get_retriever():
    """Exposes the retriever."""
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever()

def index_document(file_path: str):
    """Indexes a local file into Chroma DB."""
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
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=100, chunk_overlap=50
    )
    doc_splits = text_splitter.split_documents(docs)
    
    # Store
    vectorstore = get_vectorstore()
    batch_size = 5000
    for i in range(0, len(doc_splits), batch_size):
        batch = doc_splits[i:i+batch_size]
        vectorstore.add_documents(batch)
    print(f"Successfully indexed {abs_path}. Split into {len(doc_splits)} chunks.")

def delete_document(file_path: str):
    """Deletes all chunks of a document from Chroma DB based on its source metadata."""
    abs_path = os.path.abspath(file_path)
    vectorstore = get_vectorstore()
    try:
        db_data = vectorstore.get(where={"source": abs_path})
        ids = db_data.get("ids", [])
        if ids:
            print(f"Deleting {len(ids)} existing chunks for: {abs_path}")
            vectorstore.delete(ids=ids)
            print(f"Deleted successfully.")
        else:
            print(f"No existing chunks found for: {abs_path}")
    except Exception as e:
        print(f"Error checking/deleting existing chunks for {abs_path}: {e}")
