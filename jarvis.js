let recognition = null;
let listening = false;
let voiceSubmitted = false;
let requestSerial = 0;
let activeRequest = 0;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

function setVoiceState(text, active = false) {
  const el = document.getElementById("voiceStatus");
  if (el) el.textContent = text;
  document.getElementById("reactor")?.classList.toggle("listening", active);
}

function toggleVoice() {
  if (!SpeechRecognition) {
    setVoiceState("VOICE UNAVAILABLE · Use Chrome/Edge with microphone permission");
    return;
  }

  if (listening) {
    recognition.stop();
    return;
  }

  const input = document.getElementById("query");
  input.value = "";
  voiceSubmitted = false;

  recognition = new SpeechRecognition();
  recognition.lang = "en-IN";
  recognition.interimResults = true;
  recognition.continuous = false;

  recognition.onstart = () => {
    listening = true;
    document.getElementById("mic").textContent = "⏹ STOP";
    setVoiceState("LISTENING · Speak to JARVIS...", true);
  };

  recognition.onresult = (e) => {
    let finalText = "";
    for (const result of e.results) {
      finalText += result[0].transcript;
    }
    input.value = finalText.trim();
  };

  recognition.onerror = (e) => {
    listening = false;
    voiceSubmitted = true;
    document.getElementById("mic").textContent = "🎙 MIC";
    setVoiceState("VOICE ERROR · " + e.error, false);
  };

  recognition.onend = () => {
    listening = false;
    document.getElementById("mic").textContent = "🎙 MIC";

    // Submit exactly once. This prevents a voice query from being sent again
    // if the browser fires multiple recognition lifecycle events.
    const text = input.value.trim();
    if (text && !voiceSubmitted) {
      voiceSubmitted = true;
      askJarvis(text, true);
    } else {
      setVoiceState("VOICE LINK READY · Click MIC to speak", false);
    }
  };

  recognition.start();
}

async function askJarvis(forcedQuery = null, fromVoice = false) {
  const input = document.getElementById("query");
  const box = document.getElementById("answer");
  const q = (forcedQuery ?? input.value).trim();
  if (!q) return;

  // Give this submission a unique request number. A stale response from an
  // earlier request can no longer overwrite the current question's answer.
  const thisRequest = ++requestSerial;
  activeRequest = thisRequest;

  box.classList.remove("hidden");
  box.innerHTML = '<span class="eyebrow">JARVIS PROCESSING...</span>';
  setVoiceState("PROCESSING QUERY...", true);

  // Clear the input after capturing the query so an old question cannot be
  // accidentally resubmitted by a later Enter/microphone event.
  input.value = "";

  try {
    const r = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q })
    });

    if (!r.ok) throw new Error("Request failed");
    const d = await r.json();

    // Ignore a response that belongs to an older request.
    if (thisRequest !== activeRequest) return;

    const answer = d.answer || "I couldn't produce an answer for that query.";
    box.innerHTML = '<span class="eyebrow">JARVIS RESPONSE</span><p>' +
      escapeHtml(answer).replace(/\n/g, "<br>") + "</p>";
    setVoiceState("RESPONSE READY · Voice output active", false);

    if ("speechSynthesis" in window) {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(answer);
      u.rate = .92;
      u.pitch = .92;
      u.lang = "en-IN";
      speechSynthesis.speak(u);
    }
  } catch (err) {
    if (thisRequest !== activeRequest) return;
    box.innerHTML = '<span class="eyebrow">JARVIS ERROR</span><p>Connection to the knowledge core failed. Please try again.</p>';
    setVoiceState("CONNECTION ERROR · Try again", false);
    console.error(err);
  }
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && document.activeElement?.id === "query") {
    e.preventDefault();
    // Manual text submission is independent of the previous voice request.
    voiceSubmitted = true;
    askJarvis();
  }
});

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, m => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[m]));
}

async function review(id, action) {
  await fetch("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ flashcard_id: id, action })
  });
  alert(action === "known" ? "Review logged." : "Marked for review again.");
}

async function addKnowledge() {
  const payload = {
    chapter: chapter.value,
    title: title.value,
    keywords: keywords.value,
    content: content.value
  };
  const r = await fetch("/api/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const d = await r.json();
  addmsg.textContent = d.message || d.error;
  if (d.ok) setTimeout(() => location.reload(), 700);
}

async function generateCards(id) {
  const r = await fetch("/api/generate/" + id, { method: "POST" });
  const d = await r.json();
  alert(d.message);
  location.href = "/flashcards";
}
