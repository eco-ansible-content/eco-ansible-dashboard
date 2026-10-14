import base64
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from scripts.collect_status import APIError, GitHub, summarize_issues
from scripts.compatibility import azure_versions, collect_compatibility, document, workflow_versions

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def issue(number=1, days=1, **fields):
    return {"number": number, "title": "New issue", "html_url": "https://github.com/example/collection/issues/1",
            "created_at": (NOW - timedelta(days=days)).isoformat(), "updated_at": NOW.isoformat(),
            "state": "open", "labels": [], "assignees": [], "comments": 0, **fields}


def file_response(text):
    return {"type": "file", "encoding": "base64", "size": len(text),
            "content": base64.b64encode(text.encode()).decode()}


class IssueActivityTests(unittest.TestCase):
    def test_only_open_issues_created_within_seven_days(self):
        result = summarize_issues([issue(1, 7), issue(2, 8), issue(3, 1, pull_request={}),
                                  issue(4, 1, state="closed"), issue(5, -1)], {}, NOW)
        self.assertEqual([entry["number"] for entry in result["recent"]], [1])
        self.assertEqual(result["new_count"], 1)

    def test_updated_recently_does_not_make_old_issue_new(self):
        self.assertEqual(summarize_issues([issue(days=30)], {}, NOW)["new_count"], 0)

    def test_needs_triage_label_is_explicit_even_with_discussion(self):
        result = summarize_issues([issue(labels=[{"name": "Needs-Triage"}], comments=4, assignees=[{}])], {}, NOW)
        self.assertEqual(result["untriaged_count"], 1)
        self.assertEqual(result["recent"][0]["triage_reason"], "Needs-triage label")

    def test_heuristic_checks_assignment_comments_and_triaged_labels(self):
        rows = [issue(1), issue(2, assignees=[{}]), issue(3, comments=1),
                issue(4, labels=[{"name": "triaged"}]), issue(5, labels=[{"name": "bug"}])]
        result = summarize_issues(rows, {}, NOW)
        self.assertEqual([entry["number"] for entry in result["recent"] if entry["needs_triage"]], [1, 5])

    def test_repo_labels_and_explicit_only_rule_can_be_configured(self):
        config = {"triage": {"needs_triage_labels": ["needs review"], "triaged_labels": ["seen"], "include_no_activity": False}}
        result = summarize_issues([issue(1), issue(2, labels=[{"name": "Needs Review"}])], config, NOW)
        self.assertEqual(result["untriaged_count"], 1)

    def test_invalid_dates_are_ignored(self):
        rows = [issue(created_at="unknown"), issue(created_at="2026-10-14T12:00:00")]
        self.assertEqual(summarize_issues(rows, {}, NOW)["new_count"], 0)


