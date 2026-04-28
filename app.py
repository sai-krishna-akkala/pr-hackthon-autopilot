from __future__ import annotations

import os
import re
import shutil
import subprocess
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from auth_store import (
    authenticate_user,
    create_user,
    init_db,
    list_review_runs,
    save_review_run,
)


load_dotenv(Path(__file__).resolve().parent / ".env")
st.set_page_config(page_title="PR Review Portal", page_icon="🤖", layout="wide")

PR_URL_PATTERN = re.compile(r"^https?://github\.com/(?P<repo>[^/]+/[^/]+)/pull/(?P<pr>\d+)/?$", re.IGNORECASE)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _bot_dir() -> Path:
    return _repo_root() / "bot"


def _init_session_state() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_email", "")


def _backend_groq_key() -> str:
    return os.getenv("GROQ_API_KEY", "").strip()


def _parse_pr_target(pr_url: str, repository: str, pr_number: str) -> tuple[str, str, str | None]:
    pr_url = pr_url.strip()
    repository = repository.strip()
    pr_number = pr_number.strip()

    if pr_url:
        match = PR_URL_PATTERN.match(pr_url)
        if not match:
            return "", "", "Enter a valid GitHub PR URL like https://github.com/owner/repo/pull/123"
        return match.group("repo"), match.group("pr"), None

    if not repository:
        return "", "", "Repository is required when PR URL is empty."
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
        return "", "", "Repository must be in owner/repo format."
    if not pr_number.isdigit():
        return "", "", "PR number must be a whole number."
    return repository, pr_number, None


def _resolve_pr_number_from_branches(
    repository: str,
    github_token: str,
    head_branch: str,
    base_branch: str,
) -> tuple[str | None, str | None]:
    repository = repository.strip()
    head_branch = head_branch.strip()
    base_branch = base_branch.strip()

    if not re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
        return None, "Repository must be in owner/repo format."
    if not head_branch:
        return None, "Head branch is required when PR number is empty."

    owner = repository.split("/", maxsplit=1)[0]
    params = {"state": "open", "head": f"{owner}:{head_branch}"}
    if base_branch:
        params["base"] = base_branch

    url = f"https://api.github.com/repos/{repository}/pulls?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pr-review-portal",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as err:
        return None, f"GitHub API error while resolving PR from branches: {err.code}."
    except URLError as err:
        return None, f"Network error while resolving PR from branches: {err.reason}."

    try:
        import json

        pulls = json.loads(payload)
    except Exception:
        return None, "Unable to parse GitHub response while resolving PR from branches."

    if not isinstance(pulls, list) or not pulls:
        base_hint = f" and base '{base_branch}'" if base_branch else ""
        return None, f"No open PR found for head branch '{head_branch}'{base_hint} in {repository}."

    first_pr = pulls[0]
    pr_number = first_pr.get("number")
    if not pr_number:
        return None, "GitHub returned an invalid PR response for branch lookup."

    return str(pr_number), None


def _check_node_runtime() -> tuple[bool, str]:
    if shutil.which("node") is None:
        return False, "Node.js 18+ is required and was not found on this machine."

    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except OSError as exc:
        return False, f"Unable to start Node.js: {exc}"

    version = (result.stdout or result.stderr or "").strip()
    if result.returncode != 0:
        return False, f"Unable to read Node.js version. Output: {version or 'unknown error'}"

    major_match = re.search(r"(\d+)", version)
    if not major_match or int(major_match.group(1)) < 18:
        return False, f"Node.js 18+ is required. Current version: {version or 'unknown'}"

    return True, version


def _npm_executable() -> str | None:
    candidates = ["npm.cmd", "npm"] if os.name == "nt" else ["npm"]
    for candidate in candidates:
        if shutil.which(candidate):
            return candidate
    return None


