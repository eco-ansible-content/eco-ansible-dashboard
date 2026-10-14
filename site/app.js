"use strict";

const labels = {passing: "Passing", failing: "Failing", running: "Running", unknown: "Unknown", no_ci: "No Actions", error: "Data error"};
const rank = {error: 0, failing: 1, unknown: 2, running: 3, no_ci: 4, passing: 5};
const view = {snapshot: null, mode: "repositories", loading: false, lastFetchFailed: false};
const byId = id => document.getElementById(id);
const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));

function safeURL(value) {
  try { const url = new URL(value); return url.protocol === "https:" && url.hostname === "github.com" ? url.href : "#"; }
  catch { return "#"; }
}
function link(url, text, className = "", title = "") {
  return `<a href="${escape(safeURL(url))}" class="${className}" title="${escape(title)}" target="_blank" rel="noopener noreferrer">${escape(text)}</a>`;
}
function relative(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return "Unknown";
  const minutes = Math.max(0, Math.floor((Date.now() - Date.parse(value)) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  if (minutes < 43200) return `${Math.floor(minutes / 1440)}d ago`;
  return new Date(value).toLocaleDateString(undefined, {month: "short", day: "numeric", year: "numeric"});
}
function effectiveState(repo) { return repo.errors?.length ? "error" : (repo.ci?.state || "unknown"); }
function attention(repo) { return ["failing", "unknown", "error"].includes(effectiveState(repo)); }
function badge(state) { const known = labels[state] ? state : "unknown"; return `<span class="badge ${known}">${labels[known]}</span>`; }
function empty(title, copy) { return `<div class="empty-state"><h2>${escape(title)}</h2><p>${escape(copy)}</p></div>`; }
function allIssues() {
  return (view.snapshot?.repositories || []).flatMap(repo => (repo.issue_activity?.recent || []).map(issue => ({...issue, repo})));
}
function knownTotal(repos, getValue) {
  const values = repos.map(getValue), known = values.filter(value => typeof value === "number");
  return known.length ? known.reduce((total, value) => total + value, 0) + (known.length < values.length ? "+" : "") : repos.length ? "—" : "0";
}
function coreCell(repo) {
  const core = repo.compatibility || {}, tested = core.tested || [];
  const short = tested.slice(0, 3).join(", ") + (tested.length > 3 ? ` +${tested.length - 3}` : "");
  const support = core.supported_source ? link(core.supported_source, core.supported || "Not declared") : `<span class="no-value">${escape(core.supported || "Not declared")}</span>`;
  const testing = tested.length ? link(core.tested_sources?.[0], short, "", tested.join(", ")) : '<span class="no-value">Not declared</span>';
  return `<dl class="core-versions"><div><dt>Supported</dt><dd>${support}</dd></div><div><dt>CI tested</dt><dd>${testing}</dd></div></dl>`;
}
function repoRow(repo) {
  const ci = repo.ci || {state: "unknown", workflows: []}, core = repo.compatibility || {};
  const sha = repo.commit?.sha?.slice(0, 7) || "";
  const workflows = (ci.workflows || []).map(workflow => `<div class="workflow-item">${badge(workflow.state)}${workflow.url ? link(workflow.url, workflow.name) : `<span>${escape(workflow.name)}</span>`}<span class="cell-note">${escape(workflow.conclusion || (workflow.state === "running" ? "In progress" : "No successful run on this commit"))}</span></div>`).join("");
  const sources = (core.tested_sources || []).map((url, index) => link(url, `CI source ${index + 1}`)).join("");
  const notes = [...(repo.errors || []), ...(core.notes || [])];
  const newCount = repo.issue_activity?.new_count;
  return `<article class="repo-row"><div class="repo-summary">
    <div>${link(repo.url, repo.display_name || repo.name, "repo-name")}<div class="repo-owner">${escape(repo.display_name && repo.display_name !== repo.name ? repo.full_name : repo.full_name.split("/")[0])}</div></div>
    <div class="actions-cell">${badge(effectiveState(repo))}</div>
    <div class="core-cell">${coreCell(repo)}</div>
    <div class="metrics-cell">${newCount == null ? '<span class="no-value">—</span>' : `<a class="number-link issue-count-link" href="#new-issues" data-repo="${escape(repo.full_name)}" aria-label="Show ${newCount} new ${newCount === 1 ? "issue" : "issues"} for ${escape(repo.name)}">${newCount}</a>`}<span class="mobile-label">new issues · 7d</span>${repo.issue_activity?.untriaged_count ? `<div class="cell-note">${repo.issue_activity.untriaged_count} ${repo.issue_activity.untriaged_count === 1 ? "needs" : "need"} triage</div>` : ""}</div>
    <div class="metrics-cell">${repo.open_prs == null ? '<span class="no-value">—</span>' : link(repo.url + "/pulls", repo.open_prs, "number-link")}<span class="mobile-label">open PRs</span></div>
    <div class="release-cell"><span class="mobile-label">Release</span>${repo.release ? link(repo.release.url, repo.release.tag, "release-link") : '<span class="no-value">No release</span>'}</div>
    </div><details class="details"><summary>Repository details</summary><div class="detail-body">
      <section><h3>GitHub Actions · ${escape(repo.default_branch || "Unknown branch")}</h3><div class="workflow-list">${workflows || '<span class="no-value">No workflow results available.</span>'}</div></section>
      <section><h3>Ansible Core compatibility</h3><p>Supported: ${escape(core.supported || "Not declared")}</p><p>CI tested: ${escape((core.tested || []).join(", ") || "No explicit versions found in CI definitions")}</p><div class="sources">${core.supported_source ? link(core.supported_source, "Support metadata") : ""}${sources}</div><p>From the current default branch; configured test coverage does not imply passing runs.</p></section>
      <section><h3>Recent activity</h3><p>${escape(repo.description || "No description provided.")}</p><p>${repo.commit ? link(repo.commit.url, sha) + " · " + escape(relative(repo.commit.date)) + " · " + escape(repo.commit.message) : "No commit available."}</p><p>${repo.open_issues == null ? "Open issue count unavailable" : link(repo.url + "/issues", `${repo.open_issues} open issues`)}${repo.release ? " · Released " + escape(relative(repo.release.published_at)) : ""}</p></section>
      ${notes.length ? `<ul class="detail-errors">${notes.map(note => `<li>${escape(note)}</li>`).join("")}</ul>` : ""}
    </div></details></article>`;
}
function issueRow(issue) {
  const labelButtons = issue.labels.length ? `<div class="issue-labels">${issue.labels.map(label => `<button type="button" data-issue-label="${escape(label.toLowerCase())}">${escape(label)}</button>`).join("")}</div>` : "";
  return `<article class="issue-row"><div>${link(issue.url, `#${issue.number} ${issue.title}`, "issue-title")}<div class="issue-meta">${link(issue.repo.url, issue.repo.display_name || issue.repo.name)}<span>${escape(issue.repo.group || "Ungrouped")}</span><span>Opened ${escape(relative(issue.created_at))}</span><span>${issue.comments} ${issue.comments === 1 ? "comment" : "comments"}</span></div>${labelButtons}</div><div class="issue-triage">${issue.needs_triage ? '<strong>Needs triage</strong>' : '<span class="no-value">Other new issue</span>'}<p>${escape(issue.triage_reason || (issue.assignee_count ? "Assigned" : issue.comments ? "Has discussion" : "Not flagged by triage rule"))}</p></div></article>`;
}
function updateFreshness() {
  if (!view.snapshot) return;
  const snapshot = view.snapshot, timestamp = snapshot.generated_at, interval = Number(snapshot.refresh_minutes) || 30;
  byId("snapshot-time").textContent = timestamp ? `Updated ${relative(timestamp)}` : "No snapshot yet";
  byId("snapshot-time").title = timestamp ? new Date(timestamp).toLocaleString() : "";
  byId("refresh-description").textContent = `Updates every ${interval} minutes`;
  const incomplete = snapshot.repositories.filter(repo => repo.errors?.length).length;
  const messages = [];
  if (view.lastFetchFailed) messages.push("Reload failed. Showing the last snapshot loaded in this browser.");
  if (!timestamp || !Number.isFinite(Date.parse(timestamp)) || Date.now() - Date.parse(timestamp) > Math.max(interval * 3, 90) * 60000) messages.push("This snapshot is out of date. Check the dashboard’s Actions workflow for a newer collection.");
  if (incomplete) messages.push(`${incomplete} ${incomplete === 1 ? "repository has" : "repositories have"} incomplete data. Open repository details for the collection errors.`);
  byId("notice").hidden = messages.length === 0;
  byId("notice").textContent = messages.join(" ");
}
function render() {
  const isIssues = view.mode === "issues";
  byId("repo-list").hidden = isIssues;
  byId("issue-list").hidden = !isIssues;
  for (const id of ["status-control", "sort-control"]) byId(id).hidden = isIssues;
  for (const id of ["triage-control", "label-control"]) byId(id).hidden = !isIssues;
  document.querySelectorAll("[data-view]").forEach(button => { const selected = button.dataset.view === view.mode; button.classList.toggle("active", selected); button.setAttribute("aria-pressed", String(selected)); });
  byId("page-title").textContent = isIssues ? "New issues" : "Repository overview";
  byId("view-description").textContent = isIssues ? "Open issues created in the past seven days. Triage reasons are shown beside each issue." : "Ansible Core support and CI coverage reflect the current default branch.";
  if (!view.snapshot) return;
  const all = view.snapshot.repositories, query = byId("search").value.trim().toLowerCase(), domain = byId("domain").value;
  byId("stat-total").textContent = all.length;
  byId("stat-attention").textContent = all.filter(attention).length;
  byId("stat-triage").textContent = knownTotal(all, repo => repo.issue_activity?.untriaged_count);
  byId("stat-prs").textContent = knownTotal(all, repo => repo.open_prs);
  byId("repo-count").textContent = all.length;
  byId("issue-count").textContent = knownTotal(all, repo => repo.issue_activity?.new_count);
  if (isIssues) {
    const label = byId("issue-label").value, triage = byId("triage").value;
    const issues = allIssues().filter(issue => (!domain || issue.repo.group === domain)
      && (!label || issue.labels.some(value => value.toLowerCase() === label))
      && (triage === "all" || (triage === "needs" ? issue.needs_triage : !issue.needs_triage))
      && `${issue.repo.full_name} ${issue.repo.display_name || ""} ${issue.repo.group} ${issue.title} ${issue.labels.join(" ")}`.toLowerCase().includes(query));
    issues.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
    const loaded = all.filter(repo => repo.issue_activity).length;
    byId("issue-list").innerHTML = issues.length ? issues.map(issueRow).join("") : loaded ? empty(triage === "needs" ? "No new issues awaiting triage" : "No matching new issues", "Try another domain, label, search, or triage filter. This view includes open issues created in the past seven days.") : empty("Issue activity is not available yet", "Reload after the next successful collection to see new issues and triage signals.");
    byId("shown-count").textContent = `${issues.length} matching ${issues.length === 1 ? "issue" : "issues"} · opened in the past 7 days`;
  } else {
    const status = byId("status").value;
    const rows = all.filter(repo => (!domain || repo.group === domain)
      && `${repo.full_name} ${repo.display_name || ""} ${repo.group} ${repo.description} ${(repo.topics || []).join(" ")}`.toLowerCase().includes(query)
      && (status === "all" || (status === "attention" ? attention(repo) : effectiveState(repo) === status)));
    rows.sort((a, b) => {
      const mode = byId("sort").value;
      const delta = mode === "attention" ? rank[effectiveState(a)] - rank[effectiveState(b)] : mode === "updated" ? (Date.parse(b.commit?.date) || 0) - (Date.parse(a.commit?.date) || 0) : mode === "prs" ? (b.open_prs ?? -1) - (a.open_prs ?? -1) : 0;
      return delta || a.full_name.localeCompare(b.full_name);
    });
    const groups = [...new Set([...(view.snapshot.groups || []), ...rows.map(repo => repo.group || "Ungrouped")])];
    const headings = '<div class="column-labels" aria-hidden="true"><span>Repository</span><span>Actions</span><span>Ansible Core</span><span>New issues<br>past 7 days</span><span>PRs</span><span>Release</span></div>';
    const grouped = groups.map(group => {
      const members = rows.filter(repo => (repo.group || "Ungrouped") === group);
      return members.length ? `<section class="domain-group" aria-label="${escape(group)} repositories"><div class="domain-heading"><h2>${escape(group)}</h2><span>${members.length} ${members.length === 1 ? "repository" : "repositories"}</span></div>${members.map(repoRow).join("")}</section>` : "";
    }).join("");
    byId("repo-list").innerHTML = rows.length ? headings + grouped : all.length ? empty("No matching repositories", "Try another search, domain, or Actions status filter.") : empty("Your repositories will appear here", "Add your selected public repositories to config/repos.json, then run the dashboard workflow.");
    byId("shown-count").textContent = `Showing ${rows.length} of ${all.length} repositories`;
  }
  byId("repo-list").setAttribute("aria-busy", "false");
  updateFreshness();
}
function setView(mode) { view.mode = mode; render(); }
function populateFilters(snapshot) {
  const currentDomain = byId("domain").value, currentLabel = byId("issue-label").value;
  const groups = [...new Set([...(snapshot.groups || []), ...snapshot.repositories.map(repo => repo.group || "Ungrouped")])];
  byId("domain").innerHTML = '<option value="">All domains</option>' + groups.map(group => `<option value="${escape(group)}">${escape(group)}</option>`).join("");
  byId("domain").value = groups.includes(currentDomain) ? currentDomain : "";
  const issueLabels = new Map();
  for (const issue of allIssues()) for (const label of issue.labels) issueLabels.set(label.toLowerCase(), label);
  byId("issue-label").innerHTML = '<option value="">All labels</option>' + [...issueLabels].sort((a,b) => a[0].localeCompare(b[0])).map(([value,label]) => `<option value="${escape(value)}">${escape(label)}</option>`).join("");
  byId("issue-label").value = issueLabels.has(currentLabel) ? currentLabel : "";
}
async function loadSnapshot() {
  if (view.loading) return;
  view.loading = true;
  byId("reload").disabled = true;
  try {
    const response = await fetch(`data/status.json?t=${Date.now()}`, {cache: "no-store"});
    if (!response.ok) throw new Error("Snapshot unavailable");
    const snapshot = await response.json();
    if (snapshot.schema_version !== 1 || !Array.isArray(snapshot.repositories)) throw new Error("Unsupported snapshot");
    view.snapshot = snapshot;
    view.lastFetchFailed = false;
    byId("brand-name").textContent = snapshot.title || "ECO Ansible";
    document.title = `${snapshot.title || "ECO Ansible"} · Team dashboard`;
    populateFilters(snapshot);
    render();
  } catch {
    view.lastFetchFailed = true;
    if (view.snapshot) updateFreshness();
    else {
      const message = empty("Repository data is unavailable", "Use Reload data after the next successful dashboard deployment. For a local preview, run the collector before starting the web server.");
      byId("repo-list").innerHTML = message;
      byId("issue-list").innerHTML = message;
      byId("repo-list").setAttribute("aria-busy", "false");
      byId("shown-count").textContent = "No snapshot available";
    }
  } finally { view.loading = false; byId("reload").disabled = false; }
}
function updateThemeButton() {
  const dark = document.documentElement.dataset.theme === "dark";
  byId("theme-toggle").textContent = dark ? "Light mode" : "Dark mode";
  byId("theme-toggle").setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  byId("theme-toggle").setAttribute("aria-pressed", String(dark));
}
byId("theme-toggle").addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("eco-theme", next); } catch {}
  updateThemeButton();
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", event => {
  try { if (localStorage.getItem("eco-theme")) return; } catch {}
  document.documentElement.dataset.theme = event.matches ? "dark" : "light";
  updateThemeButton();
});
for (const id of ["search", "domain", "status", "sort", "triage", "issue-label"]) byId(id).addEventListener(id === "search" ? "input" : "change", render);
byId("reload").addEventListener("click", loadSnapshot);
document.querySelectorAll("[data-view]").forEach(button => button.addEventListener("click", () => setView(button.dataset.view)));
byId("triage-summary").addEventListener("click", () => {
  byId("search").value = ""; byId("domain").value = ""; byId("issue-label").value = ""; byId("triage").value = "needs"; setView("issues");
});
byId("repo-list").addEventListener("click", event => {
  const anchor = event.target.closest("[data-repo]");
  if (!anchor) return;
  event.preventDefault();
  byId("search").value = anchor.dataset.repo; byId("issue-label").value = ""; byId("triage").value = "all"; setView("issues");
});
byId("issue-list").addEventListener("click", event => {
  const button = event.target.closest("[data-issue-label]");
  if (button) { byId("issue-label").value = button.dataset.issueLabel; render(); }
});
updateThemeButton();
setInterval(updateFreshness, 60000);
loadSnapshot();
