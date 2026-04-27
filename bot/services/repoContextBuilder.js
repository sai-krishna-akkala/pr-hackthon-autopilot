/**
 * repoContextBuilder.js
 * Builds compact repository-wide context related to changed files.
 */

const DEFAULT_MAX_CONTEXT_FILES = Number(process.env.MAX_CONTEXT_FILES || 10);
const DEFAULT_MAX_CONTEXT_CHARS = Number(process.env.MAX_CONTEXT_CHARS || 3500);

function normalizePath(path) {
  return (path || "").replace(/\\/g, "/");
}

function getDir(path) {
  const normalized = normalizePath(path);
  const idx = normalized.lastIndexOf("/");
  return idx >= 0 ? normalized.slice(0, idx) : "";
}

function getBaseName(path) {
  const normalized = normalizePath(path);
  const name = normalized.split("/").pop() || normalized;
  return name.replace(/\.[^.]+$/, "").toLowerCase();
}

function getExt(path) {
  const normalized = normalizePath(path);
  const idx = normalized.lastIndexOf(".");
  return idx >= 0 ? normalized.slice(idx).toLowerCase() : "";
}

function isLikelyTextFile(path) {
  const ext = getExt(path);
  const textExts = new Set([
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yml", ".yaml", ".toml", ".ini",
    ".md", ".txt", ".sql", ".html", ".css", ".scss", ".sh", ".env", ".xml",
  ]);
  return textExts.has(ext) || ["Dockerfile", "Makefile"].includes(path.split("/").pop() || "");
}

function trimContent(content, maxChars) {
  if (!content) return "";
  if (content.length <= maxChars) return content;
  return `${content.slice(0, maxChars)}\n\n... [truncated]`;
}

function pickCandidatePaths(changedFiles, repoTree) {
  const treeFiles = repoTree
    .filter((n) => n.type === "blob")
    .map((n) => normalizePath(n.path))
    .filter(isLikelyTextFile);

  const changedPaths = changedFiles.map((f) => normalizePath(f.filename));
  const changedSet = new Set(changedPaths);
  const candidates = [];
  const seen = new Set();

  const add = (path) => {
    if (!path || seen.has(path) || changedSet.has(path)) return;
    seen.add(path);
    candidates.push(path);
  };

  // 1) High-signal root docs/config
  const rootHints = [
    "README.md", "requirements.txt", "package.json", "pyproject.toml", "setup.py", "Dockerfile",
    ".github/workflows/pr-review.yml",
  ];
  rootHints.forEach(add);

  // 2) For each changed file: same-directory siblings + likely tests/config
  for (const changed of changedPaths) {
    const dir = getDir(changed);
    const base = getBaseName(changed);
    const ext = getExt(changed);

    const siblings = treeFiles.filter((p) => getDir(p) === dir && p !== changed);
    siblings
      .filter((p) => getExt(p) === ext)
      .slice(0, 3)
      .forEach(add);

    siblings
      .filter((p) => {
        const n = p.toLowerCase();
        return n.includes(base) || n.includes("test") || n.includes("config") || n.includes("settings");
      })
      .slice(0, 3)
      .forEach(add);
  }

  // 3) Cross-directory tests/modules by basename similarity
  for (const changed of changedPaths) {
    const base = getBaseName(changed);
    treeFiles
      .filter((p) => {
        const low = p.toLowerCase();
        return low.includes(base) || low.includes(`/test_${base}`) || low.includes(`/${base}_test`);
      })
      .slice(0, 3)
      .forEach(add);
  }

  return candidates;
}

export async function buildRepoContext(gh, files, ref) {
  const maxFiles = Math.max(1, DEFAULT_MAX_CONTEXT_FILES);
  const maxChars = Math.max(500, DEFAULT_MAX_CONTEXT_CHARS);

  let repoTree = [];
  try {
    repoTree = await gh.getRepoTree(ref);
  } catch (err) {
    return {
      files: [],
      text: "(repository context unavailable)",
      error: err?.message || "unknown error",
    };
  }

  const candidates = pickCandidatePaths(files, repoTree).slice(0, maxFiles);
  const chunks = [];
  const included = [];

  for (const path of candidates) {
    try {
      const content = await gh.getFileContent(path, ref);
      if (!content || !content.trim()) continue;
      included.push(path);
      chunks.push(`### ${path}\n\n\`\`\`\n${trimContent(content, maxChars)}\n\`\`\``);
    } catch {
      continue;
    }
  }

  return {
    files: included,
    text: chunks.length ? chunks.join("\n\n") : "(no additional related context found)",
  };
}
