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

function addMessage(role, text, results = []) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  if (results.length > 0) {
    const resultList = document.createElement("div");
    resultList.className = "results";

    results.slice(0, 5).forEach((result) => {
      const item = document.createElement("div");
      item.className = "result";
      item.tabIndex = 0;
      item.dataset.eventId = result.id || "";

      const title = document.createElement("strong");
      title.textContent = result.event_name || "Untitled event";

      const meta = document.createElement("span");
      meta.textContent = [result.event_date, result.event_address, result.category].filter(Boolean).join(" · ");

      item.append(title, meta);
      item.addEventListener("click", () => recordInteraction(result.id));
      resultList.appendChild(item);
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

async function recordInteraction(eventId) {
  if (!eventId) return;
  await fetch("/eventService/events/interactions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: getUserId(),
      event_id: eventId,
      interaction_type: "click",
      query: lastQuery,
    }),
  });
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
    addMessage("assistant", data.answer || "I could not find an answer.", data.results || []);
  } catch (error) {
    addMessage("assistant", "Something went wrong while searching. Please try again.");
  } finally {
    submitButton.disabled = false;
    input.focus();
  }
});
