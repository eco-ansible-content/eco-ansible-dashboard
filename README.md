# ECO Ansible dashboard

A public GitHub Pages dashboard for selected Ansible collection repositories. It shows default-branch GitHub Actions results, declared Ansible Core support and CI test coverage, the latest stable GitHub release, open pull requests, and new issues awaiting triage. Domain grouping and filtering, search, status filters, sorting, and expandable workflow details work entirely in the browser.

```text
Public repositories → scheduled collector → status.json → GitHub Pages
```

## Choose the collections

The dashboard is hosted in `eco-ansible-content/eco-ansible-dashboard`. Its 19 monitored repositories span `ansible-collections`, `ansible`, and `redhat-cop`, organized into seven domains: VMware, Microsoft / Windows, Splunk, ServiceNow, Cloud, Database, and Validated Content.

Edit `config/repos.json` to add or remove team repositories under `groups`. Keep `organizations` empty to monitor only these explicit selections. The dashboard preserves domain order, groups rows by domain, and provides a domain filter that combines with search and CI filters. Sorting applies within each domain; summary cards cover the whole team.

```json
{
  "title": "ECO Ansible",
  "organizations": [],
  "repositories": [],
  "groups": {
    "VMware": [
      "ansible-collections/vmware.vmware",
      "ansible-collections/vmware.vmware_rest"
    ],
    "Microsoft / Windows": [
      "ansible-collections/ansible.windows",
      "ansible-collections/microsoft.ad",
      "ansible-collections/microsoft.iis",
      "ansible-collections/microsoft.mecm",
      "ansible-collections/microsoft.scom",
      "ansible-collections/microsoft.scvmm",
      "ansible-collections/microsoft.hyperv"
    ],
    "Splunk": [
      "ansible-collections/splunk.es",
      "ansible-collections/splunk.enterprise",
      "ansible-collections/splunk.itsi",
      "ansible/splunk-eda-ta"
    ],
    "ServiceNow": [
      "ansible-collections/servicenow.itsm"
    ],
    "Cloud": [
      "ansible-collections/azure",
      "ansible-collections/google.cloud",
      "ansible-collections/ansible.oci"
    ],
    "Database": [
      "ansible-collections/ansible.mysql"
    ],
    "Validated Content": [
      "redhat-cop/infra.windows_ops"
    ]
  },
  "exclude": [
    "eco-ansible-content/eco-ansible-dashboard"
  ],
  "include_archived": false,
  "include_forks": true,
  "display_names": {
    "ansible-collections/azure": "azure.azcollection",
    "ansible/splunk-eda-ta": "splunk-eda-ta (EDA Technology Add-on)"
  },
  "workflows": {},
  "refresh_minutes": 30
}
```

The optional `repositories` list supports extra ungrouped repositories. Groups, explicit selections, and optional organization discovery are combined and deduplicated. `display_names` gives a repository a readable label while preserving its actual GitHub URL: `ansible-collections/azure` is shown as `azure.azcollection`, and the Splunk EDA Technology Add-on is labeled separately from collections.

Archived repositories are excluded by default; forks are included because a team's collection may be a fork. Private and internal repositories are never published, even when the collector's token can access them. An explicitly selected non-public repository makes collection fail.

By default, CI monitors all active Actions workflows. To monitor only your CI workflows, select exact workflow names or repository-relative paths per repository:

```json
"workflows": {
  "ansible-collections/ansible.windows": [".github/workflows/docs-push.yml"]
}
```

This is useful when release or scheduled maintenance workflows do not run on every commit. An empty list explicitly opts a repository out of CI monitoring. Unknown workflow names appear as unknown instead of silently disappearing.

## Publish on GitHub Pages

1. Push these files to the repository's `main` branch.
2. Open **Settings → Pages → Build and deployment → Source**, and choose **GitHub Actions**.
3. Under **Actions → Dashboard**, use **Run workflow** on `main` if the initial push ran before Pages was enabled.
4. Open the deployment URL shown under **Settings → Pages** or in the workflow's deployment.

The public site will normally be at <https://eco-ansible-content.github.io/eco-ansible-dashboard/>. Confirm the actual address in Pages settings after deployment.

The `Dashboard` workflow runs tests, collects the snapshot, uploads **only `site/`**, and deploys it through the `github-pages` environment. Refreshes are scheduled at minutes 7 and 37 of each hour (UTC by default). Repository pushes and manual workflow dispatches also refresh the site. Pull requests run tests only and do not deploy. The scheduled workflow must remain on the default branch; if you rename `main`, update the workflow's branch filters and build condition.

No personal access token or GitHub App is required for public data. GitHub Actions supplies its built-in token to the collector as `GH_TOKEN`. Credentials are used only during collection and are not included in the website or JSON. Organization policy must permit GitHub Actions, Pages, and the GitHub-owned actions used here.

