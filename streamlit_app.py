import hashlib
import json

import streamlit as st
import streamlit.components.v1 as components

from voice_agent import (
    chat,
    extract_checklist_updates,
    reset_conversation,
    transcribe_audio_bytes,
)


WELCOME_MESSAGE = (
    "Hi, I can help you get your EBT documents in order. "
    "Please do not share Social Security numbers, bank account details, passwords, "
    "or other highly sensitive information."
)

SUGGESTED_QUESTIONS = [
    "What documents do I need for an EBT application?",
    "What can I use as proof of income?",
    "What can I use as proof of address?",
    "How should I organize my documents before applying?",
]

CHECKLIST_ITEMS = [
    {
        "id": "photo_id",
        "label": "Photo ID",
    },
    {
        "id": "proof_of_address",
        "label": "Proof of address",
    },
    {
        "id": "proof_of_income",
        "label": "Proof of income",
    },
    {
        "id": "rent_or_mortgage",
        "label": "Rent or mortgage document",
    },
    {
        "id": "utility_bill",
        "label": "Utility bill",
    },
    {
        "id": "household_info",
        "label": "Household member information",
    },
    {
        "id": "medical_childcare_expenses",
        "label": "Medical or childcare expense documents, if applicable",
    },
]


def initialize_state() -> None:
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": WELCOME_MESSAGE}
        ]

    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None

    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None

    if "auto_read_responses" not in st.session_state:
        st.session_state.auto_read_responses = True

    if "checklist" not in st.session_state:
        st.session_state.checklist = {
            item["id"]: False for item in CHECKLIST_ITEMS
        }

    for item in CHECKLIST_ITEMS:
        widget_key = checklist_widget_key(item["id"])
        if widget_key not in st.session_state:
            st.session_state[widget_key] = st.session_state.checklist[item["id"]]


def reset_app() -> None:
    """Reset both frontend and backend conversation state."""
    reset_conversation()
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]
    st.session_state.pending_prompt = None
    st.session_state.last_audio_hash = None
    st.session_state.checklist = {
        item["id"]: False for item in CHECKLIST_ITEMS
    }
    for item in CHECKLIST_ITEMS:
        st.session_state[checklist_widget_key(item["id"])] = False


def checklist_widget_key(item_id: str) -> str:
    """Return the Streamlit widget key for a checklist item."""
    return f"checklist_{item_id}"


def set_checklist_item(item_id: str, checked: bool) -> None:
    """Update checklist state and keep its checkbox widget in sync."""
    st.session_state.checklist[item_id] = checked
    st.session_state[checklist_widget_key(item_id)] = checked


def update_checklist_from_text(text: str) -> None:
    """Check or uncheck checklist items from model-extracted user claims."""
    try:
        updates = extract_checklist_updates(text, CHECKLIST_ITEMS)
    except Exception as e:
        print(f"Checklist extraction error: {e}")
        return

    for item_id, checked in updates.items():
        set_checklist_item(item_id, checked)


def checklist_context() -> str:
    """Build a compact checklist summary for the assistant prompt."""
    fulfilled = [
        item["label"]
        for item in CHECKLIST_ITEMS
        if st.session_state.checklist.get(item["id"], False)
    ]
    missing = [
        item["label"]
        for item in CHECKLIST_ITEMS
        if not st.session_state.checklist.get(item["id"], False)
    ]

    fulfilled_text = ", ".join(fulfilled) if fulfilled else "none"
    missing_text = ", ".join(missing) if missing else "none"

    return (
        "Current document checklist. "
        f"Fulfilled: {fulfilled_text}. "
        f"Not fulfilled: {missing_text}."
    )


def speak_in_browser(text: str) -> None:
    """
    Speak assistant reply in the browser using the Web Speech API.

    This is better than calling pyttsx3 from Streamlit because pyttsx3
    speaks on the server machine, not necessarily in the user's browser.
    """
    safe_text = json.dumps(text)

    components.html(
        f"""
        <script>
        const text = {safe_text};

        function speakText() {{
            const synth = window.speechSynthesis;
            if (!synth) {{
                return;
            }}

            synth.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.95;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;

            synth.speak(utterance);
        }}

        speakText();
        </script>
        """,
        height=0,
    )


def render_sidebar() -> None:
    """Render the document checklist sidebar."""
    with st.sidebar:
        st.title("Document checklist")

        st.write("Use this as a simple guide while preparing your application.")

        for item in CHECKLIST_ITEMS:
            widget_key = checklist_widget_key(item["id"])
            st.checkbox(item["label"], key=widget_key)
            st.session_state.checklist[item["id"]] = st.session_state[widget_key]

        st.divider()

        st.subheader("Voice settings")
        st.checkbox(
            "Read assistant replies aloud",
            key="auto_read_responses",
        )

        st.divider()

        st.subheader("Readiness")
        st.write("Check off documents as you collect them.")

        if st.button("Reset conversation"):
            reset_app()
            st.rerun()


def render_voice_input() -> None:
    """Render browser microphone input and transcribe the recording."""
    st.subheader("Speak to the assistant")

    audio_value = st.audio_input(
        "Record your question",
        sample_rate=16000,
    )

    if audio_value is None:
        return

    audio_bytes = audio_value.getvalue()
    audio_hash = hashlib.md5(audio_bytes).hexdigest()

    # Prevent the same recording from being processed again on every Streamlit rerun.
    if audio_hash == st.session_state.last_audio_hash:
        return

    st.session_state.last_audio_hash = audio_hash

    with st.spinner("Transcribing your voice..."):
        transcript = transcribe_audio_bytes(audio_bytes)

    if transcript:
        st.success(f"You said: {transcript}")
        st.session_state.pending_prompt = transcript
    else:
        st.warning("I could not understand the recording. Please try again or type your question.")


def render_suggested_questions() -> None:
    """Render quick-start prompt buttons."""
    st.write("Try asking:")

    cols = st.columns(2)

    for index, question in enumerate(SUGGESTED_QUESTIONS):
        with cols[index % 2]:
            if st.button(question):
                st.session_state.pending_prompt = question


def render_chat_history() -> None:
    """Render previous chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


def handle_user_prompt(prompt: str) -> None:
    """Send user prompt to the backend agent and render the response."""
    update_checklist_from_text(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                assistant_reply = chat(prompt, checklist_context())

            st.write(assistant_reply)

            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_reply}
            )

            if st.session_state.auto_read_responses:
                speak_in_browser(assistant_reply)

        except RuntimeError as e:
            error_message = str(e)
            st.error(error_message)

            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )

        except Exception as e:
            print(f"Frontend chat error: {e}")

            error_message = (
                "Sorry, I had trouble reaching the AI service. "
                "Please check your API key and try again."
            )

            st.error(error_message)

            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )


def main() -> None:
    st.set_page_config(
        page_title="EBT AI Assistant",
        page_icon="🧾",
        layout="wide",
    )

    initialize_state()

    st.title("EBT AI Assistant")
    st.caption(
        "A voice-first assistant to help applicants understand and organize EBT documents."
    )

    st.info(
        "Please do not enter Social Security numbers, bank account numbers, passwords, "
        "or other highly sensitive personal information."
    )

    render_voice_input()

    st.divider()

    render_suggested_questions()

    st.divider()

    render_chat_history()

    typed_prompt = st.chat_input("Or type your question here")

    prompt = st.session_state.pending_prompt or typed_prompt

    if prompt:
        st.session_state.pending_prompt = None
        handle_user_prompt(prompt)

    render_sidebar()


if __name__ == "__main__":
    main()
