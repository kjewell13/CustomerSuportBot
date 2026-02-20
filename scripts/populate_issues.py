#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List

try:
    import yaml  # pip dependency in workflow
except ImportError:
    print("Missing dependency: pyyaml. Install it or run via GitHub Actions workflow.")
    sys.exit(1)


GITHUB_API = "https://api.github.com"


def gh_request(method: str, url: str, token: str, data: Dict[str, Any] | None = None) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "issues-yaml-importer",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API error {e.code} for {method} {url}: {err_body}") from e


def issue_exists(owner: str, repo: str, token: str, title: str) -> bool:
    # Search issues/PRs by title in repo
    q = urllib.parse.quote(f'repo:{owner}/{repo} is:issue in:title "{title}"')
    url = f"{GITHUB_API}/search/issues?q={q}"
    res = gh_request("GET", url, token)
    return bool(res.get("total_count", 0))


def create_issue(owner: str, repo: str, token: str, title: str, body: str, labels: List[str]) -> None:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    payload: Dict[str, Any] = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    gh_request("POST", url, token, payload)


def main() -> int:
    yaml_path = os.getenv("ISSUES_YAML_PATH", ".issue-seeds/issues.yml")
    repo_full = os.getenv("GITHUB_REPOSITORY")  # e.g. owner/repo
    token = os.getenv("GITHUB_TOKEN")

    if not repo_full or "/" not in repo_full:
        print("GITHUB_REPOSITORY is missing or invalid.")
        return 1
    if not token:
        print("GITHUB_TOKEN is missing.")
        return 1

    owner, repo = repo_full.split("/", 1)

    if not os.path.exists(yaml_path):
        print(f"YAML file not found: {yaml_path}")
        return 1

    with open(yaml_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    issues = doc.get("issues", [])
    if not isinstance(issues, list) or not issues:
        print("No issues found under top-level key `issues:`.")
        return 1

    created = 0
    skipped = 0

    for item in issues:
        title = (item.get("title") or "").strip()
        topic = (item.get("topic") or "").strip()
        labels = item.get("labels") or []
        body = (item.get("body") or "").rstrip()

        if not title or not body:
            print(f"Skipping invalid issue item (missing title/body): {item}")
            skipped += 1
            continue

        # Optionally include topic as a label if not already
        if topic and topic not in labels:
            labels = [topic] + labels

        if issue_exists(owner, repo, token, title):
            print(f"SKIP (already exists): {title}")
            skipped += 1
            continue

        create_issue(owner, repo, token, title, body, labels)
        print(f"CREATED: {title}")
        created += 1

    print(f"Done. Created={created}, Skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
