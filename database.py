import bs4
import requests
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from config import get_embeddings

_retriever = None

def load_web_page(url: str, bs_kwargs: dict | None = None) -> list[Document]:
    """Helper to download and parse a web page using BeautifulSoup."""
    response = requests.get(url)
    response.raise_for_status()
    soup = bs4.BeautifulSoup(response.text, "html.parser", **(bs_kwargs or {}))
    return [Document(page_content=soup.get_text(), metadata={"source": url})]

def _build_retriever():
    """Internal helper to load documents, split them, and index them into InMemoryVectorStore."""
    print("Loading documents from the web...")
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
    print(f"Indexed {len(docs_list)} documents split into {len(doc_splits)} chunks.")

    embeddings = get_embeddings()
    vectorstore = InMemoryVectorStore.from_documents(
        documents=doc_splits, embedding=embeddings
    )
    return vectorstore.as_retriever()

def get_retriever():
    """Exposes the retriever as a cached singleton to avoid re-indexing on multiple imports."""
    global _retriever
    if _retriever is None:
        _retriever = _build_retriever()
    return _retriever
