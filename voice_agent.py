"""
Voice AI Agent
==============
Speak to Groq, get spoken responses back.
Uses:
  - SpeechRecognition  (mic → text)
  - pyttsx3            (text → speech, offline, no API key)
  - groq               (Groq API — free tier)

Install:
    pip install groq speechrecognition pyttsx3 pyaudio

Set your free Groq API key (https://console.groq.com/keys):
    export GROQ_API_KEY=...      # macOS / Linux
    setx GROQ_API_KEY "..."      # Windows

On macOS you may need:  brew install portaudio
On Linux:               sudo apt install portaudio19-dev python3-pyaudio espeak
"""

import io
import json
import os
import sys

import groq
from groq import Groq
from dotenv import load_dotenv
import speech_recognition as sr

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except ImportError:
    _TTS_AVAILABLE = False

# Load GROQ_API_KEY (and any other vars) from a local .env file, if present.
load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────

AGENT_INSTRUCTIONS = """
You are an EBT application assistant helping clients apply for food assistance benefits.
Keep every reply under 3 sentences — responses will be spoken aloud.
Never use bullet points, markdown, or special characters.
Speak naturally, like a conversation.
Do not ask for or repeat back sensitive personal information such as Social Security numbers, bank account details, or passwords.
If user asks to switch language, please return responses in that language.
When the user asks what requirements or documents they have fulfilled, answer from the current document checklist context.
"""

# Groq model — swap for "llama-3.1-8b-instant" (faster) or "openai/gpt-oss-20b", etc.
MODEL         = "llama-3.3-70b-versatile"
SPEECH_RATE   = 175   # words per minute (pyttsx3)
SPEECH_VOLUME = 1.0   # 0.0 – 1.0

# ─── Setup ────────────────────────────────────────────────────────────────────

client = None
recognizer = sr.Recognizer()

conversation_history = []


CHECKLIST_EXTRACTION_INSTRUCTIONS = """
You update an EBT document checklist from one user message.
The user may write in any language.
Return only a JSON object with an "updates" object.
Use checklist item ids as keys and true or false as values.
Use true only when the user clearly says they have, collected, uploaded, or completed that item.
Use false only when the user clearly says they do not have, lost, still need, or have not completed that item.
If the message is only asking a question or is unclear, return {"updates":{}}.
Do not infer unrelated checklist items.
"""


def get_client() -> Groq:
    """
    Create and return the Groq client.

    We do this lazily so voice_agent.py can be safely imported by the
    Streamlit frontend. If the API key is missing, the frontend can show
    a friendly error instead of the whole app exiting during import.
    """
    global client

    if client is not None:
        return client

    if not os.environ.get("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your Groq API key."
        )

    client = Groq()
    return client


def reset_conversation() -> None:
    """Clear the in-memory conversation history."""
    conversation_history.clear()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def speak(text: str) -> None:
    """Convert text to speech and play it (CLI only; not used by the web app)."""
    print(f"\n🤖 Agent: {text}\n")
    if not _TTS_AVAILABLE:
        return
    engine = pyttsx3.init()
    engine.setProperty("rate",   SPEECH_RATE)
    engine.setProperty("volume", SPEECH_VOLUME)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def listen(timeout: int = 8, phrase_limit: int = 15) -> str | None:
    """
    Record from the default microphone and return transcribed text.
    Returns None if nothing was heard or recognition failed.
    """
    with sr.Microphone() as source:
        print("🎙  Listening…  (speak now)")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_limit,
            )
        except sr.WaitTimeoutError:
            print("   (no speech detected, try again)")
            return None

    print("   (processing…)")
    try:
        text = recognizer.recognize_whisper(audio)
        print(f"👤 You: {text}")
        return text
    except sr.UnknownValueError:
        print("   (could not understand audio)")
        return None
    except sr.RequestError as e:
        print(f"   (Google Speech API error: {e})")
        return None

def transcribe_audio_bytes(audio_bytes: bytes) -> str | None:
    """
    Transcribe browser-recorded audio from the Streamlit frontend.

    Streamlit's st.audio_input gives us audio bytes. We wrap those bytes
    in a file-like object and let SpeechRecognition process them as an
    audio file.
    """
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_whisper(audio)
        return text

    except sr.UnknownValueError:
        return None

    except sr.RequestError as e:
        print(f"Google Speech API error: {e}")
        return None

    except Exception as e:
        print(f"Audio transcription error: {e}")
        return None


