The voice AI agent is an EBT application assistant that helps you get your EBT documents in order. It listens through the browser UI and replies out loud, powered by Groq's free LLM API.

## Web UI

This repo also includes a minimal browser UI for the Python voice agent:

- `index.html`, `styles.css`, and `script.js` show the live Recording state and conversation log.
- `voice_agent.py` serves the UI locally and streams Python events from `listen()` and `chat()`.
- `listen()` triggers browser voice input and waits for the browser transcript.
- Voice inputs are logged from the return value of `listen()`.
- Chat responses are logged from the return value of `chat()`.

Run the UI with the Python agent:

```
python voice_agent.py
```

Then open the printed local URL, usually `http://127.0.0.1:8765`.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Get a free Groq API key at https://console.groq.com/keys, then add it to a
   `.env` file in this folder (copy `.env.example` to `.env`):
   ```
   GROQ_API_KEY=your-key-here
   ```
   The `.env` file is gitignored, so your key won't be committed. (You can also
   set `GROQ_API_KEY` as a normal environment variable instead.)
3. Run it:
   ```
   python voice_agent.py
   ```

Say "quit" or "exit" to stop, or "change instructions" to update the agent at runtime.
