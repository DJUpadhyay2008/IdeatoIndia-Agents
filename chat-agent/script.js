// script.js – Connects the premium UI to a local Ollama model
// ---------------------------------------------------------------
// Adjust the model name here or expose a selector in the UI if desired.
const DEFAULT_MODEL = "gemma4:e2b"; // Change to your preferred local model
const OLLAMA_ENDPOINT = "http://localhost:11434/api/chat";

// Keep a conversation history for the Ollama chat API
let chatHistory = [];

/**
 * Append a message bubble to the chat window.
 * @param {string} text - Message content
 * @param {string} sender - "user" or "bot"
 */
function addMessage(text, sender) {
  const chatWindow = document.getElementById("chatWindow");
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}`;
  msgDiv.textContent = text;
  chatWindow.appendChild(msgDiv);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

/**
 * Send the user prompt to Ollama and stream the response.
 * @param {string} prompt
 */
async function sendPrompt(prompt) {
  // Update UI immediately
  addMessage(prompt, "user");

  // Push user message to history for context
  chatHistory.push({ role: "user", content: prompt });

  // Prepare request payload
  const payload = {
    model: DEFAULT_MODEL,
    messages: chatHistory,
    stream: true,
  };

  try {
    const response = await fetch(OLLAMA_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    // Stream the response chunks and build the bot reply.
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let botMessage = "";
    let done = false;
    while (!done) {
      const { value, done: finished } = await reader.read();
      done = finished;
      if (value) {
        const chunk = decoder.decode(value, { stream: true });
        // Ollama streams JSON lines like {"message":"..."}
        const lines = chunk.split(/\n/).filter(Boolean);
        for (const line of lines) {
          try {
            const data = JSON.parse(line);
            if (data.message) {
              botMessage += data.message;
            }
          } catch (_) {
            // ignore malformed line
          }
        }
        // Update the bot message live (optional – simpler to wait till end)
      }
    }
    // Final display
    addMessage(botMessage.trim(), "bot");
    // Append bot response to history for continuity
    chatHistory.push({ role: "assistant", content: botMessage.trim() });
  } catch (err) {
    console.error(err);
    addMessage(`Error: ${err.message}`, "bot");
  }
}

// Form handling
document.getElementById("chatForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const inputEl = document.getElementById("userInput");
  const prompt = inputEl.value.trim();
  if (prompt) {
    sendPrompt(prompt);
    inputEl.value = "";
  }
});

// Optional: clear history on page reload (can be toggled)
window.addEventListener("load", () => {
  chatHistory = [];
});
