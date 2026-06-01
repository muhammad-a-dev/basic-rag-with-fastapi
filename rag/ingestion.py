from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import load_dotenv
import os
from rag.config import *

load_dotenv()
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")




def load_document(file_path):
    """
    This function loads a document from the specified file path. It supports both PDF and TXT files.
    The function determines the file type based on the file extension and uses the appropriate loader to read the content.
    :param file_path: The path to the document file (PDF or TXT) that needs to be loaded.
    :return: A list of documents loaded from the file, where each document is represented as a dictionary with keys like 'page_content' and 'metadata'.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".txt":
        loader = TextLoader(file_path)
    else:
        raise ValueError("Unsupported file type. Only PDF and TXT are allowed.")

    return loader.load()


def chunk_document(document):
    """
    This function takes a document as input and splits it into smaller chunks using the RecursiveCharacterTextSplitter.
    :param document: A document that needs to be split into smaller chunks.
     The document is typically a dictionary containing keys like 'page_content' and 'metadata'.
    :return: A list of text chunks obtained from splitting the input document.
    Each chunk is a smaller portion of the original document's content, and the splitting is done based on the specified
    chunk size and overlap parameters.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    return text_splitter.split_documents(document)


def embedding_model():
    """
    This function initializes and returns an instance of the HuggingFaceEndpointEmbeddings class, which is used to create embeddings for text data.
    :return: An instance of the HuggingFaceEndpointEmbeddings class, configured
    """
    embeddings = HuggingFaceEndpointEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        huggingfacehub_api_token=HUGGINGFACE_API_KEY,
    )
    return embeddings







"""
load
chunk
embed
store
query
"""
