"""Prompt template and chain execution."""

import os

import openai
from openai.types.chat import ChatCompletionMessageParam

from hackday_45_talk_to_your_data.chains.base import SourceChunk

PORTKEY_GATEWAY_URL = "https://api.portkey.ai/v1"
PORTKEY_VIRTUAL_KEY = "bedrock-apac-no-3191fd"

DEFAULT_MODEL = "au.anthropic.claude-sonnet-4-5"

AVAILABLE_MODELS = [
    "au.anthropic.claude-sonnet-4-5",
    "au.anthropic.claude-haiku-3-5",
    "au.anthropic.claude-opus-4-5",
]

SYSTEM_PROMPT = """You are a BigQuery data assistant.
Answer questions about datasets, tables, schemas, query costs, slot usage, and optimisation.
Use only the provided context. If context is insufficient, say so.
Be concise. Summarise findings in 3-5 bullet points or a short paragraph.
Do not use markdown headings. Use plain bullet points or short sentences only."""

_INTENTS = {
    "cost": ["costli", "costliest", "expensive", "cost", "spend", "billing", "dollar", "price", "costly", "quota"],
    "optimise": [
        "partition",
        "cluster",
        "optimis",
        "optimi",
        "frequent",
        "cache",
        "performance",
        "slow",
        "speed",
        "optimise",
        "optimize",
    ],
}


def detect_intent(message: str) -> str:
    lower = message.lower()
    for intent, keywords in _INTENTS.items():
        if any(k in lower for k in keywords):
            return intent
    return "asset"


def run_chain(
    message: str,
    context_chunks: list[SourceChunk],
    history: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
) -> str:
    """Call LLM via Portkey gateway with retrieved context chunks."""
    api_key = os.environ.get("PORTKEY_API_KEY", "")
    if not api_key:
        return "[LLM not configured] PORTKEY_API_KEY missing. Context retrieved:\n" + "\n---\n".join(
            c.content for c in context_chunks
        )

    context_block = "\n\n".join(f"[{c.collection}]\n{c.content}" for c in context_chunks)
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,  # type: ignore[arg-type]
        {
            "role": "user",
            "content": f"<context>\n{context_block}\n</context>\n\n{message}",
        },
    ]

    client = openai.OpenAI(
        api_key=api_key,
        base_url=PORTKEY_GATEWAY_URL,
        default_headers={"x-portkey-virtual-keys": PORTKEY_VIRTUAL_KEY},
    )
    response = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        messages=messages,
    )
    return response.choices[0].message.content or ""
