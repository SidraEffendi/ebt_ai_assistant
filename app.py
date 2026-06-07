import html
import json
from urllib.parse import parse_qs

from voice_agent import WELCOME_MESSAGE, chat, reset_conversation


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EBT AI Assistant</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, sans-serif;
      background: #f6f7f9;
      color: #1f2933;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
    }}
    main {{
      width: min(760px, 100%);
      background: #ffffff;
      border: 1px solid #d9e2ec;
      border-radius: 8px;
      box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
      overflow: hidden;
    }}
    header, form, .notice {{
      padding: 20px 24px;
    }}
    header {{
      border-bottom: 1px solid #e4e7eb;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.2;
    }}
    p {{
      margin: 0;
      line-height: 1.5;
    }}
    .notice {{
      background: #fff8e6;
      border-bottom: 1px solid #f3d27a;
      color: #5c4200;
    }}
    .messages {{
      min-height: 260px;
      max-height: 52vh;
      overflow-y: auto;
      padding: 20px 24px;
      display: grid;
      gap: 12px;
      background: #fbfcfd;
    }}
    .message {{
      padding: 12px 14px;
      border-radius: 8px;
      line-height: 1.5;
      white-space: pre-wrap;
    }}
    .assistant {{
      background: #e8f1ff;
      justify-self: start;
    }}
    .user {{
      background: #dff7ec;
      justify-self: end;
    }}
    form {{
      display: grid;
      gap: 12px;
      border-top: 1px solid #e4e7eb;
    }}
    textarea {{
      min-height: 96px;
      resize: vertical;
      border: 1px solid #bcccdc;
      border-radius: 8px;
      padding: 12px;
      font: inherit;
    }}
    .actions {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }}
    button {{
      border: 0;
      border-radius: 8px;
      padding: 10px 16px;
      font: inherit;
      cursor: pointer;
    }}
    button[type="submit"] {{
      background: #2563eb;
      color: white;
    }}
    button[type="button"] {{
      background: #e4e7eb;
      color: #243b53;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>EBT AI Assistant</h1>
      <p>A text chat version of the assistant for Vercel deployment.</p>
    </header>
    <div class="notice">
      Please do not enter Social Security numbers, bank account numbers, passwords, or other highly sensitive personal information.
    </div>
    <section class="messages" id="messages">
      <div class="message assistant">{welcome}</div>
    </section>
    <form id="chat-form">
      <textarea id="prompt" name="prompt" placeholder="Type your question here" required></textarea>
      <div class="actions">
        <button type="button" id="reset">Reset conversation</button>
        <button type="submit">Send</button>
      </div>
    </form>
  </main>
  <script>
    const messages = document.getElementById("messages");
    const form = document.getElementById("chat-form");
    const promptInput = document.getElementById("prompt");
    const resetButton = document.getElementById("reset");

    function addMessage(role, text) {{
      const node = document.createElement("div");
      node.className = `message ${{role}}`;
      node.textContent = text;
      messages.appendChild(node);
      messages.scrollTop = messages.scrollHeight;
    }}

    form.addEventListener("submit", async (event) => {{
      event.preventDefault();
      const prompt = promptInput.value.trim();
      if (!prompt) return;

      addMessage("user", prompt);
      promptInput.value = "";

      const pending = document.createElement("div");
      pending.className = "message assistant";
      pending.textContent = "Thinking...";
      messages.appendChild(pending);
      messages.scrollTop = messages.scrollHeight;

      try {{
        const response = await fetch("/chat", {{
          method: "POST",
          headers: {{ "content-type": "application/json" }},
          body: JSON.stringify({{ prompt }}),
        }});
        const data = await response.json();
        pending.textContent = data.reply || data.error || "Sorry, something went wrong.";
      }} catch (error) {{
        pending.textContent = "Sorry, I had trouble reaching the assistant.";
      }}
    }});

    resetButton.addEventListener("click", async () => {{
      await fetch("/reset", {{ method: "POST" }});
      messages.innerHTML = "";
      addMessage("assistant", {welcome_json});
    }});
  </script>
</body>
</html>
"""


def _response(start_response, body, status="200 OK", content_type="text/html; charset=utf-8"):
    payload = body.encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(payload))),
        ],
    )
    return [payload]


def _read_json(environ):
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0

    body = environ["wsgi.input"].read(length).decode("utf-8") if length else ""
    content_type = environ.get("CONTENT_TYPE", "")

    if "application/json" in content_type:
        return json.loads(body or "{}")

    form = parse_qs(body)
    return {key: values[0] for key, values in form.items()}


def application(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET").upper()

    if method == "GET" and path == "/":
        page = HTML_PAGE.format(
            welcome=html.escape(WELCOME_MESSAGE),
            welcome_json=json.dumps(WELCOME_MESSAGE),
        )
        return _response(start_response, page)

    if method == "POST" and path == "/chat":
        try:
            prompt = (_read_json(environ).get("prompt") or "").strip()
            if not prompt:
                raise ValueError("Prompt is required.")

            reply = chat(prompt)
            return _response(
                start_response,
                json.dumps({"reply": reply}),
                content_type="application/json; charset=utf-8",
            )
        except Exception as exc:
            return _response(
                start_response,
                json.dumps({"error": str(exc)}),
                status="500 Internal Server Error",
                content_type="application/json; charset=utf-8",
            )

    if method == "POST" and path == "/reset":
        reset_conversation()
        return _response(
            start_response,
            json.dumps({"ok": True}),
            content_type="application/json; charset=utf-8",
        )

    return _response(start_response, "Not found", status="404 Not Found")


app = application
handler = application
