The voice AI agent is an EBT application assistant that helps you get your EBT documents in order. It listens on your microphone and replies out loud, powered by Groq's free LLM API.

## Web UI

This repo also includes a minimal Vercel-ready browser UI:

- `index.html`, `styles.css`, and `script.js` provide the microphone interface.
- `api/chat.js` is a Vercel serverless endpoint that calls Groq.
- Set `GROQ_API_KEY` in your Vercel project environment variables before deploying.

Run locally with:

```
npm install
npm run dev
```

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