def _ensure_bot_dependencies(bot_dir: Path) -> tuple[bool, str]:
    package_json = bot_dir / "package.json"
    index_file = bot_dir / "index.js"
    if not package_json.exists() or not index_file.exists():
        return False, "The PR review bot files are incomplete. Expected bot/index.js and bot/package.json."

    node_modules = bot_dir / "node_modules"
    if node_modules.exists():
        return True, "Bot dependencies are ready."

    npm_exec = _npm_executable()
    if not npm_exec:
        return (
            False,
            "npm is not available on this machine. Install Node.js (which includes npm), then restart the app.",
        )

    try:
        result = subprocess.run(
            [npm_exec, "install", "--no-fund", "--no-audit"],
            cwd=str(bot_dir),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except OSError as exc:
        return False, f"Unable to install bot dependencies with npm: {exc}"

    output = "\n".join(part for part in [(result.stdout or "").strip(), (result.stderr or "").strip()] if part)
    if result.returncode != 0:
        return False, output or "npm install failed."
    return True, output or "npm install completed successfully."


def _run_bot(repository: str, pr_number: str, github_token: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_REPOSITORY": repository,
            "PR_NUMBER": pr_number,
            "GITHUB_TOKEN": github_token,
            "LLM_PROVIDER": "groq",
            "GROQ_API_KEY": _backend_groq_key(),
        }
    )

    return subprocess.run(
        ["node", "index.js"],
        cwd=str(_bot_dir()),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def _extract_summary(log_text: str) -> dict[str, str]:
    patterns = {
        "risk_score": r"FINAL RISK SCORE\s*:\s*(.+)",
        "risk_level": r"RISK LEVEL\s*:\s*(.+)",
        "decision": r"DECISION\s*:\s*(.+)",
        "total_issues": r"TOTAL ISSUES\s*:\s*(.+)",
    }

    summary: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, log_text)
        if match:
            summary[key] = match.group(1).strip()
    return summary


def _save_run_record(
    *,
    user_email: str,
    repository: str,
    pr_number: str,
    head_branch: str,
    base_branch: str,
    status: str,
    return_code: int | None,
    summary: dict[str, str],
    stdout_text: str,
    stderr_text: str,
    combined_logs: str,
    error_message: str,
) -> None:
    save_review_run(
        user_email=user_email,
        repository=repository,
        pr_number=pr_number,
        head_branch=head_branch,
        base_branch=base_branch,
        status=status,
        return_code=return_code,
        risk_score=summary.get("risk_score", "N/A"),
        risk_level=summary.get("risk_level", "N/A"),
        decision=summary.get("decision", "N/A"),
        total_issues=summary.get("total_issues", "N/A"),
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        combined_logs=combined_logs,
        error_message=error_message,
    )


def _render_run_result(
    *,
    deps_message: str,
    status: str,
    return_code: int | None,
    summary: dict[str, str],
    stdout_text: str,
    stderr_text: str,
    combined_logs: str,
    error_message: str,
) -> None:
    if status == "success":
        st.success("PR review completed successfully. The review comments were posted to GitHub.")
    else:
        failure_text = error_message or f"PR review failed with exit code {return_code}."
        st.error(failure_text)

    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    metric_col1.metric("Risk score", summary.get("risk_score", "N/A"))
    metric_col2.metric("Risk level", summary.get("risk_level", "N/A"))
    metric_col3.metric("Decision", summary.get("decision", "N/A"))
    metric_col4.metric("Total issues", summary.get("total_issues", "N/A"))

    with st.expander("Bot setup logs", expanded=False):
        st.code(deps_message or "No setup output.", language="bash")

    with st.expander("Stdout", expanded=status != "success"):
        st.code(stdout_text or "(no stdout)", language="bash")

    with st.expander("Stderr", expanded=status != "success"):
        st.code(stderr_text or "(no stderr)", language="bash")

    with st.expander("Combined logs", expanded=False):
        st.code(combined_logs or "(no output captured)", language="bash")


