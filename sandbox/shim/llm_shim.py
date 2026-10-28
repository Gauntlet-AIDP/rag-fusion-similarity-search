"""Drop-in replacements for langchain_openai in the sandbox: local embeddings, manual or claude-cli LLM."""

import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

MANUAL_DIR = Path(os.getenv("LLM_MANUAL_DIR", "/work/.manual"))
MODEL_PATH = "/models/bge-small"
_calls = 0


def _backend() -> str:
    return os.getenv("LLM_BACKEND", "manual")


def _max_calls() -> int:
    default = "50" if _backend() == "claude-cli" else "8"
    return int(os.getenv("LLM_MAX_CALLS", default))


def render_messages(messages: List[BaseMessage]) -> str:
    return "\n\n".join(f"[{m.type}]\n{m.content}" for m in messages)


def _cache_key(prompt: str, stop: Optional[List[str]]) -> str:
    # the helper's model decides the reply, so it is part of the key (not the OpenAI label callers pass)
    payload = json.dumps([_backend(), os.getenv("CLAUDE_MODEL", ""), stop or [], prompt])
    return hashlib.sha256(payload.encode()).hexdigest()


def _extract_json(prompt: str, text: str) -> str:
    """If the prompt asks for JSON and the reply wraps it in prose, return the outermost {...} or [...].

    Anything that is not valid JSON after extraction is returned unchanged.
    """
    if "json" not in prompt.lower():
        return text
    try:
        json.loads(text)
        return text
    except ValueError:
        pass
    spans = [(text.find(o), text.rfind(c)) for o, c in (("{", "}"), ("[", "]"))]
    for start, end in sorted((s for s in spans if 0 <= s[0] < s[1]), key=lambda s: s[0] - s[1]):
        candidate = text[start : end + 1]
        try:
            json.loads(candidate)
            return candidate
        except ValueError:
            continue
    return text


def _load_cache() -> dict:
    path = MANUAL_DIR / "cache.json"
    try:
        cache = json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except ValueError:
        print(f"(ignoring corrupt cache {path})", flush=True)
        return {}
    return cache if isinstance(cache, dict) else {}


def _save_cache(cache: dict) -> None:
    # temp file + rename so a crash never leaves a half-written cache
    fd, tmp = tempfile.mkstemp(dir=MANUAL_DIR, prefix="cache.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(cache, f, indent=2)
        os.replace(tmp, MANUAL_DIR / "cache.json")
    except BaseException:
        os.unlink(tmp)
        raise


def _manual_reply(prompt: str) -> str:
    n = len(list(MANUAL_DIR.glob("*_prompt.txt"))) + 1
    path = MANUAL_DIR / f"{n:03d}_prompt.txt"
    path.write_text(prompt)
    print(f"\n===== PROMPT (saved to {path}) =====\n{prompt}\n===== END PROMPT =====", flush=True)
    print("Paste the reply, then a line with only END:", flush=True)
    lines = []
    for line in sys.stdin:
        if line.rstrip("\n").strip() == "END":
            break
        lines.append(line)
    reply = "".join(lines).strip()
    if not reply:
        raise RuntimeError("no reply received on stdin")
    return reply


def _cli_reply(prompt: str) -> str:
    url = os.environ["LLM_HELPER_URL"]
    req = urllib.request.Request(
        url,
        data=json.dumps({"prompt": prompt}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['LLM_HELPER_TOKEN']}",
        },
    )
    with urllib.request.urlopen(req, timeout=330) as resp:
        return json.load(resp)["text"]


class ManualChat(BaseChatModel):
    """Chat model that asks a human (manual) or the host claude helper (claude-cli)."""

    @property
    def _llm_type(self) -> str:
        return "manual-chat"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        global _calls
        MANUAL_DIR.mkdir(parents=True, exist_ok=True)
        prompt = render_messages(messages)
        key = _cache_key(prompt, stop)
        cache = _load_cache()
        if key in cache:
            print("(reply served from cache)", flush=True)
            text = cache[key]
        else:
            if _calls >= _max_calls():
                raise RuntimeError(f"LLM_MAX_CALLS={_max_calls()} reached; raise it to continue")
            backend = _backend()
            if backend == "claude-cli":
                text = _cli_reply(prompt)
            elif backend == "manual":
                text = _manual_reply(prompt)
            else:
                raise ValueError(f"unknown LLM_BACKEND: {backend}")
            if not text.strip():  # raise before caching so an empty reply is never replayed
                raise RuntimeError(f"empty reply from {backend} backend")
            _calls += 1  # only successful calls count against the cap
            cache[key] = text
            _save_cache(cache)
        text = _extract_json(prompt, text)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])


def get_llm(**_ignored: Any) -> ManualChat:
    """Ignores model=, temperature=, openai_api_key= and friends."""
    return ManualChat()


@lru_cache(maxsize=1)
def _embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=MODEL_PATH,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_embeddings(**_ignored: Any):
    """One shared model per process, whatever kwargs the callers pass."""
    return _embeddings()


ChatOpenAI = get_llm
OpenAIEmbeddings = get_embeddings
