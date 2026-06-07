const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const recordingBanner = document.querySelector("#recordingBanner");
const recordingText = document.querySelector("#recordingText");
const statusText = document.querySelector("#statusText");
const connectionPill = document.querySelector("#connectionPill");
const chatLog = document.querySelector("#chatLog");
const enableVoiceButton = document.querySelector("#enableVoiceButton");

const messages = [];
let recognition;
let voiceEnabled = false;
let requestedRecording = false;
let activeRecording = false;
let pendingTranscript = "";

function setConnected(connected) {
  connectionPill.textContent = connected ? "Online" : "Offline";
  connectionPill.classList.toggle("online", connected);
  statusText.textContent = connected ? "Connected to Python agent" : "Waiting for Python agent";
}

function setRecording(recording) {
  recordingBanner.classList.toggle("is-idle", !recording);
  recordingText.textContent = recording ? "Recording" : "Idle";
}

function renderEmptyState() {
  if (messages.length > 0) return;
  chatLog.innerHTML =
    '<p class="empty">Run the Python agent, enable voice input, then speak when Recording appears.</p>';
}

function appendMessage(role, content) {
  messages.push({ role, content });

  const empty = chatLog.querySelector(".empty");
  if (empty) empty.remove();

  const message = document.createElement("article");
  message.className = `message ${role}`;
  const label = role === "user" ? "Voice input" : role === "assistant" ? "Chat output" : "Status";
  message.innerHTML = `<strong>${label}</strong>${escapeHtml(content)}`;
  chatLog.appendChild(message);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const map = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return map[char];
  });
}

async function postListenResult(text) {
  await fetch("/listen-result", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
}

function startBrowserListening() {
  requestedRecording = true;
  if (!recognition || activeRecording || !voiceEnabled) return;

  pendingTranscript = "";

  try {
    recognition.start();
  } catch (error) {
    postListenResult("");
  }
}

function setupSpeechRecognition() {
  if (!SpeechRecognition) {
    enableVoiceButton.disabled = true;
    appendMessage("system", "This browser does not support voice input. Use Chrome or Edge for browser audio.");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onstart = () => {
    activeRecording = true;
    setRecording(true);
  };

  recognition.onresult = (event) => {
    pendingTranscript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join(" ");
  };

  recognition.onerror = (event) => {
    activeRecording = false;
    setRecording(false);
    appendMessage("system", event.error === "not-allowed" ? "Browser audio permission was denied." : "Voice input stopped.");
    postListenResult("");
  };

  recognition.onend = () => {
    activeRecording = false;
    setRecording(false);

    if (!requestedRecording) return;
    requestedRecording = false;
    postListenResult(pendingTranscript.trim());
  };
}

function connectToPythonEvents() {
  if (!("EventSource" in window)) {
    appendMessage("system", "This browser does not support live event streaming.");
    return;
  }

  const events = new EventSource("/events");

  events.addEventListener("open", () => {
    setConnected(true);
  });

  events.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);

    if (payload.type === "recording") {
      if (payload.recording) {
        startBrowserListening();
      } else if (recognition && activeRecording) {
        recognition.stop();
      } else {
        setRecording(false);
      }
      return;
    }

    if (payload.type === "listen_output") {
      appendMessage("user", payload.text);
      return;
    }

    if (payload.type === "chat_output") {
      appendMessage("assistant", payload.text);
      return;
    }

    if (payload.type === "status") {
      appendMessage("system", payload.text);
    }
  });

  events.addEventListener("error", () => {
    setConnected(false);
    setRecording(false);
  });
}

enableVoiceButton.addEventListener("click", () => {
  voiceEnabled = true;
  enableVoiceButton.textContent = "Voice input enabled";
  enableVoiceButton.disabled = true;
  appendMessage("system", "Voice input enabled. Speak when Recording appears.");

  if (requestedRecording) {
    startBrowserListening();
  }
});

setupSpeechRecognition();
renderEmptyState();
setRecording(false);
setConnected(false);
connectToPythonEvents();
