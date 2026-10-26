"""Drives a local AI model as the intruder: ask the model for a move, run it, feed back the result.

The model talks over an OpenAI-compatible chat API, which is what local runners expose (Ollama at
http://localhost:11434/v1, LM Studio, vLLM, llama.cpp, or a hosted endpoint). Point it at your own
"unrestricted" local model and it decides the attack; the tools (attacker/tools.py) make sure every
move lands only on the demo portal. Nothing it says can make it reach anything else.

Run it with attacker.py (see --help). Settings come from the command line or environment:
  ATTACKER_BASE_URL  the model's OpenAI-compatible endpoint (default http://localhost:11434/v1)
  ATTACKER_MODEL     the model name (default llama3.1)
  ATTACKER_API_KEY   sent as a bearer token if the endpoint needs one (local runners usually don't)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterable

import requests

from . import tools

BRIEF = (Path(__file__).resolve().parent / "brief.md").read_text(encoding="utf-8")


def _openai_tools() -> list[dict[str, Any]]:
    """The attacker tools, described the way the chat API expects function tools."""
    out = []
    for name, (desc, params) in tools.TOOLS.items():
        props = {p: {"type": "string"} for p in params}
        out.append({"type": "function", "function": {
            "name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": params}}})
    return out


class ModelError(RuntimeError):
    pass


def ask_model(messages: list[dict[str, Any]], base_url: str, model: str, api_key: str = "",
              post: Callable[..., Any] = requests.post) -> dict[str, Any]:
    """One chat-completions call. Returns the assistant message (may carry tool_calls)."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    body = {"model": model, "messages": messages, "tools": _openai_tools(), "temperature": 0.7}
    try:
        r = post(f"{base_url.rstrip('/')}/chat/completions", json=body, headers=headers, timeout=120)
    except requests.RequestException as exc:
        raise ModelError(f"could not reach the local model at {base_url}: {exc.__class__.__name__}. "
                         f"Is it running? (e.g. `ollama serve`)") from exc
    if r.status_code != 200:
        raise ModelError(f"the model endpoint returned {r.status_code}: {r.text[:200]}")
    try:
        return r.json()["choices"][0]["message"]
    except (ValueError, KeyError, IndexError) as exc:
        raise ModelError(f"unexpected reply from the model endpoint: {exc}") from exc


def _tool_calls(msg: dict[str, Any]) -> list[dict[str, Any]]:
    return msg.get("tool_calls") or []


def run(portal: tools.Portal, base_url: str, model: str, api_key: str = "", max_steps: int = 20,
        delay: float = 1.0, say: Callable[[str], None] = print,
        ask: Callable[..., dict[str, Any]] = ask_model) -> list[dict[str, Any]]:
    """Let the model attack the portal for up to max_steps moves. Returns the transcript."""
    say(f"[attacker] model {model} via {base_url}  ->  portal {portal.base}  (as {portal.src_ip})")
    say("[attacker] every move can only touch this portal; it runs nothing on any machine.\n")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": BRIEF},
        {"role": "user", "content": f"The portal is at {portal.base}. Begin."}]
    for step in range(1, max_steps + 1):
        msg = ask(messages, base_url, model, api_key)
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        if msg.get("content"):
            say(f"[intruder] {msg['content'].strip()}")
        calls = _tool_calls(msg)
        if not calls:
            say("\n[attacker] the model stopped on its own.")
            break
        for call in calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            result = tools.dispatch(portal, name, args)
            flag = " [BLOCKED by SentrAI]" if result.get("blocked") else ""
            say(f"  -> {name}({', '.join(f'{k}={v!r}' for k, v in args.items())}) "
                f"=> HTTP {result.get('status', '?')}{flag}")
            messages.append({"role": "tool", "tool_call_id": call.get("id", name),
                             "name": name, "content": json.dumps(result)[:MAX_TOOL_REPLY]})
        time.sleep(delay)
    else:
        say("\n[attacker] reached the step limit.")
    return messages


MAX_TOOL_REPLY = 2000