def extract_checklist_updates(
    user_text: str,
    checklist_items: list[dict[str, str]],
) -> dict[str, bool]:
    """Ask the model for explicit checklist updates from the user's message."""
    groq_client = get_client()

    checklist_description = "\n".join(
        f"- {item['id']}: {item['label']}"
        for item in checklist_items
    )

    response = groq_client.chat.completions.create(
        model=MODEL,
        max_tokens=128,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": CHECKLIST_EXTRACTION_INSTRUCTIONS.strip(),
            },
            {
                "role": "user",
                "content": (
                    "Checklist items:\n"
                    f"{checklist_description}\n\n"
                    "User message:\n"
                    f"{user_text}"
                ),
            },
        ],
    )

    content = response.choices[0].message.content.strip()

    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            return {}
        try:
            payload = json.loads(content[start:end])
        except json.JSONDecodeError:
            return {}

    updates = payload.get("updates", {})
    valid_ids = {item["id"] for item in checklist_items}

    return {
        item_id: checked
        for item_id, checked in updates.items()
        if item_id in valid_ids and isinstance(checked, bool)
    }


def chat(user_text: str, checklist_context: str | None = None) -> str:
    """Send user_text to Groq and return the assistant reply."""
    groq_client = get_client()

    conversation_history.append({"role": "user", "content": user_text})

    system_content = AGENT_INSTRUCTIONS.strip()
    if checklist_context:
        system_content = f"{system_content}\n\n{checklist_context}"

    response = groq_client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "system", "content": system_content}]
        + conversation_history,
    )

    reply = response.choices[0].message.content.strip()
    conversation_history.append({"role": "assistant", "content": reply})
    return reply


def update_instructions(new_instructions: str) -> None:
    """
    Hot-swap the agent's instructions at runtime.
    Clears conversation history so the new persona starts fresh.
    """
    global AGENT_INSTRUCTIONS
    AGENT_INSTRUCTIONS = new_instructions
    conversation_history.clear()
    print("\n✅ Instructions updated. Conversation reset.\n")


# ─── Main loop ────────────────────────────────────────────────────────────────

def run():
    try:
        get_client()
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    print("=" * 55)
    print("  Voice AI Agent  —  powered by Groq")
    print("=" * 55)
    print("  Say 'quit' or 'exit' to stop.")
    print("  Say 'change instructions' to update the agent.")
    print("  Current instructions:")
    print(AGENT_INSTRUCTIONS.strip())
    print("=" * 55)

    speak(
        "Hello! I'm your EBT application assistant, here to help you apply for food assistance benefits. "
        "Please do not share sensitive personal information such as Social Security numbers, "
        "bank account details, or passwords during our conversation. "
        "You can request to switch language at any time."
        "How can I help you today?"
    )

    while True:
        user_input = listen()

        if user_input is None:
            continue

        lower = user_input.lower().strip()

        # ── Exit commands ──────────────────────────────────────────────────
        if any(lower.startswith(w) for w in ("quit", "exit", "stop", "goodbye")):
            speak("Goodbye! Have a great day.")
            sys.exit(0)

        # ── Update instructions at runtime ─────────────────────────────────
        if "change instructions" in lower or "update instructions" in lower:
            speak("Sure. Please type your new instructions in the terminal.")
            print("\nEnter new instructions (blank line to finish):\n")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            if lines:
                update_instructions("\n".join(lines))
                speak("Got it. Instructions updated. Let's continue.")
            else:
                speak("No changes made.")
            continue

        # ── Normal conversation ────────────────────────────────────────────
        try:
            reply = chat(user_input)
            speak(reply)
        except groq.APIError as e:
            print(f"   (API error: {e})")
            speak("Sorry, I had trouble reaching the AI. Please try again.")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Optional: accept instructions as a CLI argument
    # Usage: python voice_agent.py "You are a pirate assistant."
    if len(sys.argv) > 1:
        update_instructions(" ".join(sys.argv[1:]))

    run()
