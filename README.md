The voice AI agent is an EBT application assistant that helps you get your EBT documents in order. It listens on your microphone and replies out loud, powered by Groq's free LLM API.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Get a free Groq API key at https://console.groq.com/keys and set it:
   ```
   setx GROQ_API_KEY "your-key-here"     # Windows (then reopen the terminal)
   export GROQ_API_KEY=your-key-here      # macOS / Linux
   ```
3. Run it:
   ```
   python voice_agent.py
   ```

Say "quit" or "exit" to stop, or "change instructions" to update the agent at runtime.
