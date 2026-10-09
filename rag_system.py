import os
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.vectorstores import VectorStoreRetriever

import sys

def setup_rag() -> VectorStoreRetriever:
    """
    Initializes the Retrieval-Augmented Generation (RAG) system by loading
    the safety manual, splitting it by section, and storing it in a ChromaDB vector store.
    
    Returns:
        VectorStoreRetriever: The initialized document retriever.
    """
    loader = TextLoader("safety_manual.txt")
    documents = loader.load()
    
    # We split by SECTION to keep rules intact
    text_splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=0, separator="SECTION")
    docs = text_splitter.split_documents(documents)
    
    # Redirect both stdout and stderr to devnull to prevent tqdm OSError
    with open(os.devnull, 'w') as devnull:
        old_stderr = sys.stderr
        old_stdout = sys.stdout
        sys.stderr = devnull
        sys.stdout = devnull
        try:
            # Local, free, and fast embeddings
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            # Store in ChromaDB
            vectorstore = Chroma.from_documents(documents=docs, embedding=embeddings, collection_name="railway_safety")
        finally:
            sys.stderr = old_stderr
            sys.stdout = old_stdout
            
    return vectorstore.as_retriever(search_kwargs={"k": 2})

retriever: VectorStoreRetriever = setup_rag()

def query_safety_manual(query: str) -> str:
    """
    Queries the safety manual vector database for rules related to the given query.
    
    Args:
        query (str): The search query.
        
    Returns:
        str: A concatenated string of retrieved rule contents.
    """
    docs = retriever.invoke(query)
    return "\n\n".join([d.page_content for d in docs])
