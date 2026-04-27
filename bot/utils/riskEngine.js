/**
 * riskEngine.js
 *
 * Risk score convention (HIGH SCORE = HIGH RISK):
 *   0  – 20  → None/Low   → Approve
 *   21 – 50  → Medium     → Needs Changes
 *   51 – 75  → High       → Needs Changes (block merge)
 *   76 – 100 → Critical   → Reject
 */

/**
 * Merge risk scores from multiple agents.
 * We take the MAX score (worst-case) then add a weighted average boost.
 */
export function mergeRiskScores(agentResults) {
  const scores = agentResults.map((r) => Number(r.risk_score) || 0);
  const maxScore = Math.max(...scores);
  const avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
  // Final = 60% max + 40% average (pessimistic merge)
  return Math.round(maxScore * 0.6 + avgScore * 0.4);
}

export function getRiskLevel(score) {
  if (score <= 20) return "Low";
  if (score <= 50) return "Medium";
  if (score <= 75) return "High";
  return "Critical";
}

export function getDecision(score) {
  if (score <= 20) return "Approve";
  if (score <= 75) return "Needs Changes";
  return "Reject";
}

export function getOverallAssessment(score) {
  if (score <= 20) return "Good Improvement";
  if (score <= 50) return "Mixed Change";
  if (score <= 75) return "Risky Change";
  return "Bad Change";
}

export function riskEmoji(level) {
  return { Low: "🟢", Medium: "🟡", High: "🟠", Critical: "🔴" }[level] ?? "⚪";
}

export function decisionBadge(decision) {
  return (
    { Approve: "✅ Approve", "Needs Changes": "⚠️ Needs Changes", Reject: "❌ Reject" }[
      decision
    ] ?? decision
  );
}
