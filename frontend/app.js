const apiBase = "http://127.0.0.1:8000";

const modeRadios = document.querySelectorAll('input[name="mode"]');
const textInputs = document.getElementById("text-inputs");
const urlInputs  = document.getElementById("url-inputs");
const fileInputs = document.getElementById("file-inputs");

const textEl = document.getElementById("text");
const urlEl  = document.getElementById("url");
const fileEl = document.getElementById("file");

const modelEl = document.getElementById("model");
const maxWordsEl = document.getElementById("max_words");
const wpmEl = document.getElementById("speaking_wpm");
const tsEl = document.getElementById("include_timestamps");

const btn = document.getElementById("generateBtn");
const statusEl = document.getElementById("status");

const resultSec = document.getElementById("result");
const rTitle = document.getElementById("r-title");
const rIntro = document.getElementById("r-intro");
const rSegs = document.getElementById("r-segments");
const rOutro = document.getElementById("r-outro");
const rNotes = document.getElementById("r-notes");

modeRadios.forEach(r => r.addEventListener("change", () => {
  const v = document.querySelector('input[name="mode"]:checked').value;
  textInputs.classList.toggle("hidden", v !== "text");
  urlInputs.classList.toggle("hidden",  v !== "url");
  fileInputs.classList.toggle("hidden", v !== "file");
}));

function renderResult(data) {
  resultSec.classList.remove("hidden");
  rTitle.textContent = data.title || "Podcast Episode";
  rIntro.textContent = data.intro || "";

  rSegs.innerHTML = "";
  (data.segments || []).forEach(seg => {
    const div = document.createElement("div");
    div.className = "seg";
    div.innerHTML = `<h4>${seg.heading || "Segment"}</h4><p>${seg.content || ""}</p>`;
    rSegs.appendChild(div);
  });

  rOutro.textContent = data.outro || "";

  rNotes.innerHTML = "";
  (data.show_notes || []).forEach(n => {
    const li = document.createElement("li");
    const time = n.time ? `<span class="t">${n.time}</span>` : "";
    li.innerHTML = `${time}<span>${n.note}</span>`;
    rNotes.appendChild(li);
  });
}

async function callJson(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || res.statusText);
  }
  return res.json();
}

async function callForm(url, formData) {
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) {
    const msg = await res.text();
    throw new Error(msg || res.statusText);
  }
  return res.json();
}

btn.addEventListener("click", async () => {
  resultSec.classList.add("hidden");
  statusEl.textContent = "Generating…";
  btn.disabled = true;

  const mode = document.querySelector('input[name="mode"]:checked').value;
  const model = modelEl.value;
  const max_words = Number(maxWordsEl.value || 1200);
  const speaking_wpm = Number(wpmEl.value || 150);
  const include_timestamps = tsEl.checked;

  try {
    let data;
    if (mode === "text") {
      const text = (textEl.value || "").trim();
      if (!text) throw new Error("Please paste some text.");
      data = await callJson(`${apiBase}/generate`, { text, model, max_words, speaking_wpm, include_timestamps });
    } else if (mode === "url") {
      const url = (urlEl.value || "").trim();
      if (!url) throw new Error("Please enter a URL.");
      data = await callJson(`${apiBase}/generate`, { url, model, max_words, speaking_wpm, include_timestamps });
    } else {
      const f = fileEl.files[0];
      if (!f) throw new Error("Please select a .txt or .pdf file.");
      const fd = new FormData();
      fd.append("file", f);
      fd.append("model", model);
      fd.append("max_words", String(max_words));
      fd.append("speaking_wpm", String(speaking_wpm));
      fd.append("include_timestamps", String(include_timestamps));
      data = await callForm(`${apiBase}/generate/file`, fd);
    }
    renderResult(data);
    statusEl.textContent = "Done.";
  } catch (err) {
    console.error(err);
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
});