import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.collect_status import APIError, GitHub, collect_repo, discover, load_config, summarize_ci


def workflow(identifier, name="Tests"):
    return {"id": identifier, "name": name, "path": f".github/workflows/{name}.yml",
            "state": "active", "html_url": "https://github.com/example/collection/actions"}


def run(identifier, conclusion="success", status="completed", sha="head", number=1, attempt=1):
    return {"id": number, "workflow_id": identifier, "head_sha": sha, "run_number": number,
            "run_attempt": attempt, "status": status, "conclusion": conclusion,
            "html_url": "https://github.com/example/collection/actions/runs/1", "updated_at": "2026-01-01T00:00:00Z"}


def repo(slug="example/collection", **overrides):
    return {"name": slug.split("/")[1], "full_name": slug,
            "html_url": f"https://github.com/{slug}", "private": False,
            "visibility": "public", "default_branch": "main", **overrides}


class CITests(unittest.TestCase):
    def test_failure_in_one_workflow_is_not_hidden_by_another_success(self):
        result = summarize_ci([workflow(1), workflow(2, "Lint")], [run(1, "failure"), run(2)], "head")
        self.assertEqual(result["state"], "failing")
        self.assertEqual(len(result["workflows"]), 2)

    def test_old_commit_cannot_be_green_for_current_commit(self):
        result = summarize_ci([workflow(1)], [run(1, sha="old-head")], "head")
        self.assertEqual(result["state"], "unknown")

    def test_missing_workflow_cannot_be_green(self):
        result = summarize_ci([workflow(1), workflow(2, "Lint")], [run(1)], "head")
        self.assertEqual(result["state"], "unknown")

    def test_latest_rerun_supersedes_previous_attempt(self):
        result = summarize_ci([workflow(1)], [run(1, "failure", attempt=1), run(1, attempt=2)], "head")
        self.assertEqual(result["state"], "passing")

    def test_newer_run_wins_independent_of_response_order(self):
        result = summarize_ci([workflow(1)], [run(1, number=2), run(1, "failure", number=1)], "head")
        self.assertEqual(result["state"], "passing")

    def test_running_workflow_is_not_success(self):
        result = summarize_ci([workflow(1)], [run(1, None, "in_progress")], "head")
        self.assertEqual(result["state"], "running")

    def test_skipped_cancelled_and_neutral_are_unknown(self):
        for conclusion in ("skipped", "cancelled", "neutral", "stale", None):
            with self.subTest(conclusion=conclusion):
                result = summarize_ci([workflow(1)], [run(1, conclusion)], "head")
                self.assertEqual(result["state"], "unknown")

    def test_no_workflows_is_distinct_from_unknown(self):
        self.assertEqual(summarize_ci([], [], "head")["state"], "no_ci")

    def test_disabled_workflows_are_not_monitored(self):
        disabled = {**workflow(2), "state": "disabled_manually"}
        result = summarize_ci([workflow(1), disabled], [run(1)], "head")
        self.assertEqual(result["state"], "passing")

    def test_explicit_selection_and_invalid_selector(self):
        active = [workflow(1), workflow(2, "Release")]
        runs = [run(1), run(2, "failure")]
        self.assertEqual(summarize_ci(active, runs, "head", ["Tests"])["state"], "passing")
        self.assertEqual(summarize_ci(active, runs, "head", ["Typo"])["state"], "unknown")


