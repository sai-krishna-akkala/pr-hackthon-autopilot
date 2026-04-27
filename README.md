# PR Review Repo (Standalone)

This repository is now self-contained for:

- code changes + tests
- multi-agent AI PR review bot (`bot/`)
- local Streamlit runner UI (`app.py`)

No `AI-Alert-System` folder is required for this flow.

## Repo Structure

- `src/` – sample Python code under review
- `tests/` – sample tests
- `bot/` – JavaScript multi-agent PR review bot
- `app.py` – local Streamlit UI to run the bot and see output

## 1) Python setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

## 2) Bot setup

```bash
cd bot
npm install
cd ..
```

## 3) Run Streamlit app (recommended)

```bash
streamlit run app.py
```

In the UI, fill:

- `GITHUB_REPOSITORY` (example: `owner/repo`)
- `PR_NUMBER`
- `GITHUB_TOKEN`
- `GROQ_API_KEY` (or choose `claude` + `ANTHROPIC_API_KEY`)

Then click **Run Bot** to see stdout/stderr/combined logs and post results to your PR.

## 4) Run bot directly from terminal (optional)

```bash
cd bot
set GITHUB_REPOSITORY=owner/repo
set PR_NUMBER=123
set GITHUB_TOKEN=your_token
set LLM_PROVIDER=groq
set GROQ_API_KEY=your_key
node index.js
```

## 5) Git workflow

```bash
git checkout -b feature/ai-review-improvements
git add -A
git commit -m "add standalone PR review bot workflow"
git push -u origin feature/ai-review-improvements
```

Create PR on GitHub and check PR comments + Actions logs.
