"""Read declared Core requirements and configured CI versions without executing CI."""
import base64
import json
import re
from urllib.parse import quote

import yaml

CORE_KEYS = {"ansible-core-version", "ansible-version", "ansible_version", "ansible_core_version"}
VERSION = re.compile(r"^(?:stable-|v)?(2\.\d+(?:\.\d+)?|devel|milestone)$")
MATRIX_VAR = re.compile(r"matrix\.([\w-]+)")
INPUT_VAR = re.compile(r"^\$\{\{\s*inputs\.([\w-]+)\s*\}\}$")
REUSABLE = re.compile(r"^([\w.-]+/[\w.-]+)/(.github/workflows/[\w./-]+)@(.+)$")
MATRIX_FILE = re.compile(r"(?<![\w/])(?:\.github|tests)/[\w./-]*matrix[\w.-]*\.(?:ya?ml|json)\b")
CORE_INSTALL = re.compile(
    r"(?:https?://github\.com/ansible/ansible/archive/(?:refs/heads/)?|"
    r"(?:git\+)?https?://github\.com/ansible/ansible(?:\.git)?@|ansible-core==)"
    r"(\$\{\{[^}]+\}\}|(?:stable-)?2\.\d+(?:\.\d+)?|devel|milestone)"
)


def document(text):
    # BaseLoader preserves version strings such as unquoted 2.20 and cannot build objects.
    result = yaml.load(text, Loader=yaml.BaseLoader)
    return result if isinstance(result, dict) else {}


def versions(values):
    result = set()
    if isinstance(values, str):
        match = VERSION.fullmatch(values.strip())
        if match:
            result.add(match.group(1))
        elif values.strip().startswith("["):
            try:
                result.update(versions(json.loads(values)))
            except (ValueError, TypeError):
                pass
    elif isinstance(values, list):
        for value in values:
            result.update(versions(value))
    return result


def matrix_versions(matrix, variables):
    if not isinstance(matrix, dict):
        return set()
    result = set()
    for variable in variables:
        result.update(versions(matrix.get(variable)))
        for entry in matrix.get("include", []) if isinstance(matrix.get("include", []), list) else []:
            if isinstance(entry, dict):
                result.update(versions(entry.get(variable)))
        # A version-only exclusion removes the whole version; multi-axis exclusions do not.
        for entry in matrix.get("exclude", []) if isinstance(matrix.get("exclude", []), list) else []:
            if isinstance(entry, dict) and set(entry) == {variable}:
                result.difference_update(versions(entry[variable]))
    return result


def bindings(node):
    result = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "strategy":
                continue
            if str(key).casefold() in CORE_KEYS:
                result.append(value)
            elif isinstance(value, (dict, list)):
                result.extend(bindings(value))
    elif isinstance(node, list):
        for value in node:
            result.extend(bindings(value))
    return result


def workflow_versions(data, inputs=None):
    found, matrix_variables = set(), set()
    for name, job in data.get("jobs", {}).items() if isinstance(data.get("jobs"), dict) else []:
        if not isinstance(job, dict) or str(job.get("if", "")).strip() in {"false", "${{ false }}"}:
            continue
        context = " ".join([name, str(job.get("name", "")), str(job.get("uses", ""))] + [
            str(step.get("uses", "")) for step in job.get("steps", []) if isinstance(step, dict)
        ])
        if not re.search(r"(?<![a-z])(?:tests?|testing|sanity|units?|integration|certification|molecule)(?![a-z])", context, re.I):
            continue
        variables = set()
        core_bindings = bindings(job)
        for step in job.get("steps", []):
            if not isinstance(step, dict) or not isinstance(step.get("run"), str):
                continue
            for command in step["run"].splitlines():
                if re.match(r"\s*(?:python[\d.]*\s+-m\s+)?pip3?\s+install\b", command):
                    core_bindings.extend(CORE_INSTALL.findall(command))
        for binding in core_bindings:
            if not isinstance(binding, str):
                continue
            input_match = INPUT_VAR.fullmatch(binding.strip())
            if input_match:
                binding = (inputs or {}).get(input_match.group(1), "")
            found.update(versions(binding))
            variables.update(MATRIX_VAR.findall(str(binding)))
        strategy = job.get("strategy") if isinstance(job.get("strategy"), dict) else {}
        found.update(matrix_versions(strategy.get("matrix"), variables))
        matrix_variables.update(variables)
    return found, matrix_variables


def azure_versions(data):
    found = set()
    for stage in data.get("stages", []) if isinstance(data.get("stages", []), list) else []:
        if not isinstance(stage, dict) or str(stage.get("condition", "")).strip() == "false":
            continue
        if not str(stage.get("stage", "")).startswith("Ansible_"):
            continue
        for job in stage.get("jobs", []):
            if isinstance(job, dict):
                value = job.get("parameters", {}).get("testFormat", "")
                if isinstance(value, str):
                    found.update(versions(value.split("/", 1)[0]))
    return found


