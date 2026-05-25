<div align="center">

<br/>

```
██████╗ ██████╗      ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ 
██╔══██╗██╔══██╗    ██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
██████╔╝██████╔╝    ██║  ███╗██║   ██║███████║██████╔╝██║  ██║
██╔═══╝ ██╔══██╗    ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
██║     ██║  ██║    ╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
╚═╝     ╚═╝  ╚═╝     ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ 
```

# PR Autopilot · Multi-Agent PR Review System

**Instant. Intelligent. Uncompromising.**  
Three specialized AI agents that dissect every pull request — so you don't have to.

<br/>

[![JavaScript](https://img.shields.io/badge/Bot-JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)](https://nodejs.org)
[![Python](https://img.shields.io/badge/UI-Python%20%2F%20Streamlit-3776AB?style=flat-square&logo=python&logoColor=white)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Powered%20by-Groq-F55036?style=flat-square)](https://groq.com)
[![Claude](https://img.shields.io/badge/Compatible-Claude-CC785C?style=flat-square)](https://anthropic.com)
[![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)

</div>

---

## What Is This?

**PR Autopilot** is a multi-agent system that automatically reviews pull requests using three independent AI agents. Each agent has a focused mandate — code quality, runtime performance, and security — and together they produce an instant, structured verdict posted directly as a PR comment.

No more slow review cycles. No more missed vulnerabilities. Just fast, consistent, AI-powered analysis with a clear decision: ✅ **Accept**, 🔄 **Needs Changes**, or ❌ **Reject**.

---

## How It Works

```
                        ┌─────────────────────┐
                        │    Pull Request      │
                        │  (raised on GitHub)  │
                        └──────────┬──────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
           ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
           │  Code Quality │ │ Performance  │ │   Security   │
           │    Agent 🧹   │ │   Agent ⚡   │ │   Agent 🔒   │
           │              │ │              │ │              │
           │ • Readability │ │ • Complexity │ │ • Vuln scan  │
           │ • Best pract.│ │ • Memory use │ │ • Secrets    │
           │ • Test cov.  │ │ • DB queries │ │ • Injections │
           │ • Duplication│ │ • Caching    │ │ • Auth flows │
           └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                  │                │                 │
                  └────────────────┼─────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   Orchestrator       │
                        │  Aggregates Results  │
                        └──────────┬──────────┘
                                   │
                                   ▼
                   ┌───────────────────────────────┐
                   │  Verdict posted as PR Comment  │
                   │       ✅  /  🔄  /  ❌         │
                   └───────────────────────────────┘
```

---

## Why PR Autopilot?

### 🚀 Reviews Posted Directly on Your PR
The verdict doesn't live in a terminal — it gets posted as a structured comment on the pull request itself, right where your team already works.

### 🧠 Three Specialized Agents, One Clear Verdict
Rather than a single model juggling everything, each agent owns its domain completely. The code quality agent thinks like a lead engineer. The performance agent thinks like an SRE. The security agent thinks like a penetration tester. Together they cover what no single reviewer reliably catches.

### 🖥️ Local Streamlit UI for Instant Testing
Run reviews on any PR from a browser-based UI — no CLI required. Fill in your repo, PR number, and API keys, hit **Run Bot**, and watch the live output stream in real time.

### 🔁 GitHub Actions Ready Out of the Box
Drop the included workflow into `.github/workflows/` and every new PR triggers an automatic review. No manual steps, no extra tooling.

### 🔌 Groq by Default, Claude When You Need Depth
Built around Groq for blazing-fast inference in CI pipelines. Switch to Claude for more nuanced reasoning on complex security logic — one config change, no code modifications needed.

### 🛡️ Catches What Human Reviews Miss
Hardcoded secrets, SQL injection patterns, N+1 query bugs, dead code, missing tests — the kind of issues that slip through review fatigue. PR Autopilot is consistent, thorough, and doesn't have off days.

### 🧪 Sample Code Included for Immediate Validation
The `src/` directory ships with intentionally flawed Python code seeded with quality, performance, and security issues — so you can see the agents in action without touching your own codebase first.

---

## Agents

### 🧹 Code Quality Agent
Reviews the pull request for maintainability and engineering standards.

| Check | Description |
|-------|-------------|
| **Readability** | Naming conventions, comment quality, code clarity |
| **Best Practices** | Design patterns, SOLID principles, DRY violations |
| **Test Coverage** | Presence and quality of unit/integration tests |
| **Dead Code** | Unused variables, imports, and unreachable blocks |

---

### ⚡ Performance Agent
Flags bottlenecks and inefficiencies before they hit production.

| Check | Description |
|-------|-------------|
| **Algorithmic Complexity** | O(n²) patterns, nested loops, brute-force logic |
| **Memory Usage** | Leaks, large in-memory collections, redundant copies |
| **Database Queries** | N+1 problems, missing indexes, unoptimized joins |
| **Caching** | Opportunities for memoization or cache layers |

---

### 🔒 Security Agent
Scans for vulnerabilities and unsafe patterns.

| Check | Description |
|-------|-------------|
| **Vulnerability Scan** | Known CVEs, dependency risks |
| **Secrets Detection** | Hardcoded API keys, passwords, tokens |
| **Injection Risks** | SQL injection, XSS, command injection |
| **Auth & Access** | Broken auth patterns, privilege escalation |

---

## Sample Output

> *Paste your actual bot output here — the comment posted on the PR*

---

## LLM Providers

| Provider | Default Model | Best For |
|----------|--------------|----------|
| **Groq** *(default)* | `llama3-70b-8192` | Fastest inference, great for CI pipelines |
| **Anthropic Claude** | `claude-sonnet-4-5` | Deep reasoning, nuanced security analysis |

---

## Project Structure

```
pr-hackthon-autopilot/
├── .github/
│   └── workflows/          # GitHub Actions — auto-triggers bot on new PRs
│
├── bot/                    # JavaScript multi-agent review bot
│   └── index.js            # Orchestrator + three agents
│
├── src/                    # Sample Python code used for testing agents
│
├── tests/                  # Sample tests for the src/ code
│
├── app.py                  # Streamlit UI — run and visualize reviews locally
└── requirements.txt
```

---

## Roadmap

- [ ] Support for GitLab and Bitbucket PRs
- [ ] Per-agent severity scoring
- [ ] Web dashboard for review history across repos
- [ ] Custom agent plugins via config file
- [ ] Slack / Teams notifications on verdict

---

## Contributing

Contributions are welcome. To add a new agent, extend the bot in `bot/index.js` following the existing agent pattern and register it in the orchestrator. Please open an issue before submitting large changes.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with [Groq](https://groq.com) · Compatible with [Claude](https://anthropic.com) · Made for engineers who ship fast

</div>
