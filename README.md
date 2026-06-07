The voice AI agent is an EBT application assistant that helps you get your EBT documents in order. It listens on your microphone, transcribes speech with Groq Whisper, and replies out loud, powered by Groq's API.

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

## Run the frontend

Do not run `python app.py`.

Run the Streamlit frontend with:

```bash
python -m streamlit run app.py
