from __future__ import annotations

import os
import subprocess
from pathlib import Path

import streamlit as st


st.set_page_config(page_title="PR Review Runner", page_icon="🤖", layout="wide")


def _bot_dir() -> Path:
    return Path(__file__).resolve().parent / "bot"


def main() -> None:
    st.title("🤖 PR Review Repo Runner")
    st.caption("Run the multi-agent JS review bot directly from this repository.")

    bot_dir = _bot_dir()
    if not (bot_dir / "index.js").exists():
        st.error("Missing bot/index.js. Ensure bot folder exists in this repository.")
        return

    c1, c2 = st.columns(2)
    with c1:
        repository = st.text_input("GITHUB_REPOSITORY", value=os.getenv("GITHUB_REPOSITORY", ""))
        pr_number = st.text_input("PR_NUMBER", value=os.getenv("PR_NUMBER", ""))
        provider = st.selectbox("LLM_PROVIDER", options=["groq", "claude"], index=0)
    with c2:
        github_token = st.text_input("GITHUB_TOKEN", value=os.getenv("GITHUB_TOKEN", ""), type="password")
        groq_key = st.text_input("GROQ_API_KEY", value=os.getenv("GROQ_API_KEY", ""), type="password")
        claude_key = st.text_input("ANTHROPIC_API_KEY", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password")

    st.markdown("---")
    st.subheader("One-time setup")
    st.code("cd bot\nnpm install", language="bash")

    if st.button("Run Bot", type="primary"):
        missing = []
        if not repository:
            missing.append("GITHUB_REPOSITORY")
        if not pr_number:
            missing.append("PR_NUMBER")
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
            st.success("Bot completed successfully. Check your PR comments on GitHub.")
        else:
            st.error(f"Bot failed with exit code {result.returncode}")

        st.markdown("**Stdout**")
        st.code(out_text or "(no stdout)", language="bash")
        st.markdown("**Stderr**")
        st.code(err_text or "(no stderr)", language="bash")
        st.markdown("**Combined Logs**")
        st.code(combined or "(no output captured)", language="bash")


if __name__ == "__main__":
    main()
