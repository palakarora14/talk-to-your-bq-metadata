"""Streamlit chat UI."""

import os
import uuid
from typing import Any

import httpx
import streamlit as streamlit

from hackday_45_talk_to_your_data.chains.chains import AVAILABLE_MODELS, DEFAULT_MODEL

API_URL = os.environ.get("API_URL", "http://localhost:8000")

PROJECTS = ["rea-gcp-dp-dev", "all_projects"]

QUICK_PROMPTS = [
    "What are the most expensive queries in the last 7 days by bytes billed?",
    "Which datasets and tables exist in the usage_metrics dataset?",
    "Who are the top users by cost usage?",
    "What tables are in the gcp_audit_logs dataset and what do they contain?",
]

TIME_RANGES = ["last_1_day", "last_7_days", "last_30_days", "last_90_days", "all_time"]


def init_state() -> None:
    if "session_id" not in streamlit.session_state:
        streamlit.session_state.session_id = str(uuid.uuid4())
    if "messages" not in streamlit.session_state:
        streamlit.session_state.messages = []
    if "filters_active" not in streamlit.session_state:
        streamlit.session_state.filters_active = False


def send(
    message: str, project: str | None, dataset: str | None, time_range: str | None, user_email: str | None, model: str
) -> tuple[str, list[dict[str, Any]]]:
    payload = {
        "session_id": streamlit.session_state.session_id,
        "message": message,
        "project": project,
        "dataset": dataset or None,
        "time_range": time_range,
        "user_email": user_email or None,
        "model": model,
    }
    try:
        resp = httpx.post(f"{API_URL}/chat", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return data["reply"], data.get("sources", [])
    except Exception as e:
        return f"Error contacting API: {e}", []


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return
    with streamlit.expander(f"📎 Sources ({len(sources)})"):
        for i, s in enumerate(sources, 1):
            collection = s.get("collection", "unknown")
            content = s.get("content", "")
            score = s.get("score", 0.0)
            preview = content[:200].replace("\n", " ") + ("…" if len(content) > 200 else "")
            streamlit.markdown(
                f"**{i}. `{collection}`** &nbsp;"
                f"<span style='color:grey;font-size:0.8rem'>{score * 100:.0f}% relevance</span>",
                unsafe_allow_html=True,
            )
            streamlit.caption(preview)
            if i < len(sources):
                streamlit.divider()


def main() -> None:
    streamlit.set_page_config(page_title="Talk to Your Data", page_icon="🗂️", layout="wide")
    init_state()

    streamlit.title("🗂️ Talk to Your Data")
    streamlit.caption(f"Session: `{streamlit.session_state.session_id}`")

    # Sidebar controls
    with streamlit.sidebar:
        streamlit.header("Filters")
        default_project = os.environ.get("GCP_PROJECT", "rea-gcp-dp-dev")
        default_idx = PROJECTS.index(default_project) if default_project in PROJECTS else 0
        project = streamlit.selectbox("Project", PROJECTS, index=default_idx)
        time_range = streamlit.selectbox("Time range", TIME_RANGES, index=0)
        dataset = streamlit.text_input("Dataset (optional)")
        user_email = streamlit.text_input("Your email (optional)")

        filters_active = streamlit.session_state.filters_active
        btn_label = "✅ Filters ON" if filters_active else "⬜ Apply Filters"
        btn_type = "primary" if filters_active else "secondary"
        if streamlit.button(btn_label, use_container_width=True, type=btn_type):
            streamlit.session_state.filters_active = not filters_active
            streamlit.rerun()

        streamlit.divider()
        streamlit.header("Model")
        default_model_idx = AVAILABLE_MODELS.index(DEFAULT_MODEL) if DEFAULT_MODEL in AVAILABLE_MODELS else 0
        model = streamlit.selectbox("LLM model", AVAILABLE_MODELS, index=default_model_idx)

        streamlit.divider()
        if streamlit.button("🗑️ Clear conversation"):
            try:
                httpx.delete(f"{API_URL}/chat/{streamlit.session_state.session_id}", timeout=10)
            except Exception:
                pass
            streamlit.session_state.messages = []
            streamlit.session_state.session_id = str(uuid.uuid4())
            streamlit.rerun()

    # Resolve filter values — only pass them if filters are active
    active = streamlit.session_state.filters_active
    effective_project = project if active and project != "all_projects" else None
    effective_dataset = dataset if active else None
    effective_time_range = time_range if active else None
    effective_email = user_email if active else None

    if active:
        parts = [f"project: `{project}`", f"time: `{time_range}`"]
        if dataset:
            parts.append(f"dataset: `{dataset}`")
        if user_email:
            parts.append(f"user: `{user_email}`")
        streamlit.info("🔍 Filters active — " + " · ".join(parts))

    # Quick-prompt buttons
    cols = streamlit.columns(len(QUICK_PROMPTS))
    for col, prompt in zip(cols, QUICK_PROMPTS, strict=True):
        if col.button(prompt[:40] + "…", help=prompt):
            streamlit.session_state["_pending"] = prompt

    # Display history
    for msg in streamlit.session_state.messages:
        with streamlit.chat_message(msg["role"]):
            streamlit.markdown(
                f"<div style='font-size:0.92rem'>{msg['content']}</div>",
                unsafe_allow_html=True,
            )
            render_sources(msg.get("sources", []))

    # Handle quick-prompt injection
    user_input: str | None = streamlit.session_state.pop("_pending", None)

    # Chat input
    typed = streamlit.chat_input("Ask about your data…")
    if typed:
        user_input = typed

    if user_input:
        streamlit.session_state.messages.append({"role": "user", "content": user_input})
        with streamlit.chat_message("user"):
            streamlit.markdown(
                f"<div style='font-size:0.92rem'>{user_input}</div>",
                unsafe_allow_html=True,
            )

        with streamlit.chat_message("assistant"):
            with streamlit.spinner("Thinking…"):
                reply, sources = send(
                    user_input,
                    effective_project,
                    effective_dataset,
                    effective_time_range,
                    effective_email,
                    model,
                )
            streamlit.markdown(
                f"<div style='font-size:0.92rem'>{reply}</div>",
                unsafe_allow_html=True,
            )
            render_sources(sources)

        streamlit.session_state.messages.append({"role": "assistant", "content": reply, "sources": sources})


if __name__ == "__main__":
    main()
