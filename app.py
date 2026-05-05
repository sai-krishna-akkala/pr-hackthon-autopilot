from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib import error, parse, request

import streamlit as st


st.set_page_config(page_title="PR Review Runner", page_icon="🤖", layout="wide")


def _bot_dir() -> Path:
    return Path(__file__).resolve().parent / "bot"


def _github_get_json(url: str, token: str) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pr-review-runner",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_pr_responses(repository: str, pr_number: int, token: str) -> tuple[dict, list, list, list]:
    repo = repository.strip()
    if "/" not in repo:
        raise ValueError("GITHUB_REPOSITORY must be in the format owner/repo")

    encoded_repo = parse.quote(repo, safe="/")
    base = f"https://api.github.com/repos/{encoded_repo}"

    pr_meta = _github_get_json(f"{base}/pulls/{pr_number}", token)
    issue_comments = _github_get_json(f"{base}/issues/{pr_number}/comments?per_page=100", token)
    reviews = _github_get_json(f"{base}/pulls/{pr_number}/reviews?per_page=100", token)
    inline_comments = _github_get_json(f"{base}/pulls/{pr_number}/comments?per_page=100", token)

    if not isinstance(pr_meta, dict):
        raise ValueError("Unable to parse PR metadata from GitHub")
    if not isinstance(issue_comments, list):
        issue_comments = []
    if not isinstance(reviews, list):
        reviews = []
    if not isinstance(inline_comments, list):
        inline_comments = []

    return pr_meta, issue_comments, reviews, inline_comments


def _build_response_items(
    repository: str,
    pr_number: int,
    pr_meta: dict,
    issue_comments: list,
    reviews: list,
    inline_comments: list,
) -> list[dict]:
    head_ref = (pr_meta.get("head") or {}).get("ref", "")
    items: list[dict] = []

    for comment in issue_comments:
        items.append(
            {
                "repository": repository,
                "pr_number": str(pr_number),
                "branch": head_ref,
                "type": "Top-level Comment",
                "user": (comment.get("user") or {}).get("login", "unknown"),
                "created_at": comment.get("created_at", ""),
                "body": comment.get("body", ""),
                "meta": "",
            }
        )

    for review in reviews:
        state = review.get("state", "")
        items.append(
            {
                "repository": repository,
                "pr_number": str(pr_number),
                "branch": head_ref,
                "type": "Review Summary",
                "user": (review.get("user") or {}).get("login", "unknown"),
                "created_at": review.get("submitted_at") or review.get("created_at", ""),
                "body": review.get("body", ""),
                "meta": f"State: {state}",
            }
        )

    for inline_comment in inline_comments:
        path = inline_comment.get("path", "")
        line = inline_comment.get("line") or inline_comment.get("original_line")
        items.append(
            {
                "repository": repository,
                "pr_number": str(pr_number),
                "branch": head_ref,
                "type": "Inline Comment",
                "user": (inline_comment.get("user") or {}).get("login", "unknown"),
                "created_at": inline_comment.get("created_at", ""),
                "body": inline_comment.get("body", ""),
                "meta": f"{path}:{line}" if path and line else path,
            }
        )

    return items


def _upsert_response_entry(entry: dict) -> None:
    entries: list[dict] = st.session_state["response_entries"]
    target_key = f"{entry['repository']}#{entry['pr_number']}"
    replaced = False
    for idx, existing in enumerate(entries):
        existing_key = f"{existing['repository']}#{existing['pr_number']}"
        if existing_key == target_key:
            entries[idx] = entry
            replaced = True
            break
    if not replaced:
        entries.append(entry)
    st.session_state["response_entries"] = entries


