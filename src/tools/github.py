"""GitHub issue tool — lets the CLI/UI accept a GitHub issue URL as the task
input, fetching the issue title + body via the public REST API and handing
that to the Planner as the task description.
"""
import re
import requests

_ISSUE_URL_RE = re.compile(
    r"github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)/issues/(?P<number>\d+)"
)


def is_github_issue_url(text: str) -> bool:
    return bool(_ISSUE_URL_RE.search(text.strip()))


def fetch_issue_as_task(url: str) -> str:
    """Given a GitHub issue URL, return a task description string combining
    the issue title and body, suitable as input to the Planner agent."""
    match = _ISSUE_URL_RE.search(url.strip())
    if not match:
        raise ValueError(f"Not a recognizable GitHub issue URL: {url}")

    owner, repo, number = match["owner"], match["repo"], match["number"]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}"

    response = requests.get(api_url, timeout=10)
    response.raise_for_status()
    issue = response.json()

    title = (issue.get("title") or "").strip()
    body = (issue.get("body") or "").strip()

    task = f"{title}\n\n{body}".strip()
    if not task:
        raise ValueError(f"Issue #{number} in {owner}/{repo} has no title or body.")
    return task
