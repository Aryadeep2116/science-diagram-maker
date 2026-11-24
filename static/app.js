// static/app.js
// Draws the library, saves review decisions in localStorage, and runs Generate.

const CHECKS = [
  ["valid_xml", "Valid XML"],
  ["in_viewbox", "Static viewBox bounds"],
  ["animated_bounds", "Animated bounds"],
  ["title_and_labels", "Title + 3 labels"],
  ["has_animation", "Animation"],
  ["custom_checks", "Keywords + safe (mine)"],
];

const savedResults = JSON.parse(document.getElementById("data").textContent);
// A generated result is saved only in this browser, never on the server.
const liveIds = new Set();
let results = savedResults.map(saved => {
  try {
    const live = JSON.parse(localStorage.getItem("live-result:" + saved.id));
    if (live && live.id === saved.id && typeof live.svg === "string" && live.checks && live.final_status) {
      liveIds.add(saved.id);
      return { ...live,
        checks: Object.fromEntries(CHECKS.map(([key]) => [key, {passed: null, reason: "Rechecking browser-saved SVG…"}])),
        final_status: "needs_review",
        scientific_verification: {status: "unverified", reason: "Scientific review required for this SVG."},
      };
    }
  } catch (e) { /* Storage may be unavailable or corrupted. */ }
  return saved;
});
const rowsEl = document.getElementById("rows");
const messageEl = document.getElementById("message");
const issuesEl = document.getElementById("issues");
const generationErrors = new Map();

// Configuration status does not make a Gemini request or guarantee quota.
async function refreshStatus() {
  const target = document.getElementById("connection-status");
  target.textContent = "Checking server configuration…";
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error();
    const status = await response.json();
    const key = status.key_configured ? "API key configured" : "API key missing on server";
    const fallback = status.fallback_model ? ` · Fallback: ${status.fallback_model}` : " · No fallback configured";
    const worker = status.busy ? " · Generation in progress" : status.cooldown_seconds ? ` · Cooldown: ${status.cooldown_seconds}s` : "";
    target.textContent = `${key} · Primary: ${status.primary_model}${fallback}${worker}. Gemini quota has not been checked.`;
  } catch (error) {
    target.textContent = "Could not check server status. Try refreshing or check your connection.";
  }
}
document.getElementById("refresh-status").onclick = refreshStatus;
refreshStatus();

