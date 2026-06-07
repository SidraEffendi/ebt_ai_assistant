import hashlib
import json

import streamlit as st
import streamlit.components.v1 as components

from voice_agent import chat, reset_conversation, transcribe_audio_bytes


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


def reset_app() -> None:
    """Reset both frontend and backend conversation state."""
    reset_conversation()
    st.session_state.messages = [
        {"role": "assistant", "content": WELCOME_MESSAGE}
    ]
    st.session_state.pending_prompt = None
    st.session_state.last_audio_hash = None


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

        st.checkbox("Photo ID")
        st.checkbox("Proof of address")
        st.checkbox("Proof of income")
        st.checkbox("Rent or mortgage document")
        st.checkbox("Utility bill")
        st.checkbox("Household member information")
        st.checkbox("Medical or childcare expense documents, if applicable")

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
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                assistant_reply = chat(prompt)

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
    render_sidebar()

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


if __name__ == "__main__":
    main()