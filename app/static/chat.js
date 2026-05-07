const form = document.querySelector("#chat-form");
const appShell = document.querySelector("#app-shell");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const submitButton = form.querySelector("button");
const authPanel = document.querySelector("#auth-panel");
const authForm = document.querySelector("#auth-form");
const authStatus = document.querySelector("#auth-status");
const authUsername = document.querySelector("#auth-username");
const authPassword = document.querySelector("#auth-password");
const registerButton = document.querySelector("#register-button");
const modeSlider = document.querySelector("#mode-slider");
const modeCheckbox = document.querySelector("#mode-checkbox");
const userChip = document.querySelector("#user-chip");
const logoutButton = document.querySelector("#logout-button");
const USER_ID_KEY = "getahint_user_id";
const AUTH_TOKEN_KEY = "getahint_auth_token";
const AUTH_USERNAME_KEY = "getahint_auth_username";
let lastQuery = "";
let activeMode = localStorage.getItem(AUTH_TOKEN_KEY) ? "user" : "guest";

function getUserId() {
  const username = activeMode === "user" ? localStorage.getItem(AUTH_USERNAME_KEY) : null;
  if (username) return `account-${username}`;

  let userId = localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    userId = `web-${crypto.randomUUID()}`;
    localStorage.setItem(USER_ID_KEY, userId);
  }
  return userId;
}

function getAuthToken() {
  return activeMode === "user" ? localStorage.getItem(AUTH_TOKEN_KEY) : null;
}

function authHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function updateAuthUi() {
  const username = localStorage.getItem(AUTH_USERNAME_KEY);
  const isUserMode = activeMode === "user";

  appShell.classList.toggle("guest-mode", !isUserMode);
  appShell.classList.toggle("user-mode", isUserMode);
  modeCheckbox.checked = isUserMode;

  if (isUserMode && username) {
    authStatus.textContent = username;
    authPanel.classList.add("signed-in");
    modeSlider.classList.add("d-none");
    userChip.classList.remove("d-none");
  } else if (isUserMode) {
    authPanel.classList.remove("signed-in");
    modeSlider.classList.remove("d-none");
    userChip.classList.add("d-none");
  } else {
    authPanel.classList.remove("signed-in");
    modeSlider.classList.remove("d-none");
    userChip.classList.add("d-none");
  }
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
      note.className = "personalization-note badge rounded-pill text-bg-success-subtle";
      note.textContent = "Personalized using your previous event picks.";
      resultList.appendChild(note);
    }

    results.slice(0, 5).forEach((result) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "result card";
      item.dataset.eventId = result.id || "";
      item.setAttribute("aria-expanded", "false");
      item.setAttribute("aria-label", `Show details for ${result.event_name || "this event"}`);

      const body = document.createElement("span");
      body.className = "card-body";

      const topLine = document.createElement("span");
      topLine.className = "result-topline";

      const title = document.createElement("strong");
      title.className = "result-title";
      title.textContent = result.event_name || "Untitled event";

      const category = document.createElement("span");
      category.className = "result-category badge rounded-pill";
      category.textContent = result.category || "event";

      const meta = document.createElement("span");
      meta.className = "result-meta";
      meta.textContent = [result.event_date, result.event_address].filter(Boolean).join(" · ");

      const details = document.createElement("p");
      details.className = "result-details";
      details.textContent = result.event_description || "No additional details available.";

      const action = document.createElement("span");
      action.className = "result-action";
      action.textContent = "Show details";

      topLine.append(title, category);
      body.append(topLine, meta, details, action);
      item.append(body);
      item.addEventListener("click", async () => {
        const isExpanded = item.classList.toggle("expanded");
        item.classList.add("selected");
        item.setAttribute("aria-expanded", String(isExpanded));
        action.textContent = isExpanded ? "Hide details · preference saved" : "Show details";
        await recordInteraction(result.id, "save");
      });
      resultList.appendChild(item);

      recordInteraction(result.id, "view");
    });

    bubble.appendChild(resultList);
  }

  article.appendChild(bubble);
  messages.appendChild(article);
  messages.scrollTop = messages.scrollHeight;
  return article;
}

function removeMessage(article) {
  if (article && article.parentNode) {
    article.parentNode.removeChild(article);
  }
}

function addThinkingMessage() {
  const article = addMessage("assistant", "Thinking...");
  article.classList.add("thinking");
  return article;
}

async function sendMessage(message) {
  const response = await fetch("/modelService/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
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
      headers: { "Content-Type": "application/json", ...authHeaders() },
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

async function authenticate(mode) {
  const username = authUsername.value.trim();
  const password = authPassword.value;
  if (!username || !password) {
    addMessage("assistant", "Enter a username and password first.");
    return;
  }

  const response = await fetch(`/auth/${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  const payload = await response.json();
  if (!response.ok) {
    addMessage("assistant", payload.detail || "Authentication failed.");
    return;
  }

  localStorage.setItem(AUTH_TOKEN_KEY, payload.token);
  localStorage.setItem(AUTH_USERNAME_KEY, payload.username);
  activeMode = "user";
  authPassword.value = "";
  updateAuthUi();
  addMessage("assistant", `Signed in as ${payload.username}. I will use your event picks for personalization.`);
}

async function logout() {
  await fetch("/auth/logout", { method: "POST", headers: authHeaders() });
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USERNAME_KEY);
  activeMode = "guest";
  updateAuthUi();
  addMessage("assistant", "Signed out. I will use this browser's guest preferences now.");
}

function setMode(mode) {
  activeMode = mode;
  updateAuthUi();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = input.value.trim();
  if (!message) return;

  addMessage("user", message);
  lastQuery = message;
  input.value = "";
  submitButton.disabled = true;
  const thinkingMessage = addThinkingMessage();

  try {
    const data = await sendMessage(message);
    removeMessage(thinkingMessage);
    addMessage("assistant", data.answer || "I could not find an answer.", data.results || [], {
      personalized: Boolean(data.personalized),
    });
  } catch (error) {
    removeMessage(thinkingMessage);
    addMessage("assistant", "Something went wrong while searching. Please try again.");
  } finally {
    submitButton.disabled = false;
    input.focus();
  }
});

modeCheckbox.addEventListener("change", () => {
  setMode(modeCheckbox.checked ? "user" : "guest");
  if (modeCheckbox.checked) {
    authUsername.focus();
  }
});

logoutButton.addEventListener("click", logout);

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await authenticate("login");
});

registerButton.addEventListener("click", async () => {
  await authenticate("register");
});

updateAuthUi();
