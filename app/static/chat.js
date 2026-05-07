const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const submitButton = form.querySelector("button");
const USER_ID_KEY = "getahint_user_id";
let lastQuery = "";

function getUserId() {
  let userId = localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    userId = `web-${crypto.randomUUID()}`;
    localStorage.setItem(USER_ID_KEY, userId);
  }
  return userId;
}

function addMessage(role, text, results = [], meta = {}) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  if (results.length > 0) {
    const resultList = document.createElement("div");
    resultList.className = "results";

    if (meta.personalized) {
      const note = document.createElement("p");
      note.className = "personalization-note";
      note.textContent = "Personalized using your previous event picks.";
      resultList.appendChild(note);
    }

    results.slice(0, 5).forEach((result) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "result";
      item.dataset.eventId = result.id || "";
      item.setAttribute("aria-label", `More like ${result.event_name || "this event"}`);

      const title = document.createElement("strong");
      title.textContent = result.event_name || "Untitled event";

      const meta = document.createElement("span");
      meta.textContent = [result.event_date, result.event_address, result.category].filter(Boolean).join(" · ");

      const action = document.createElement("span");
      action.className = "result-action";
      action.textContent = "More like this";

      item.append(title, meta, action);
      item.addEventListener("click", async () => {
        await recordInteraction(result.id, "save");
        item.classList.add("selected");
        action.textContent = "Preference saved";
      });
      resultList.appendChild(item);

      recordInteraction(result.id, "view");
    });

    bubble.appendChild(resultList);
  }

  article.appendChild(bubble);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(message) {
  const response = await fetch("/modelService/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, user_id: getUserId() }),
  });

  if (!response.ok) {
    throw new Error("Chat request failed");
  }

  return response.json();
}

async function recordInteraction(eventId, interactionType = "click") {
  if (!eventId) return;
  try {
    await fetch("/eventService/events/interactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: getUserId(),
        event_id: eventId,
        interaction_type: interactionType,
        query: lastQuery,
      }),
    });
  } catch (error) {
    console.warn("Could not record event preference", error);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = input.value.trim();
  if (!message) return;

  addMessage("user", message);
  lastQuery = message;
  input.value = "";
  submitButton.disabled = true;

  try {
    const data = await sendMessage(message);
    addMessage("assistant", data.answer || "I could not find an answer.", data.results || [], {
      personalized: Boolean(data.personalized),
    });
  } catch (error) {
    addMessage("assistant", "Something went wrong while searching. Please try again.");
  } finally {
    submitButton.disabled = false;
    input.focus();
  }
});
