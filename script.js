const DEFAULT_INSTRUCTIONS = `
You are an EBT application assistant helping clients apply for food assistance benefits.
Keep every reply under 3 sentences because responses may be spoken aloud.
Never use bullet points, markdown, or special characters.
Speak naturally, like a conversation.
Do not ask for or repeat back sensitive personal information such as Social Security numbers, bank account details, or passwords.
If user asks to switch language, return responses in that language.
`;

const GREETING =
  "Hello! I'm your EBT application assistant, here to help you apply for food assistance benefits. Please do not share sensitive personal information such as Social Security numbers, bank account details, or passwords during our conversation. You can request to switch language at any time. How can I help you today?";

const recordingBanner = document.querySelector("#recordingBanner");
const recordingText = document.querySelector("#recordingText");
const statusText = document.querySelector("#statusText");
const chatLog = document.querySelector("#chatLog");
const listenButton = document.querySelector("#listenButton");
const textForm = document.querySelector("#textForm");
const textInput = document.querySelector("#textInput");
const instructionsButton = document.querySelector("#instructionsButton");
const instructionsPanel = document.querySelector("#instructionsPanel");
const instructionsInput = document.querySelector("#instructionsInput");
const saveInstructionsButton = document.querySelector("#saveInstructionsButton");
const resetInstructionsButton = document.querySelector("#resetInstructionsButton");

const messages = [];
let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let hasGreeted = false;
let awaitingInstructionText = false;
let agentInstructions = localStorage.getItem("agentInstructions") || DEFAULT_INSTRUCTIONS.trim();

function setStatus(text) {
  statusText.textContent = text;
}

function setRecording(recording) {
  isRecording = recording;
  recordingBanner.classList.toggle("is-idle", !recording);
  recordingText.textContent = recording ? "Recording" : "Idle";
  listenButton.textContent = recording ? "Stop listening" : "Start listening";
}

function renderEmptyState() {
  if (messages.length > 0) return;
  chatLog.innerHTML =
    '<p class="empty">Start listening or type a message to begin. Voice inputs and responses will appear here.</p>';
}

function appendMessage(role, content, options = {}) {
  const shouldSave = options.save !== false;
  const empty = chatLog.querySelector(".empty");
  if (empty) empty.remove();

  if (shouldSave && (role === "user" || role === "assistant")) {
    messages.push({ role, content });
  }

  const message = document.createElement("article");
  message.className = `message ${role}`;
  const label = role === "user" ? "Voice input" : role === "assistant" ? "Response" : "Status";
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

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.volume = 1;
  window.speechSynthesis.speak(utterance);
}

function greetOnce() {
  if (hasGreeted) return;
  hasGreeted = true;
  appendMessage("assistant", GREETING, { save: false });
  speak(GREETING);
}

function isExitCommand(text) {
  const lower = text.toLowerCase().trim();
  return ["quit", "exit", "stop", "goodbye"].some((word) => lower.startsWith(word));
}

function isInstructionCommand(text) {
  const lower = text.toLowerCase();
  return lower.includes("change instructions") || lower.includes("update instructions");
}

function updateInstructions(value) {
  const next = value.trim();
  if (!next) {
    appendMessage("system", "No instruction changes made.");
    return;
  }

  agentInstructions = next;
  localStorage.setItem("agentInstructions", agentInstructions);
  instructionsInput.value = agentInstructions;
  messages.length = 0;
  chatLog.innerHTML = "";
  hasGreeted = false;
  awaitingInstructionText = false;
  appendMessage("system", "Instructions updated. Conversation reset.");
  greetOnce();
}

async function sendToAgent(userText) {
  const text = userText.trim();
  if (!text) return;

  greetOnce();

  if (awaitingInstructionText) {
    updateInstructions(text);
    return;
  }

  if (isExitCommand(text)) {
    appendMessage("user", text);
    const farewell = "Goodbye! Have a great day.";
    appendMessage("assistant", farewell, { save: false });
    speak(farewell);
    setStatus("Stopped");
    return;
  }

  if (isInstructionCommand(text)) {
    appendMessage("user", text);
    awaitingInstructionText = true;
    instructionsPanel.hidden = false;
    const prompt = "Sure. Type your new instructions below or in the message box.";
    appendMessage("assistant", prompt, { save: false });
    speak(prompt);
    return;
  }

  appendMessage("user", text);
  setStatus("Thinking");

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        instructions: agentInstructions,
        messages,
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

function supportedMimeType() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"];
  return types.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

async function startRecording() {
  greetOnce();

  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    appendMessage("system", "This browser does not support audio recording. You can still type messages.");
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mimeType = supportedMimeType();
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      setRecording(false);
      await transcribeRecording(mimeType || mediaRecorder.mimeType || "audio/webm");
    };

    mediaRecorder.start();
    setRecording(true);
    setStatus("Listening");
  } catch (error) {
    setRecording(false);
    setStatus("Ready");
    appendMessage("system", "Browser audio permission was denied or unavailable.");
  }
}

function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") return;
  setStatus("Transcribing");
  mediaRecorder.stop();
}

async function transcribeRecording(mimeType) {
  const audioBlob = new Blob(audioChunks, { type: mimeType });
  audioChunks = [];

  if (!audioBlob.size) {
    appendMessage("system", "No audio was captured.");
    setStatus("Ready");
    return;
  }

  try {
    const response = await fetch("/api/transcribe", {
      method: "POST",
      headers: { "Content-Type": audioBlob.type || "audio/webm" },
      body: audioBlob,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Transcription failed.");
    }

    if (!data.text) {
      appendMessage("system", "I could not understand the audio.");
      setStatus("Ready");
      return;
    }

    await sendToAgent(data.text);
  } catch (error) {
    appendMessage("system", error.message || "Unable to transcribe audio.");
    setStatus("Ready");
  }
}

listenButton.addEventListener("click", () => {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
});

textForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = textInput.value;
  textInput.value = "";
  sendToAgent(value);
});

instructionsButton.addEventListener("click", () => {
  instructionsPanel.hidden = !instructionsPanel.hidden;
});

saveInstructionsButton.addEventListener("click", () => {
  updateInstructions(instructionsInput.value);
  instructionsPanel.hidden = true;
});

resetInstructionsButton.addEventListener("click", () => {
  instructionsInput.value = DEFAULT_INSTRUCTIONS.trim();
});

instructionsInput.value = agentInstructions;
renderEmptyState();
setRecording(false);
setStatus("Ready");