def source_url(slug, ref, path):
    return f"https://github.com/{slug}/blob/{quote(ref, safe='')}/{quote(path, safe='/')}"


def collect_compatibility(api, repo, workflows, head_sha):
    slug = repo["full_name"]
    ref = head_sha or repo.get("default_branch") or "HEAD"
    result = {"supported": None, "tested": [], "supported_source": None,
              "tested_sources": [], "basis": "default_branch", "notes": []}
    cache = getattr(api, "compatibility_cache", None)
    if cache is None:
        cache = api.compatibility_cache = {}

    def read(owner_repo, path, revision):
        key = (owner_repo, path, revision)
        if key in cache:
            return cache[key]
        try:
            response = api.data(f"/repos/{owner_repo}/contents/{path}", {"ref": revision})
            text = base64.b64decode(response["content"], validate=False).decode("utf-8") if (
                isinstance(response, dict) and response.get("type") == "file"
                and response.get("encoding") == "base64" and response.get("size", 0) <= 500_000
            ) else None
        except (RuntimeError, ValueError, UnicodeError, KeyError) as error:
            if getattr(error, "status", None) != 404:
                result["notes"].append(f"Could not read {path}")
            text = None
        cache[key] = text
        return text

    def parse(text, path):
        try:
            return document(text) if text else {}
        except yaml.YAMLError:
            result["notes"].append(f"Could not parse {path}")
            return {}

    metadata = parse(read(slug, "meta/runtime.yml", ref), "meta/runtime.yml")
    if isinstance(metadata.get("requires_ansible"), str):
        result["supported"] = metadata["requires_ansible"]
        result["supported_source"] = source_url(slug, ref, "meta/runtime.yml")
    tested = set()

    def record(found, owner_repo, revision, path):
        if found:
            tested.update(found)
            url = source_url(owner_repo, revision, path)
            if url not in result["tested_sources"]:
                result["tested_sources"].append(url)

    def scan(owner_repo, path, revision, inputs=None, depth=0):
        text = read(owner_repo, path, revision)
        data = parse(text, path)
        found, variables = workflow_versions(data, inputs)
        record(found, owner_repo, revision, path)
        for job in data.get("jobs", {}).values() if isinstance(data.get("jobs"), dict) else []:
            if not isinstance(job, dict) or str(job.get("if", "")).strip() in {"false", "${{ false }}"}:
                continue
            for step in job.get("steps", []):
                if not isinstance(step, dict) or not isinstance(step.get("run"), str):
                    continue
                commands = "\n".join(line for line in step["run"].splitlines() if not line.lstrip().startswith("#"))
                for matrix_path in set(MATRIX_FILE.findall(commands)):
                    matrix = parse(read(owner_repo, matrix_path, revision), matrix_path)
                    record(matrix_versions(matrix, variables), owner_repo, revision, matrix_path)
            match = REUSABLE.fullmatch(str(job.get("uses", "")))
            if match and depth == 0:
                called_slug, called_path, called_ref = match.groups()
                public_key = (called_slug, "public")
                if public_key not in cache:
                    try:
                        external = api.data(f"/repos/{called_slug}")
                        cache[public_key] = (isinstance(external, dict) and external.get("private") is False
                                             and external.get("visibility", "public") == "public")
                    except RuntimeError:
                        cache[public_key] = False
                if not cache[public_key]:
                    continue
                called = parse(read(called_slug, called_path, called_ref), called_path)
                triggers = called.get("on") if isinstance(called.get("on"), dict) else {}
                invocation = triggers.get("workflow_call") if isinstance(triggers.get("workflow_call"), dict) else {}
                default_inputs = invocation.get("inputs", {})
                resolved = {name: options.get("default", "") for name, options in default_inputs.items()
                            if isinstance(options, dict)} if isinstance(default_inputs, dict) else {}
                resolved.update(job.get("with", {}) if isinstance(job.get("with"), dict) else {})
                scan(called_slug, called_path, called_ref, resolved, depth=1)

    for workflow in workflows or []:
        if workflow.get("state") == "active" and isinstance(workflow.get("path"), str):
            scan(slug, workflow["path"], ref)
    for path in (".azure-pipelines/azure-pipelines.yml", "azure-pipelines.yml"):
        azure = parse(read(slug, path, ref), path)
        record(azure_versions(azure), slug, ref, path)

    def sort_key(version):
        return (0, tuple(map(int, version.split(".")))) if version[0].isdigit() else (1, version)
    result["tested"] = sorted(tested, key=sort_key)
    result["notes"] = list(dict.fromkeys(result["notes"]))
    return result
