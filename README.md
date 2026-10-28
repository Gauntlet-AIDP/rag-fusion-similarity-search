# Class 3: RAG (Retrieval-Augmented Generation)

## Introduction
Master a technique that integrates relevant documents into the generation process, enhancing the quality and contextuality of LLM responses. This repo demonstrates a simple RAG example and more advanced implementations.

## Class Materials
- [Link to Class Slides](https://docs.google.com/presentation/d/1WJ4hMDeAah6ZIlBKNvMtR8l8BpfVegc7e8vI57vxnFM/edit?usp=sharing)

## Prerequisites
- Docker (for containerized usage - recommended)
- Python 3.11 (for local setup)
- An OpenAI API key (or use the local Claude sandbox, see [sandbox/README.md](sandbox/README.md))

## Setup

Vectors are stored locally in FAISS (`faiss_index/`), so no vector database account is needed. Set `OPENAI_API_KEY` for the original OpenAI path, or use [sandbox/README.md](sandbox/README.md) to run with no cloud accounts on the local Claude sandbox.

### Set up environment variables:
- Copy the sample environment file:
  ```
  cp .env.sample .env
  ```
- Edit the `.env` file and add your API keys and other required variables:
  ```
   OPENAI_API_KEY=your-secret-key
   LANGCHAIN_API_KEY=your-secret-key
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=gauntlet_class_3
  ```

## Quick Start with Docker

1. Run the upload script:
   ```
   docker compose run --rm upload_service
   ```

2. Run the main RAG example:
   ```
   docker compose run --rm rag_app
   ```

3. Start Jupyter for notebook examples:
   ```
   docker compose up jupyter
   ```

4. Run a specific script (any new `.py` file you may add):
   ```
   docker compose run --rm rag_app python <script_name.py>
   ```

Note: The Docker setup will automatically use the environment variables from your `.env` file. You don't need to export them to your system environment when using Docker.

## Running Different Scripts
You can use the provided `run.sh` script for easier execution.
Make sure to make the script executable with `chmod +x run.sh` before using:
```
./run.sh upload
./run.sh main
./run.sh jupyter
./run.sh <your_new_py_file>
```

## Local Setup (Alternative to Docker)
If you prefer to run the examples locally:

1. Ensure you have Python 3.10+ installed.
2. Clone the repository:
   ```
   git clone [repository-url]
   cd [repository-name]
   ```
3. Set up the environment:
   ```
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   pip install -r requirements.txt
   ```
4. Configure environment variables as described in the Setup section.
5. Export the environment variables (python-dotenv should handle this automatically in the ):
   ```
   export $(cat .env | xargs)
   ```
6. Run an example:
   ```
   python3 upload.py
   ```

## Troubleshooting
- Ensure you're using Python 3.11.0 or later for local setup.
- For Docker issues, check your Docker installation and version.
- If you encounter package issues, try updating pip: `pip install --upgrade pip`
- Make sure all required environment variables are set in your `.env` file.
- If you're having issues with environment variables in Docker, ensure your `.env` file is in the same directory as your `docker-compose.yml` file.

## Need Help?
Refer to the project documentation or reach out to the learning assistant
