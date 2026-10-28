try:
    from langchain_openai import OpenAIEmbeddings
except ImportError:  # sandbox
    from llm_shim import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders.pdf import PyPDFLoader
from langchain_community.document_loaders import DirectoryLoader
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")

# Prep documents to be uploaded to the vector database (FAISS)
loader = DirectoryLoader('./docs', glob="**/*.pdf", loader_cls=PyPDFLoader)
raw_docs = loader.load()
print(f"Loaded {len(raw_docs)} pages from {len({d.metadata['source'] for d in raw_docs})} PDFs")

# Split documents into smaller chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
documents = text_splitter.split_documents(raw_docs)
print(f"Going to add {len(documents)} chunks to FAISS")

# Choose the embedding model and vector store
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
FAISS.from_documents(documents, embeddings).save_local("faiss_index")
print("Loading to vectorstore done")