def _render_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: #f6f8fb;
            }
            .pr-hero {
                background: #ffffff;
                border: 1px solid #e6e9ef;
                border-radius: 12px;
                padding: 16px 18px;
                margin-bottom: 12px;
            }
            .trust-banner {
                background: #eef8f1;
                border: 1px solid #cfe8d6;
                color: #1f6b3a;
                border-radius: 10px;
                padding: 10px 12px;
                margin: 8px 0 12px 0;
                font-weight: 500;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _backend_status() -> dict:
    provider = (os.getenv("LLM_PROVIDER", "groq") or "groq").lower()
    has_github = bool(os.getenv("GITHUB_TOKEN"))
    has_groq = bool(os.getenv("GROQ_API_KEY"))
    has_claude = bool(os.getenv("ANTHROPIC_API_KEY"))

    if provider == "claude":
        has_llm = has_claude
        llm_label = "Anthropic"
    else:
        has_llm = has_groq
        llm_label = "Groq"

    return {
        "provider": provider,
        "has_github": has_github,
        "has_llm": has_llm,
        "llm_label": llm_label,
    }


def _load_pr_responses(repository: str, pr_number_text: str, github_token: str) -> dict | None:
    if not repository or not pr_number_text:
        st.warning("Enter repository and PR number in the sidebar.")
        return None

    try:
        pr_number = int(pr_number_text)
    except ValueError:
        st.error("PR_NUMBER must be an integer.")
        return None

    try:
        with st.spinner("Loading PR responses from GitHub..."):
            pr_meta, issue_comments, reviews, inline_comments = _fetch_pr_responses(
                repository=repository,
                pr_number=pr_number,
                token=github_token,
            )
    except error.HTTPError as http_err:
        details = http_err.read().decode("utf-8", errors="ignore")
        st.error(f"GitHub API error: HTTP {http_err.code}")
        st.code(details or "(no error body)", language="json")
        return None
    except Exception as exc:
        st.error(f"Failed to load PR responses: {exc}")
        return None

    entry = {
        "repository": repository,
        "pr_number": str(pr_number),
        "pr_title": pr_meta.get("title", ""),
        "pr_state": pr_meta.get("state", ""),
        "pr_url": pr_meta.get("html_url", ""),
        "branch": (pr_meta.get("head") or {}).get("ref", ""),
        "base_branch": (pr_meta.get("base") or {}).get("ref", ""),
        "loaded_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "items": _build_response_items(
            repository=repository,
            pr_number=pr_number,
            pr_meta=pr_meta,
            issue_comments=issue_comments,
            reviews=reviews,
            inline_comments=inline_comments,
        ),
        "counts": {
            "top_level": len(issue_comments),
            "reviews": len(reviews),
            "inline": len(inline_comments),
        },
    }
    _upsert_response_entry(entry)
    st.session_state["active_entry_key"] = f"{repository}#{pr_number}"
    return entry


def _render_response_panel(repo_filter: str, branch_filter: str, pr_filter: str) -> None:
    st.subheader("Review Timeline")
    entries: list[dict] = st.session_state.get("response_entries", [])
    if not entries:
        st.info("No responses loaded yet. Use 'Load PR Responses' from the sidebar.")
        return

    filtered_items: list[dict] = []
    for entry in entries:
        repository = entry.get("repository", "")
        branch = entry.get("branch", "")
        pr_number = entry.get("pr_number", "")

        if repo_filter and repo_filter.lower() not in repository.lower():
            continue
        if branch_filter and branch_filter.lower() not in branch.lower():
            continue
        if pr_filter and pr_filter.lower() not in str(pr_number).lower():
            continue

        filtered_items.extend(entry.get("items", []))

    filtered_items.sort(key=lambda item: item.get("created_at", ""), reverse=True)

    st.caption(f"Showing {len(filtered_items)} response items")
    if not filtered_items:
        st.warning("No response items match the current filters.")
        return

    for idx, item in enumerate(filtered_items, start=1):
        header = (
            f"{idx}. {item['type']} | {item['repository']} | PR #{item['pr_number']} | "
            f"{item['branch']} | {item['user']}"
        )
        with st.expander(header, expanded=False):
            st.write(f"Created: {item.get('created_at', '')}")
            if item.get("meta"):
                st.write(item["meta"])
            st.write(item.get("body") or "(no body text)")


def _render_active_pr_summary(branch_name: str) -> None:
    key = st.session_state.get("active_entry_key", "")
    entries: list[dict] = st.session_state.get("response_entries", [])
    active = None
    for entry in entries:
        entry_key = f"{entry['repository']}#{entry['pr_number']}"
        if entry_key == key:
            active = entry
            break

    if not active:
        return

    st.subheader("Active PR")
    st.write(f"Repository: {active['repository']}")
    st.write(f"PR: #{active['pr_number']} — {active['pr_title']}")
    st.write(f"State: {active['pr_state']}")
    st.write(f"Branch: {active['branch']} → {active['base_branch']}")
    st.write(f"Loaded at: {active['loaded_at']}")
    if active.get("pr_url"):
        st.markdown(f"PR Link: {active['pr_url']}")

    counts = active.get("counts", {})
    m1, m2, m3 = st.columns(3)
    m1.metric("Top-level", counts.get("top_level", 0))
    m2.metric("Reviews", counts.get("reviews", 0))
    m3.metric("Inline", counts.get("inline", 0))

    if branch_name:
        if branch_name == active["branch"]:
            st.success(f"Selected branch '{branch_name}' matches PR head branch.")
        else:
            st.warning(
                f"Selected branch '{branch_name}' does not match PR head branch '{active['branch']}'."
            )


