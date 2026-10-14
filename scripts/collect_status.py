#!/usr/bin/env python3
"""Build a public snapshot of repository health, issue triage, and Core compatibility."""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

if __package__:
    from .compatibility import collect_compatibility
else:
    from compatibility import collect_compatibility

API = "https://api.github.com"
SLUG = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
OWNER = re.compile(r"^[A-Za-z0-9-]+$")
FAILURES = {"failure", "timed_out", "action_required", "startup_failure"}
PENDING = {"queued", "in_progress", "waiting", "pending", "requested"}
NEEDS_TRIAGE = {"needs_triage", "needs-triage", "needs triage", "untriaged", "triage-needed"}
TRIAGED = {"triaged", "confirmed", "accepted"}


class APIError(RuntimeError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


class GitHub:
    def __init__(self, token=None):
        self.token = token

    def get(self, path, params=None):
        url = path if path.startswith("https://") else API + path
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != "api.github.com":
            raise ValueError("Only the public GitHub API is supported")
        if params:
            url += ("&" if "?" in url else "?") + urlencode(params)
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "eco-ansible-dashboard",
        }
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers=headers), timeout=30) as response:
                    body = json.load(response)
                    link = response.headers.get("Link", "")
                match = re.search(r'<([^>]+)>; rel="next"', link)
                return body, match.group(1) if match else None
            except HTTPError as error:
                if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(min(int(error.headers.get("Retry-After", "2")), 15))
                    continue
                # Do not echo request headers, credentials, or raw API responses.
                message = {
                    401: "GitHub authentication failed",
                    403: "GitHub access denied or API rate limit reached",
                    404: "GitHub resource was not found",
                    409: "Repository has no commits",
                    429: "GitHub API rate limit reached",
                }.get(error.code, "GitHub API request failed")
                raise APIError(error.code, message) from None
            except (URLError, TimeoutError) as error:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(0, "GitHub API connection failed") from error

    def data(self, path, params=None):
        return self.get(path, params)[0]

    def pages(self, path, params=None, key=None):
        params = {**(params or {}), "per_page": 100}
        result = []
        while path:
            body, path = self.get(path, params)
            items = body[key] if key else body
            if not isinstance(items, list):
                raise ValueError("Unexpected GitHub list response")
            result.extend(items)
            params = None
        return result


def configured_repositories(config):
    return config.get("repositories", []) + [
        slug for slugs in config.get("groups", {}).values() for slug in slugs
    ]


def repository_group(config, slug):
    for group, slugs in config.get("groups", {}).items():
        if slug.lower() in {item.lower() for item in slugs}:
            return group
    return "Ungrouped"


def load_config(path):
    config = json.loads(Path(path).read_text())
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")
    for field in ("organizations", "repositories", "exclude"):
        if not isinstance(config.get(field, []), list):
            raise ValueError(f"{field} must be a list")
    groups = config.get("groups", {})
    if not isinstance(groups, dict):
        raise ValueError("groups must map domain names to repository lists")
    assigned = set()
    for group, slugs in groups.items():
        if not isinstance(group, str) or not group.strip() or not isinstance(slugs, list):
            raise ValueError("groups must map non-empty domain names to repository lists")
        for slug in slugs:
            if not isinstance(slug, str) or not SLUG.fullmatch(slug):
                raise ValueError("Grouped repositories must use owner/repository format")
            if slug.lower() in assigned:
                raise ValueError(f"Repository appears in multiple group entries: {slug}")
            assigned.add(slug.lower())
    for org in config.get("organizations", []):
        if not isinstance(org, str) or not OWNER.fullmatch(org):
            raise ValueError("Organizations must be GitHub organization names")
    for slug in configured_repositories(config) + config.get("exclude", []):
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            raise ValueError("Repositories must use owner/repository format")
    display_names = config.get("display_names", {})
    if not isinstance(display_names, dict) or any(
        not SLUG.fullmatch(slug) or not isinstance(name, str) or not name.strip()
        for slug, name in display_names.items()
    ):
        raise ValueError("display_names must map owner/repository to non-empty labels")
    for slug, names in config.get("workflows", {}).items():
        if not SLUG.fullmatch(slug) or not isinstance(names, list) or not all(
            isinstance(name, str) for name in names
        ):
            raise ValueError("Workflow selectors must map owner/repository to names or paths")
    if not isinstance(config.get("refresh_minutes", 30), int) or config.get("refresh_minutes", 30) < 5:
        raise ValueError("refresh_minutes must be an integer of at least 5")
    triage = config.get("triage", {})
    if not isinstance(triage, dict):
        raise ValueError("triage must be an object")
    for key in ("needs_triage_labels", "triaged_labels"):
        if key in triage and (not isinstance(triage[key], list) or not all(isinstance(label, str) for label in triage[key])):
            raise ValueError(f"triage.{key} must be a list of label names")
    if "include_no_activity" in triage and not isinstance(triage["include_no_activity"], bool):
        raise ValueError("triage.include_no_activity must be true or false")
    return config


