try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
except ImportError:  # sandbox
    from llm_shim import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")

prompt = "How has Berkshire Hathaway's investment in Coca-cola grown?"

# Note: we must use the same embedding model that we used when uploading the docs
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Querying the vector database for relevant docs
document_vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
retriever = document_vectorstore.as_retriever()
context = retriever.invoke(prompt)
for doc in context:
    print(f"Source: {doc.metadata['source']}\nContent: {doc.page_content}\n\n")
print("__________________________")

# Adding context to our prompt
template = PromptTemplate(template="{query} Context: {context}", input_variables=["query", "context"])
prompt_with_context = template.invoke({"query": prompt, "context": context})

# Asking the LLM for a response from our prompt with the provided context
llm = ChatOpenAI(temperature=0.7, model_name="gpt-4o-mini")
results = llm.invoke(prompt_with_context)

print(results.content)
