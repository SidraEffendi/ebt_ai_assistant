The voice AI agent is an EBT application assistant that helps you get your EBT documents in order. It listens through the browser, calls Groq from a Vercel API route, logs the conversation, and replies out loud.

## Web UI

This repo includes a minimal Vercel-ready browser UI:

- `index.html`, `styles.css`, and `script.js` run the browser voice experience.
- `api/transcribe.js` transcribes recorded browser audio with Groq Whisper.
- `api/chat.js` calls Groq with the current conversation and fixed agent instructions.
- The UI shows `Recording` while browser audio recording is active.
- Voice inputs and assistant responses are logged in a scrollable chat window.
- Saying `quit`, `exit`, `stop`, or `goodbye` ends the conversation with a farewell.

Run locally with Vercel:

```
npm install
npm run dev
```

Set `GROQ_API_KEY` in `.env` locally and in Vercel project environment variables before deploying.

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

Say "quit" or "exit" to stop the local Python agent.
