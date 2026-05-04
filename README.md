# PR Review Repo (Multi-User App)

This repository now includes a reusable PR review application with:

- email/password account creation and login
- a Streamlit UI for any user on your deployment
- backend-managed Groq configuration
- GitHub PR review execution through the existing JavaScript bot

Users only provide the GitHub information needed to run a review:

- GitHub token
- PR URL, or repository + PR number

The Groq API key stays on the server and is never shown in the UI.

## Repo Structure

- `app.py` – Streamlit application with authentication and PR review flow
- `auth_store.py` – SQLite-backed user account storage with hashed passwords
- `bot/` – JavaScript multi-agent PR review bot
- `src/` – sample Python code under review
- `tests/` – sample tests

## 1) Python setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

## 2) Backend environment setup

Copy `.env.example` to `.env` and set your backend secrets.

Required:

- `GROQ_API_KEY`

Optional tuning:

- `GROQ_MODEL`
- `GROQ_FALLBACK_MODEL`
- `GROQ_MAX_RETRIES`
- `GROQ_MAX_TOKENS`

## 3) Run the app

```bash
streamlit run app.py
```

## 4) User flow

1. Create an account with an email address and password.
2. Log in.
3. Enter either:
	- a GitHub PR URL, or
	- a repository in `owner/repo` format plus a PR number
4. Enter a GitHub token with repository read access and PR comment write access.
5. Run the review and inspect the result in the UI and on GitHub.

## 5) Bot runtime notes

- Node.js 18+ is required.
- The app auto-installs `bot/` dependencies the first time they are missing.
- The review bot still posts the final comment directly to GitHub.

## 6) Run the bot directly from terminal (optional)

```bash
cd bot
set GITHUB_REPOSITORY=owner/repo
set PR_NUMBER=123
set GITHUB_TOKEN=your_token
set LLM_PROVIDER=groq
set GROQ_API_KEY=your_backend_key
node index.js
```
