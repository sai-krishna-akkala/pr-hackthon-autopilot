/**
 * llmClient.js – Groq / Anthropic caller shared by all agents.
 */

const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const CLAUDE_URL = "https://api.anthropic.com/v1/messages";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseRetryAfterMs(headers, errorText) {
  const headerVal = headers.get("retry-after");
  if (headerVal) {
    const seconds = Number(headerVal);
    if (!Number.isNaN(seconds) && seconds > 0) return Math.ceil(seconds * 1000);
  }

  const msg = (errorText || "").toLowerCase();
  const match = msg.match(/try again in\s+([\d.]+)s/);
  if (match) {
    const seconds = Number(match[1]);
    if (!Number.isNaN(seconds) && seconds > 0) return Math.ceil(seconds * 1000);
  }

  return null;
}

function cleanJSON(text) {
  const cleaned = text.replace(/^```(?:json)?\s*/m, "").replace(/\s*```\s*$/m, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    // Try extracting first JSON object
    const match = cleaned.match(/\{[\s\S]*\}/);
    if (match) return JSON.parse(match[0]);
    throw new Error("LLM did not return valid JSON:\n" + text.slice(0, 300));
  }
}

export async function callLLM(systemPrompt, userMessage) {
  const provider = (process.env.LLM_PROVIDER || "groq").toLowerCase();

  if (provider === "claude") {
    const res = await fetch(CLAUDE_URL, {
      method: "POST",
      headers: {
        "x-api-key": process.env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: process.env.CLAUDE_MODEL || "claude-3-5-haiku-20241022",
        max_tokens: 4096,
        system: systemPrompt,
        messages: [{ role: "user", content: userMessage }],
      }),
    });
    if (!res.ok) throw new Error(`Claude error ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return cleanJSON(data.content[0].text);
  }

  // Default: Groq (free tier, fast)
  const primaryModel = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";
  const fallbackModel = process.env.GROQ_FALLBACK_MODEL || "llama-3.1-8b-instant";
  const modelsToTry = Array.from(new Set([primaryModel, fallbackModel]));
  const maxRetries = Number(process.env.GROQ_MAX_RETRIES || 4);
  const maxTokens = Number(process.env.GROQ_MAX_TOKENS || 1400);

  let lastError = null;

  for (const model of modelsToTry) {
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      const res = await fetch(GROQ_URL, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${process.env.GROQ_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userMessage },
          ],
          temperature: 0.2,
          max_tokens: maxTokens,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        return cleanJSON(data.choices[0].message.content);
      }

      const errorText = await res.text();
      const isRateLimit = res.status === 429;

      const isPayloadTooLarge = res.status === 413;
      if (!isRateLimit && !isPayloadTooLarge) {
        throw new Error(`Groq error ${res.status}: ${errorText}`);
      }

      // For 413 (too large), skip retries and try fallback model immediately
      if (isPayloadTooLarge) {
        console.warn(`[Groq] Request too large for model=${model}. Trying next model…`);
        lastError = new Error(`Groq error ${res.status}: ${errorText}`);
        break;
      }

      lastError = new Error(`Groq error ${res.status}: ${errorText}`);

      if (attempt >= maxRetries) {
        break;
      }

      const hintedWait = parseRetryAfterMs(res.headers, errorText);
      const backoffMs = Math.min(60000, 1500 * 2 ** attempt);
      const jitterMs = Math.floor(Math.random() * 750);
      const waitMs = Math.max(hintedWait || 0, backoffMs + jitterMs);

      console.warn(
        `[Groq] Rate limited on model=${model}. Retrying in ${Math.ceil(waitMs / 1000)}s (attempt ${attempt + 1}/${maxRetries})...`
      );
      await sleep(waitMs);
    }

    console.warn(`[Groq] Switching model fallback from ${model} to next candidate...`);
  }

  throw lastError || new Error("Groq request failed after retries.");
}
