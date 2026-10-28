# Local sandbox for rag-fusion-similarity-search

**Hard requirements: Apple Silicon Mac with Docker Desktop (the dependency lock targets aarch64 and the relay reaches the helper through `host.docker.internal`), and Go 1.26+.**

Runs `similarity_search.ipynb`, `upload.py`, `main.py` and `RAG_fusion_101.ipynb` with no cloud accounts and no API keys. Everything runs in Docker; the only host tools are Docker Desktop, Go and Claude Code.

## Prerequisites

- Docker Desktop, running, on an Apple Silicon Mac.
- Go 1.26+ (builds the helper and relay).
- Claude Code installed and signed in with your own seat (`claude -p "hi"` must work).

## One-time setup

```sh
cd sandbox
./init.sh
```

It creates `.env` from `.env.example`, generates a helper token in `claude-helper/.token`, copies it into `.env`, creates `.manual`, `faiss_index` (repo root) and `out` (here), and builds the helper and relay. Re-running keeps an existing `.env` and token, and appends any key that `.env.example` has gained since (existing values are never changed). The one exception: `LLM_HELPER_TOKEN=<its token> ./init.sh` replaces the token in both, which is how you reuse the token of a helper that is already running.

## Start

```sh
cd sandbox
CLAUDE_MODEL=sonnet ./claude-helper/claude-helper &      # host helper, 127.0.0.1:8765
docker compose up -d claude-relay                        # builds and starts only the relay
```

The helper listens on 8765, which is the port the relay targets. Keep `CLAUDE_MODEL` in `.env` equal to the one you start the helper with: it is part of the reply cache key.

The app image builds on the first `docker compose run` (several minutes); run `docker compose build` first to do that up front.

Stop with `docker compose down` and `kill %1`. The FAISS index is a file in `faiss_index/`, so it survives `down`.

## Run order

```sh
# 1. similarity_search.ipynb (no Claude call). Executed copies land in sandbox/out
docker compose run --rm -T app python -m nbconvert --to notebook --execute similarity_search.ipynb --output-dir /out

# 2. Build the FAISS index from docs/ (20 letters, several minutes on CPU)
docker compose run --rm -T app python upload.py

# 3. Ask one question (1 Claude call)
docker compose run --rm -T app python main.py

# 4. RAG_fusion_101.ipynb (1 Claude call for query generation); the fused ranking is in the last cell
docker compose run --rm -T app python -m nbconvert --to notebook --execute RAG_fusion_101.ipynb --output-dir /out
```

`main.py` needs the index from step 2. Read an executed notebook's output without Jupyter, from `sandbox`:

```sh
python3 -c "import json;[print(''.join(o.get('text') or o.get('data',{}).get('text/plain',''))) for c in json.load(open('out/RAG_fusion_101.ipynb'))['cells'] for o in c.get('outputs',[])]"
```

There is no Jupyter server: the app container has no published ports and no internet, so notebooks run headless with nbconvert.

Rebuild the image after changing `requirements.lock` or `Dockerfile`: `docker compose build app`. Re-lock with `./compile.sh` (delete `requirements.lock` first, otherwise uv keeps old pins).

## Manual paste mode (fallback)

```sh
docker compose run --rm -e LLM_BACKEND=manual app python main.py
```

The prompt is saved to `.manual/NNN_prompt.txt` at the repo root and printed. Paste it into any chat, then paste the reply into the terminal followed by a line `END`. Replies are cached by backend, model, stop words and prompt. `LLM_MAX_CALLS` (default in `.env.example`: 50) caps successful uncached calls per process.

## What is substituted

| Original | Sandbox |
|---|---|
| Pinecone (hosted index, 3072 and 1536 dims) | FAISS, in process; `upload.py` saves it to `faiss_index/`, the second notebook keeps it in memory |
| OpenAI embeddings | Local `BAAI/bge-small-en-v1.5` (384 dims), baked into the image |
| OpenAI chat model | Claude via `claude -p` through the helper (`LLM_BACKEND=claude-cli`), or manual paste |
| `hub.pull("langchain-ai/rag-fusion-query-generation")` | The prompt is inlined in `RAG_fusion_101.ipynb`, so nothing is pulled from the hub (GHSA-3644-q5cj-c5c7) |

The original used Pinecone, which needs an account and an index. The code edits are small (`git diff main`): imports moved to the langchain 1.x packages, FAISS in place of Pinecone, and an import fallback to `sandbox/shim/llm_shim.py`. The code still runs outside the sandbox: `langchain_openai` is used when installed, and the shim only when it is not. A FAISS index built with one embedding model cannot be loaded with the other (different dimensions); delete `faiss_index/` when switching.

Scores and answers differ from the original because the embedding and chat models differ.

## Security

- No runtime egress: the app container is on an internal network and reaches only a fixed relay to the helper.
- Images pinned by digest; dependencies hash-locked (`--require-hashes`); the embedding model is pinned to a revision, safetensors only.
- App runs as a non-root user with all capabilities dropped, a read-only root filesystem, a `/tmp` tmpfs and a process limit. Code, notebooks and `docs/` are mounted read-only; only `.manual`, `faiss_index` and `out` are writable.
- The helper runs `claude -p` with no tools, no MCP servers and no settings or hooks, because prompts carry untrusted PDF text. The relay caps concurrent connections and enforces idle and overall deadlines.
- Tracing is off.
- The helper listens on localhost only and requires a bearer token.
- `FAISS.load_local(..., allow_dangerous_deserialization=True)` unpickles the index: only load the file `upload.py` wrote.
- The helper sets `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, so `claude -p` loads no CLAUDE.md files (user, project or auto memory) into the prompt.

## Troubleshooting

- `401 Unauthorized` from the helper: the token in `.env` does not match the token the running helper loaded. `init.sh` warns about this. Fix with `LLM_HELPER_TOKEN=$(cat claude-helper/.token) ./init.sh`, restart the helper (it reads the token from `.token` next to its binary, `claude-helper/.token`, whatever directory you start it from), then recreate the app container.
- `main.py` fails to load `faiss_index`: run `upload.py` first.

## Usage notes

Generation uses your own Claude seat, so questions count against your usage. The helper is localhost-only: do not expose it, and do not share your `.env` or `claude-helper/.token`.
