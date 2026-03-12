"""Chatbot component using Streamlit chat elements."""

from __future__ import annotations

import logging

import streamlit as st

from src.frontend.api_client import APIClient
from src.frontend.i18n import t

logger = logging.getLogger(__name__)

# Maximum messages kept in memory to avoid excessive session_state growth.
# Older messages are trimmed from the front when this limit is reached.
_MAX_HISTORY_LENGTH: int = 100

# Session state key for the chat message list
_HISTORY_KEY: str = "chat_history"


def _init_chat_history() -> None:
    """Ensure the chat history list exists in Streamlit session state."""
    if _HISTORY_KEY not in st.session_state:
        st.session_state[_HISTORY_KEY] = []


def _trim_history() -> None:
    """Drop the oldest messages if history exceeds ``_MAX_HISTORY_LENGTH``."""
    history: list[dict[str, str]] = st.session_state[_HISTORY_KEY]
    if len(history) > _MAX_HISTORY_LENGTH:
        # Keep the most recent N messages (each exchange = 2 entries)
        st.session_state[_HISTORY_KEY] = history[-_MAX_HISTORY_LENGTH:]


def render_chatbot(api_client: APIClient) -> None:
    """Render a conversational chatbot interface with persistent message history.

    Message history is stored in ``st.session_state`` under the key
    ``chat_history`` and survives page rerenders within the same session.
    A "Clear conversation" button allows the user to reset the history.

    The assistant response always appends a regulatory disclaimer.  When the
    API is unavailable the component shows a graceful fallback message rather
    than crashing.

    Args:
        api_client: The shared API client instance used to call the chat endpoint.
    """
    st.subheader(t("chatbot.header"))

    _init_chat_history()

    # --- Controls row: clear button aligned to the right ---
    ctrl_spacer, ctrl_btn = st.columns([5, 1])
    with ctrl_btn:
        if st.button("Clear", use_container_width=True, help="Clear conversation history"):
            st.session_state[_HISTORY_KEY] = []
            logger.debug("Chat history cleared by user")

    # --- Render existing conversation history ---
    for msg in st.session_state[_HISTORY_KEY]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        with st.chat_message(role):
            st.markdown(content)

    # --- Chat input (fixed at bottom of the component) ---
    user_input: str | None = st.chat_input(t("chatbot.placeholder"))

    if not user_input:
        # Nothing to process — exit early without side effects
        return

    # Show and persist the user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state[_HISTORY_KEY].append({"role": "user", "content": user_input})

    # Fetch and display the assistant response
    with st.chat_message("assistant"):
        try:
            reply, disclaimer = api_client.chat(user_input)
        except Exception as exc:
            # Log the error but show a friendly message — never surface stack traces
            logger.warning("Chat API error for input %r: %s", user_input[:80], exc)
            reply, disclaimer = None, None

        if reply:
            disc = disclaimer or t("chatbot.disclaimer")
            full_response = f"{reply}\n\n_Warning: {disc}_"
        else:
            full_response = f"{t('chatbot.unavailable')}\n\n_Warning: {t('chatbot.disclaimer')}_"

        st.markdown(full_response)

    st.session_state[_HISTORY_KEY].append({"role": "assistant", "content": full_response})

    # Trim history to prevent unbounded growth across long sessions
    _trim_history()