def main() -> None:
    if "response_entries" not in st.session_state:
        st.session_state["response_entries"] = []
    if "active_entry_key" not in st.session_state:
        st.session_state["active_entry_key"] = ""

    _render_styles()

    st.markdown(
        """
        <div class="pr-hero">
            <h3 style="margin:0;">PR Review Workspace</h3>
            <p style="margin:4px 0 0 0; color:#4b5563;">Select repository context and review PR responses without entering secrets in the UI.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    bot_dir = _bot_dir()
    if not (bot_dir / "index.js").exists():
        st.error("Missing bot/index.js. Ensure bot folder exists in this repository.")
        return

    backend = _backend_status()
    if backend["has_github"] and backend["has_llm"]:
        st.markdown(
            f"<div class='trust-banner'>✅ Secure backend credentials active · GitHub + {backend['llm_label']} connected</div>",
            unsafe_allow_html=True,
        )
    else:
        st.warning(
            f"Backend credentials are incomplete. Required: GITHUB_TOKEN and {backend['llm_label']} API key in environment."
        )

    with st.sidebar:
        st.header("Context Selector")
        repository = st.text_input("Repository (owner/repo)", value=os.getenv("GITHUB_REPOSITORY", ""))
        pr_number = st.text_input("PR Number", value=os.getenv("PR_NUMBER", ""))
        branch_name = st.text_input("Branch (optional)", value=os.getenv("BRANCH_NAME", ""))

        st.header("Connection Status")
        st.caption("Credentials are managed server-side.")
        st.write(f"GitHub: {'🟢 Connected' if backend['has_github'] else '🔴 Missing'}")
        st.write(f"LLM ({backend['llm_label']}): {'🟢 Connected' if backend['has_llm'] else '🔴 Missing'}")
        st.write(f"Provider: {backend['provider']}")

        st.header("Actions")
        load_clicked = st.button("Load PR Responses", use_container_width=True)
        run_clicked = st.button("Run Bot", type="primary", use_container_width=True)
        st.caption("No personal tokens required")

    if load_clicked:
        loaded = _load_pr_responses(
            repository=repository,
            pr_number_text=pr_number,
            github_token=os.getenv("GITHUB_TOKEN", ""),
        )
        if loaded:
            st.success("PR responses loaded successfully.")

    left_col, right_col = st.columns([1.05, 1.95], gap="large")

    with left_col:
        _render_active_pr_summary(branch_name=branch_name)
        st.markdown("---")
        st.subheader("Bot Runner")
        st.caption("Runs with backend-managed credentials.")
        if run_clicked:
            missing = []
            if not repository:
                missing.append("GITHUB_REPOSITORY")
            if not pr_number:
                missing.append("PR_NUMBER")

            provider = (os.getenv("LLM_PROVIDER", "groq") or "groq").lower()
            github_token = os.getenv("GITHUB_TOKEN", "")
            groq_key = os.getenv("GROQ_API_KEY", "")
            claude_key = os.getenv("ANTHROPIC_API_KEY", "")

            if not github_token:
                missing.append("GITHUB_TOKEN")
            if provider == "groq" and not groq_key:
                missing.append("GROQ_API_KEY")
            if provider == "claude" and not claude_key:
                missing.append("ANTHROPIC_API_KEY")

            if missing:
                st.error("Missing required fields: " + ", ".join(missing))
                return

            env = os.environ.copy()
            env.update(
                {
                    "GITHUB_REPOSITORY": repository,
                    "PR_NUMBER": pr_number,
                    "GITHUB_TOKEN": github_token,
                    "LLM_PROVIDER": provider,
                    "GROQ_API_KEY": groq_key,
                    "ANTHROPIC_API_KEY": claude_key,
                }
            )

            with st.spinner("Running bot..."):
                result = subprocess.run(
                    ["node", "index.js"],
                    cwd=str(bot_dir),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

            out_text = (result.stdout or "").strip()
            err_text = (result.stderr or "").strip()
            combined = "\n".join([part for part in [out_text, err_text] if part])

            if result.returncode == 0:
                st.success("Bot completed successfully. Refreshing PR responses...")
                _load_pr_responses(
                    repository=repository,
                    pr_number_text=pr_number,
                    github_token=os.getenv("GITHUB_TOKEN", ""),
                )
            else:
                st.error(f"Bot failed with exit code {result.returncode}")

            tabs = st.tabs(["Stdout", "Stderr", "Combined Logs"])
            with tabs[0]:
                st.code(out_text or "(no stdout)", language="bash")
            with tabs[1]:
                st.code(err_text or "(no stderr)", language="bash")
            with tabs[2]:
                st.code(combined or "(no output captured)", language="bash")

    with right_col:
        f1, f2, f3 = st.columns(3)
        with f1:
            repo_filter = st.text_input("Filter by Repo", value=repository)
        with f2:
            branch_filter = st.text_input("Filter by Branch", value=branch_name)
        with f3:
            pr_filter = st.text_input("Filter by PR", value=pr_number)

        _render_response_panel(
            repo_filter=repo_filter,
            branch_filter=branch_filter,
            pr_filter=pr_filter,
        )


if __name__ == "__main__":
    main()
