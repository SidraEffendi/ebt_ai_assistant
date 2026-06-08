import hashlib
import re

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
    analyze_user_message,
    chat,
    detect_tts_language,
    normalize_tts_language,
    reset_conversation,
    synthesize_speech,
    transcribe_audio_bytes,
)

LANGUAGE_NAMES = {
    "arabic": "ar",
    "arabe": "ar",
    "arabisch": "ar",
    "arabo": "ar",
    "arabe portugues": "ar",
    "عربي": "ar",
    "العربية": "ar",
    "german": "de",
    "deutsch": "de",
    "alemán": "de",
    "aleman": "de",
    "allemand": "de",
    "tedesco": "de",
    "duits": "de",
    "niemiecki": "de",
    "немецкий": "de",
    "ドイツ語": "de",
    "독일어": "de",
    "德语": "de",
    "德語": "de",
    "english": "en",
    "en": "en",
    "inglés": "en",
    "ingles": "en",
    "anglais": "en",
    "englisch": "en",
    "inglese": "en",
    "engels": "en",
    "angielski": "en",
    "английский": "en",
    "الإنجليزية": "en",
    "الانجليزية": "en",
    "अंग्रेजी": "en",
    "英語": "en",
    "영어": "en",
    "英语": "en",
    "英文": "en",
    "英語繁體": "en",
    "spanish": "es",
    "espanol": "es",
    "español": "es",
    "espagnol": "es",
    "spanisch": "es",
    "spagnolo": "es",
    "spaans": "es",
    "hiszpański": "es",
    "испанский": "es",
    "スペイン語": "es",
    "스페인어": "es",
    "西班牙语": "es",
    "西班牙語": "es",
    "french": "fr",
    "francais": "fr",
    "français": "fr",
    "französisch": "fr",
    "franzoesisch": "fr",
    "francese": "fr",
    "frans": "fr",
    "francuski": "fr",
    "французский": "fr",
    "フランス語": "fr",
    "프랑스어": "fr",
    "法语": "fr",
    "法語": "fr",
    "hindi": "hi",
    "हिन्दी": "hi",
    "हिंदी": "hi",
    "italian": "it",
    "italiano": "it",
    "italien": "it",
    "italienisch": "it",
    "włoski": "it",
    "итальянский": "it",
    "イタリア語": "it",
    "이탈리아어": "it",
    "意大利语": "it",
    "義大利語": "it",
    "japanese": "ja",
    "日本語": "ja",
    "japonés": "ja",
    "japones": "ja",
    "japonais": "ja",
    "japanisch": "ja",
    "giapponese": "ja",
    "japoński": "ja",
    "японский": "ja",
    "일본어": "ja",
    "日语": "ja",
    "日語": "ja",
    "korean": "ko",
    "한국어": "ko",
    "coreano": "ko",
    "coréen": "ko",
    "coreen": "ko",
    "koreanisch": "ko",
    "koreański": "ko",
    "корейский": "ko",
    "韓国語": "ko",
    "韩语": "ko",
    "韓語": "ko",
    "dutch": "nl",
    "nederlands": "nl",
    "holandés": "nl",
    "holandes": "nl",
    "néerlandais": "nl",
    "neerlandais": "nl",
    "niederländisch": "nl",
    "niederlaendisch": "nl",
    "olandese": "nl",
    "niderlandzki": "nl",
    "голландский": "nl",
    "オランダ語": "nl",
    "네덜란드어": "nl",
    "荷兰语": "nl",
    "荷蘭語": "nl",
    "polish": "pl",
    "polski": "pl",
    "polaco": "pl",
    "polonais": "pl",
    "polnisch": "pl",
    "polacco": "pl",
    "pools": "pl",
    "польский": "pl",
    "ポーランド語": "pl",
    "폴란드어": "pl",
    "波兰语": "pl",
    "波蘭語": "pl",
    "portuguese": "pt",
    "portugues": "pt",
    "português": "pt",
    "portugais": "pt",
    "portugiesisch": "pt",
    "portoghese": "pt",
    "portugees": "pt",
    "portugalski": "pt",
    "португальский": "pt",
    "ポルトガル語": "pt",
    "포르투갈어": "pt",
    "葡萄牙语": "pt",
    "葡萄牙語": "pt",
    "russian": "ru",
    "русский": "ru",
    "ruso": "ru",
    "russe": "ru",
    "russisch": "ru",
    "rosyjski": "ru",
    "ロシア語": "ru",
    "러시아어": "ru",
    "俄语": "ru",
    "俄語": "ru",
    "chinese": "zh-cn",
    "chino": "zh-cn",
    "chinois": "zh-cn",
    "chinesisch": "zh-cn",
    "cinese": "zh-cn",
    "chiński": "zh-cn",
    "китайский": "zh-cn",
    "中国語": "zh-cn",
    "중국어": "zh-cn",
    "simplified chinese": "zh-cn",
    "chinese simplified": "zh-cn",
    "mandarin": "zh-cn",
    "中文": "zh-cn",
    "简体中文": "zh-cn",
    "traditional chinese": "zh-tw",
    "chinese traditional": "zh-tw",
    "繁體中文": "zh-tw",
}

