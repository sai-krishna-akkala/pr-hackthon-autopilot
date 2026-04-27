/**
 * orchestrator.js
 * Runs all three agents IN PARALLEL using Promise.all, then merges results.
 */

import { runSecurityAgent } from "../agents/securityAgent.js";
import { runPerformanceAgent } from "../agents/performanceAgent.js";
import { runCodeQualityAgent } from "../agents/codeQualityAgent.js";
import { buildRepoContext } from "../services/repoContextBuilder.js";
import {
  mergeRiskScores,
  getRiskLevel,
  getDecision,
  getOverallAssessment,
} from "../utils/riskEngine.js";

// ~4 chars per token; keep total well under Groq's 12 K TPM limit
const MAX_DIFF_CHARS = Number(process.env.MAX_DIFF_CHARS || 18000);

function buildFilesText(files) {
  let text = "";
  for (const f of files) {
    const block =
      `### ${f.filename}  (status: ${f.status}, +${f.additions}/-${f.deletions})\n` +
      "```diff\n" +
      (f.patch || "(binary or no patch)") +
      "\n```\n\n";
    if (text.length + block.length > MAX_DIFF_CHARS) {
      text += `\n... (${files.length - text.split("### ").length + 1} more files truncated to fit token limit)\n`;
      break;
    }
    text += block;
  }
  return text;
}

export async function orchestrate(prMeta, files, gh) {
  const filesText = buildFilesText(files);
  console.log("📚 Building related repository context …");
  const repoContext = await buildRepoContext(gh, files, prMeta.head?.sha);
  console.log(`   Context files included: ${repoContext.files.length}`);

  console.log("\n🤖 Launching 3 AI agents in parallel…");
  const [secResult, perfResult, qualResult] = await Promise.all([
    runSecurityAgent(filesText, repoContext.text),
    runPerformanceAgent(filesText, repoContext.text),
    runCodeQualityAgent(filesText, repoContext.text),
  ]);
  console.log("✅ All agents completed.\n");

  // Log individual scores
  console.log(
    `  Scores — Security: ${secResult.risk_score}  Performance: ${perfResult.risk_score}  Quality: ${qualResult.risk_score}`
  );

  // Merge
  const finalScore = mergeRiskScores([secResult, perfResult, qualResult]);
  const riskLevel = getRiskLevel(finalScore);
  const decision = getDecision(finalScore);
  const overallAssessment = getOverallAssessment(finalScore);

  // Collect all issues from all agents
  const allIssues = [
    ...(secResult.issues || []).map((i) => ({ ...i, agent: "Security" })),
    ...(perfResult.issues || []).map((i) => ({ ...i, agent: "Performance" })),
    ...(qualResult.issues || []).map((i) => ({ ...i, agent: "Code Quality" })),
  ];

  return {
    pr_number: prMeta.number,
    pr_title: prMeta.title,
    risk_score: finalScore,
    risk_level: riskLevel,
    decision,
    overall_assessment: overallAssessment,
    agent_scores: {
      security: secResult.risk_score,
      performance: perfResult.risk_score,
      code_quality: qualResult.risk_score,
    },
    agent_summaries: {
      security: secResult.summary,
      performance: perfResult.summary,
      code_quality: qualResult.summary,
    },
    issues: allIssues,
    good_improvements: qualResult.good_improvements || [],
    bad_regressions: qualResult.bad_regressions || [],
    context_files_used: repoContext.files,
  };
}
