// static/app.js
// Draws the library, saves review decisions in localStorage, and runs Generate.

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
const issuesEl = document.getElementById("issues");
const generationErrors = new Map();

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
  try { localStorage.setItem("review:" + result.id, JSON.stringify({ ...review, svg: result.svg })); }
  catch (e) { showMessage("Could not save your decision in this browser."); }
}

function showMessage(text) {
  messageEl.textContent = text;
  messageEl.hidden = !text;
}

// Display actual failures separately from diagrams awaiting scientific review.
function renderIssues() {
  issuesEl.replaceChildren();
  let affected = 0;
  let pending = 0;
  for (const result of results) {
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
  const count = status => results.filter(result => result.final_status === status).length;
  stats.innerHTML = [
    [results.length, "Diagrams", ""],
    [count("pass"), "Passed", "pass-stat"],
    [count("fail"), "Failed", "fail-stat"],
    [count("needs_review"), "Needs review", "pending-stat"],
  ].map(([value, label, cls]) => `<div class="stat ${cls}"><strong>${value}</strong><span>${label}</span></div>`).join("");
}

function buildRow(r) {
  const review = loadReview(r);
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
    return `<div class="check-item"><div class="check-top"><span>${esc(label)}</span><span class="status-pill ${state}">${name}</span></div><p class="reason">${esc(c.reason)}</p></div>`;
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
        <div class="review-section"><div class="review-heading"><strong>Your review</strong><span class="review-state">Browser decision: ${esc(review.decision || "not reviewed")}</span></div>
          <div class="review-actions"><button type="button" class="approve ${review.decision === "approved" ? "on" : ""}" aria-pressed="${review.decision === "approved"}">✓ &nbsp;Approve</button><button type="button" class="reject ${review.decision === "rejected" ? "on" : ""}" aria-pressed="${review.decision === "rejected"}">× &nbsp;Reject</button></div>
          <textarea aria-label="Reviewer note for ${esc(r.name)}" placeholder="Add a reviewer note…">${esc(review.note || "")}</textarea>
          <p class="review-note">Saved in this browser for this diagram; separate from scientific verification.</p>
        </div>
      </div>
    </div>
    <div class="card-footer"><div class="metrics"><span><strong>$${esc(r.cost_usd)}</strong> estimated cost</span><span><strong>${esc(r.validation_retries)}</strong> validation retries</span><span><strong>${esc(r.api_retries)}</strong> API retries</span><span><strong>${esc(r.input_tokens)} / ${esc(r.output_tokens)}</strong> tokens in / out</span><span><strong>${esc(r.latency_seconds)}s</strong></span><span>${esc(r.model)}</span>${r.note ? `<br>Note: ${esc(r.note)}` : ""}</div>
      <button type="button" class="generate">✦ &nbsp;Generate live</button></div>`;

  const approveBtn = card.querySelector(".approve");
  const rejectBtn = card.querySelector(".reject");
  const note = card.querySelector("textarea");
  approveBtn.onclick = () => setDecision(r, card.closest("tr"), "approved");
  rejectBtn.onclick = () => setDecision(r, card.closest("tr"), "rejected");
  note.oninput = () => {
    const current = loadReview(r);
    current.note = note.value;
    saveReview(r, current);
  };
  card.querySelector(".generate").onclick = (event) => generate(r.id, event.currentTarget, card.closest("tr"));
  const row = document.createElement("tr");
  row.id = "diagram-" + r.id;
  const cell = document.createElement("td");
  cell.appendChild(card);
  row.appendChild(cell);
  return row;
}

function setDecision(r, tr, decision) {
  const review = loadReview(r);
  review.decision = decision;
  review.note = tr.querySelector("textarea").value;   // keep whatever is typed
  saveReview(r, review);
  tr.replaceWith(buildRow(r));                         // redraw so the buttons update
}

async function generate(id, button, tr) {
  showMessage("");
  generationErrors.delete(id);
  renderIssues();
  button.disabled = true;
  tr.querySelectorAll(".approve, .reject, textarea").forEach(control => { control.disabled = true; });
  button.textContent = "Generating…";
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
    renderIssues();
  } catch (error) {
    generationErrors.set(id, error.message);
    renderIssues();
    showMessage("Generate failed for concept " + id + ": " + error.message);
    button.disabled = false;
    tr.querySelectorAll(".approve, .reject, textarea").forEach(control => { control.disabled = false; });
    button.textContent = "✦  Generate live";
  }
}

results.forEach((r) => rowsEl.appendChild(buildRow(r)));
renderIssues();
if (results.length === 0) showMessage("No saved results found. Run python generate_all.py first.");