def is_public(repo):
    return repo.get("private") is False and repo.get("visibility", "public") == "public"


def discover(api, config):
    repositories = {}
    for org in config.get("organizations", []):
        for repo in api.pages(f"/orgs/{org}/repos", {"type": "public"}):
            if is_public(repo):
                repositories[repo["full_name"].lower()] = repo
    for slug in dict.fromkeys(configured_repositories(config)):
        repo = api.data(f"/repos/{slug}")
        if not is_public(repo):
            raise ValueError(f"Refusing to publish private repository data: {slug}")
        repo["_dashboard_group"] = repository_group(config, slug)
        repositories[repo["full_name"].lower()] = repo
    excluded = {slug.lower() for slug in config.get("exclude", [])}
    return sorted([
        repo for slug, repo in repositories.items()
        if slug not in excluded
        and (config.get("include_archived", False) or not repo.get("archived"))
        and (config.get("include_forks", True) or not repo.get("fork"))
    ], key=lambda repo: repo["full_name"].lower())


def summarize_ci(workflows, runs, head_sha, selectors=None):
    active = [workflow for workflow in workflows if workflow.get("state") == "active"]
    if selectors is not None:
        active = [workflow for workflow in active if
                  workflow["name"] in selectors or workflow["path"] in selectors]
    latest = {}
    for run in runs:
        if not head_sha or run.get("head_sha") != head_sha:
            continue
        workflow_id = run["workflow_id"]
        order = (run.get("run_number", 0), run.get("run_attempt", 1), run.get("id", 0))
        previous = latest.get(workflow_id)
        if previous is None or order > previous[0]:
            latest[workflow_id] = (order, run)
    details = []
    for workflow in active:
        run = latest.get(workflow["id"], (None, None))[1]
        state = "unknown"
        if run:
            if run.get("status") in PENDING:
                state = "running"
            elif run.get("conclusion") in FAILURES:
                state = "failing"
            elif run.get("status") == "completed" and run.get("conclusion") == "success":
                state = "passing"
        details.append({
            "name": workflow["name"], "path": workflow["path"], "state": state,
            "conclusion": run.get("conclusion") if run else None,
            "url": run["html_url"] if run else workflow.get("html_url"),
            "updated_at": run.get("updated_at") if run else None,
        })
    # A typo in explicit selectors must never silently report that no CI exists.
    if selectors:
        matched = {value for workflow in active for value in (workflow["name"], workflow["path"])}
        for missing in set(selectors) - matched:
            details.append({"name": missing, "path": missing, "state": "unknown",
                            "conclusion": None, "url": None, "updated_at": None})
    states = {item["state"] for item in details}
    if "failing" in states:
        overall = "failing"
    elif "running" in states:
        overall = "running"
    elif "unknown" in states:
        overall = "unknown"
    elif states:
        overall = "passing"
    else:
        overall = "no_ci"
    return {"state": overall, "workflows": details}