RESPONSE_LANGUAGE_NAMES = {
    "ar": "Arabic",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "hi": "Hindi",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
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

    if "reset_generation" not in st.session_state:
        st.session_state.reset_generation = 0

    if "checklist_generation" not in st.session_state:
        st.session_state.checklist_generation = 0

    if "checklist" not in st.session_state:
        st.session_state.checklist = {
            item["id"]: False for item in CHECKLIST_ITEMS
        }


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
    st.session_state.checklist_generation += 1
    st.session_state.checklist = {
        item["id"]: False for item in CHECKLIST_ITEMS
    }


def checklist_widget_key(item_id: str) -> str:
    """Return the Streamlit widget key for a checklist item."""
    return (
        f"checklist_{item_id}_"
        f"{st.session_state.reset_generation}_"
        f"{st.session_state.checklist_generation}"
    )


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


def explicit_language_request(text: str) -> str | None:
    """Detect clear language switch requests without statistical guessing."""
    language, confidence = language_request_candidate(text)
    if confidence == "explicit":
        return language
    return None


def language_request_candidate(text: str) -> tuple[str | None, str | None]:
    """Return a language candidate and whether the local parse is explicit or ambiguous."""
    normalized = re.sub(r"[^\w\s\u0080-\uffff-]", " ", text.casefold())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return None, None

    command_words = (
        "switch",
        "change",
        "use",
        "speak",
        "language",
        "to",
        "in",
        "please",
        "por favor",
        "cambiar",
        "cambia",
        "cambie",
        "cambiar a",
        "habla",
        "hablar",
        "idioma",
        "a",
        "en",
        "changer",
        "parler",
        "langue",
        "vers",
        "bitte",
        "wechseln",
        "sprich",
        "sprechen",
        "sprache",
        "zu",
        "passa",
        "passare",
        "parla",
        "lingua",
        "para",
        "mudar",
        "falar",
        "idioma",
        "taal",
        "spreek",
        "zmień",
        "zmien",
        "mów",
        "mow",
        "język",
        "jezyk",
        "переключи",
        "переключить",
        "говори",
        "язык",
        "切换",
        "切換",
        "说",
        "說",
        "语言",
        "語言",
        "言語",
        "話して",
        "切り替え",
        "언어",
        "말해",
        "전환",
    )

    candidates = {normalized}
    stripped = normalized
    for word in sorted(command_words, key=len, reverse=True):
        stripped = re.sub(rf"(^|\s){re.escape(word)}(\s|$)", " ", stripped)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if stripped:
        candidates.add(stripped)

    for name in sorted(LANGUAGE_NAMES, key=len, reverse=True):
        if name in candidates:
            return LANGUAGE_NAMES[name], "explicit"
        has_non_ascii = any(ord(character) > 127 for character in name)
        if has_non_ascii and name in normalized and stripped != normalized:
            return LANGUAGE_NAMES[name], "explicit"

    matches = set()
    for name, code in LANGUAGE_NAMES.items():
        has_non_ascii = any(ord(character) > 127 for character in name)
        if has_non_ascii and name in normalized:
            matches.add(code)
        elif re.search(rf"(^|\s){re.escape(name)}(\s|$)", normalized):
            matches.add(code)

    if len(matches) == 1:
        return matches.pop(), "ambiguous"

    if matches:
        return None, "ambiguous"

    return None, None


def is_language_only_request(text: str) -> bool:
    """Return True when a prompt is only asking to switch language."""
    language, confidence = language_request_candidate(text)
    if confidence != "explicit" or not language:
        return False

    normalized = re.sub(r"[^\w\s\u0080-\uffff-]", " ", text.casefold())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return False

    return len(normalized.split()) <= 5


def resolve_language_switch_with_llm(text: str, analysis: dict | None = None) -> str | None:
    """Use the model only for ambiguous language-switch intent."""
    if analysis is not None:
        return analysis.get("language")

    cache = st.session_state.setdefault("language_switch_intent_cache", {})
    if text in cache:
        return cache[text]

    return None


def remember_language_from_text(text: str, analysis: dict | None = None) -> None:
    """Update remembered language without letting weak English detections erase it."""
    requested_language, confidence = language_request_candidate(text)
    if confidence == "explicit" and requested_language:
        st.session_state.current_language = normalize_tts_language(requested_language)
        return

    if confidence == "ambiguous":
        resolved_language = resolve_language_switch_with_llm(text, analysis)
        if resolved_language:
            st.session_state.current_language = normalize_tts_language(resolved_language)
        return

    requested_language = explicit_language_request(text)
    if requested_language:
        st.session_state.current_language = normalize_tts_language(requested_language)
        return

    detected_language = normalize_tts_language(
        detect_tts_language(text)
    )
    current_language = normalize_tts_language(st.session_state.current_language)

    if detected_language != DEFAULT_LANGUAGE or current_language == DEFAULT_LANGUAGE:
        st.session_state.current_language = detected_language


def analyze_prompt_once(prompt: str) -> dict:
    """Run the combined model analysis once per unique prompt."""
    cache = st.session_state.setdefault("user_message_analysis_cache", {})
    if prompt in cache:
        return cache[prompt]

    try:
        analysis = analyze_user_message(prompt, CHECKLIST_ITEMS)
    except Exception as e:
        print(f"User message analysis error: {e}")
        analysis = {"updates": {}, "language": None}

    cache[prompt] = analysis
    return analysis


def welcome_message(language: str) -> dict[str, str | bool]:
    """Build a marked welcome chat message for the current language."""
    return {
        "role": "assistant",
        "content": get_welcome_message(language),
        "is_welcome": True,
    }


def set_checklist_item(item_id: str, checked: bool) -> None:
    """Update checklist state from extracted user claims."""
    st.session_state.checklist[item_id] = checked


def update_checklist_from_analysis(analysis: dict | None) -> None:
    """Check or uncheck checklist items from model-extracted user claims."""
    if not analysis:
        return

    updates = analysis.get("updates", {})
    if not updates:
        return

    for item_id, checked in updates.items():
        set_checklist_item(item_id, checked)

    st.session_state.checklist_generation += 1


def checklist_context() -> str:
    """Build a compact checklist summary for the assistant prompt."""
    current_language = current_ui_language()
    response_language = RESPONSE_LANGUAGE_NAMES.get(
        current_language,
        RESPONSE_LANGUAGE_NAMES[DEFAULT_LANGUAGE],
    )
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
        f"Current response language: {response_language}. "
        "Always answer using that language's normal native writing system. "
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
            st.checkbox(
                checklist_label(item["id"]),
                value=st.session_state.checklist[item["id"]],
                key=widget_key,
            )
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
        st.rerun()
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
                st.rerun()


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
            elif (
                message.get("auto_speak")
                and st.session_state.auto_read_responses
            ):
                render_spoken_response(message["content"])
                message["auto_speak"] = False


def handle_user_prompt(prompt: str) -> None:
    """Send user prompt to the backend agent and render the response."""
    requested_language, confidence = language_request_candidate(prompt)
    analysis = None
    language_only_request = is_language_only_request(prompt)
    if confidence != "explicit":
        analysis = analyze_prompt_once(prompt)

    remember_language_from_text(prompt, analysis)

    if analysis is None and not language_only_request:
        analysis = analyze_prompt_once(prompt)

    update_checklist_from_analysis(analysis)

    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        with st.spinner(ui_text("thinking")):
            assistant_reply = chat(prompt, checklist_context())

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": assistant_reply,
                "auto_speak": True,
            }
        )

    except RuntimeError as e:
        error_message = str(e)
        st.session_state.messages.append(
            {"role": "assistant", "content": error_message}
        )

    except Exception as e:
        print(f"Frontend chat error: {e}")

        error_message = ui_text("service_error")
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

    typed_prompt = st.chat_input(
        ui_text("chat_input"),
        key=f"chat_input_{st.session_state.reset_generation}",
    )

    prompt = st.session_state.pending_prompt or typed_prompt

    if prompt:
        st.session_state.pending_prompt = None
        handle_user_prompt(prompt)
        st.rerun()

    render_sidebar()

    st.title(ui_text("page_title"))
    st.caption(ui_text("page_caption"))

    st.info(ui_text("privacy_notice"))

    render_voice_input()

    st.divider()

    render_suggested_questions()

    st.divider()

    render_chat_history()


if __name__ == "__main__":
    main()



