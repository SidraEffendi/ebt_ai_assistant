import hashlib

import streamlit as st

from voice_agent import (
    chat,
    detect_tts_language,
    extract_checklist_updates,
    get_welcome_message,
    normalize_tts_language,
    reset_conversation,
    synthesize_speech,
    transcribe_audio_bytes,
)


DEFAULT_LANGUAGE = "en"

UI_TEXT_BY_LANGUAGE = {
    "en": {
        "page_title": "EBT AI Assistant",
        "page_caption": (
            "A voice-first assistant to help applicants understand and organize EBT documents."
        ),
        "privacy_notice": (
            "Please do not enter Social Security numbers, bank account numbers, passwords, "
            "or other highly sensitive personal information."
        ),
        "sidebar_title": "Document checklist",
        "sidebar_help": "Use this as a simple guide while preparing your application.",
        "reset_button": "Reset conversation",
        "voice_settings": "Voice settings",
        "auto_read": "Read assistant replies aloud",
        "readiness": "Readiness",
        "readiness_help": "Check off documents as you collect them.",
        "voice_input_title": "Speak to the assistant",
        "record_question": "Record your question",
        "transcribing": "Transcribing your voice...",
        "you_said": "You said: {transcript}",
        "transcription_failed": (
            "I could not understand the recording. Please try again or type your question."
        ),
        "try_asking": "Try asking:",
        "chat_input": "Or type your question here",
        "thinking": "Thinking...",
        "service_error": (
            "Sorry, I had trouble reaching the AI service. "
            "Please check your API key and try again."
        ),
    },
    "es": {
        "page_title": "Asistente de EBT",
        "page_caption": (
            "Un asistente de voz para ayudar a los solicitantes a entender y organizar documentos de EBT."
        ),
        "privacy_notice": (
            "Por favor no ingrese números de Seguro Social, números de cuentas bancarias, "
            "contraseñas u otra información muy sensible."
        ),
        "sidebar_title": "Lista de documentos",
        "sidebar_help": "Use esta guía sencilla mientras prepara su solicitud.",
        "reset_button": "Reiniciar conversación",
        "voice_settings": "Configuración de voz",
        "auto_read": "Leer respuestas en voz alta",
        "readiness": "Preparación",
        "readiness_help": "Marque los documentos a medida que los reúna.",
        "voice_input_title": "Hable con el asistente",
        "record_question": "Grabe su pregunta",
        "transcribing": "Transcribiendo su voz...",
        "you_said": "Usted dijo: {transcript}",
        "transcription_failed": (
            "No pude entender la grabación. Inténtelo de nuevo o escriba su pregunta."
        ),
        "try_asking": "Pruebe preguntar:",
        "chat_input": "O escriba su pregunta aquí",
        "thinking": "Pensando...",
        "service_error": (
            "Lo siento, tuve problemas para comunicarme con el servicio de IA. "
            "Revise su clave de API e inténtelo de nuevo."
        ),
    },
}

SUGGESTED_QUESTIONS = [
    "What documents do I need for an EBT application?",
    "What can I use as proof of income?",
    "What can I use as proof of address?",
    "How should I organize my documents before applying?",
]

SUGGESTED_QUESTIONS_BY_LANGUAGE = {
    "en": SUGGESTED_QUESTIONS,
    "es": [
        "¿Qué documentos necesito para una solicitud de EBT?",
        "¿Qué puedo usar como prueba de ingresos?",
        "¿Qué puedo usar como prueba de domicilio?",
        "¿Cómo debo organizar mis documentos antes de solicitar?",
    ],
}

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

CHECKLIST_LABELS_BY_LANGUAGE = {
    "en": {item["id"]: item["label"] for item in CHECKLIST_ITEMS},
    "es": {
        "photo_id": "Identificación con foto",
        "proof_of_address": "Prueba de domicilio",
        "proof_of_income": "Prueba de ingresos",
        "rent_or_mortgage": "Documento de renta o hipoteca",
        "utility_bill": "Factura de servicios públicos",
        "household_info": "Información de los miembros del hogar",
        "medical_childcare_expenses": (
            "Documentos de gastos médicos o de cuidado infantil, si corresponde"
        ),
    },
}


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
        welcome_message(st.session_state.current_language)
    ]
    st.session_state.pending_prompt = None
    st.session_state.last_audio_hash = None
    st.session_state.welcome_audio_played = False
    st.session_state.checklist = {
        item["id"]: False for item in CHECKLIST_ITEMS
    }
    for item in CHECKLIST_ITEMS:
        st.session_state[checklist_widget_key(item["id"])] = False


def checklist_widget_key(item_id: str) -> str:
    """Return the Streamlit widget key for a checklist item."""
    return f"checklist_{item_id}"


def current_ui_language() -> str:
    """Return the supported UI language, using English as the deterministic fallback."""
    language = normalize_tts_language(st.session_state.current_language)
    if language in UI_TEXT_BY_LANGUAGE:
        return language
    return DEFAULT_LANGUAGE


def ui_text(key: str) -> str:
    """Return localized UI text with English fallback."""
    language = current_ui_language()
    return UI_TEXT_BY_LANGUAGE.get(language, UI_TEXT_BY_LANGUAGE[DEFAULT_LANGUAGE]).get(
        key,
        UI_TEXT_BY_LANGUAGE[DEFAULT_LANGUAGE][key],
    )


def suggested_questions() -> list[str]:
    """Return localized suggested prompts with English fallback."""
    return SUGGESTED_QUESTIONS_BY_LANGUAGE.get(
        current_ui_language(),
        SUGGESTED_QUESTIONS_BY_LANGUAGE[DEFAULT_LANGUAGE],
    )


def checklist_label(item_id: str) -> str:
    """Return a localized checklist label with English fallback."""
    language = current_ui_language()
    return CHECKLIST_LABELS_BY_LANGUAGE.get(
        language,
        CHECKLIST_LABELS_BY_LANGUAGE[DEFAULT_LANGUAGE],
    ).get(item_id, CHECKLIST_LABELS_BY_LANGUAGE[DEFAULT_LANGUAGE][item_id])


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
            if st.button(question):
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
    prompt_language = detect_tts_language(prompt)
    if prompt_language != DEFAULT_LANGUAGE:
        st.session_state.current_language = prompt_language

    update_checklist_from_text(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner(ui_text("thinking")):
                assistant_reply = chat(prompt, checklist_context())

            st.write(assistant_reply)
            st.session_state.current_language = detect_tts_language(assistant_reply)

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

    st.title(ui_text("page_title"))
    st.caption(ui_text("page_caption"))

    st.info(ui_text("privacy_notice"))

    render_voice_input()

    st.divider()

    render_suggested_questions()

    st.divider()

    render_chat_history()

    typed_prompt = st.chat_input(ui_text("chat_input"))

    prompt = st.session_state.pending_prompt or typed_prompt

    if prompt:
        st.session_state.pending_prompt = None
        handle_user_prompt(prompt)

    render_sidebar()


if __name__ == "__main__":
    main()
