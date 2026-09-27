const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        detail = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(detail);
  }

  return response.json();
}

export function getCases() {
  return request("/api/cases");
}

export function getCase(caseId) {
  return request(`/api/cases/${encodeURIComponent(caseId)}`);
}

export function getCaseNetwork(caseId) {
  return request(
    `/api/cases/${encodeURIComponent(caseId)}/network`
  );
}

export function getEntity(entityId) {
  return request(
    `/api/entities/${encodeURIComponent(entityId)}`
  );
}

export function createCase(payload) {
  return request("/api/cases", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function uploadCaseFile(caseId, sourceType, file) {
  const formData = new FormData();

  formData.append("source_type", sourceType);
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/api/cases/${encodeURIComponent(caseId)}/ingest`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    let detail = `Upload failed with status ${response.status}`;

    try {
      const errorData = await response.json();

      if (typeof errorData.detail === "string") {
        detail = errorData.detail;
      }
    } catch {
      // Keep the default error message.
    }

    throw new Error(detail);
  }

  return response.json();
}