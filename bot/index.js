/**
 * index.js – Main entry point for the AI Multi-Agent PR Review Bot.
 *
 * Required env vars:
 *   GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER
 *   + GROQ_API_KEY (default) or ANTHROPIC_API_KEY (set LLM_PROVIDER=claude)
 */

import { GitHubClient } from "./services/githubClient.js";
import { orchestrate } from "./agents/orchestrator.js";
import { formatSummaryComment } from "./utils/formatter.js";

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    console.error(`❌ Missing required environment variable: ${name}`);
    process.exit(1);
  }
  return value;
}

async function main() {
  console.log("🚀 AI Multi-Agent PR Review Bot starting…\n");

  // ── Validate env ──────────────────────────────────────────────────────────
  const token = requireEnv("GITHUB_TOKEN");
  const repo = requireEnv("GITHUB_REPOSITORY");
  const prNumber = parseInt(requireEnv("PR_NUMBER"), 10);
  if (isNaN(prNumber)) {
    console.error("❌ PR_NUMBER must be an integer.");
    process.exit(1);
  }

  const provider = (process.env.LLM_PROVIDER || "groq").toLowerCase();
  if (provider === "claude") requireEnv("ANTHROPIC_API_KEY");
  else requireEnv("GROQ_API_KEY");

  // ── GitHub client ─────────────────────────────────────────────────────────
  const gh = new GitHubClient(token, repo);

  // ── Fetch PR data ─────────────────────────────────────────────────────────
  console.log(`📦 Fetching PR #${prNumber} from ${repo}…`);
  const [prMeta, files] = await Promise.all([
    gh.getPRMetadata(prNumber),
    gh.getPRFiles(prNumber),
  ]);
  console.log(`   PR: "${prMeta.title}" by ${prMeta.user?.login}`);
  console.log(`   Changed files: ${files.length}\n`);

  // ── Run agents ────────────────────────────────────────────────────────────
  const review = await orchestrate(prMeta, files, gh);

  // ── Log results ───────────────────────────────────────────────────────────
  console.log("═══════════════════════════════════════════");
  console.log(`  FINAL RISK SCORE : ${review.risk_score} / 100`);
  console.log(`  RISK LEVEL       : ${review.risk_level}`);
  console.log(`  DECISION         : ${review.decision}`);
  console.log(`  TOTAL ISSUES     : ${review.issues.length}`);
  console.log("═══════════════════════════════════════════\n");

  // ── Post comment ──────────────────────────────────────────────────────────
  const comment = formatSummaryComment(review, repo);
  console.log("💬 Posting review comment to GitHub…");
  await gh.postComment(prNumber, comment);
  console.log("✅ Review posted successfully!\n");

  // ── Post inline comments (High/Critical issues only) ──────────────────────
  const inlineIssues = review.issues
    .filter((i) => i.severity === "High" && i.file && i.line)
    .slice(0, 20); // GitHub caps at 20 per review

  if (inlineIssues.length > 0) {
    console.log(`📌 Posting ${inlineIssues.length} inline comments…`);
    try {
      const inlineComments = inlineIssues.map((i) => ({
        path: i.file,
        line: i.line,
        body:
          `**🔴 ${i.severity} [${i.agent} Agent]** — ${i.issue}\n\n` +
          `**Risk:** ${i.risk}\n\n**Fix:** ${i.suggestion}` +
          (i.suggested_code ? `\n\`\`\`suggestion\n${i.suggested_code}\n\`\`\`` : ""),
      }));
      await gh.postReview(
        prNumber,
        prMeta.head.sha,
        inlineComments,
        `Multi-agent review complete. Risk Score: ${review.risk_score}/100 — ${review.risk_level}`
      );
      console.log("✅ Inline comments posted.");
    } catch (err) {
      console.warn("⚠️ Inline comments failed (non-fatal):", err.message);
    }
  }

  console.log("\n🎉 Done!");
}

main().catch((err) => {
  console.error("💥 Fatal error:", err);
  process.exit(1);
});