def _render_run_history(user_email: str) -> None:
    st.markdown("### Recent runs")
    runs = list_review_runs(user_email, limit=20)
    if not runs:
        st.info("No previous runs yet.")
        return

    options = []
    for run in runs:
        run_id = run.get("id")
        created_at = run.get("created_at", "")
        repo = run.get("repository") or "unknown-repo"
        pr_num = run.get("pr_number") or "N/A"
        status = run.get("status") or "unknown"
        options.append((f"#{run_id} | {created_at} | {repo} | PR {pr_num} | {status}", run))

    selected_label = st.selectbox(
        "Select a run",
        options=[label for label, _ in options],
        index=0,
        key="run_history_select",
    )
    selected_run = next(run for label, run in options if label == selected_label)

    summary = {
        "risk_score": selected_run.get("risk_score") or "N/A",
        "risk_level": selected_run.get("risk_level") or "N/A",
        "decision": selected_run.get("decision") or "N/A",
        "total_issues": selected_run.get("total_issues") or "N/A",
    }

    _render_run_result(
        deps_message="Loaded from run history.",
        status=selected_run.get("status") or "failed",
        return_code=selected_run.get("return_code"),
        summary=summary,
        stdout_text=selected_run.get("stdout_text") or "",
        stderr_text=selected_run.get("stderr_text") or "",
        combined_logs=selected_run.get("combined_logs") or "",
        error_message=selected_run.get("error_message") or "",
    )


def _render_login_screen() -> None:
    st.title("🤖 PR Review Portal")
    st.caption("Create an account, sign in with email and password, then run automated GitHub PR reviews.")

    login_tab, signup_tab = st.tabs(["Login", "Create account"])

    with login_tab:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="you@gmail.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", type="primary")

        if submitted:
            user = authenticate_user(email, password)
            if not user:
                st.error("Invalid email or password.")
            else:
                st.session_state.authenticated = True
                st.session_state.user_email = user["email"]
                st.success("Login successful.")
                st.rerun()

    with signup_tab:
        with st.form("signup_form", clear_on_submit=True):
            email = st.text_input("Email address", placeholder="you@gmail.com")
            password = st.text_input("Password", type="password", help="Use at least 8 characters with letters and numbers.")
            confirm_password = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account")

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                created, message = create_user(email, password)
                if created:
                    st.success(message)
                else:
                    st.error(message)