// Escape text before putting it in HTML.
function esc(text) {
  const div = document.createElement("div");
  div.textContent = text == null ? "" : String(text);
  return div.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// Show the SVG inside <img> with a data URI: scripts can never run in an <img>.
function svgSrc(svg) {
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

// localStorage helpers (wrapped in try/catch because storage can be blocked).
function loadReview(result) {
  try {
    const review = JSON.parse(localStorage.getItem("review:" + result.id)) || {};
    return review.svg === result.svg ? review : {};
  }
  catch (e) { return {}; }
}
function saveReview(result, review) {
  try { localStorage.setItem("review:" + result.id, JSON.stringify({ ...review, svg: result.svg })); return true; }
  catch (e) { showMessage("Could not save your decision in this browser."); return false; }
}
function saveLiveResult(result) {
  liveIds.add(result.id); // still allow restoring the saved diagram if storage is unavailable
  try { localStorage.setItem("live-result:" + result.id, JSON.stringify(result)); return true; }
  catch (e) { showMessage("The live result could not be saved in this browser; it will be lost on refresh."); return false; }
}
function displayResult(result) { return withBrowserReview(result, loadReview(result)); }

function showMessage(text) {
  messageEl.textContent = text;
  messageEl.hidden = !text;
}

// Display actual failures separately from diagrams awaiting scientific review.
function renderIssues() {
  issuesEl.replaceChildren();
  let affected = 0;
  let pending = 0;
  for (const rawResult of results) {
    const result = displayResult(rawResult);
    const issues = collectIssues(result, CHECKS, generationErrors.get(result.id));
    if (!result.scientific_verification || result.scientific_verification.status === "unverified" || Object.values(result.checks || {}).some(check => check.passed === null)) pending++;
    if (!issues.length) continue;
    affected++;
    const group = document.createElement("div");
    group.className = "issue-group";
    const link = document.createElement("a");
    link.href = "#diagram-" + result.id;
    link.textContent = result.name;
    group.appendChild(link);
    const list = document.createElement("ul");
    for (const issue of issues) {
      const item = document.createElement("li");
      item.textContent = `${issue.category} — ${issue.label}: ${issue.reason}`;
      list.appendChild(item);
    }
    group.appendChild(list);
    issuesEl.appendChild(group);
  }
  const summary = document.createElement("p");
  summary.className = "issues-summary";
  summary.textContent = !results.length ? "No diagrams available to check." : affected
    ? `${affected} diagram${affected === 1 ? " has" : "s have"} current issues.`
    : "No known issues in the current results.";
  if (pending) summary.textContent += ` ${pending} diagram${pending === 1 ? " is" : "s are"} awaiting verification.`;
  issuesEl.prepend(summary);
  const stats = document.getElementById("stats");
  const count = status => results.filter(result => displayResult(result).final_status === status).length;
  stats.innerHTML = [
    [results.length, "Diagrams", ""],
    [count("pass"), "Passed", "pass-stat"],
    [count("fail"), "Failed", "fail-stat"],
    [count("needs_review"), "Needs review", "pending-stat"],
  ].map(([value, label, cls]) => `<div class="stat ${cls}"><strong>${value}</strong><span>${label}</span></div>`).join("");
}

function buildRow(raw) {
  const review = loadReview(raw);
  const r = displayResult(raw);
  const card = document.createElement("article");
  card.className = "diagram-card";
  card.dataset.id = r.id;


  const allChecks = r.checks || {};
  const passedChecks = CHECKS.filter(([key]) => allChecks[key] && allChecks[key].passed).length;
  const checks = CHECKS.map(([key, label]) => {
    const c = allChecks[key] || { passed: false, reason: "No data" };
    const skipped = c.passed === false && String(c.reason || "").startsWith("Skipped");
    const unverified = c.passed === null;
    const state = skipped || unverified ? "unverified" : c.passed ? "pass" : "fail";
    const name = skipped ? "SKIPPED" : unverified ? "UNVERIFIED" : c.passed ? "PASS" : "FAIL";
    return `<div class="check-item" data-check="${esc(key)}"><div class="check-top"><span>${esc(label)}</span><span class="status-pill ${state}">${name}</span></div><p class="reason">${esc(c.reason)}</p></div>`;
  }).join("");

  const verification = r.scientific_verification || { status: "unverified", reason: "Scientific review required." };
  const verificationLabel = { pass: "PASS", fail: "FAIL", unverified: "NOT VERIFIED" }[verification.status] || "NOT VERIFIED";
  const verificationClass = verification.status === "pass" ? "pass" : verification.status === "fail" ? "fail" : "unverified";
  const overallClass = r.final_status === "pass" ? "pass" : r.final_status === "fail" ? "fail" : "unverified";
  const overallLabel = {pass: "PASSED", fail: "FAILED", needs_review: "NEEDS REVIEW"}[r.final_status] || "NEEDS REVIEW";
  card.innerHTML = `
    <div class="card-header">
      <div class="card-heading"><span class="card-number">${esc(String(r.id).padStart(2, "0"))}</span><div><h3>${esc(r.name)}</h3><p>${esc(r.subject)} <span aria-hidden="true">·</span> Science concept</p></div></div>
      <span class="status-pill ${overallClass}">${overallLabel}</span>
    </div>
    <div class="card-body">
      <div class="visual-column"><div class="visual-label"><span>DIAGRAM PREVIEW</span><span class="preview-tag">SVG illustration</span></div>
        <div class="diagram-frame">${r.svg ? `<img class="diagram" alt="${esc(r.name)} diagram" src="${svgSrc(r.svg)}">` : "No SVG produced"}</div>
      </div>
      <div class="card-side">
        <div class="verification-box"><div class="verification-top"><span class="panel-label">SCIENTIFIC VERIFICATION</span><span class="status-pill ${verificationClass}">${verificationLabel}</span></div>
          <p class="reason">${esc(verification.reason)}</p>${verification.method ? `<p class="method">Review method: ${esc(verification.method)}</p>` : ""}
        </div>
        <details class="check-details"><summary><span>Automatic checks</span><span class="check-summary-right">${passedChecks} / ${CHECKS.length} passed</span></summary><div class="check-list">${checks}</div></details>
        <div class="review-section"><div class="review-heading"><strong>Your review</strong><span class="review-state">Browser review: ${esc(review.decision || "not reviewed")}${review.reviewedAt ? " · " + esc(review.reviewedAt) : ""}</span></div>
          <div class="review-actions"><button type="button" class="approve ${review.decision === "approved" ? "on" : ""}" aria-pressed="${review.decision === "approved"}">✓ &nbsp;Verify &amp; approve</button><button type="button" class="reject ${review.decision === "rejected" ? "on" : ""}" aria-pressed="${review.decision === "rejected"}">× &nbsp;Verify &amp; reject</button></div>
          <textarea aria-label="Reviewer note for ${esc(r.name)}" placeholder="Add a reviewer note…">${esc(review.note || "")}</textarea>
          <p class="review-note">Explicit scientific review is stored only in this browser for this exact SVG. It cannot override failed or unverified automatic checks.</p>
        </div>
      </div>
    </div>
    <p class="generation-feedback" role="status" aria-live="polite" hidden></p>
    <div class="card-footer"><div class="metrics"><span><strong>${r.cost_usd == null ? "Unavailable" : "$" + esc(r.cost_usd)}</strong> estimated cost</span><span><strong>${esc(r.validation_retries)}</strong> validation retries</span><span><strong>${esc(r.api_retries)}</strong> API retries</span><span><strong>${esc(r.input_tokens)} / ${esc(r.output_tokens)}</strong> tokens in / out</span><span><strong>${esc(r.latency_seconds)}s</strong></span><span>${esc(r.model)}</span>${r.note ? `<br>Note: ${esc(r.note)}` : ""}</div>
      <div class="generation-actions">${liveIds.has(r.id) ? '<button type="button" class="restore-saved">Restore saved diagram</button>' : ''}<button type="button" class="generate">✦ &nbsp;Generate live</button></div></div>`;

  const feedback = card.querySelector(".generation-feedback");
  const previousError = generationErrors.get(r.id);
  if (previousError) {
    feedback.textContent = "Generation failed: " + previousError;
    feedback.hidden = false;
    feedback.classList.add("error");
  }
  const approveBtn = card.querySelector(".approve");
  const rejectBtn = card.querySelector(".reject");
  const note = card.querySelector("textarea");
  approveBtn.onclick = () => setDecision(raw, card.closest("tr"), "approved");
  rejectBtn.onclick = () => setDecision(raw, card.closest("tr"), "rejected");
  note.oninput = () => {
    const current = loadReview(raw);
    current.note = note.value;
    saveReview(raw, current);
  };
  const restore = card.querySelector(".restore-saved");
  if (restore) restore.onclick = () => restoreSaved(raw.id, card.closest("tr"));
  card.querySelector(".generate").onclick = (event) => generate(r.id, event.currentTarget, card.closest("tr"));
  const row = document.createElement("tr");
  row.id = "diagram-" + r.id;
  const cell = document.createElement("td");
  cell.appendChild(card);
  row.appendChild(cell);
  return row;
}

function setDecision(r, tr, decision) {
  const question = decision === "approved"
    ? "Record that you personally reviewed the science in this exact diagram? This browser-only verdict cannot override automatic failures or unverified bounds."
    : "Record that this exact diagram failed your scientific review? This verdict is stored in this browser only.";
  if (!window.confirm(question)) return;
  const review = loadReview(r);
  review.decision = decision;
  review.scientificStatus = decision === "approved" ? "pass" : "fail";
  review.reviewedAt = new Date().toISOString();
  review.note = tr.querySelector("textarea").value;
  if (!saveReview(r, review)) return;
  tr.replaceWith(buildRow(r));
  renderIssues();
}

// Re-run server checks before trusting locally cached live results after refresh.
async function recheckSavedLiveResults() {
  for (const id of liveIds) {
    const index = results.findIndex(result => result.id === id);
    if (index < 0) continue;
    const current = results[index];
    try {
      const response = await fetch(`/api/check/${id}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({svg: current.svg}),
      });
      const checked = await response.json();
      if (!response.ok || !checked.checks || !checked.scientific_verification) throw new Error();
      if (!liveIds.has(id) || results[index].svg !== current.svg) continue;
      results[index] = { ...current, checks: checked.checks, final_status: checked.final_status,
                         scientific_verification: checked.scientific_verification };
      saveLiveResult(results[index]);
    } catch (e) {
      if (!liveIds.has(id) || results[index].svg !== current.svg) continue;
      results[index] = { ...current, checks: Object.fromEntries(CHECKS.map(([key]) =>
        [key, {passed: null, reason: "Could not recheck this browser-saved diagram. Retry after reconnecting."}])) };
    }
    const row = document.getElementById("diagram-" + id);
    if (row && !row.querySelector(".generate:disabled")) row.replaceWith(buildRow(results[index]));
    renderIssues();
    inspectAnimation(results[index]);
  }
}

// Browser samples are advisory, never a proof of all animation frames.
async function inspectAnimation(result) {
  if (!result.checks || !result.checks.animated_bounds || result.checks.animated_bounds.passed !== null ||
      !result.checks.custom_checks || result.checks.custom_checks.passed !== true) return;
  const reason = await sampleAnimatedBounds(result.svg);
  const index = results.findIndex(item => item.id === result.id);
  if (index < 0 || results[index].svg !== result.svg || !results[index].checks.animated_bounds ||
      results[index].checks.animated_bounds.passed !== null) return;
  results[index] = { ...results[index], checks: { ...results[index].checks,
    animated_bounds: { passed: null, reason } } };
  const row = document.getElementById("diagram-" + result.id);
  if (row) {
    const reasonEl = row.querySelector('[data-check="animated_bounds"] .reason');
    if (reasonEl) reasonEl.textContent = reason;
  }
}

function restoreSaved(id, row) {
  const saved = savedResults.find(result => result.id === id);
  if (!saved) return;
  try { localStorage.removeItem("live-result:" + id); }
  catch (e) { showMessage("Could not remove the locally saved generation."); return; }
  liveIds.delete(id);
  generationErrors.delete(id);
  const index = results.findIndex(result => result.id === id);
  results[index] = saved;
  row.replaceWith(buildRow(saved));
  renderIssues();
  inspectAnimation(saved);
}

async function generate(id, button, tr) {
  showMessage("");
  generationErrors.delete(id);
  renderIssues();
  const feedback = tr.querySelector(".generation-feedback");
  feedback.hidden = false;
  feedback.classList.remove("error");
  feedback.textContent = "Contacting Gemini and checking the diagram. This may take a minute.";
  button.disabled = true;
  tr.querySelectorAll(".approve, .reject, .restore-saved, textarea").forEach(control => { control.disabled = true; });
  button.textContent = "Generating…";
  try {
    let response;
    try {
      response = await fetch("/api/generate/" + id, { method: "POST" });
    } catch (error) {
      throw new Error("Could not reach the server. Check your connection and try again.");
    }
    let data = null;
    try { data = await response.json(); } catch (e) { /* not JSON (e.g. server timeout) */ }
    if (!response.ok || !data || data.error) {
      throw new Error((data && data.error) || `The server returned HTTP ${response.status}. It may have timed out; please try again.`);
    }
    if (data.id !== id || typeof data.svg !== "string" || !data.checks || typeof data.checks !== "object") {
      throw new Error("The server returned an incomplete generation result. Please try again.");
    }
    const index = results.findIndex((x) => x.id === id);
    if (index < 0) throw new Error("The diagram could not be found in this page. Refresh and try again.");
    const persisted = saveLiveResult(data);
    const newRow = buildRow(data);
    results[index] = data;                              // browser only: results.json is NOT changed
    tr.replaceWith(newRow);
    const newFeedback = newRow.querySelector(".generation-feedback");
    newFeedback.textContent = persisted ? "Generation finished. This result is saved only in this browser. Review its science and checks." : "Generation finished. Browser storage is unavailable; this result will be lost on refresh.";
    newFeedback.hidden = false;
    renderIssues();
    inspectAnimation(data);
  } catch (error) {
    const errorMessage = error.message || "An unexpected error occurred. Please try again.";
    generationErrors.set(id, errorMessage);
    feedback.textContent = "Generation failed: " + errorMessage;
    feedback.classList.add("error");
    renderIssues();
    showMessage("Generate failed for concept " + id + ": " + errorMessage);
    const index = results.findIndex(item => item.id === id);
    if (index >= 0) tr.replaceWith(buildRow(results[index]));
    else {
      button.disabled = false;
      tr.querySelectorAll(".approve, .reject, .restore-saved, textarea").forEach(control => { control.disabled = false; });
      button.textContent = "✦  Generate live";
    }
  } finally {
    refreshStatus();
  }
}

results.forEach((r) => rowsEl.appendChild(buildRow(r)));
renderIssues();
results.filter(r => !liveIds.has(r.id)).forEach(inspectAnimation);
recheckSavedLiveResults();
if (results.length === 0) showMessage("No saved results found. Run python generate_all.py first.");