Generated `site/data/status.json` is ignored by Git and deployed as part of the Pages artifact; each refresh does not create a commit. A discovery failure leaves the previous deployed website intact. Individual metric failures are published as incomplete data and shown on affected rows. Review the workflow's collection output for details.

## Run locally

Requires Python 3.10 or newer. Install the pinned YAML parser dependency before running the collector. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/collect_status.py
.venv/bin/python -m http.server 8000 --directory site
```

Visit <http://localhost:8000>. Public API collection can run without a token, but GitHub allows only 60 unauthenticated requests per hour. If already signed into the GitHub CLI, use your existing session without writing credentials to a file:

```bash
GH_TOKEN="$(gh auth token)" .venv/bin/python scripts/collect_status.py
```

Never commit a token. The **Reload snapshot** button reloads the published data; it does not trigger collection or bypass the workflow schedule.

## Interpret the results

- **Passing:** every monitored workflow's newest run on the current default-branch commit succeeded.
- **Failing:** at least one monitored workflow failed, timed out, or requires action.
- **Running:** a monitored workflow is queued, waiting, or running, with no known failure.
- **Unknown:** a monitored workflow has no run on the current commit, was skipped or cancelled, has a neutral/unknown conclusion, or a workflow selector does not match.
- **No CI:** no active workflows are monitored. This is distinct from passing.
- **Data error:** one or more metrics could not be collected. Missing counts remain unknown rather than becoming zero.

CI currently covers GitHub Actions workflows, not external CI providers' commit statuses. Releases refer to the latest stable GitHub release, not an Ansible Galaxy version or a prerelease. Open issue counts exclude pull requests. Metrics are fetched sequentially and represent a snapshot rather than an atomic view of all repositories.

A warning appears after the snapshot is older than three expected refresh intervals (at least 90 minutes). GitHub can delay scheduled jobs and disables schedules in public repositories after 60 days without repository activity. Re-enable the workflow from Actions if necessary. Changing `refresh_minutes` updates the displayed freshness expectation; change the workflow's cron schedule too if you change the actual cadence.

## Check changes

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
node --check site/app.js
```

Tests cover domain selection across organizations, domain validation, display labels, CI aggregation, current-commit matching, reruns, workflow selection, API pagination, private-data exclusion, and incomplete metrics.

References: [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages), [workflow triggers](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule), [workflow runs API](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository).

## Issue triage and Core compatibility

The **New issues** view includes open issues created in the past seven days, excluding pull requests. It defaults to **Needs triage**. An issue is flagged when it has a configured needs-triage label, or has no assignee/comments and no configured triaged label. Each issue shows the reason, labels, repository, and creation time. This heuristic is not proof that nobody has read an issue. Configure `triage.needs_triage_labels`, `triage.triaged_labels`, and `triage.include_no_activity` in `config/repos.json`; set the last option to `false` to use explicit labels only. Search, domain, label, and triage filters work together. Summary counts cover the whole team.

**Supported** Core versions come only from the current default branch's `meta/runtime.yml` `requires_ansible` field. **CI tested** versions mean configured coverage from explicit Ansible Core inputs, environment variables, and matrices in test jobs in active GitHub Actions workflows, directly referenced matrix files, public reusable workflows (one level), and Azure Pipelines Ansible-stage test parameters. Comments, disabled jobs, Python matrices, and unresolved expressions are not treated as Core versions. Sources link to the inspected commit or reusable workflow ref. CI coverage is not a statement that all tests passed, and unsupported CI formats appear as **Not declared** rather than inferred coverage. This is default-branch compatibility, not release-specific compatibility.

The interface uses a larger type scale and search field, shows detailed workflow and activity information only on expansion, and supports light/dark themes. It follows the system preference initially and stores an explicit theme choice in browser local storage. The redundant header logo has been removed.


## Red Hat visual language

The interface follows the [Red Hat design system](https://ux.redhat.com/) through locally defined design tokens and native HTML controls. It uses self-hosted Red Hat Display headings and Red Hat Text UI typography, neutral light/dark surfaces, a black masthead, red selected-view indicators, blue interactive elements, and shape-plus-label status indicators. It does not require the RHDS JavaScript component runtime or a third-party font CDN.

Reference guidance: [font family](https://ux.redhat.com/foundations/typography/font-family/), [colors](https://ux.redhat.com/foundations/color/), [tabs](https://ux.redhat.com/elements/tabs/style/), [buttons](https://ux.redhat.com/elements/button/style/), and [borders](https://ux.redhat.com/tokens/border/). Font sources and redistribution notices are in `site/fonts/`. `DESIGN.md` records the implemented tokens and component rules for future changes.
