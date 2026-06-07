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

import os
import sys

import groq
from groq import Groq
import speech_recognition as sr
import pyttsx3

# ─── Configuration ────────────────────────────────────────────────────────────

AGENT_INSTRUCTIONS = """
You are an EBT application assistant helping clients apply for food assistance benefits.
Keep every reply under 3 sentences — responses will be spoken aloud.
Never use bullet points, markdown, or special characters.
Speak naturally, like a conversation.
Do not ask for or repeat back sensitive personal information such as Social Security numbers, bank account details, or passwords.
"""

# Groq model — swap for "llama-3.1-8b-instant" (faster) or "openai/gpt-oss-20b", etc.
MODEL         = "llama-3.3-70b-versatile"
SPEECH_RATE   = 175   # words per minute (pyttsx3)
SPEECH_VOLUME = 1.0   # 0.0 – 1.0

# ─── Setup ────────────────────────────────────────────────────────────────────

if not os.environ.get("GROQ_API_KEY"):
    print(
        "GROQ_API_KEY is not set.\n"
        "Get a free key at https://console.groq.com/keys and set it before running:\n"
        '    setx GROQ_API_KEY "your-key-here"   (Windows, then reopen the terminal)\n'
        "    export GROQ_API_KEY=your-key-here    (macOS / Linux)"
    )
    sys.exit(1)

client     = Groq()   # reads GROQ_API_KEY from env
recognizer = sr.Recognizer()
engine     = pyttsx3.init()

engine.setProperty("rate",   SPEECH_RATE)
engine.setProperty("volume", SPEECH_VOLUME)

conversation_history = []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def speak(text: str) -> None:
    """Convert text to speech and play it."""
    print(f"\n🤖 Agent: {text}\n")
    engine.say(text)
    engine.runAndWait()


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
        text = recognizer.recognize_google(audio)
        print(f"👤 You: {text}")
        return text
    except sr.UnknownValueError:
        print("   (could not understand audio)")
        return None
    except sr.RequestError as e:
        print(f"   (Google Speech API error: {e})")
        return None


def chat(user_text: str) -> str:
    """Send user_text to Groq and return the assistant reply."""
    conversation_history.append({"role": "user", "content": user_text})

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "system", "content": AGENT_INSTRUCTIONS.strip()}]
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