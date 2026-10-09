import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.retrievers import BM25Retriever

def setup_rag():
    """
    Initializes the Retrieval-Augmented Generation (RAG) system using BM25.
    This replaces ChromaDB and PyTorch embeddings to allow deployment on Render Free Tier.
    """
    loader = TextLoader("safety_manual.txt")
    documents = loader.load()
    
    # We split by SECTION to keep rules intact
    text_splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=0, separator="SECTION")
    docs = text_splitter.split_documents(documents)
    
    # Lightweight BM25 Retriever (No PyTorch/Chroma needed)
    retriever = BM25Retriever.from_documents(docs)
    retriever.k = 2
    
    return retriever

retriever = setup_rag()

def query_safety_manual(query: str) -> str:
    """
    Queries the safety manual using BM25 statistical search.
    """
    docs = retriever.invoke(query)
    return "\n\n".join([d.page_content for d in docs])