def _render_authenticated_app() -> None:
    with st.sidebar:
        st.success(f"Signed in as {st.session_state.user_email}")
        st.markdown("### Backend status")
        st.write("Groq API key: configured on server")
        st.write("LLM provider: Groq")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_email = ""
            st.rerun()

    st.title("🤖 GitHub PR Review Application")
    st.caption("Submit a pull request for review. The Groq API key stays on the backend and is never shown to users.")

    if not _backend_groq_key():
        st.error("Missing GROQ_API_KEY on the server. Add it to pr-review-repo-sample/.env before using this app.")
        st.stop()

    node_ok, node_message = _check_node_runtime()
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        st.info(f"Node.js status: {node_message}")
    with status_col2:
        st.info("Required user inputs: GitHub token + PR URL, or GitHub token + repository + PR number")

    if not node_ok:
        st.stop()

    with st.expander("GitHub token requirements", expanded=False):
        st.write(
            "Use a fine-grained GitHub token that can read pull requests and repository contents, and write pull request comments."
        )

    with st.form("review_form", clear_on_submit=False):
        pr_url = st.text_input("Pull request URL", placeholder="https://github.com/owner/repo/pull/123")
        col1, col2 = st.columns(2)
        with col1:
            repository = st.text_input("Repository", placeholder="owner/repo")
        with col2:
            pr_number = st.text_input("PR number", placeholder="123")

        branch_col1, branch_col2 = st.columns(2)
        with branch_col1:
            head_branch = st.text_input("Head branch (optional)", placeholder="feature/my-change")
        with branch_col2:
            base_branch = st.text_input("Base branch (optional)", placeholder="main")

        github_token = st.text_input("GitHub token", type="password")
        submitted = st.form_submit_button("Run PR review", type="primary")

    st.markdown("---")
    _render_run_history(st.session_state.user_email)

    if not submitted:
        return

    if not github_token.strip():
        st.error("GitHub token is required.")
        return

    repository_value, pr_number_value, error_message = _parse_pr_target(pr_url, repository, pr_number)
    if error_message and not pr_url.strip() and repository.strip() and head_branch.strip():
        resolved_pr, resolve_error = _resolve_pr_number_from_branches(
            repository=repository,
            github_token=github_token.strip(),
            head_branch=head_branch,
            base_branch=base_branch,
        )
        if resolve_error:
            st.error(resolve_error)
            _save_run_record(
                user_email=st.session_state.user_email,
                repository=repository.strip(),
                pr_number="",
                head_branch=head_branch.strip(),
                base_branch=base_branch.strip(),
                status="failed",
                return_code=None,
                summary={},
                stdout_text="",
                stderr_text="",
                combined_logs="",
                error_message=resolve_error,
            )
            return
        repository_value = repository.strip()
        pr_number_value = resolved_pr or ""
        st.info(f"Resolved open PR #{pr_number_value} from branch '{head_branch.strip()}'.")
    elif error_message:
        st.error(error_message)
        _save_run_record(
            user_email=st.session_state.user_email,
            repository=repository.strip(),
            pr_number=pr_number.strip(),
            head_branch=head_branch.strip(),
            base_branch=base_branch.strip(),
            status="failed",
            return_code=None,
            summary={},
            stdout_text="",
            stderr_text="",
            combined_logs="",
            error_message=error_message,
        )
        return

    with st.spinner("Preparing review bot dependencies..."):
        deps_ok, deps_message = _ensure_bot_dependencies(_bot_dir())
    if not deps_ok:
        st.error("Bot setup failed.")
        st.code(deps_message or "No setup logs were captured.", language="bash")
        _save_run_record(
            user_email=st.session_state.user_email,
            repository=repository_value,
            pr_number=pr_number_value,
            head_branch=head_branch.strip(),
            base_branch=base_branch.strip(),
            status="failed",
            return_code=None,
            summary={},
            stdout_text="",
            stderr_text="",
            combined_logs=deps_message,
            error_message="Bot setup failed.",
        )
        return

    with st.spinner("Running PR review..."):
        try:
            result = _run_bot(repository_value, pr_number_value, github_token.strip())
        except subprocess.TimeoutExpired:
            st.error("The PR review timed out after 10 minutes.")
            _save_run_record(
                user_email=st.session_state.user_email,
                repository=repository_value,
                pr_number=pr_number_value,
                head_branch=head_branch.strip(),
                base_branch=base_branch.strip(),
                status="failed",
                return_code=None,
                summary={},
                stdout_text="",
                stderr_text="",
                combined_logs="",
                error_message="The PR review timed out after 10 minutes.",
            )
            return
        except OSError as exc:
            st.error(f"Unable to start the PR review bot: {exc}")
            _save_run_record(
                user_email=st.session_state.user_email,
                repository=repository_value,
                pr_number=pr_number_value,
                head_branch=head_branch.strip(),
                base_branch=base_branch.strip(),
                status="failed",
                return_code=None,
                summary={},
                stdout_text="",
                stderr_text="",
                combined_logs="",
                error_message=f"Unable to start the PR review bot: {exc}",
            )
            return

    stdout_text = (result.stdout or "").strip()
    stderr_text = (result.stderr or "").strip()
    combined_logs = "\n".join(part for part in [stdout_text, stderr_text] if part)
    summary = _extract_summary(combined_logs)

    status = "success" if result.returncode == 0 else "failed"
    error_message = "" if status == "success" else f"PR review failed with exit code {result.returncode}."

    _save_run_record(
        user_email=st.session_state.user_email,
        repository=repository_value,
        pr_number=pr_number_value,
        head_branch=head_branch.strip(),
        base_branch=base_branch.strip(),
        status=status,
        return_code=result.returncode,
        summary=summary,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        combined_logs=combined_logs,
        error_message=error_message,
    )

    _render_run_result(
        deps_message=deps_message,
        status=status,
        return_code=result.returncode,
        summary=summary,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        combined_logs=combined_logs,
        error_message=error_message,
    )


def main() -> None:
    init_db()
    _init_session_state()

    if not st.session_state.authenticated:
        _render_login_screen()
        return

    _render_authenticated_app()


if __name__ == "__main__":
    main()
