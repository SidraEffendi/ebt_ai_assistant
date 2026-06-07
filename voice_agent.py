"""
Voice AI Agent
==============
Speak to Groq, get spoken responses back.
Uses:
  - Browser SpeechRecognition  (voice input -> text)
  - pyttsx3                    (text -> speech, offline, no API key)
  - groq                       (Groq API)

Install:
    pip install groq python-dotenv pyttsx3

Set your Groq API key (https://console.groq.com/keys):
    export GROQ_API_KEY=...      # macOS / Linux
    setx GROQ_API_KEY "..."      # Windows

Open the local UI URL printed by the agent and enable voice input in the browser.
"""

import os
import sys
import json
import mimetypes
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import groq
from groq import Groq
from dotenv import load_dotenv
import pyttsx3

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
"""

# Groq model — swap for "llama-3.1-8b-instant" (faster) or "openai/gpt-oss-20b", etc.
MODEL         = "llama-3.3-70b-versatile"
SPEECH_RATE   = 175   # words per minute (pyttsx3)
UI_PORT       = int(os.environ.get("UI_PORT", "8765"))
UI_ROOT       = Path(__file__).resolve().parent
SPEECH_VOLUME = 1.0   # 0.0 – 1.0

# ─── Setup ────────────────────────────────────────────────────────────────────

if not os.environ.get("GROQ_API_KEY"):
    print(
        "GROQ_API_KEY is not set.\n"
        "Get a free key at https://console.groq.com/keys, then add it to a .env file\n"
        "in this folder:\n"
        "    GROQ_API_KEY=your-key-here\n"
        "(or set it as an environment variable instead)."
    )
    sys.exit(1)

client     = Groq()   # reads GROQ_API_KEY from env

conversation_history = []
browser_listen_results = queue.Queue(maxsize=1)
ui_clients = set()
ui_clients_lock = threading.Lock()
ui_server_started = False


def emit_ui_event(payload: dict) -> None:
    """Broadcast an event to every connected browser UI."""
    with ui_clients_lock:
        clients = list(ui_clients)

    for client in clients:
        try:
            client.put_nowait(payload)
        except queue.Full:
            pass


class VoiceAgentUiHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/events":
            self.handle_events()
            return

        path = self.path.split("?", 1)[0]
        if path == "/":
            path = "/index.html"

        file_path = (UI_ROOT / path.lstrip("/")).resolve()
        try:
            file_path.relative_to(UI_ROOT)
        except ValueError:
            self.send_error(404)
            return

        if not file_path.is_file():
            self.send_error(404)
            return

        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if self.path != "/listen-result":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body or "{}")
            text = str(payload.get("text", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self.send_error(400)
            return

        while not browser_listen_results.empty():
            try:
                browser_listen_results.get_nowait()
            except queue.Empty:
                break

        browser_listen_results.put(text)
        self.send_response(204)
        self.end_headers()

    def handle_events(self):
        client_queue = queue.Queue(maxsize=100)
        with ui_clients_lock:
            ui_clients.add(client_queue)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            self.write_event({"type": "status", "text": "Python agent connected."})
            while True:
                try:
                    payload = client_queue.get(timeout=15)
                    self.write_event(payload)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with ui_clients_lock:
                ui_clients.discard(client_queue)

    def write_event(self, payload: dict):
        data = json.dumps(payload)
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()


def start_ui_server() -> None:
    global ui_server_started
    if ui_server_started:
        return

    server = ThreadingHTTPServer(("127.0.0.1", UI_PORT), VoiceAgentUiHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    ui_server_started = True
    print(f"UI available at http://127.0.0.1:{UI_PORT}")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def speak(text: str) -> None:
    """Convert text to speech and play it.

    A fresh engine is created per call on purpose: reusing a single pyttsx3
    engine on Windows (SAPI5) only produces audio on the first runAndWait(),
    leaving later utterances silent.
    """
    print(f"\n🤖 Agent: {text}\n")
    engine = pyttsx3.init()
    engine.setProperty("rate",   SPEECH_RATE)
    engine.setProperty("volume", SPEECH_VOLUME)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def listen(timeout: int = 8, phrase_limit: int = 15) -> str | None:
    """
    Ask the browser UI to capture audio and return transcribed text.
    Returns None if nothing was heard or the browser does not send a transcript.
    """
    while not browser_listen_results.empty():
        try:
            browser_listen_results.get_nowait()
        except queue.Empty:
            break

    print("Listening in browser... (speak now)")
    emit_ui_event({"type": "recording", "recording": True})

    try:
        text = browser_listen_results.get(timeout=timeout + phrase_limit + 5)
    except queue.Empty:
        print("   (no browser speech result, try again)")
        emit_ui_event({"type": "recording", "recording": False})
        return None

    emit_ui_event({"type": "recording", "recording": False})
    if not text:
        print("   (could not understand browser audio)")
        return None

    print(f"You: {text}")
    emit_ui_event({"type": "listen_output", "text": text})
    return text


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
    emit_ui_event({"type": "chat_output", "text": reply})
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
    start_ui_server()
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
