# ECO Ansible dashboard

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The Ecosystem Ansible Content team maintains selected public collection repositories across seven domains.

## Product Purpose

Show repository health, declared Ansible Core support, configured CI coverage, releases, open pull requests, and new issues that may need triage in one public dashboard.

## Capabilities and Constraints

Static HTML, CSS, and JavaScript hosted on GitHub Pages. A Python collector in GitHub Actions refreshes the public snapshot every 30 minutes. Retain the 19 configured repositories, domain filters, search, Actions filters, sorting, repository details, issue labels, approved triage heuristic, source links, stale/error states, and system-aware light/dark themes. CI coverage is configuration, not a claim that tests passed.

## Brand Commitments

The user requested Red Hat design language, using https://ux.redhat.com/ as authority, while retaining the cleaner direction of the existing dashboard. Preserve the ECO Ansible name and omit the redundant letter logo.

## Evidence on Hand

config/repos.json, the collector and tests, public GitHub metadata, and the current production dashboard. Use actual snapshots; never invent repository counts or compatibility.
