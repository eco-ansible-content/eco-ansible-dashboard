"use strict";

const labels = {passing: "Passing", failing: "Failing", running: "Running", unknown: "Unknown", no_ci: "No CI", error: "Data error"};
const rank = {error: 0, failing: 1, unknown: 2, running: 3, no_ci: 4, passing: 5};
const view = {snapshot: null, filter: "all", loading: false, lastFetchFailed: false};
const byId = (id) => document.getElementById(id);
const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));
function safeURL(value) {
  try { const url = new URL(value); return url.protocol === "https:" && url.hostname === "github.com" ? url.href : "#"; }
  catch { return "#"; }
}
function link(url, text, className = "") {
  return `<a href="${escape(safeURL(url))}" class="${className}" target="_blank" rel="noopener noreferrer">${escape(text)}</a>`;
}
function relative(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return "Unknown";
  const minutes = Math.max(0, Math.floor((Date.now() - Date.parse(value)) / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  if (minutes < 43200) return `${Math.floor(minutes / 1440)}d ago`;
  return new Date(value).toLocaleDateString(undefined, {month: "short", day: "numeric", year: "numeric"});
}
function effectiveState(repo) { return repo.errors?.length ? "error" : (repo.ci?.state || "unknown"); }
function attention(repo) { return ["failing", "unknown", "error"].includes(effectiveState(repo)); }
function badge(state) { const known = labels[state] ? state : "unknown"; return `<span class="badge ${known}">${labels[known]}</span>`; }
function empty(title, copy) {
  return `<div class="empty-state"><span class="empty-icon" aria-hidden="true">▤</span><h3>${escape(title)}</h3><p>${escape(copy)}</p></div>`;
}
function numberLink(repo, value, route) { return value == null ? '<span class="no-value">—</span>' : link(`${repo.url}/${route}`, value, "number-link"); }
function repoRow(repo) {
  const state = effectiveState(repo), ci = repo.ci || {state: "unknown", workflows: []};
  const sha = repo.commit?.sha?.slice(0, 7) || "";
  const ciContext = repo.errors?.length ? "Collection incomplete" : ci.workflows?.length ? `${ci.workflows.length} workflow${ci.workflows.length === 1 ? "" : "s"} · ${repo.default_branch}` : "No monitored workflows";
  const workflowDetails = (ci.workflows || []).map((workflow) => `<div class="workflow-item">${badge(workflow.state)}${workflow.url ? link(workflow.url, workflow.name) : `<span>${escape(workflow.name)}</span>`}<span class="cell-sub">${escape(workflow.conclusion || (workflow.state === "running" ? "In progress" : workflow.state === "unknown" ? "No successful run on this commit" : ""))}</span></div>`).join("");
  return `<article class="repo-row"><div class="repo-summary">
    <div>${link(repo.url, repo.display_name || repo.name, "repo-name")}<div class="repo-owner">${escape(repo.display_name && repo.display_name !== repo.name ? repo.full_name : repo.full_name.split("/")[0])}${repo.fork ? " · fork" : ""}${repo.archived ? " · archived" : ""}</div><div class="repo-description">${escape(repo.description || "No description provided.")}</div></div>
    <div>${badge(state)}<div class="cell-sub">${escape(ciContext)}</div></div>
    <div>${repo.release ? link(repo.release.url, repo.release.tag, "release-link") : '<span class="no-value">No release</span>'}<div class="cell-sub">${repo.release ? escape(relative(repo.release.published_at)) : "Stable GitHub release"}</div></div>
    <div>${numberLink(repo, repo.open_prs, "pulls")}<div class="cell-sub">open PRs</div></div>
    <div>${numberLink(repo, repo.open_issues, "issues")}<div class="cell-sub">open issues</div></div>
    <div><div class="commit-time">${escape(repo.commit ? relative(repo.commit.date) : "No commits")}</div>${repo.commit ? link(repo.commit.url, sha, "commit-link") : '<span class="no-value">—</span>'}</div>
    </div><details class="details"><summary>View checks & activity</summary><div class="detail-body"><div><h4>Default branch · ${escape(repo.default_branch || "Unknown")}</h4><div class="workflow-list">${workflowDetails || '<span class="no-value">No workflow results available.</span>'}</div></div><div><h4>Latest commit</h4><p class="detail-commit">${escape(repo.commit?.message || "No commit available.")}</p><div class="cell-sub">${repo.commit ? link(repo.commit.url, sha) + " · " + escape(relative(repo.commit.date)) : ""}</div><div class="cell-sub">${numberLink(repo, repo.open_prs, "pulls")} open PRs · ${numberLink(repo, repo.open_issues, "issues")} open issues</div></div>${repo.errors?.length ? `<ul class="detail-errors">${repo.errors.map((error) => `<li>${escape(error)}</li>`).join("")}</ul>` : ""}</div></details></article>`;
}
function updateFreshness() {
  if (!view.snapshot) return;
  const snapshot = view.snapshot, timestamp = snapshot.generated_at;
  const interval = Number(snapshot.refresh_minutes) || 30;
  const stale = !timestamp || !Number.isFinite(Date.parse(timestamp)) || Date.now() - Date.parse(timestamp) > Math.max(interval * 3, 90) * 60000;
  byId("snapshot-time").textContent = timestamp ? `Updated ${relative(timestamp)}` : "No snapshot yet";
  byId("snapshot-time").title = timestamp ? new Date(timestamp).toLocaleString() : "";
  byId("refresh-description").textContent = `Collected by GitHub Actions · Every ${interval} minutes`;
  const incomplete = snapshot.repositories.filter((repo) => repo.errors?.length).length;
  const messages = [];
  if (view.lastFetchFailed) messages.push("Reload failed. Showing the last snapshot loaded in this browser.");
  if (stale) messages.push("This snapshot is out of date. Check the dashboard’s Actions workflow for a newer collection.");
  if (incomplete) messages.push(`${incomplete} ${incomplete === 1 ? "repository has" : "repositories have"} incomplete data. Expand the affected rows for details.`);
  byId("notice").hidden = messages.length === 0;
  byId("notice").textContent = messages.join(" ");
}
function render() {
  if (!view.snapshot) return;
  const all = view.snapshot.repositories;
  const query = byId("search").value.trim().toLowerCase();
  const domain = byId("domain").value;
  const rows = all.filter((repo) => {
    const match = `${repo.full_name} ${repo.display_name || ""} ${repo.description} ${repo.group || ""} ${(repo.topics || []).join(" ")}`.toLowerCase().includes(query);
    return match && (!domain || (repo.group || "Ungrouped") === domain) && (view.filter === "all" || (view.filter === "attention" ? attention(repo) : effectiveState(repo) === view.filter));
  });
  rows.sort((a, b) => {
    const mode = byId("sort").value;
    const delta = mode === "attention" ? rank[effectiveState(a)] - rank[effectiveState(b)] : mode === "updated" ? (Date.parse(b.commit?.date) || 0) - (Date.parse(a.commit?.date) || 0) : mode === "prs" ? (b.open_prs ?? -1) - (a.open_prs ?? -1) : 0;
    return delta || a.full_name.localeCompare(b.full_name);
  });
  byId("stat-total").textContent = all.length;
  byId("stat-passing").textContent = all.filter((repo) => effectiveState(repo) === "passing").length;
  byId("stat-attention").textContent = all.filter(attention).length;
  const knownPRs = all.filter((repo) => repo.open_prs != null);
  byId("stat-prs").textContent = knownPRs.length ? knownPRs.reduce((sum, repo) => sum + repo.open_prs, 0) + (knownPRs.length < all.length ? "+" : "") : all.length ? "—" : "0";
  byId("repo-count").textContent = all.length;
  byId("shown-count").textContent = `Showing ${rows.length} of ${all.length} repositories`;
  const headings = '<div class="column-labels" aria-hidden="true"><span>REPOSITORY</span><span>CI STATUS</span><span>LATEST RELEASE</span><span>PRS</span><span>ISSUES</span><span>LAST COMMIT</span></div>';
  const groups = Array.from(new Set([...(view.snapshot.groups || []), ...rows.map(repo => repo.group || "Ungrouped")]));
  const groupedRows = groups.map(group => {
    const members = rows.filter(repo => (repo.group || "Ungrouped") === group);
    if (!members.length) return "";
    return `<section class="domain-group" aria-label="${escape(group)} repositories"><div class="domain-heading"><h3>${escape(group)}</h3><span>${members.length} ${members.length === 1 ? "repository" : "repositories"}</span></div>${members.map(repoRow).join("")}</section>`;
  }).join("");
  byId("repo-list").innerHTML = rows.length ? headings + groupedRows : all.length ? empty("No matching repositories", "Try another search, domain, or status filter.") : empty("Your repositories will appear here", "Add your selected public repositories to config/repos.json, then run the dashboard workflow.");
  byId("repo-list").setAttribute("aria-busy", "false");
  updateFreshness();
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
    const currentDomain = byId("domain").value;
    const groups = Array.from(new Set([...(snapshot.groups || []), ...snapshot.repositories.map(repo => repo.group || "Ungrouped")]));
    byId("domain").innerHTML = '<option value="">All domains</option>' + groups.map(group => `<option value="${escape(group)}">${escape(group)}</option>`).join("");
    byId("domain").value = groups.includes(currentDomain) ? currentDomain : "";
    byId("brand-name").textContent = snapshot.title || "ECO Ansible";
    document.title = `${snapshot.title || "ECO Ansible"} · Repository dashboard`;
    render();
  } catch {
    view.lastFetchFailed = true;
    if (view.snapshot) updateFreshness();
    else {
      byId("repo-list").innerHTML = empty("The first snapshot is on its way", "Run the dashboard workflow to collect repository data. For a local preview, run the collector before starting the web server.");
      byId("repo-list").setAttribute("aria-busy", "false");
      byId("shown-count").textContent = "No snapshot available";
      byId("notice").hidden = false;
      byId("notice").textContent = "Repository status is unavailable. Reload after the next successful deployment.";
    }
  } finally {
    view.loading = false;
    byId("reload").disabled = false;
  }
}
byId("search").addEventListener("input", render);
byId("sort").addEventListener("change", render);
byId("domain").addEventListener("change", render);
byId("reload").addEventListener("click", loadSnapshot);
document.querySelectorAll("[data-filter]").forEach((button) => button.addEventListener("click", () => {
  view.filter = button.dataset.filter;
  document.querySelectorAll("[data-filter]").forEach((item) => {
    item.classList.toggle("active", item === button);
    item.setAttribute("aria-pressed", String(item === button));
  });
  render();
}));
setInterval(updateFreshness, 60000);
loadSnapshot();
