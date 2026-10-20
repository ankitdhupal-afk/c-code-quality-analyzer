/**
 * API client module for SCA Analyzer backend.
 */

export async function fetchHealth() {
  const res = await fetch("/api/health");
  return await res.json();
}

export async function fetchRules() {
  const res = await fetch("/api/rules");
  return await res.json();
}

export async function fetchExamples() {
  const res = await fetch("/api/examples");
  return await res.json();
}

export async function fetchExample(name) {
  const res = await fetch(`/api/examples/${encodeURIComponent(name)}`);
  return await res.json();
}

export async function analyzeCode(code, disabledRules = []) {
  const payload = { code, disabled_rules: disabledRules };
  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok && !data.ok) {
    throw new Error(data.error?.message || `HTTP ${res.status}`);
  }
  return data;
}

export async function fetchAst(code) {
  const res = await fetch("/api/ast", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  return await res.json();
}

export async function fetchCfg(code, funcName = "main") {
  const res = await fetch("/api/cfg", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, function: funcName }),
  });
  return await res.json();
}
