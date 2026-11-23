const fileList = document.querySelector("#fileList");
const fileSearch = document.querySelector("#fileSearch");
const messages = document.querySelector("#messages");
const prompt = document.querySelector("#prompt");
const chatForm = document.querySelector("#chatForm");
const sendButton = document.querySelector("#sendButton");
const selectedCount = document.querySelector("#selectedCount");
const contextChips = document.querySelector("#contextChips");
const previewTitle = document.querySelector("#previewTitle");
const filePreview = document.querySelector("#filePreview");
const connectionStatus = document.querySelector("#connectionStatus");

let history = [];
let allFiles = [];
let busy = false;

function headers() {
  return { "Content-Type": "application/json" };
}

async function responseError(response, fallback) {
  const text = await response.text();
  if (!text) return fallback;
  try {
    const body = JSON.parse(text);
    return body.detail || fallback;
  } catch {
    return text.length > 300 ? fallback : text;
  }
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value;
  return node.innerHTML;
}

function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/gi, '<pre><code>$2</code></pre>');
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\n/g, "<br>");
  return html;
}

function toast(message, isError = false) {
  const element = document.createElement("div");
  element.className = `toast${isError ? " error" : ""}`;
  element.textContent = message;
  document.querySelector("#toastRegion").append(element);
  setTimeout(() => element.remove(), 4500);
}

function setConnection(ok) {
  connectionStatus.classList.toggle("error", !ok);
  connectionStatus.innerHTML = `<i></i> ${ok ? "Verbunden" : "Verbindung prüfen"}`;
}

function selectedFiles() {
  return [...fileList.querySelectorAll("input:checked")].map((input) => input.value);
}

function updateSelection() {
  const selected = selectedFiles();
  selectedCount.textContent = `${selected.length} ${selected.length === 1 ? "Datei" : "Dateien"} ausgewählt`;
  contextChips.innerHTML = selected.slice(0, 8).map((path) =>
    `<button class="context-chip" type="button" data-path="${escapeHtml(path)}">${escapeHtml(path.split("/").pop())}</button>`
  ).join("");
  document.querySelectorAll(".file-row").forEach((row) => {
    row.classList.toggle("selected", row.querySelector("input").checked);
  });
}

async function loadFiles() {
  try {
    const response = await fetch("/context/files", { headers: headers() });
    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.detail || "Dateien konnten nicht geladen werden");
    }
    allFiles = (await response.json()).files;
    renderFiles();
    setConnection(true);
  } catch (error) {
    setConnection(false);
    toast(error.message, true);
  }
}

function renderFiles() {
  const query = fileSearch.value.trim().toLowerCase();
  const filtered = allFiles.filter((path) => path.toLowerCase().includes(query));
  fileList.innerHTML = filtered.map((path) => {
    const extension = path.includes(".") ? path.split(".").pop().slice(0, 4).toUpperCase() : "FILE";
    return `<label class="file-row" title="${escapeHtml(path)}">
      <input type="checkbox" value="${escapeHtml(path)}" />
      <span class="file-name">${escapeHtml(path)}</span>
      <span class="file-type">${escapeHtml(extension)}</span>
    </label>`;
  }).join("");
  fileList.querySelectorAll(".file-row").forEach((row) => {
    const input = row.querySelector("input");
    input.addEventListener("change", updateSelection);
    row.addEventListener("click", (event) => {
      if (event.target !== input) previewFile(input.value);
    });
  });
  updateSelection();
}

async function previewFile(path) {
  previewTitle.textContent = path;
  filePreview.innerHTML = "<code>Vorschau wird geladen...</code>";
  try {
    const response = await fetch("/context/read", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ paths: [path] }),
    });
    if (!response.ok) {
      throw new Error(await responseError(response, "Vorschau fehlgeschlagen"));
    }
    const data = await response.json();
    filePreview.innerHTML = `<code>${escapeHtml(data.files[0].content)}</code>`;
  } catch (error) {
    filePreview.innerHTML = `<code>${escapeHtml(error.message)}</code>`;
  }
}

function addMessage(role, content = "") {
  const empty = messages.querySelector(".empty-state");
  if (empty) empty.remove();
  const element = document.createElement("article");
  element.className = `message ${role}`;
  element.innerHTML = `
    <div class="avatar">${role === "user" ? "DU" : "AI"}</div>
    <div class="message-body">${role === "user" ? escapeHtml(content) : renderMarkdown(content)}</div>
  `;
  messages.append(element);
  messages.scrollTop = messages.scrollHeight;
  return element.querySelector(".message-body");
}

function showEmptyState() {
  messages.innerHTML = `<div class="empty-state"><div><div class="empty-icon">&lt;/&gt;</div><h2>Woran arbeiten wir heute?</h2><p>Wähle Projektdateien als Kontext aus und beschreibe eine Aufgabe, ein Problem oder eine Änderung.</p></div></div>`;
}

async function sendMessage(event) {
  event.preventDefault();
  if (busy) return;
  const text = prompt.value.trim();
  if (!text) return;

  addMessage("user", text);
  history.push({ role: "user", content: text });
  prompt.value = "";
  resizePrompt();
  busy = true;
  sendButton.disabled = true;
  const assistantBody = addMessage("assistant", "");
  assistantBody.innerHTML = '<span class="cursor"></span>';

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ messages: history, project_files: selectedFiles(), temperature: 0.2 }),
    });
    if (!response.ok) {
      throw new Error(await responseError(response, "Die Anfrage ist fehlgeschlagen"));
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let answer = "";
    let buffered = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffered += decoder.decode(value, { stream: true });
      const lines = buffered.split("\n");
      buffered = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6).trim();
        if (data === "[DONE]") continue;
        try {
          answer += JSON.parse(data).delta || "";
        } catch {}
        assistantBody.innerHTML = `${renderMarkdown(answer)}<span class="cursor"></span>`;
        messages.scrollTop = messages.scrollHeight;
      }
    }
    assistantBody.innerHTML = renderMarkdown(answer);
    history.push({ role: "assistant", content: answer });
    setConnection(true);
  } catch (error) {
    assistantBody.textContent = `Fehler: ${error.message}`;
    setConnection(false);
  } finally {
    busy = false;
    sendButton.disabled = false;
  }
}

function resizePrompt() {
  prompt.style.height = "auto";
  prompt.style.height = `${Math.min(prompt.scrollHeight, 160)}px`;
}

document.querySelector("#refreshFiles").addEventListener("click", loadFiles);
document.querySelector("#clearChat").addEventListener("click", () => { history = []; showEmptyState(); });
document.querySelector("#closePreview").addEventListener("click", () => {
  previewTitle.textContent = "Keine Vorschau";
  filePreview.innerHTML = "<code>Wähle eine Projektdatei aus.</code>";
});
fileSearch.addEventListener("input", renderFiles);
prompt.addEventListener("input", resizePrompt);
prompt.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    chatForm.requestSubmit();
  }
});
chatForm.addEventListener("submit", sendMessage);

showEmptyState();
loadFiles();
