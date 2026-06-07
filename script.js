const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

const micButton = document.querySelector("#micButton");
const recordingBanner = document.querySelector("#recordingBanner");
const statusText = document.querySelector("#statusText");
const chatLog = document.querySelector("#chatLog");
const textForm = document.querySelector("#textForm");
const textInput = document.querySelector("#textInput");

const messages = [];
let recognition;
let isRecording = false;
let pendingTranscript = "";

function setStatus(text) {
  statusText.textContent = text;
}

function setRecording(recording) {
  isRecording = recording;
  micButton.classList.toggle("recording", recording);
  recordingBanner.hidden = !recording;
  micButton.setAttribute("aria-label", recording ? "Stop voice input" : "Start voice input");
  setStatus(recording ? "Recording" : "Ready");
}

function renderEmptyState() {
  if (messages.length > 0) return;
  chatLog.innerHTML =
    '<p class="empty">Tap the microphone and ask about getting EBT application documents in order.</p>';
}

function appendMessage(role, content) {
  messages.push({ role, content });

  const empty = chatLog.querySelector(".empty");
  if (empty) empty.remove();

  const message = document.createElement("article");
  message.className = `message ${role}`;
  const label = role === "user" ? "You" : role === "assistant" ? "Assistant" : "Status";
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

async function sendToAgent(userText) {
  const trimmed = userText.trim();
  if (!trimmed) return;

  appendMessage("user", trimmed);
  setStatus("Thinking");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: messages.filter((message) => ["user", "assistant"].includes(message.role)),
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed.");
    }

    appendMessage("assistant", data.reply);
    speak(data.reply);
    setStatus("Ready");
  } catch (error) {
    appendMessage("system", error.message || "Something went wrong.");
    setStatus("Ready");
  }
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  window.speechSynthesis.speak(utterance);
}

function setupSpeechRecognition() {
  if (!SpeechRecognition) {
    micButton.disabled = true;
    micButton.title = "Speech recognition is not supported in this browser.";
    appendMessage("system", "Speech recognition is not supported in this browser. You can still type.");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onstart = () => {
    pendingTranscript = "";
    setRecording(true);
  };

  recognition.onresult = (event) => {
    pendingTranscript = Array.from(event.results)
      .map((result) => result[0].transcript)
      .join(" ");
  };

  recognition.onerror = (event) => {
    setRecording(false);
    appendMessage("system", event.error === "not-allowed" ? "Microphone permission was denied." : "Voice input stopped.");
  };

  recognition.onend = () => {
    const transcript = pendingTranscript.trim();
    setRecording(false);
    if (transcript) sendToAgent(transcript);
  };
}

micButton.addEventListener("click", () => {
  if (!recognition) return;

  if (isRecording) {
    recognition.stop();
    return;
  }

  try {
    recognition.start();
  } catch (error) {
    setRecording(false);
  }
});

textForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = textInput.value;
  textInput.value = "";
  sendToAgent(value);
});

setupSpeechRecognition();
renderEmptyState();