class CollectionTests(unittest.TestCase):
    def test_grouped_repositories_are_discovered_across_owners(self):
        config = {"repositories": ["example/collection"], "groups": {
            "Cloud": ["example/collection"], "Validated Content": ["other/validated"]
        }}
        api = GitHub()
        with patch.object(api, "data", side_effect=lambda path: repo(path.removeprefix("/repos/"))) as get:
            found = discover(api, config)
        self.assertEqual(get.call_count, 2)
        self.assertEqual([(item["full_name"], item["_dashboard_group"]) for item in found],
                         [("example/collection", "Cloud"), ("other/validated", "Validated Content")])

    def test_group_is_kept_when_github_returns_canonical_repo_name(self):
        api = GitHub()
        with patch.object(api, "data", return_value=repo("example/renamed")):
            found = discover(api, {"groups": {"Cloud": ["example/old-name"]}})
        self.assertEqual(found[0]["_dashboard_group"], "Cloud")

    def test_grouped_private_repo_is_blocked(self):
        api = GitHub()
        with patch.object(api, "data", return_value=repo(private=True)):
            with self.assertRaisesRegex(ValueError, "Refusing"):
                discover(api, {"groups": {"Cloud": ["example/collection"]}})

    def test_ambiguous_domain_and_invalid_grouped_slug_rejected(self):
        for config in ({"groups": {"Cloud": ["example/collection"], "Other": ["EXAMPLE/collection"]}},
                       {"groups": {"Cloud": ["example/repo?bad"]}},
                       {"groups": {"Cloud": "example/collection"}}):
            with self.subTest(config=config), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "config.json"
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    load_config(path)

    def test_pagination_follows_next_link(self):
        api = GitHub()
        with patch.object(api, "get", side_effect=[([1], "https://api.github.com/items?page=2"), ([2], None)]) as get:
            self.assertEqual(api.pages("/items"), [1, 2])
            self.assertEqual(get.call_args_list[1].args, ("https://api.github.com/items?page=2", None))

    def test_discovery_filters_private_archived_and_excluded_and_deduplicates(self):
        api = GitHub()
        config = {"organizations": ["example"], "repositories": ["example/collection"],
                  "exclude": ["example/dashboard"], "include_forks": False}
        with patch.object(api, "pages", return_value=[repo(), repo("example/dashboard"),
              repo("example/private", private=True), repo("example/archive", archived=True),
              repo("example/fork", fork=True)]), patch.object(api, "data", return_value=repo()):
            self.assertEqual([item["full_name"] for item in discover(api, config)], ["example/collection"])

    def test_explicit_private_repo_aborts_before_collection(self):
        api = GitHub()
        with patch.object(api, "data", return_value=repo(private=True, visibility="private")):
            with self.assertRaisesRegex(ValueError, "Refusing"):
                discover(api, {"repositories": ["example/collection"]})

    def test_private_repo_is_blocked_even_if_directly_passed_to_collector(self):
        with self.assertRaisesRegex(ValueError, "Refusing"):
            collect_repo(GitHub(), repo(private=True), {})

    def test_failed_metric_is_unknown_and_pulls_not_counted_as_issues(self):
        api = GitHub()
        def pages(path, *args, **kwargs):
            if path.endswith("/pulls"):
                raise APIError(403, "Access denied")
            if path.endswith("/issues"):
                return [{"id": 1}, {"id": 2, "pull_request": {}}]
            return []
        def data(path, *args, **kwargs):
            if path.endswith("/releases/latest"):
                raise APIError(404, "No release")
            return []
        with patch.object(api, "pages", side_effect=pages), patch.object(api, "data", side_effect=data):
            result = collect_repo(api, repo(), {})
        self.assertIsNone(result["open_prs"])
        self.assertEqual(result["open_issues"], 1)
        self.assertIsNone(result["release"])
        self.assertEqual(result["errors"], ["Pull requests: Access denied"])

    def test_domain_and_display_name_reach_snapshot_row(self):
        api = GitHub()
        config = {"groups": {"Cloud": ["example/collection"]},
                  "display_names": {"example/collection": "Collection label"}}
        with patch.object(api, "data", return_value=[]), patch.object(api, "pages", return_value=[]):
            row = collect_repo(api, repo(), config)
        self.assertEqual(row["group"], "Cloud")
        self.assertEqual(row["display_name"], "Collection label")

    def test_api_refuses_external_urls_before_sending_token(self):
        with self.assertRaises(ValueError):
            GitHub("test-token").get("https://attacker.example/items")

    def test_invalid_repo_slug_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"repositories": ["example/repo?token=bad"]}))
            with self.assertRaises(ValueError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