def summarize_issues(issues, config, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    rule = config.get("triage", {})
    pending_labels = {value.casefold() for value in rule.get("needs_triage_labels", NEEDS_TRIAGE)}
    reviewed_labels = {value.casefold() for value in rule.get("triaged_labels", TRIAGED)}
    recent = []
    for issue in issues:
        if "pull_request" in issue or issue.get("state", "open") != "open":
            continue
        try:
            created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if created.tzinfo is None or not cutoff <= created <= now:
            continue
        labels = [item["name"] if isinstance(item, dict) else str(item) for item in issue.get("labels", [])]
        normalized = {label.casefold() for label in labels}
        reason = None
        if normalized & pending_labels:
            reason = "Needs-triage label"
        elif rule.get("include_no_activity", True) and not (
            normalized & reviewed_labels or issue.get("assignees") or issue.get("comments", 0)
        ):
            reason = "No assignee or comments"
        recent.append({"number": issue["number"], "title": issue["title"], "url": issue["html_url"],
                       "created_at": issue["created_at"], "labels": labels,
                       "needs_triage": bool(reason), "triage_reason": reason,
                       "comments": issue.get("comments", 0), "assignee_count": len(issue.get("assignees", []))})
    recent.sort(key=lambda issue: issue["created_at"], reverse=True)
    return {"recent": recent, "new_count": len(recent),
            "untriaged_count": sum(issue["needs_triage"] for issue in recent), "days": 7}


def collect_repo(api, repo, config):
    if not is_public(repo):
        raise ValueError("Refusing to collect private repository data")
    slug = repo["full_name"]
    base = f"/repos/{slug}"
    row = {
        "name": repo["name"], "full_name": slug, "url": repo["html_url"],
        "group": repo.get("_dashboard_group", repository_group(config, slug)),
        "display_name": config.get("display_names", {}).get(slug, repo["name"]),
        "description": repo.get("description") or "",
        "default_branch": repo.get("default_branch"), "fork": repo.get("fork", False),
        "archived": repo.get("archived", False), "language": repo.get("language"),
        "topics": repo.get("topics", []), "stars": repo.get("stargazers_count", 0),
        "open_prs": None, "open_issues": None, "commit": None, "release": None,
        "ci": {"state": "unknown", "workflows": []}, "errors": [],
        "issue_activity": None, "compatibility": None,
    }

    def fetch(label, call, allowed=()):
        try:
            return call()
        except APIError as error:
            if error.status not in allowed:
                row["errors"].append(f"{label}: {error}")
            return None

    commits = fetch("Commit", lambda: api.data(base + "/commits", {
        "sha": repo["default_branch"], "per_page": 1,
    }), allowed=(409,))
    if commits:
        commit = commits[0]
        row["commit"] = {
            "sha": commit["sha"], "url": commit["html_url"],
            "message": commit["commit"]["message"].splitlines()[0],
            "date": commit["commit"]["committer"]["date"],
        }
    pulls = fetch("Pull requests", lambda: api.pages(base + "/pulls", {"state": "open"}))
    if pulls is not None:
        row["open_prs"] = len(pulls)
    # Count issues from their own API response, excluding PRs and avoiding a metadata race.
    issues = fetch("Issues", lambda: api.pages(base + "/issues", {"state": "open"}))
    if issues is not None:
        row["open_issues"] = sum("pull_request" not in item for item in issues)
        row["issue_activity"] = summarize_issues(issues, config)
    release = fetch("Release", lambda: api.data(base + "/releases/latest"), allowed=(404,))
    if release:
        row["release"] = {
            "tag": release["tag_name"], "url": release["html_url"],
            "published_at": release.get("published_at"),
        }
    workflows = fetch("Workflows", lambda: api.pages(base + "/actions/workflows", key="workflows"))
    head_sha = row["commit"]["sha"] if row["commit"] else None
    runs = []
    if workflows and head_sha:
        runs = fetch("CI runs", lambda: api.pages(base + "/actions/runs", {
            "branch": repo["default_branch"], "head_sha": head_sha,
        }, key="workflow_runs"))
    if workflows is not None and runs is not None:
        selectors = config.get("workflows", {}).get(slug)
        row["ci"] = summarize_ci(workflows, runs, head_sha, selectors)
    row["compatibility"] = collect_compatibility(api, repo, workflows, head_sha)
    return row


def build_snapshot(api, config):
    repos = discover(api, config)
    rows = []
    for repo in repos:
        print(f"Collecting {repo['full_name']}", flush=True)
        rows.append(collect_repo(api, repo, config))
    return {
        "schema_version": 1,
        "title": config.get("title", "Repository dashboard"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "refresh_minutes": config.get("refresh_minutes", 30),
        "organizations": config.get("organizations", []),
        "groups": list(config.get("groups", {})),
        "repositories": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/repos.json")
    parser.add_argument("--output", default="site/data/status.json")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        snapshot = build_snapshot(GitHub(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")), config)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(snapshot, indent=2) + "\n")
        temporary.replace(output)
        errors = sum(bool(repo["errors"]) for repo in snapshot["repositories"])
        print(f"Collected {len(snapshot['repositories'])} public repositories; {errors} with collection errors")
        for repo in snapshot["repositories"]:
            for error in repo["errors"]:
                print(f"{repo['full_name']}: {error}", file=sys.stderr)
        return 0
    except (APIError, ValueError, KeyError, OSError) as error:
        print(f"Collection failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