class CompatibilityTests(unittest.TestCase):
    def test_core_archive_install_resolves_integration_matrix(self):
        data = document("""jobs:
  integration:
    strategy: {matrix: {ansible_version: [stable-2.19, stable-2.20]}}
    steps:
      - run: pip install https://github.com/ansible/ansible/archive/${{ matrix.ansible_version }}.tar.gz
      - run: echo 'pip install ansible-core==2.15'
""")
        self.assertEqual(workflow_versions(data)[0], {"2.19", "2.20"})

    def test_core_environment_variable_resolves_test_matrix(self):
        data = document("""jobs:
  integration:
    strategy:
      matrix: {ansible_version: [stable-2.19, stable-2.20]}
    steps:
      - env: {ANSIBLE_VERSION: '${{ matrix.ansible_version }}'}
        run: run-tests
""")
        self.assertEqual(workflow_versions(data)[0], {"2.19", "2.20"})

    def test_documentation_core_install_is_not_test_coverage(self):
        data = document("""jobs:
  latest_docs:
    steps: [{with: {ansible-core-version: 2.20}}]
""")
        self.assertEqual(workflow_versions(data)[0], set())

    def test_unquoted_versions_preserved_and_comments_not_tested(self):
        data = document("""jobs:
  sanity:
    strategy:
      matrix:
        ansible: [2.20, stable-2.21, devel] # stable-2.15 is not tested
    steps:
      - with:
          ansible-core-version: ${{ matrix.ansible }}
""")
        self.assertEqual(workflow_versions(data)[0], {"2.20", "2.21", "devel"})

    def test_unrelated_matrix_does_not_claim_core_coverage(self):
        data = document("""jobs:
  docs:
    strategy:
      matrix:
        python: [3.10, 3.11]
        include: [{ansible_version: 2.19}]
    steps: [{run: echo docs}]
""")
        self.assertEqual(workflow_versions(data)[0], set())

    def test_include_and_version_only_exclude_are_applied(self):
        data = document("""jobs:
  test:
    strategy:
      matrix:
        ansible: [stable-2.16, stable-2.18]
        include: [{ansible: devel}]
        exclude: [{ansible: stable-2.16}]
    steps: [{with: {ansible-core-version: '${{ matrix.ansible }}'}}]
""")
        self.assertEqual(workflow_versions(data)[0], {"2.18", "devel"})

    def test_disabled_job_and_unresolved_expressions_are_not_versions(self):
        data = document("""jobs:
  disabled:
    if: false
    steps: [{with: {ansible-core-version: 2.17}}]
  dynamic:
    steps: [{with: {ansible-core-version: '${{ inputs.version }}'}}]
""")
        self.assertEqual(workflow_versions(data)[0], set())

    def test_azure_stage_uses_test_parameters_not_free_text(self):
        data = document("""stages:
  - stage: Ansible_2_20
    jobs: [{parameters: {testFormat: '2.20/{0}'}}]
  - stage: Ansible_devel
    jobs: [{parameters: {testFormat: 'devel/{0}'}}]
  - stage: Unrelated_2_19
    jobs: [{parameters: {testFormat: '2.19/{0}'}}]
  - stage: Ansible_2_16
    condition: false
    jobs: [{parameters: {testFormat: '2.16/{0}'}}]
""")
        self.assertEqual(azure_versions(data), {"2.20", "devel"})

    def test_missing_support_metadata_is_not_inferred_from_tests(self):
        api = GitHub()
        def get(path, params=None):
            if path.endswith("test.yml"):
                return file_response("jobs: {test: {steps: [{with: {ansible-core-version: 2.19}}]}}")
            raise APIError(404, "Not found")
        api.data = Mock(side_effect=get)
        result = collect_compatibility(api, {"full_name": "example/collection", "default_branch": "main"},
                                       [{"path": ".github/workflows/test.yml", "state": "active"}], "abc123")
        self.assertIsNone(result["supported"])
        self.assertEqual(result["tested"], ["2.19"])
        self.assertIn("/blob/abc123/", result["tested_sources"][0])

    def test_reusable_defaults_matrix_file_and_private_source_guard(self):
        api = GitHub()
        root = """jobs:
  setup:
    steps: [{run: 'yq .github/test-matrix.yaml'}]
  test:
    strategy: {matrix: '${{ fromJSON(needs.setup.outputs.matrix) }}'}
    steps: [{with: {ansible-core-version: '${{ matrix.ansible }}'}}]
  reused:
    uses: public/ci/.github/workflows/test.yml@v1
  private:
    uses: private/ci/.github/workflows/test.yml@v1
"""
        reusable = """on:
  workflow_call:
    inputs:
      ansible-core-version: {default: 2.18}
jobs:
  test:
    steps: [{with: {ansible-core-version: '${{ inputs.ansible-core-version }}'}}]
"""
        def get(path, params=None):
            if path == "/repos/public/ci": return {"private": False}
            if path == "/repos/private/ci": return {"private": True}
            if path.startswith("/repos/private/ci/contents/"): self.fail("Private reusable workflow was read")
            if path.endswith("meta/runtime.yml"): return file_response('requires_ansible: ">=2.16.0"')
            if path.endswith(".github/test-matrix.yaml"): return file_response("ansible: [stable-2.20, devel]")
            if path == "/repos/example/collection/contents/.github/workflows/test.yml": return file_response(root)
            if path == "/repos/public/ci/contents/.github/workflows/test.yml": return file_response(reusable)
            raise APIError(404, "Not found")
        api.data = Mock(side_effect=get)
        result = collect_compatibility(api, {"full_name": "example/collection", "default_branch": "main"},
                                       [{"path": ".github/workflows/test.yml", "state": "active"}], "abc123")
        self.assertEqual(result["supported"], ">=2.16.0")
        self.assertEqual(result["tested"], ["2.18", "2.20", "devel"])


if __name__ == "__main__":
    unittest.main()
