/**
 * githubClient.js – Thin wrapper around GitHub REST API.
 */

const BASE = "https://api.github.com";

export class GitHubClient {
  constructor(token, repo) {
    this.token = token;
    this.repo = repo; // "owner/repo"
  }

  _headers() {
    return {
      Authorization: `Bearer ${this.token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
    };
  }

  async _get(path) {
    const res = await fetch(`${BASE}${path}`, { headers: this._headers() });
    if (!res.ok) throw new Error(`GitHub GET ${path} → ${res.status}: ${await res.text()}`);
    return res.json();
  }

  async _post(path, body) {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`GitHub POST ${path} → ${res.status}: ${await res.text()}`);
    return res.json();
  }

  async _getRaw(path) {
    const res = await fetch(`${BASE}${path}`, { headers: this._headers() });
    if (!res.ok) throw new Error(`GitHub GET ${path} → ${res.status}: ${await res.text()}`);
    return res;
  }

  /** Fetch PR metadata */
  async getPRMetadata(prNumber) {
    return this._get(`/repos/${this.repo}/pulls/${prNumber}`);
  }

  /** Fetch all changed files + patches */
  async getPRFiles(prNumber) {
    return this._get(`/repos/${this.repo}/pulls/${prNumber}/files`);
  }

  /** Fetch repository tree for a ref (sha/branch), recursively. */
  async getRepoTree(ref) {
    const data = await this._get(`/repos/${this.repo}/git/trees/${ref}?recursive=1`);
    return data.tree || [];
  }

  /** Fetch text file content at a specific ref. Returns null for binary/non-text. */
  async getFileContent(path, ref) {
    const encodedPath = path
      .split("/")
      .map((part) => encodeURIComponent(part))
      .join("/");

    const res = await this._getRaw(`/repos/${this.repo}/contents/${encodedPath}?ref=${encodeURIComponent(ref)}`);
    const data = await res.json();

    if (!data || data.type !== "file") return null;
    if (data.encoding === "base64" && typeof data.content === "string") {
      try {
        const raw = Buffer.from(data.content, "base64").toString("utf8");
        return raw;
      } catch {
        return null;
      }
    }
    if (typeof data.content === "string") return data.content;
    return null;
  }

  /** Post a summary comment on the PR */
  async postComment(prNumber, body) {
    return this._post(`/repos/${this.repo}/issues/${prNumber}/comments`, { body });
  }

  /** Post inline review comments */
  async postReview(prNumber, commitSha, comments, body, event = "COMMENT") {
    return this._post(`/repos/${this.repo}/pulls/${prNumber}/reviews`, {
      commit_id: commitSha,
      body,
      event,
      comments,
    });
  }
}
