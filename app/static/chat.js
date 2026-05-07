const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const submitButton = form.querySelector("button");
const authForm = document.querySelector("#auth-form");
const authToggle = document.querySelector("#auth-toggle");
const authStatus = document.querySelector("#auth-status");
const authUsername = document.querySelector("#auth-username");
const authPassword = document.querySelector("#auth-password");
const registerButton = document.querySelector("#register-button");
const USER_ID_KEY = "getahint_user_id";
const AUTH_TOKEN_KEY = "getahint_auth_token";
const AUTH_USERNAME_KEY = "getahint_auth_username";
let lastQuery = "";

function getUserId() {
  const username = localStorage.getItem(AUTH_USERNAME_KEY);
  if (username) return `account-${username}`;

  let userId = localStorage.getItem(USER_ID_KEY);
  if (!userId) {
    userId = `web-${crypto.randomUUID()}`;
    localStorage.setItem(USER_ID_KEY, userId);
  }
  return userId;
}

function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function authHeaders() {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function updateAuthUi() {
  const username = localStorage.getItem(AUTH_USERNAME_KEY);
  if (username) {
    authStatus.textContent = `Signed in as ${username}`;
    authToggle.textContent = "Logout";
    authForm.classList.add("hidden");
  } else {
    authStatus.textContent = "Guest mode";
    authToggle.textContent = "Login";
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
  authPassword.value = "";
  updateAuthUi();
  addMessage("assistant", `Signed in as ${payload.username}. I will use your event picks for personalization.`);
}

async function logout() {
  await fetch("/auth/logout", { method: "POST", headers: authHeaders() });
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USERNAME_KEY);
  updateAuthUi();
  addMessage("assistant", "Signed out. I will use this browser's guest preferences now.");
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

authToggle.addEventListener("click", async () => {
  if (getAuthToken()) {
    await logout();
  } else {
    authForm.classList.toggle("hidden");
    authUsername.focus();
  }
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await authenticate("login");
});

registerButton.addEventListener("click", async () => {
  await authenticate("register");
});

updateAuthUi();
