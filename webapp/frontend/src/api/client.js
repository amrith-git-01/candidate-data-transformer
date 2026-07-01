const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),

  generateSample: (count, seed) =>
    request("/sample/generate", {
      method: "POST",
      body: JSON.stringify({ count, seed }),
    }),

  getSourcePage: (source, page, pageSize) =>
    request(`/sample/${source}?page=${page}&page_size=${pageSize}`),

  listConfigs: () => request("/configs"),

  getConfig: (name) => request(`/configs/${name}`),

  runPipeline: (config, enrichGithub) =>
    request("/run", {
      method: "POST",
      body: JSON.stringify({ config, enrich_github: enrichGithub }),
    }),

  getResults: (page, pageSize) =>
    request(`/run/results?page=${page}&page_size=${pageSize}`),
};
