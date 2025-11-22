// ---------------- Chat UI helpers ---------------- //
const chatBox = document.getElementById("chatBox");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const remindersList = document.getElementById("remindersList");

function appendMessage(sender, text) {
  const msgDiv = document.createElement("div");
  msgDiv.classList.add("message", sender);

  const bubble = document.createElement("div");
  bubble.classList.add("bubble");
  bubble.textContent = text;

  msgDiv.appendChild(bubble);
  chatBox.appendChild(msgDiv);
  chatBox.scrollTop = chatBox.scrollHeight;
}

// ---------------- Handle server actions ---------------- //
function handleAction(action) {
  if (!action || !action.type) return;

  switch (action.type) {
    case "open_url": {
      const url = action.url;
      if (url) {
        window.open(url, "_blank");
      }
      break;
    }

    case "search_youtube": {
      const query = action.query || "";
      const url =
        "https://www.youtube.com/results?search_query=" +
        encodeURIComponent(query);
      window.open(url, "_blank");
      break;
    }

    case "set_reminder": {
      const minutes = action.delay_minutes || 0;
      const text = action.text || "Reminder";

      // Add to visible list
      const li = document.createElement("li");
      li.textContent = `${text} — in ${minutes} minute(s)`;
      remindersList.appendChild(li);

      const delayMs = minutes * 60 * 1000;

      // Schedule browser alert (works while tab is open)
      setTimeout(() => {
        alert("⏰ Reminder: " + text);
        li.textContent = `✅ ${text} — done`;
      }, delayMs);
      break;
    }

    default:
      console.warn("Unknown action type:", action.type);
  }
}

// ---------------- Send message to backend ---------------- //
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  appendMessage("user", text);
  userInput.value = "";

  setLoading(true);
  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: text }),
    });

    // If server returned a non-JSON or error status, handle gracefully
    if (!res.ok) {
      const txt = await res.text();
      console.error('Server error:', res.status, txt);
      appendMessage(
        "assistant",
        "Sorry, server returned an error. Try again later."
      );
      return;
    }

    const data = await res.json();
    const reply = data.reply || "Sorry, I got no reply.";

    appendMessage("assistant", reply);
    speakText(reply);

    // Handle optional action (open URL, reminder, play, etc.)
    if (data.action) {
      handleAction(data.action);
    }
  } catch (err) {
    console.error(err);
    appendMessage(
      "assistant",
      "Oops, something went wrong with the server request. Please check your connection or try again."
    );
  } finally {
    setLoading(false);
  }
}


// ---------------- Loading state helpers ---------------- //
function setLoading(isLoading) {
  if (!sendBtn) return;
  if (isLoading) {
    sendBtn.disabled = true;
    micBtn.disabled = true;
    sendBtn.classList.add('loading');
  } else {
    sendBtn.disabled = false;
    micBtn.disabled = false;
    sendBtn.classList.remove('loading');
  }
}

// Send on button click
sendBtn.addEventListener("click", sendMessage);

// Send on Enter key
userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    sendMessage();
  }
});

// ---------------- Voice Input (Web Speech API) ---------------- //
let recognition;
let listening = false;

if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = "en-IN"; // you can change language
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => {
    listening = true;
    micBtn.classList.add("active");
    micBtn.textContent = "🎙";
  };

  recognition.onend = () => {
    listening = false;
    micBtn.classList.remove("active");
    micBtn.textContent = "🎙";
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    userInput.value = transcript;
    sendMessage();
  };

  recognition.onerror = (event) => {
    console.error("Speech recognition error:", event.error);
    appendMessage(
      "assistant",
      "I couldn’t hear you properly. Please try again or type your message."
    );
  };
} else {
  micBtn.disabled = true;
  micBtn.title = "Speech recognition not supported in this browser.";
}

micBtn.addEventListener("click", () => {
  if (!recognition) return;
  if (listening) {
    recognition.stop();
  } else {
    recognition.start();
  }
});

// ---------------- Voice Output (Speech Synthesis) ---------------- //
function speakText(text) {
  if (!("speechSynthesis" in window)) {
    return; // Not supported
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-IN"; // change if you want
  window.speechSynthesis.speak(utterance);
}

// Greet on load
window.addEventListener("DOMContentLoaded", () => {
  appendMessage(
    "assistant",
    "Hello, I’m Mini Alexa 🤖 powered by Gemini. Ask me anything or say a command like: ‘Open YouTube’, ‘Play lofi beats on YouTube’, or ‘Remind me in 15 minutes to revise GATE notes’."
  );
});
