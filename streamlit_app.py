import hashlib

import streamlit as st

from localization import (
    CHECKLIST_ITEMS,
    DEFAULT_LANGUAGE,
    UI_TEXT_BY_LANGUAGE,
    checklist_label as localized_checklist_label,
    get_welcome_message,
    suggested_questions as localized_suggested_questions,
    ui_language,
    ui_text as localized_ui_text,
)

from voice_agent import (
    chat,
    detect_tts_language,
    extract_checklist_updates,
    normalize_tts_language,
    reset_conversation,
    synthesize_speech,
    transcribe_audio_bytes,
)


def initialize_state() -> None:
    """Initialize Streamlit session state."""
    if "current_language" not in st.session_state:
        st.session_state.current_language = DEFAULT_LANGUAGE

    if "messages" not in st.session_state:
        st.session_state.messages = [
            welcome_message(st.session_state.current_language)
        ]

    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None

    if "last_audio_hash" not in st.session_state:
        st.session_state.last_audio_hash = None

    if "auto_read_responses" not in st.session_state:
        st.session_state.auto_read_responses = True

    if "welcome_audio_played" not in st.session_state:
        st.session_state.welcome_audio_played = False

    if "reset_generation" not in st.session_state:
        st.session_state.reset_generation = 0

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
    current_language = normalize_tts_language(st.session_state.current_language)

    reset_conversation()
    st.session_state.current_language = current_language
    st.session_state.messages = [
        welcome_message(current_language)
    ]
    st.session_state.pending_prompt = None
    st.session_state.last_audio_hash = None
    st.session_state.welcome_audio_played = False
    st.session_state.reset_generation += 1
    st.session_state.checklist = {
        item["id"]: False for item in CHECKLIST_ITEMS
    }
    for item in CHECKLIST_ITEMS:
        st.session_state[checklist_widget_key(item["id"])] = False


def checklist_widget_key(item_id: str) -> str:
    """Return the Streamlit widget key for a checklist item."""
    return f"checklist_{item_id}"


def current_ui_language() -> str:
    """Return the current UI language for this session."""
    return ui_language(st.session_state.current_language)


def ui_text(key: str) -> str:
    """Return localized UI text for this session."""
    return localized_ui_text(st.session_state.current_language, key)


def suggested_questions() -> list[str]:
    """Return localized suggested prompts for this session."""
    return localized_suggested_questions(st.session_state.current_language)


def checklist_label(item_id: str) -> str:
    """Return a localized checklist label for this session."""
    return localized_checklist_label(st.session_state.current_language, item_id)


def welcome_message(language: str) -> dict[str, str | bool]:
    """Build a marked welcome chat message for the current language."""
    return {
        "role": "assistant",
        "content": get_welcome_message(language),
        "is_welcome": True,
    }


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


def render_spoken_response(text: str) -> None:
    """Generate and render language-aware speech audio for an assistant reply."""
    audio_bytes = synthesize_speech(text)
    if audio_bytes:
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)


def render_sidebar() -> None:
    """Render the document checklist sidebar."""
    with st.sidebar:
        st.title(ui_text("sidebar_title"))

        st.write(ui_text("sidebar_help"))

        if st.button(ui_text("reset_button")):
            reset_app()
            st.rerun()

        for item in CHECKLIST_ITEMS:
            widget_key = checklist_widget_key(item["id"])
            st.checkbox(checklist_label(item["id"]), key=widget_key)
            st.session_state.checklist[item["id"]] = st.session_state[widget_key]

        st.divider()

        st.subheader(ui_text("voice_settings"))
        st.checkbox(
            ui_text("auto_read"),
            key="auto_read_responses",
        )

        st.divider()

        st.subheader(ui_text("readiness"))
        st.write(ui_text("readiness_help"))


def render_voice_input() -> None:
    """Render browser microphone input and transcribe the recording."""
    st.subheader(ui_text("voice_input_title"))

    audio_value = st.audio_input(
        ui_text("record_question"),
        sample_rate=16000,
        key=f"audio_input_{st.session_state.reset_generation}",
    )

    if audio_value is None:
        return

    audio_bytes = audio_value.getvalue()
    audio_hash = hashlib.md5(audio_bytes).hexdigest()

    # Prevent the same recording from being processed again on every Streamlit rerun.
    if audio_hash == st.session_state.last_audio_hash:
        return

    st.session_state.last_audio_hash = audio_hash

    with st.spinner(ui_text("transcribing")):
        try:
            transcript = transcribe_audio_bytes(audio_bytes)
        except RuntimeError as e:
            st.error(str(e))
            return

    if transcript:
        st.success(ui_text("you_said").format(transcript=transcript))
        st.session_state.pending_prompt = transcript
    else:
        st.warning(ui_text("transcription_failed"))


def render_suggested_questions() -> None:
    """Render quick-start prompt buttons."""
    st.write(ui_text("try_asking"))

    cols = st.columns(2)

    for index, question in enumerate(suggested_questions()):
        with cols[index % 2]:
            if st.button(
                question,
                key=f"suggested_{current_ui_language()}_{index}_{st.session_state.reset_generation}",
            ):
                st.session_state.pending_prompt = question


def render_chat_history() -> None:
    """Render previous chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if (
                message.get("is_welcome")
                and st.session_state.auto_read_responses
                and not st.session_state.welcome_audio_played
            ):
                render_spoken_response(message["content"])
                st.session_state.welcome_audio_played = True


def handle_user_prompt(prompt: str) -> None:
    """Send user prompt to the backend agent and render the response."""
    remember_language_from_text(prompt)

    update_checklist_from_text(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner(ui_text("thinking")):
                assistant_reply = chat(prompt, checklist_context())

            st.write(assistant_reply)
            remember_language_from_text(assistant_reply)

            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_reply}
            )

            if st.session_state.auto_read_responses:
                render_spoken_response(assistant_reply)

        except RuntimeError as e:
            error_message = str(e)
            st.error(error_message)

            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )

        except Exception as e:
            print(f"Frontend chat error: {e}")

            error_message = ui_text("service_error")

            st.error(error_message)

            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )


def main() -> None:
    st.set_page_config(
        page_title=UI_TEXT_BY_LANGUAGE[DEFAULT_LANGUAGE]["page_title"],
        page_icon="🧾",
        layout="wide",
    )

    initialize_state()
    render_sidebar()

    st.title(ui_text("page_title"))
    st.caption(ui_text("page_caption"))

    st.info(ui_text("privacy_notice"))

    render_voice_input()

    st.divider()

    render_suggested_questions()

    st.divider()

    render_chat_history()

    typed_prompt = st.chat_input(
        ui_text("chat_input"),
        key=f"chat_input_{st.session_state.reset_generation}",
    )

    prompt = st.session_state.pending_prompt or typed_prompt

    if prompt:
        st.session_state.pending_prompt = None
        handle_user_prompt(prompt)


if __name__ == "__main__":
    main()


