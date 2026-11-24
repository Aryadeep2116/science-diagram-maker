// static/app.js
// Draws the table, saves review decisions in localStorage, and runs Generate.

const CHECKS = [
  ["valid_xml", "Valid XML"],
  ["in_viewbox", "Inside viewBox"],
  ["title_and_labels", "Title + 3 labels"],
  ["has_animation", "Animation"],
  ["custom_checks", "Keywords + safe (mine)"],
];

let results = JSON.parse(document.getElementById("data").textContent);
const rowsEl = document.getElementById("rows");
const messageEl = document.getElementById("message");

// Escape text before putting it in HTML.
function esc(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML;
}

// Show the SVG inside <img> with a data URI: scripts can never run in an <img>.
function svgSrc(svg) {
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

// localStorage helpers (wrapped in try/catch because storage can be blocked).
function loadReview(id) {
  try { return JSON.parse(localStorage.getItem("review:" + id)) || {}; }
  catch (e) { return {}; }
}
function saveReview(id, review) {
  try { localStorage.setItem("review:" + id, JSON.stringify(review)); }
  catch (e) { showMessage("Could not save your decision in this browser."); }
}

function showMessage(text) {
  messageEl.textContent = text;
  messageEl.hidden = !text;
}

function buildRow(r) {
  const review = loadReview(r.id);
  const tr = document.createElement("tr");
  tr.dataset.id = r.id;

  const badges = CHECKS.map(([key, label]) => {
    const c = r.checks[key] || { passed: false, reason: "No data" };
    return `<span class="badge ${c.passed ? "pass" : "fail"}">${c.passed ? "PASS" : "FAIL"}: ${esc(label)}</span>` +
           `<div class="reason">${esc(c.reason)}</div>`;
  }).join("");

  tr.innerHTML = `
    <td><b>${esc(r.name)}</b><br>${esc(r.subject)}<br><b>${esc(r.final_status.toUpperCase())}</b></td>
    <td>${r.svg ? `<img class="diagram" alt="${esc(r.name)} diagram" src="${svgSrc(r.svg)}">` : "No SVG produced"}</td>
    <td>${badges}</td>
    <td class="small">
      Cost: $${r.cost_usd}<br>
      Validation retries: ${r.validation_retries}<br>
      API retries: ${r.api_retries}<br>
      Tokens: ${r.input_tokens} in / ${r.output_tokens} out<br>
      Time: ${r.latency_seconds}s<br>Model: ${esc(r.model)}
      ${r.note ? "<br>Note: " + esc(r.note) : ""}
    </td>
    <td>
      <button class="approve ${review.decision === "approved" ? "on" : ""}">Approve</button>
      <button class="reject ${review.decision === "rejected" ? "on" : ""}">Reject</button>
      <div class="small">Status: <b>${review.decision || "not reviewed"}</b></div>
      <textarea placeholder="Reviewer note">${esc(review.note || "")}</textarea>
      <button class="generate">Generate (live)</button>
    </td>`;

  const approveBtn = tr.querySelector(".approve");
  const rejectBtn = tr.querySelector(".reject");
  const note = tr.querySelector("textarea");

  approveBtn.onclick = () => setDecision(r, tr, "approved");
  rejectBtn.onclick = () => setDecision(r, tr, "rejected");
  note.oninput = () => {                       // save the note as the reviewer types
    const current = loadReview(r.id);
    current.note = note.value;
    saveReview(r.id, current);
  };
  tr.querySelector(".generate").onclick = (event) => generate(r.id, event.target, tr);
  return tr;
}

function setDecision(r, tr, decision) {
  const review = loadReview(r.id);
  review.decision = decision;
  review.note = tr.querySelector("textarea").value;   // keep whatever is typed
  saveReview(r.id, review);
  tr.replaceWith(buildRow(r));                         // redraw so the buttons update
}

async function generate(id, button, tr) {
  showMessage("");
  button.disabled = true;
  button.textContent = "Generating... (can take up to a minute)";
  try {
    const response = await fetch("/api/generate/" + id, { method: "POST" });
    let data = null;
    try { data = await response.json(); } catch (e) { /* not JSON (e.g. server timeout) */ }
    if (!response.ok || !data || data.error) {
      throw new Error((data && data.error) || "The server did not answer properly (it may have timed out). Please try again.");
    }
    const index = results.findIndex((x) => x.id === id);
    results[index] = data;                              // browser only: results.json is NOT changed
    tr.replaceWith(buildRow(data));
  } catch (error) {
    showMessage("Generate failed for concept " + id + ": " + error.message);
    button.disabled = false;
    button.textContent = "Generate (live)";
  }
}

results.forEach((r) => rowsEl.appendChild(buildRow(r)));
if (results.length === 0) showMessage("No saved results found. Run python generate_all.py first.");


